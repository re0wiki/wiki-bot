"""P8 round-trip 校验（合流版）：月表 ⊇ lua_base——既有条目零丢失零变形；多出部分 = raw 新推。"""

import re
from collections import Counter
from pathlib import Path

import pywikibot

TABLES = [
    "佩特拉",
    "加菲尔",
    "奥托",
    "威尔海姆",
    "安娜塔西亚",
    "由里乌斯",
    "帕克",
    "库珥修",
    "普莉希拉",
    "特蕾西亚",
    "福尔图娜",
    "约书亚",
    "罗兹瓦尔",
    "罗姆爷",
    "艾姬多娜",
    "艾尔莎",
    "爱蜜莉雅",
    "弗雷德莉卡",
    "莱茵哈鲁特",
    "菲莉丝",
    "菲鲁特",
    "蜜蜜",
    "早期ask/2014-05~2014-08",
    "早期ask/2014-09~2015-10",
    "Nico生放送",
    "动画实况解说/第一季旧版",
    "动画实况解说/第一季新编集版",
    "动画实况解说/OVA",
    "动画实况解说/第二季",
    "Web连载网站上评论",
    "十周年问答",
    "签名会",
]

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
for f in Path("logs/p8/lua_base").glob("*.lua"):
    src_counter.update(entries_of(f.read_text(encoding="utf-8")))

dst_counter = Counter()
for f in Path("logs/p8/lua").glob("*.lua"):
    dst_counter.update(entries_of(f.read_text(encoding="utf-8")))

print(f"基线 {sum(src_counter.values())}，月表 {sum(dst_counter.values())}")
missing = src_counter - dst_counter
extra = dst_counter - src_counter
print(f"既有缺失 {sum(missing.values())} 种 / 新增（raw）{sum(extra.values())} 条")
for e, n in list(missing.items())[:5]:
    print(f"  缺失×{n}:", str(e)[:120])
print("\n校验", "通过 ✅" if not missing else "失败 ❌")
