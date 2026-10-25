"""手动增量合流：Discrub 导出目录 → 新推入库 → 全链。

用法：python -m src.nekoquote.merge [导出目录]（默认 Desktop\\tappei_tweets）
自动通道（src/scripts/re0_nekoquote.py 循环任务）之外的备份/排障手段。
幂等：已入库 id 跳过，可反复对同一导出跑。
"""

import json
import sys
from pathlib import Path

from . import DATA
from .chain import run_chain
from .parse import extract
from .state import PENDING, clear_pending, mark_pending, state_lock, write_json


def _main() -> None:
    export_dir = Path(
        sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\ccxxx\Desktop\tappei_tweets"
    )
    msgs = []
    for f in sorted(export_dir.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        msgs.extend(data if isinstance(data, list) else data.get("messages", []))
    print(f"导出消息 {len(msgs)}")

    found = extract(msgs)
    print(f"长月本人推文 {len(found)}（非 RT）")

    tw_path = DATA / "tweets.json"
    tw = json.loads(tw_path.read_text(encoding="utf-8"))
    new = {t: x for t, x in found.items() if t not in tw}
    print(f"库外新推 {len(new)}")
    if not new and not PENDING.exists():
        print("无新增，结束")
        return
    if new:
        # 先落待完成标记再入库，失败后的同一导出或其他入口都会续跑。
        mark_pending(PENDING)
        for tid, text in new.items():
            tw[tid] = {"text": text, "author": "nezumiironyanko", "src": "dc_manual"}
        write_json(tw_path, tw)

    pend_path = DATA / "wb_pending.txt"
    if pend_path.exists():
        pending = set(pend_path.read_text(encoding="utf-8").split())
        still = pending - set(new)
        if len(still) != len(pending):
            pend_path.write_text("\n".join(sorted(still)), encoding="utf-8")
            print(f"pending 划掉 {len(pending) - len(still)}，余 {len(still)}")

    run_chain()
    clear_pending(PENDING)
    print("全链完成 ✓")


def main() -> None:
    with state_lock(DATA):
        _main()


if __name__ == "__main__":
    main()
