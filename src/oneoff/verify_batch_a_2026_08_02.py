"""只读：A 组修复后的终态验证。"""

import os

os.environ.pop("PYTHONPATH", None)

import pywikibot

site = pywikibot.Site("zh", "re0")

cr = pywikibot.Page(site, "Template:Category redirect").text
assert 'style="border: none;' in cr and 'style:"' not in cr
print("1. Category redirect: style 属性已修复 OK")

common = pywikibot.Page(site, "MediaWiki:Common.css").text
assert "Poll" not in common and "Assert" not in common
print("2. Common.css: 无 Poll/Assert 残留 OK")

assert not pywikibot.Page(site, "MediaWiki:Gadget-Assert.css").exists()
print("3. Gadget-Assert.css: 已删除 OK")

ij = pywikibot.Page(site, "MediaWiki:ImportJS").text
assert "AjaxPoll" not in ij
print("4. ImportJS: 无 AjaxPoll 残留 OK")

print("\nALL VERIFIED")
