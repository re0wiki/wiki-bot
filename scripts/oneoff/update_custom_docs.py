"""一次性：修正 Project 页规则中的链接笔误。"""

import pywikibot

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

proj = pywikibot.Page(site, "Project:Wiki-navigation")
old = "# 简体值写在 [[:zh:MediaWiki:Custom-|MediaWiki:Custom-<英文名称>/zh-hans]]；繁体值写在 <code>…/zh-hant</code>。"
new = "# 简体值写在 <code>MediaWiki:Custom-<英文名称>/zh-hans</code>（[https://rezero.fandom.com/zh/wiki/Special:PrefixIndex/MediaWiki:Custom- 现有消息一览]）；繁体值写在 <code>…/zh-hant</code>。"
assert old in proj.text
proj.text = proj.text.replace(old, new, 1)
proj.save(summary="修正链接笔误", bot=False, minor=False)
print("fixed")
