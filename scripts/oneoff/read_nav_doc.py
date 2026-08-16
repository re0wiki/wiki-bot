"""一次性：修正 Project:Wiki-navigation 简繁转换节为 Custom-nav- 前缀。"""

import pywikibot

OLD = """=== 简繁转换 ===
导航显示文本经「Custom-」系统消息按界面语言区分简繁：
# 写法：<code><nowiki>[[目标页面|Custom-日文名称]]</nowiki></code>（裸标签则直接写 <code>Custom-日文名称</code>）。
# 简体值写在 <code>MediaWiki:Custom-<日文名称>/zh-hans</code>（[https://rezero.fandom.com/zh/wiki/Special:PrefixIndex/MediaWiki:Custom- 现有消息一览]）；繁体值写在 <code>…/zh-hant</code>。"""

NEW = """=== 简繁转换 ===
导航显示文本经「Custom-nav-」系统消息按界面语言区分简繁：
# 写法：<code><nowiki>[[目标页面|Custom-nav-英文名称]]</nowiki></code>（裸标签则直接写 <code>Custom-nav-英文名称</code>）。
# 简体值写在 <code>MediaWiki:Custom-nav-<英文名称>/zh-hans</code>（[https://rezero.fandom.com/zh/wiki/Special:PrefixIndex/MediaWiki:Custom-nav- 现有消息一览]）；繁体值写在 <code>…/zh-hant</code>。"""

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

proj = pywikibot.Page(site, "Project:Wiki-navigation")
assert OLD in proj.text, "文档节与预期不符"
proj.text = proj.text.replace(OLD, NEW, 1)
proj.save(summary="修正简繁转换节：Custom-nav- 前缀、英文 key", bot=False, minor=False)
print("doc fixed")
