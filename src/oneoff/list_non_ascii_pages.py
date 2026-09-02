"""一次性统计：MediaWiki/Template/Module 命名空间中的非 ASCII 标题页面。"""

import pywikibot

site = pywikibot.Site("zh", "re0")

NS = {"MediaWiki": 8, "Template": 10, "Module": 828}

for name, ns in NS.items():
    pages = [p for p in site.allpages(namespace=ns)]
    non_ascii = [p.title() for p in pages if not p.title().isascii()]
    print(f"== {name} (ns={ns}): 共 {len(pages)} 页，非 ASCII {len(non_ascii)} 页 ==")
    for t in sorted(non_ascii):
        print(t)
    print()
