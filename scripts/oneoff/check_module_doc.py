"""一次性：查看现有 Module doc 子页的格式惯例。"""

import pywikibot

site = pywikibot.Site("zh", "re0")
for title in (
    "Module:Init/doc",
    "Module:Title/doc",
    "Module:NekoQuote/doc",
    "Template:Documentation",
):
    p = pywikibot.Page(site, title)
    print("=" * 20, title, "exists:", p.exists(), "=" * 20)
    if p.exists():
        print(p.text[:1200])
