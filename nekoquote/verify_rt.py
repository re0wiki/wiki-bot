"""round-trip 校验：月表 ⊇ lua_base——既有条目零丢失零变形；多出部分 = raw 新推。"""

import re
from collections import Counter
from pathlib import Path

import pywikibot

ENTRY_RE = re.compile(r"\{\s*src\s*=.*?\n\s*\}", re.DOTALL)
FIELD_RE = re.compile(r"(\w+)\s*=\s*(['\"])((?:\\.|(?!\2).)*?)\2", re.DOTALL)


def entries_of(lua):
    out = []
    for bm in ENTRY_RE.finditer(lua):
        fields = tuple(
            (f.group(1), f.group(2), f.group(3)) for f in FIELD_RE.finditer(bm.group(0))
        )
        out.append(fields)
    return out


site = pywikibot.Site("zh", "re0")
site.login()

src_counter = Counter()
for f in Path("logs/nekoquote/lua_base").glob("*.lua"):
    src_counter.update(entries_of(f.read_text(encoding="utf-8")))

dst_counter = Counter()
for f in Path("logs/nekoquote/lua").glob("*.lua"):
    dst_counter.update(entries_of(f.read_text(encoding="utf-8")))

print(f"基线 {sum(src_counter.values())}，月表 {sum(dst_counter.values())}")
missing = src_counter - dst_counter
extra = dst_counter - src_counter
print(f"既有缺失 {sum(missing.values())} 种 / 新增（raw）{sum(extra.values())} 条")
for e, n in list(missing.items())[:5]:
    print(f"  缺失×{n}:", str(e)[:120])
print("\n校验", "通过 ✅" if not missing else "失败 ❌")
