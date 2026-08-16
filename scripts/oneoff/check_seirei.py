"""一次性：精简注释后复验模块展开输出。"""

from pywikibot.data import api

import pywikibot

site = pywikibot.Site("zh", "re0")
req = api.Request(
    site=site,
    parameters={
        "action": "expandtemplates",
        "text": "{{#invoke:Wiki-navigation|main}}",
        "prop": "wikitext",
    },
)
expanded = req.submit()["expandtemplates"]["wikitext"]
lines = expanded.splitlines()
print("lines:", len(lines))
print("first:", repr(lines[1]))
print("Seirei line:", [line for line in lines if "术语:精灵|" in line])
