"""一次性：purge 首页，尝试刷新导航片段缓存。"""

import pywikibot
from pywikibot.data import api

site = pywikibot.Site("zh", "re0")
site.login()
req = api.Request(
    site=site,
    parameters={"action": "purge", "titles": "Re:Zero Wiki", "forcelinkupdate": 1},
)
print(req.submit())
