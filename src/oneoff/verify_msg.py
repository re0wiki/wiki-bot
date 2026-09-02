"""一次性：验证移动后 zh-hant 消息解析。"""

import pywikibot
from pywikibot.data import api

site = pywikibot.Site("zh", "re0")
for key in (
    "Custom-Emilia",
    "Custom-Wilhelm van Astrea",
    "Custom-Re:Zero kara Hajimeru Isekai Seikatsu (light novel)",
):
    for lang in ("zh-hant", "zh-hans"):
        req = api.Request(
            site=site,
            parameters={
                "action": "query",
                "meta": "allmessages",
                "ammessages": key,
                "amlang": lang,
            },
        )
        msgs = req.submit()["query"]["allmessages"]
        print(key, lang, "->", [m.get("*") for m in msgs])
