"""NekoQuote 语录增量同步：中文 wiki 服务器 FBK 转发频道 → 月表全链更新。

数据流：Discord API 拉频道新消息（bot token，水位线增量）→ 复用
logs/p8_discord_merge.py 的 extract 解析（FBK 组件布局/RT 剥除/机翻段切除）
→ 新推入 logs/p8_tweets.json（src=dc_zh_fbk）→ 翻译→归一→构建→校验→部署
（复用增量管线各阶段脚本）→ 推进水位线。

- token 读 discord-bot-token.txt（gitignored，bot 账号读频道合规；勿用用户 token）
- 幂等：推 id 级去重，无新推即静默退出；水位线在全链成功后才推进
- EN 频道同为 FBK 转发、无独立兜底；FBK/nitter 单点故障时任务自然无新增
"""

import importlib.util
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

import pywikibot as pwb

ROOT = Path(__file__).resolve().parent.parent
CHANNEL_ID = "1293525355663196243"  # 中文服务器 FBK 转发频道
STATE = ROOT / "logs/nekoquote_sync.json"
PY = sys.executable

_spec = importlib.util.spec_from_file_location(
    "p8_discord_merge", ROOT / "logs/p8_discord_merge.py"
)
assert _spec and _spec.loader
_merge = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_merge)
extract = _merge.extract


def api(path: str, token: str) -> list:
    req = urllib.request.Request(
        f"https://discord.com/api/v10{path}",
        headers={"Authorization": f"Bot {token}", "User-Agent": "wiki-bot"},
    )
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def fetch_new(token: str, after: str | None) -> list[dict]:
    """水位线后全量新消息（雪花 id 即时间序，翻页直到没有更多）。"""
    msgs = []
    while True:
        q = f"?limit=100{'&after=' + after if after else ''}"
        batch = api(f"/channels/{CHANNEL_ID}/messages{q}", token)
        if not batch:
            break
        msgs.extend(batch)
        after = max(m["id"] for m in batch)
        if len(batch) < 100:
            break
    return msgs


def main() -> None:
    pwb.handle_args()  # 吞掉 pwb 全局参数（-always 等）
    token = (ROOT / "discord-bot-token.txt").read_text(encoding="utf-8").strip()
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}

    msgs = fetch_new(token, state.get("last_id"))
    if not msgs:
        pwb.info("无新消息")
        return
    newest = max(m["id"] for m in msgs)
    pwb.info(f"新消息 {len(msgs)} 条")

    found = extract(msgs)
    tw_path = ROOT / "logs/p8_tweets.json"
    tw = json.loads(tw_path.read_text(encoding="utf-8"))
    new = {t: x for t, x in found.items() if t not in tw}
    if not new:
        pwb.info("无库外新推")
        STATE.write_text(json.dumps({"last_id": newest}), encoding="utf-8")
        return
    pwb.info(f"库外新推 {len(new)} 条")
    for tid, text in new.items():
        tw[tid] = {"text": text, "author": "nezumiironyanko", "src": "dc_zh_fbk"}
    tw_path.write_text(json.dumps(tw, ensure_ascii=False), encoding="utf-8")

    # 全链：翻译 → 归一 → 构建 → 校验 → 部署（任一失败非零退出，水位线不推进下轮重试）
    for s in (
        "p8_translate.py",
        "p8_normalize.py",
        "p8_build.py",
        "p8_verify_rt.py",
        "p8_deploy3.py",
    ):
        r = subprocess.run(
            [PY, str(ROOT / "logs" / s)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        print((r.stdout or "")[-400:])
        if r.returncode != 0:
            print(r.stderr[-800:])
            raise SystemExit(f"{s} 失败")

    import shutil

    live = ROOT / "logs/p8/lua_live"
    shutil.rmtree(live, ignore_errors=True)
    shutil.copytree(ROOT / "logs/p8/lua", live)
    STATE.write_text(json.dumps({"last_id": newest}), encoding="utf-8")
    pwb.info("语录同步全链完成 ✓")


if __name__ == "__main__":
    main()
