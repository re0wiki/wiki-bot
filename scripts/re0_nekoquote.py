"""NekoQuote 语录增量同步：中文 wiki 服务器 FBK 转发频道 → 月表全链更新。

数据流：Discord API 拉频道新消息（bot token，水位线增量）→ nekoquote.parse
解析（FBK 组件布局/RT 剥除/机翻段切除）→ 新推入 logs/nekoquote/tweets.json
（src=dc_zh_fbk）→ nekoquote.chain 全链（翻译→归一→构建→校验→部署）→
推进水位线。

- token 读 secrets.json 的 discord_bot_token（gitignored，bot 账号读频道合规；勿用用户 token）；
  文件缺失则任务跳过（退出码 0，不阻塞其他循环任务）
- 本地基线缺失时自动从 wiki 重建（nekoquote.bootstrap）——新 clone 开箱即用
- 幂等：推 id 级去重；水位线在全链成功后才推进
- EN 频道同为 FBK 转发、无独立兜底；FBK/nitter 单点故障时任务自然无新增
"""

import json
import sys
from pathlib import Path

import requests

import pywikibot as pwb

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nekoquote import bootstrap
from nekoquote.chain import run_chain
from nekoquote.parse import extract

CHANNEL_ID = "1293525355663196243"  # 中文服务器 FBK 转发频道
STATE = ROOT / "logs/nekoquote/sync_state.json"


def api(path: str, token: str) -> list:
    resp = requests.get(
        f"https://discord.com/api/v10{path}",
        headers={"Authorization": f"Bot {token}", "User-Agent": "wiki-bot"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


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
    token_file = ROOT / "secrets.json"
    if not token_file.exists():
        pwb.info("无 secrets.json，语录同步任务跳过")
        return
    token = json.loads(token_file.read_text(encoding="utf-8"))[
        "discord_bot_token"
    ].strip()

    if bootstrap.needed():
        pwb.info("本地语录基线缺失，从 wiki 重建…")
        bootstrap.run()
        # 基线已含全部既有推，水位线直接设为最新频道消息（不吃存量）
        latest = api(f"/channels/{CHANNEL_ID}/messages?limit=1", token)
        if latest:
            STATE.write_text(json.dumps({"last_id": latest[0]["id"]}), encoding="utf-8")

    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    msgs = fetch_new(token, state.get("last_id"))
    if not msgs:
        pwb.info("无新消息")
        return
    newest = max(m["id"] for m in msgs)
    pwb.info(f"新消息 {len(msgs)} 条")

    found = extract(msgs)
    tw_path = ROOT / "logs/nekoquote/tweets.json"
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

    run_chain()  # 任一失败非零退出，水位线不推进下轮重试
    STATE.write_text(json.dumps({"last_id": newest}), encoding="utf-8")
    pwb.info("语录同步全链完成 ✓")


if __name__ == "__main__":
    main()
