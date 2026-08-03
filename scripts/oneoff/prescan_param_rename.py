"""只读：全命名空间（para fix generator 范围）区分大小写扫描全部待替换旧参数名。

目的：① 确认替换后新名的目标模板与使用页一致；② 发现 infobox 之外的碰撞（通用名 Date/Result 等）。
"""

import json
import os
import re
from collections import defaultdict

os.environ.pop("PYTHONPATH", None)

from pywikibot.data import api

import pywikibot

site = pywikibot.Site("zh", "re0")

# 待替换候选：模板 -> [(旧名, 拟定新名)]
MAPPINGS = [
    # seiyu/staff（es 搬运旧名）
    ("nombre", "name_en"),
    ("nacimiento", "birth"),
    ("personaje", "role"),
    ("guión", "script"),
    ("diseño", "design"),
    ("compositor", "composer"),
    ("image1", "image"),
    ("title1", "name"),
    ("caption1", "Caption"),
    # anime
    ("Volume", "volume"),
    ("Air Date", "air_date"),
    ("Opening", "opening"),
    ("Ending", "ending"),
    # bd
    ("Number", "number"),
    ("Previous", "previous"),
    ("Next", "next"),
    # music
    ("Singer", "singer"),
    ("Composition", "composition"),
    ("Arrangement", "arrangement"),
    ("Lyric", "lyric"),
    ("Length", "length"),
    # game
    ("Developers", "developers"),
    ("Publishers", "publishers"),
    ("Platform", "platform"),
    ("Genre", "genre"),
    ("Modes", "modes"),
    # battle + event 归一
    ("rōmaji", "name_ja_romaji"),
    ("Rōmaji", "name_ja_romaji"),
    ("Date", "date"),
    ("Place", "place"),
    ("Result", "result"),
    ("also known as", "also_known_as"),
    ("Also known as", "also_known_as"),
    # game 副标题（视扫描结果决定是否纳入）
    ("Name_en", "name_en"),
]

pats = {o: re.compile(rf"\|\s*{re.escape(o)}\s*=") for o, _ in MAPPINGS}
ibox_re = re.compile(r"\{\{\s*(Infobox\s+\w+)", re.IGNORECASE)

usage = defaultdict(list)
for ns in [0, 4, 8, 10, 14, 828]:
    gen = api.QueryGenerator(
        site=site,
        action="query",
        generator="allpages",
        gapnamespace=ns,
        gaplimit="max",
        prop="revisions",
        rvprop="content",
        rvslots="main",
    )
    for info in gen:
        revs = info.get("revisions")
        text = revs[0]["slots"]["main"]["*"] if revs else ""
        for o, pat in pats.items():
            if pat.search(text):
                ib = sorted({m.group(1) for m in ibox_re.finditer(text)})
                usage[o].append((info["title"], ib))

print("=== 全 ns 区分大小写扫描 ===")
for o, n in MAPPINGS:
    pages = usage.get(o, [])
    # 分类：有信息框的页 vs 无信息框的页（潜在碰撞）
    with_ib = [t for t, ib in pages if ib]
    without_ib = [t for t, ib in pages if not ib]
    flag = f" ⚠️ 无信息框页: {without_ib[:6]}" if without_ib else ""
    print(f"{o} -> {n}: {len(pages)} 页{flag}")

os.makedirs("logs", exist_ok=True)
with open("logs/param_rename_prescan.json", "w", encoding="utf-8") as f:
    json.dump(
        {o: usage.get(o, []) for o, _ in MAPPINGS}, f, ensure_ascii=False, indent=1
    )
print("\nsaved logs/param_rename_prescan.json")
