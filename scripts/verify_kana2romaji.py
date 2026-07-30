"""验证 Kana2Romaji 的 ヴ 系假名首字母大写疑点（只读 parse）。"""

import os

os.environ.pop("PYTHONPATH", None)

from pywikibot.data import api

import pywikibot

site = pywikibot.Site("zh", "re0")

for kana in ["ヴァルグレン", "バルガ", "ヴィルヘルム", "スバル"]:
    req = api.Request(
        site=site,
        parameters={
            "action": "parse",
            "text": "{{#invoke:Kana2Romaji|Kana2Romaji|kana=" + kana + "}}",
            "contentmodel": "wikitext",
            "prop": "text",
        },
    )
    html = req.submit()["parse"]["text"]["*"]
    print(f"{kana} -> {html.strip()}")
