"""nav Custom- 迁移 阶段2：改写 Project:Wiki-navigation 的标签为 Custom- key 引用。

--simulate：只输出 diff 统计，不写 wiki。
"""

import json
import re
import sys
from pathlib import Path

import pywikibot

OUT = Path(".cache/nav_custom")
final = json.loads((OUT / "final_map.json").read_text(encoding="utf-8"))
label2key = {label: rec["key"] for label, rec in final.items()}

site = pywikibot.Site("zh", "re0")
proj = pywikibot.Page(site, "Project:Wiki-navigation")
src = proj.text

new_lines = []
n_changed = 0
for line in src.splitlines():
    if not line.startswith("*") or " " not in line:
        new_lines.append(line)
        continue
    stars, stem = line.split(" ", 1)
    m = re.match(r"\[\[([^\]|]+)\|([^\]]+)\]\]", stem)
    m2 = re.match(r"\[\[([^\]|]+)\]\]", stem)
    if m:
        target, label = m.group(1), m.group(2)
        key = label2key.get(label)
        new_stem = f"[[{target}|{key}]]" if key else stem
    elif m2:
        target = label = m2.group(1)
        key = label2key.get(label)
        new_stem = f"[[{target}|{key}]]" if key else stem
    elif "|" in stem:
        target, label = stem.split("|", 1)
        key = label2key.get(label)
        new_stem = f"{target}|{key}" if key else stem
    else:
        key = label2key.get(stem)
        new_stem = key if key else stem
    if new_stem != stem:
        n_changed += 1
    new_lines.append(f"{stars} {new_stem}")

new_src = "\n".join(new_lines)
print(f"changed lines: {n_changed}")
leftover = [
    line
    for line in new_src.splitlines()
    if line.startswith("*")
    and "Custom-" not in line
    and re.search(r"[一-鿿぀-ヿ]", line)
]
print("改写后仍含中日文的行（应为 0 或仅剩特殊个案）:", len(leftover))
for line in leftover[:20]:
    print("  ", line)

if "--simulate" in sys.argv:
    print("SIMULATE, not saving")
    sys.exit(0)

site.login()
assert site.user() == "IchiSanNi"
proj.text = new_src
proj.save(
    summary="导航简繁转换：标签迁移至 Custom- 英文 key（hant 暂 fallback 至 hans）",
    bot=False,
    minor=False,
)
print("saved")
