"""手动增量合流：Discrub 导出目录 → 新推入库 → 全链。

用法：python -m nekoquote.merge [导出目录]（默认 Desktop\\tappei_tweets）
自动通道（scripts/re0_nekoquote.py 循环任务）之外的备份/排障手段。
幂等：已入库 id 跳过，可反复对同一导出跑。
"""

import json
import sys
from pathlib import Path

from .chain import run_chain
from .parse import extract


def main() -> None:
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

    tw_path = Path("logs/p8_tweets.json")
    tw = json.loads(tw_path.read_text(encoding="utf-8"))
    new = {t: x for t, x in found.items() if t not in tw}
    print(f"库外新推 {len(new)}")
    if not new:
        print("无新增，结束")
        return
    for tid, text in new.items():
        tw[tid] = {"text": text, "author": "nezumiironyanko", "src": "dc_manual"}
    tw_path.write_text(json.dumps(tw, ensure_ascii=False), encoding="utf-8")

    pend_path = Path("logs/p8_wb_pending.txt")
    if pend_path.exists():
        pending = set(pend_path.read_text(encoding="utf-8").split())
        still = pending - set(new)
        if len(still) != len(pending):
            pend_path.write_text("\n".join(sorted(still)), encoding="utf-8")
            print(f"pending 划掉 {len(pending) - len(still)}，余 {len(still)}")

    run_chain()
    print("全链完成 ✓")


if __name__ == "__main__":
    main()
