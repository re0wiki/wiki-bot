"""只读：对比两个渲染快照阶段，忽略 data-source 属性差异，只看实际内容变化。"""

import json
import re
import sys

stage_a = sys.argv[1] if len(sys.argv) > 1 else "0_before"
stage_b = sys.argv[2] if len(sys.argv) > 2 else "1_fallbacks"
with open(f"logs/render_snapshots/{stage_a}.json", encoding="utf-8") as f:
    before = json.load(f)
with open(f"logs/render_snapshots/{stage_b}.json", encoding="utf-8") as f:
    after = json.load(f)
print(f"对比 {stage_a} vs {stage_b}\n")


def normalize(html: str) -> str:
    # data-source 属性随参数改名必然变化，非内容差异
    html = re.sub(r'data-source="[^"]*"', 'data-source="X"', html)
    # 各类解析报告/缓存注释（时间戳、耗时、trigger 原因）每次 parse 都变——整注释剥离
    html = re.sub(r"<!--[\s\S]*?-->", "", html)
    return re.sub(r"pi-tab(panel)?-[0-9a-f]+-", r"pi-tab\1-H-", html)


ok = True
for t in before:
    b, a = normalize(before[t]), normalize(after[t])
    if b == a:
        print(f"✓ {t}: 内容等价")
    else:
        ok = False
        print(f"⚠️ {t}: 内容有差异")
        # 打印差异上下文
        for i, (cb, ca) in enumerate(zip(b, a)):
            if cb != ca:
                print(f"  首个差异位置 {i}:")
                print(f"  before: ...{b[max(0, i - 80) : i + 120]!r}")
                print(f"  after:  ...{a[max(0, i - 80) : i + 120]!r}")
                break
        if len(b) != len(a):
            print(f"  长度: {len(b)} -> {len(a)}")
print("\nALL EQUIVALENT" if ok else "\nDIFFS FOUND")
