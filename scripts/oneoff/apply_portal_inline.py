"""把内联版写入首页，验证渲染后删除 Portal 链 10 个模板（存档 logs/）。"""

import json

import pywikibot
from pywikibot.data import api

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"
MAIN = "Re:从零开始的异世界生活 Wiki"

with open("logs/mainpage_inlined_2026-07-28.wiki", encoding="utf-8") as f:
    inlined = f.read()

p = pywikibot.Page(site, MAIN)
assert "{{Portal}}" in p.text, "首页结构已变化，停止"
p.text = inlined
p.save(summary="Portal 链模板内联（渲染等价已验证；沙盒预览确认一致）")
print("main page saved")

# 写入后验证：嵌套 tab 正常
r = api.Request(
    site=site,
    parameters={"action": "parse", "page": MAIN, "prop": "text", "format": "json"},
).submit()
html = r["parse"]["text"]["*"]
assert (
    'data-hash="轻小说"' in html
    and 'data-hash="正传"' in html
    and 'data-hash="第一章(完)"' in html
)
print("render check OK")

CHAIN = [
    "Portal",
    "Portal Left",
    "Portal Right",
    "Slider",
    "Welcome",
    "Announcements",
    "Latest Volume",
    "Latest Volume/LN",
    "Latest Volume/Manga",
    "Social Media",
]
archive = {}
for t in CHAIN:
    tp = pywikibot.Page(site, f"Template:{t}")
    assert tp.exists(), t
    archive[f"Template:{t}"] = tp.text
with open("logs/deleted_portal_chain_2026-07-28.json", "w", encoding="utf-8") as f:
    json.dump(archive, f, ensure_ascii=False, indent=1)
for t in CHAIN:
    tp = pywikibot.Page(site, f"Template:{t}")
    tp.delete(reason="已内联进首页（Portal 链组件化取消）", prompt=False)
    print(f"deleted Template:{t}")

# 首页模板分类是否已空
cat = pywikibot.Category(site, "Category:首页模板")
members = [m.title() for m in cat.members()]
print("Category:首页模板 剩余成员:", members)
print("DONE")
