"""一次性：将 MediaWiki:Wiki-navigation 切换为 #invoke 实时编译，并验证页面 HTML 中的导航。"""

import re

from pywikibot.data import api

import pywikibot

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

msg = pywikibot.Page(site, "MediaWiki:Wiki-navigation")
new_text = "{{#invoke:Wiki-navigation|main}}"
if msg.text != new_text:
    msg.text = new_text
    msg.save(
        summary="切换为 Module:Wiki-navigation 实时编译，取代 bot 定期编译",
        bot=False,
        minor=False,
    )
    print("MediaWiki:Wiki-navigation saved")
else:
    print("already switched")

# 用 API 解析该消息，确认输出是编译后的导航行
req = api.Request(
    site=site,
    parameters={
        "action": "parse",
        "title": "MediaWiki:Wiki-navigation",
        "text": new_text,
        "prop": "text",
        "contentmodel": "wikitext",
    },
)
html = req.submit()["parse"]["text"]["*"]
n_li = len(re.findall(r"<li>", html))
print("parse ok, <li> count:", n_li)
print("含 Custom-エミリア:", "Custom-エミリア" in html)
print("含 {{Seirei}} 展开检查（不应出现字面 {{Seirei}}）:", "{{Seirei}}" not in html)
