"""nav Custom- 迁移 阶段0-2：OpenCC 转换推导 zh-hans 候选值（无 pywikibot 依赖）。

uv run --no-project --with opencc-python-reimplemented python scripts/oneoff/nav_custom_step2.py

产出 .cache/nav_custom/candidates.json：
  {label: {kind, key_hint_en, hant, hans_candidate, hans_source, flags}}
"""

import json
import re
from pathlib import Path

from opencc import OpenCC

OUT = Path(".cache/nav_custom")
labels = json.loads((OUT / "labels.json").read_text(encoding="utf-8"))

t2s = OpenCC("t2s")  # 繁 -> 简
s2t = OpenCC("s2t")  # 简 -> 繁

AS_IS_RE = re.compile(r'<div class="as-is">(.*)</div>', re.DOTALL)


def unwrap(v):
    m = AS_IS_RE.fullmatch(v.strip())
    return m.group(1) if m else v.strip()


def has_cjk(s):
    return bool(re.search(r"[一-鿿]", s))


out = {}
for label, rec in labels.items():
    if label.startswith("Custom-"):
        ascii_key = label.removeprefix("Custom-")
        existing_ascii_key = ascii_key if ascii_key.isascii() else None
        hant = unwrap(rec["hant"]) if rec.get("hant") else None
        conv = t2s.convert(hant) if hant else None
        targets = rec["targets"]
        stem = None
        if len(targets) == 1:
            t0 = targets[0]
            if "#" in t0:
                stem = t0.split("#", 1)[1]
            else:
                stem = t0.split(":", 1)[1] if ":" in t0 else t0
        entry = {
            "kind": "custom",
            "key_hint_en": existing_ascii_key or rec.get("en"),
            "hant": hant,
            "hans_candidate": conv,
            "flags": [],
        }
        if hant is None:
            entry["flags"].append("缺 zh-hant 消息")
        elif stem is not None and conv != stem:
            entry["flags"].append(
                f"hant简体化({conv}) != 目标词干({stem})——需查条目全名"
            )
        elif stem is None:
            entry["flags"].append("裸标签，hans 取 hant 简体化")
        out[label] = entry
    elif has_cjk(label):
        conv = t2s.convert(label)
        entry = {
            "kind": "cjk",
            "key_hint_en": rec.get("en"),
            "hant": None,  # 不建
            "hans_candidate": conv,
            "flags": [],
        }
        if conv != label:
            entry["flags"].append(f"导航源含繁体字，hans 取转换值 {conv}")
        if len(rec["targets"]) > 1:
            entry["flags"].append(f"多目标: {rec['targets']}")
        if not rec["targets"]:
            entry["flags"].append("裸标签")
        if not rec.get("en"):
            entry["flags"].append("无 en 链接，key 需拟名")
        out[label] = entry
    # 纯 ASCII 标签跳过

n_flag = sum(1 for e in out.values() if e["flags"])
print("需迁移标签:", len(out), "| 有 flag:", n_flag)
from collections import Counter

c = Counter(
    f.split("——")[0].split(":")[0].split("(")[0]
    for e in out.values()
    for f in e["flags"]
)
for k, n in c.most_common():
    print(f"  {n:4d}  {k}")

(OUT / "candidates.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8"
)
print("saved", OUT / "candidates.json")
