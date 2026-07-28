"""删除真零引用模板（2026-07-28 复核，用户已确认范围）：

StructuredQuote、Infobox、Infobox album/episode/item/location/quest、Tocright，连同各自 /doc。
删除前 wikitext 存档到 logs/deleted_templates_2026-07-28.json。
同步更新 ReZero Wiki:模板 索引页。
"""

import json

import pywikibot

TARGETS = [
    "StructuredQuote",
    "Infobox",
    "Infobox album",
    "Infobox episode",
    "Infobox item",
    "Infobox location",
    "Infobox quest",
    "Tocright",
]
REASON = "零引用模板清理（2026-07-28 复核：全命名空间 wikitext grep + embeddedin 双确认无使用）"

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

# 1. 存档
archive = {}
for t in TARGETS:
    for title in (f"Template:{t}", f"Template:{t}/doc"):
        p = pywikibot.Page(site, title)
        if p.exists():
            archive[title] = p.text
with open("logs/deleted_templates_2026-07-28.json", "w", encoding="utf-8") as f:
    json.dump(archive, f, ensure_ascii=False, indent=1)
print(f"archived {len(archive)} pages")

# 2. 删除
for title in archive:
    p = pywikibot.Page(site, title)
    p.delete(reason=REASON, prompt=False)
    print(f"deleted {title}")

# 3. 更新索引页
idx = pywikibot.Page(site, "ReZero Wiki:模板")
text = idx.text
DROP_LINES = [
    "* {{t|Infobox episode}} — 动画剧集",
    "* {{t|Infobox album}} — 音乐专辑",
    "* {{t|Infobox item}} — 物品",
    "* {{t|Infobox location}} — 地点",
    "* {{t|Infobox quest}} — 任务（游戏）",
    "* {{t|Infobox}} — 信息框元模板，以上信息框的基底",
    "* {{t|StructuredQuote}} — 结构化引文",
    "* {{t|Tocright}} — 目录右置",
]
for line in DROP_LINES:
    assert line in text, line
    text = text.replace(line + "\n", "")
idx.text = text
idx.save(
    summary="移除已删除的零引用模板（StructuredQuote、未用 Infobox 系、Tocright）",
    bot=True,
)
print("updated ReZero Wiki:模板")
print("DONE")
