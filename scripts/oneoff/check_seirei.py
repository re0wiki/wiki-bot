"""一次性：确认 Template:Seirei 存在性与内容，及导航源中 {{Seirei}} 的来历。"""

import pywikibot

site = pywikibot.Site("zh", "re0")
t = pywikibot.Page(site, "Template:Seirei")
print("Template:Seirei exists:", t.exists())
if t.exists():
    print("---- content ----")
    print(t.text)

# Project 源中的相关行
src = pywikibot.Page(site, "Project:Wiki-navigation").text
for line in src.splitlines():
    if "Seirei" in line or "精灵" in line:
        print("src line:", repr(line))
