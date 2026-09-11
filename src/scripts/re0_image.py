"""图片差量同步（en → zh，只增不删）。

2026-08-13 重写：原实现两侧全量 FilePage + calc_diff 里 latest_file_info
逐页懒加载（history=True，每张共有图两侧各 1-2 次请求，总计 ~2N 次）。
现改为：两侧 list=allimages&aiprop=timestamp 各 500/批（时间戳随列表同批
返回，列表上限匿名即 500，不依赖登录——Fandom 会话不稳定，见 AGENTS.md
坑节），内存比对差量；缺失或过时才下载/上传（差量通常很小）。

2026-09-11：aiprop 加 mime。mime=video/youtube 的不是真实文件，是 Fandom
从 YouTube 导入的外部视频（无扩展名的伪文件：FilePage 构造直接 ValueError，
「下载」只能拿到缩略图）。按名称差量改用站内端点
wikia.php?controller=Fandom\\Video\\IngestionController&method=uploadVideo
从 YouTube 重新导入（videoId 取自 en 侧 imageinfo metadata；该端点即
Special:NewFiles「添加视频」按钮的前端调用，是 Nirvana 内部接口，不走
api.php 上传）。创建的文件页标题与正文自动取自 YouTube 当前值。
视频标题保持 en 侧原名（外语原文），不做译名归一——re0_move 对 File
空间无有效扩展名的标题有硬性跳过。
"""

import time
from os import path
from tempfile import TemporaryDirectory
from urllib.parse import urlencode

from tqdm import tqdm

import pywikibot as pwb
import pywikibot.config
from pywikibot.comms import http

YOUTUBE_MIME = "video/youtube"


def list_images(site) -> dict[str, dict[str, str]]:
    """{图片名（无命名空间前缀）: {"ts": 最新版本时间戳, "mime": MIME 类型}}。

    时间戳与 mime 随列表同批返回。以 name 为键：en/zh 的 File 命名空间
    本地化名不同（File:/文件:），跨站比对必须避开标题形式。
    """
    out = {}
    cont = {}
    while True:
        data = site.simple_request(
            action="query",
            list="allimages",
            aiprop="timestamp|mime",
            ailimit="max",
            formatversion="2",
            format="json",
            **cont,
        ).submit()
        for img in data["query"]["allimages"]:
            out[img["name"]] = {"ts": img["timestamp"], "mime": img["mime"]}
        if "continue" not in data:
            break
        cont = data["continue"]
    return out


def calc_diff(
    en: dict[str, dict[str, str]], zh: dict[str, dict[str, str]]
) -> tuple[list[str], list[str]]:
    """(普通文件差量, 视频差量)：en 有而 zh 缺失或过时的标题。

    普通文件比时间戳（ISO 字典序即时间序）；视频只补缺失——导入端点
    不能更新已有视频，且同一标题即同一 YouTube 视频。
    只增不删：en 侧删除/改名的图片不会在 zh 侧清理——残留无害，删除还要
    同步更新引用，不值得（2026-07-31 已决策维持，见 docs/todo.md）。
    """
    normal = [
        t
        for t, i in en.items()
        if i["mime"] != YOUTUBE_MIME and (t not in zh or zh[t]["ts"] < i["ts"])
    ]
    videos = [t for t, i in en.items() if i["mime"] == YOUTUBE_MIME and t not in zh]
    return normal, videos


def fetch_video_ids(site, titles: list[str]) -> dict[str, str]:
    """批量取 en 视频标题的 YouTube videoId（imageinfo metadata，匿名可读）。

    返回键为 API 规范化后的标题（下划线→空格），仅作日志标签。
    """
    out = {}
    for i in range(0, len(titles), 50):
        data = site.simple_request(
            action="query",
            titles="|".join(f"File:{t}" for t in titles[i : i + 50]),
            prop="imageinfo",
            iiprop="metadata",
            formatversion="2",
            format="json",
        ).submit()
        for page in data["query"]["pages"]:
            md = {
                m["name"]: m["value"] for m in page["imageinfo"][0].get("metadata", [])
            }
            out[page["title"].removeprefix("File:")] = md["videoId"]
    return out


def fresh_csrf(site) -> str:
    """裸取当前会话的 csrf token（不用 TokenWallet 缓存）。

    token 绑定会话；Fandom 跨站流量互踢后 pywikibot 自愈重登换新会话，
    TokenWallet 缓存不感知轮换会继续发旧 token（2026-09-11 实测：en 侧
    读图后 import 全批 400 "provide a valid edit token"）。simple_request
    的 api 请求内嵌 userinfo，会话已被作废时会先触发自愈重登，返回的
    就是新会话的 token。
    """
    return site.simple_request(
        action="query", meta="tokens", type="csrf", format="json"
    ).submit()["query"]["tokens"]["csrftoken"]


