"""一次性：验证 MediaWiki:Wiki-navigation 解析缓存对 Project:Wiki-navigation 的依赖登记。"""

from pywikibot.data import api

import pywikibot

site = pywikibot.Site("zh", "re0")
req = api.Request(
    site=site,
    parameters={
        "action": "query",
        "prop": "templates",
        "titles": "MediaWiki:Wiki-navigation",
        "tllimit": "max",
    },
)
data = req.submit()
for page in data["query"]["pages"].values():
    print(
        "templates on",
        page["title"],
        ":",
        [t["title"] for t in page.get("templates", [])],
    )
