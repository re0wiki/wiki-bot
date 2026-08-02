"""只读：核实 Common.css @import 清单与实际存在的 Gadget 页面的差异。"""

import os
import re

os.environ.pop("PYTHONPATH", None)

import pywikibot

site = pywikibot.Site("zh", "re0")

common = pywikibot.Page(site, "MediaWiki:Common.css").text
imported = re.findall(r"MediaWiki:[^|'\"]+\.css", common)
print("Common.css @import 引用的本地 CSS：")
for t in imported:
    p = pywikibot.Page(site, t)
    n = len(p.text) if p.exists() else -1
    status = "MISSING(已删)" if n < 0 else ("EMPTY" if n == 0 else f"{n} chars")
    print(f"  {t}: {status}")

print("\n--- MediaWiki:Gadget-Assert.css ---")
print(pywikibot.Page(site, "MediaWiki:Gadget-Assert.css").text)
print("\n--- MediaWiki:Common.js ---")
print(pywikibot.Page(site, "MediaWiki:Common.js").text)
