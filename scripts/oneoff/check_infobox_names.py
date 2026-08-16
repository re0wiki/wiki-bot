"""一次性：查看角色条目信息框字段，确定全名取值来源。"""

import pywikibot

site = pywikibot.Site("zh", "re0")
for title in ("角色:海伦", "角色:莎克拉 (虚假的王选候补)", "角色:贝尔蒙特"):
    p = pywikibot.Page(site, title)
    print("=" * 20, title, "=" * 20)
    print(p.text[:900])
