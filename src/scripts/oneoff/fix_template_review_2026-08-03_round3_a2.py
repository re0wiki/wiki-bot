"""A2：摘除 Quote/doc templatedata 里无效的 small 参数声明。"""

import pywikibot

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

doc = pywikibot.Page(site, "Template:Quote/doc")
old = """		"small": {
			"description": "非空则使用较小字体，留空则使用较大字体",
			"type": "string"
		},
"""
assert doc.text.count(old) == 1, f"匹配 {doc.text.count(old)} 次，预期 1"
doc.text = doc.text.replace(old, "")
doc.save(
    summary="摘除 templatedata 无效的 small 声明（Quote 固定 small=1 小字体，该参数不对外生效）"
)
print("saved Template:Quote/doc")