def import_videos(site, videos: dict[str, str]) -> None:
    """经 Fandom 视频导入端点把缺失视频从 YouTube 逐个导入 zh。

    单个失败记日志继续：未导入的标题留在下轮差量里自动重试，幂等。
    """
    site.login()
    assert site.user() == "IchiSanNi", f"unexpected user: {site.user()}"
    uri = (
        site.scriptpath()
        + "/wikia.php?"
        + urlencode(
            {"controller": r"Fandom\Video\IngestionController", "method": "uploadVideo"}
        )
    )
    token = fresh_csrf(site)
    ok = 0
    for title, video_id in tqdm(videos.items(), "Importing videos"):
        yt_url = f"https://www.youtube.com/watch?v={video_id}"
        for attempt in range(2):
            try:
                r = http.request(
                    site, uri, method="POST", data={"url": yt_url, "token": token}
                )
                result = r.json()
            except Exception as e:  # noqa: BLE001 - 单个失败不阻断整批，交由日志人工复查
                pwb.logging.error(e)
                break
            if result.get("success"):
                ok += 1
                break
            # token 类失败重取一次再试（会话可能刚被互踢轮换）
            if "edit token" in str(result.get("details")) and attempt == 0:
                token = fresh_csrf(site)
                continue
            pwb.logging.error("FAILED to import %s (%s): %s", title, video_id, result)
            break
        time.sleep(max(pwb.config.put_throttle, 2))
    pwb.logging.info("Imported %d/%d videos.", ok, len(videos))


def download_one(image: pwb.FilePage, tmp_dir: str) -> None:
    """从 en 下载一张图片文件到临时目录。"""
    filename = path.join(tmp_dir, image.title(with_ns=False, as_filename=True))
    try:
        image.download(filename)
    except Exception as e:  # noqa: BLE001 - 单张失败不阻断整批，交由日志人工复查
        pwb.logging.error(e)


def upload_one(image: pwb.FilePage, tmp_dir: str) -> None:
    """从临时目录上传一张图片文件到 zh。"""
    filename = path.join(tmp_dir, image.title(with_ns=False, as_filename=True))
    title = image.title()
    text = f"[[en:{title}]]"

    try:
        pwb.FilePage(pwb.Site("zh", "re0"), title).upload(
            filename,
            comment=text,
            text=text,
            report_success=False,
            ignore_warnings=True,
        )
    except Exception as e:  # noqa: BLE001 - 单张失败不阻断整批，交由日志人工复查
        pwb.logging.error(e)


def download_all(images: list[pwb.FilePage], tmp_dir: str):
    """从 en 匿名下载所有图片文件到临时目录（下载不需要登录）。"""
    for image in tqdm(images, "Downloading images"):
        download_one(image, tmp_dir)


def upload_all(images: list[pwb.FilePage], tmp_dir: str):
    """从临时目录上传所有图片文件到 zh。"""
    pwb.Site("zh", "re0").login()
    for image in tqdm(images, "Uploading images"):
        upload_one(image, tmp_dir)


def main() -> None:
    # 必须消费 -simulate/-always 等全局参数：config.simulate 只在 handle_args
    # 里设置，不调用则 main.py -s 干跑对本脚本无效，会真实上传。
    pwb.handle_args()
    en = pwb.Site("en", "re0")
    zh = pwb.Site("zh", "re0")
    en_images = list_images(en)
    zh_images = list_images(zh)
    diff_titles, video_titles = calc_diff(en_images, zh_images)
    if pwb.config.simulate:
        # 干跑连下载都跳过（下载同样打 en 站），只报告差量
        pwb.logging.info(
            "SIMULATE: %d images and %d videos to sync, skip download/upload/import.",
            len(diff_titles),
            len(video_titles),
        )
        for title in diff_titles[:20]:
            pwb.logging.info("SIMULATE: would sync %s", title)
        if len(diff_titles) > 20:
            pwb.logging.info("SIMULATE: ... and %d more.", len(diff_titles) - 20)
        for title in video_titles:
            pwb.logging.info("SIMULATE: would import video %s", title)
        return
    if diff_titles:
        diff = [pwb.FilePage(en, f"File:{title}") for title in diff_titles]
        with TemporaryDirectory() as tmp_dir:
            download_all(diff, tmp_dir)
            upload_all(diff, tmp_dir)
    if video_titles:
        import_videos(zh, fetch_video_ids(en, video_titles))


if __name__ == "__main__":
    main()
