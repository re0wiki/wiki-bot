"""修正 character/doc name_zh_tw 的 description（原表述的规则不存在）。"""

import pywikibot

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

doc = pywikibot.Page(site, "Template:Infobox character/doc")
old = '"description": "台湾中文版译名（与通用译名不同时填写）"'
new = '"description": "官方繁体中文译名（通常青文出版社）"'
assert doc.text.count(old) == 1, f"匹配 {doc.text.count(old)} 次"
doc.text = doc.text.replace(old, new)
doc.save(
    summary="修正 name_zh_tw 描述：无「与通用译名不同才填」的规定，按译名表——官方繁体中文译名记录于此栏"
)
print("saved Template:Infobox character/doc")
