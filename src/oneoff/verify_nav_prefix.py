"""一次性：nav- 前缀切换后验证编译输出。"""

import re

import pywikibot
from pywikibot.data import api

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
lines = [line for line in expanded.splitlines() if line.startswith("*")]
print("编译行数:", len(lines))
nav_keys = [line for line in lines if "Custom-nav-" in line]
old_keys = [line for line in lines if re.search(r"Custom-(?!nav-)", line)]
print("含 Custom-nav-:", len(nav_keys), "| 旧前缀残留:", len(old_keys))
# 抽查消息解析
for lang in ("zh-hans", "zh-hant"):
    req = api.Request(
        site=site,
        parameters={
            "action": "query",
            "meta": "allmessages",
            "ammessages": "Custom-nav-Emilia",
            "amlang": lang,
        },
    )
    print(lang, "->", [m.get("*") for m in req.submit()["query"]["allmessages"]])
# purge 消息页（聊胜于无）
site.login()
req = api.Request(
    site=site, parameters={"action": "purge", "titles": "MediaWiki:Wiki-navigation"}
)
req.submit()
print("purged")
