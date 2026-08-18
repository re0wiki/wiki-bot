"""只读：全 MediaWiki CSS/JS 搜 data-source 选择器引用（确认 PI data-source 改名无样式依赖）。"""

import os

os.environ.pop("PYTHONPATH", None)

import pywikibot
from pywikibot.data import api

site = pywikibot.Site("zh", "re0")
gen = api.QueryGenerator(
    site=site, action="query", generator="allpages", gapnamespace=8, gaplimit="max"
)
found = False
for info in gen:
    t = info["title"]
    if t.endswith((".js", ".css")):
        text = pywikibot.Page(site, t).text
        if "data-source" in text:
            print(f"FOUND data-source in {t}")
            found = True
print("none" if not found else "see above")
