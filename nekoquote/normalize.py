"""P8 译文归一：对 p8_zh.json 的 zh/qzh 值应用 translation fix 规则。"""

import importlib
import json
import re
from collections import Counter
from pathlib import Path

fx = importlib.import_module("pywikibot.fixes")
replacements = fx.__dict__["user_fixes"]["translation"]["replacements"]

data = json.loads(Path("logs/p8_zh.json").read_text(encoding="utf-8"))
hits = Counter()
for rec in data.values():
    for k in ("zh", "qzh"):
        v = rec.get(k)
        if not v:
            continue
        new = v
        for pattern, repl in replacements:
            new2 = re.sub(pattern, repl, new)
            if new2 != new:
                hits[f"{pattern}→{repl}"] += 1
                new = new2
        rec[k] = new
Path("logs/p8_zh.json").write_text(
    json.dumps(data, ensure_ascii=False), encoding="utf-8"
)
print("归一命中:", sum(hits.values()))
for k, c in hits.most_common(20):
    print(f"  {c}× {k[:90]}")
