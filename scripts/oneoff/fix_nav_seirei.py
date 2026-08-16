"""一次性：导航源内联 {{Seirei}}（模块返回值不会被二次展开模板，须写展开后的内容）。"""

import pywikibot

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

proj = pywikibot.Page(site, "Project:Wiki-navigation")
old = "[[术语:精灵|{{Seirei}}]]"
new = "[[术语:精灵|精<!--nobot-->灵]]"
assert proj.text.count(old) == 1
proj.text = proj.text.replace(old, new, 1)
proj.save(
    summary="内联 {{Seirei}}：Module:Wiki-navigation 返回值不会被二次展开模板",
    bot=False,
    minor=False,
)
print("saved")

# 验证模块展开输出中新行
from pywikibot.data import api

req = api.Request(
    site=site,
    parameters={
        "action": "expandtemplates",
        "text": "{{#invoke:Wiki-navigation|main}}",
        "prop": "wikitext",
    },
)
expanded = req.submit()["expandtemplates"]["wikitext"]
for line in expanded.splitlines():
    if "精灵" in line and "术语" in line:
        print("expanded line:", repr(line))
