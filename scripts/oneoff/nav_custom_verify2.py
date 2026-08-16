"""nav Custom- 迁移：阶段2后验证 + purge MediaWiki:Wiki-navigation。"""

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
lines = [line for line in expanded.splitlines() if line.startswith("*")]
print("编译行数:", len(lines))
print("含 Custom- 的行:", sum("Custom-" in line for line in lines))
import re

cjk_label = [line for line in lines if re.search(r"\|[^|]*[一-鿿぀-ヿ]", line)]
print("编译后 label 位仍含中日文的行:", len(cjk_label))
for line in cjk_label[:5]:
    print("  ", line)

# purge 消息页（推动导航缓存刷新）
site.login()
req = api.Request(
    site=site, parameters={"action": "purge", "titles": "MediaWiki:Wiki-navigation"}
)
r = req.submit()
print("purge:", r)
