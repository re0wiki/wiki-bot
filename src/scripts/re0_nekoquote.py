"""NekoQuote 语录增量同步：FxTwitter v2 时间线 → 月表全链更新。

数据流：FxTwitter v2 拉长月原创（含 Note Tweet 长文，RT 剥除）→ 新推入
tweets.json（src=fxtwitter_v2）→ nekoquote.chain 全链（翻译→归一→构建→校验→部署）
→ 推进原创边界。

- 无 Discord token 依赖；公共实例失败时非零退出，不推进边界
- 本地基线缺失时自动从 wiki 重建（nekoquote.bootstrap）——新 clone 开箱即用
- 幂等：推 id 级去重；原创边界在全链成功后才推进
- FBK 旧状态首次迁移时回扫到其启用日期，补收其漏转内容
"""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import requests

import pywikibot as pwb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.nekoquote import DATA, bootstrap
from src.nekoquote.chain import run_chain
from src.nekoquote.fxtwitter import fetch_quotes, latest_original_id
from src.nekoquote.state import (
    PENDING,
    clear_pending,
    mark_pending,
    state_lock,
    write_json,
)

SOURCE = "fxtwitter_v2"
MIGRATION_SINCE = int(datetime(2026, 8, 18, tzinfo=UTC).timestamp())
STATE = DATA / "sync_state.json"


def _ensure_baseline(session) -> None:
    """本地基线缺失时重建；状态缺失时播种到最新原创，不吃存量。"""
    if bootstrap.needed():
        pwb.info("本地语录基线缺失，从 wiki 重建…")
        bootstrap.run()
    if not STATE.exists():
        write_json(
            STATE,
            {"source": SOURCE, "last_original_id": latest_original_id(session)},
        )


def _store_new_quotes(found: dict) -> bool:
    """入库库外新推；返回是否有新增。待完成标记先于数据落盘。"""
    tw_path = DATA / "tweets.json"
    tw = json.loads(tw_path.read_text(encoding="utf-8"))
    new = {t: x for t, x in found.items() if t not in tw}
    if not new:
        return False
    pwb.info(f"库外新推 {len(new)} 条")
    # 先落待完成标记再入库：任何后续失败都会在下一轮续跑，不会被当成已完成。
    mark_pending(PENDING)
    for tid, text in new.items():
        tw[tid] = {"text": text, "author": "nezumiironyanko", "src": SOURCE}
    write_json(tw_path, tw)
    return True


def _next_state(state: dict, newest: str | None) -> dict:
    previous = state.get("last_original_id") if state.get("source") == SOURCE else None
    if newest and (not previous or int(newest) > int(previous)):
        previous = newest
    return {"source": SOURCE, "last_original_id": previous}


def _main() -> None:
    pwb.handle_args()  # 吞掉 pwb 全局参数（-always 等）
    session = requests.Session()
    session.headers.update({"User-Agent": "wiki-bot"})

    _ensure_baseline(session)
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    previous = state.get("last_original_id") if state.get("source") == SOURCE else None
    found, newest = fetch_quotes(
        session,
        stop_id=previous,
        stop_before=None if previous else MIGRATION_SINCE,
    )
    next_state = _next_state(state, newest)
    new = _store_new_quotes(found)
    if not new and not PENDING.exists():
        pwb.info("无库外新推")
        write_json(STATE, next_state)
        return
    if not new:
        pwb.info("上次语录全链未完成，续跑")

    run_chain()  # 任一失败非零退出，原创边界不推进下轮重试
    clear_pending(PENDING)
    write_json(STATE, next_state)
    pwb.info("语录同步全链完成 ✓")


def main() -> None:
    with state_lock(DATA):
        _main()


if __name__ == "__main__":
    main()
