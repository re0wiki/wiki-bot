"""图片差量同步（en → zh，只增不删）。

2026-08-13 重写：原实现两侧全量 FilePage + calc_diff 里 latest_file_info
逐页懒加载（history=True，每张共有图两侧各 1-2 次请求，总计 ~2N 次）。
现改为：两侧 list=allimages&aiprop=timestamp 各 500/批（时间戳随列表同批
返回，列表上限匿名即 500，不依赖登录——Fandom 会话不稳定，见 AGENTS.md
坑节），内存比对差量；缺失或过时才下载/上传（差量通常很小）。
"""

from os import path
from tempfile import TemporaryDirectory

from tqdm import tqdm

import pywikibot as pwb
import pywikibot.config


def list_images(site) -> dict[str, str]:
    """{图片名（无命名空间前缀）: 最新版本时间戳}（时间戳随列表同批返回）。

    以 name 为键：en/zh 的 File 命名空间本地化名不同（File:/文件:），
    跨站比对必须避开标题形式。
    """
    out = {}
    cont = {}
    while True:
        data = site.simple_request(
            action="query",
            list="allimages",
            aiprop="timestamp",
            ailimit="max",
            formatversion="2",
            format="json",
            **cont,
        ).submit()
        for img in data["query"]["allimages"]:
            out[img["name"]] = img["timestamp"]
        if "continue" not in data:
            break
        cont = data["continue"]
    return out


def calc_diff(en: dict[str, str], zh: dict[str, str]) -> list[str]:
    """en 的图片中，zh 缺失或过时的标题（ISO 时间戳字典序即时间序）。

    只增不删：en 侧删除/改名的图片不会在 zh 侧清理——残留无害，删除还要
    同步更新引用，不值得（2026-07-31 已决策维持，见 docs/todo.md）。
    """
    return [t for t, ts in en.items() if (zts := zh.get(t)) is None or zts < ts]


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
    diff_titles = calc_diff(en_images, zh_images)
    if pwb.config.simulate:
        # 干跑连下载都跳过（下载同样打 en 站），只报告差量
        pwb.logging.info(
            "SIMULATE: %d images to sync, skip download/upload.", len(diff_titles)
        )
        for title in diff_titles[:20]:
            pwb.logging.info("SIMULATE: would sync %s", title)
        if len(diff_titles) > 20:
            pwb.logging.info("SIMULATE: ... and %d more.", len(diff_titles) - 20)
        return
    diff = [pwb.FilePage(en, f"File:{title}") for title in diff_titles]
    with TemporaryDirectory() as tmp_dir:
        download_all(diff, tmp_dir)
        upload_all(diff, tmp_dir)


if __name__ == "__main__":
    main()
