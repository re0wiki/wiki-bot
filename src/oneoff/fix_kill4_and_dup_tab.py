"""KILL4 换挂正确 tab + 删除零引用重复模板 Tab/The Great Spirit Puck（先查 en）。"""

import pywikibot

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

# KILL4: {{Tab/KILL}}（不存在的模板）-> 正确 tab
p = pywikibot.Page(site, "小说:艾尔莎和梅莉，地下行业姐妹暗中活动的日报/KILL4")
assert "{{Tab/KILL}}" in p.text
p.text = p.text.replace(
    "{{Tab/KILL}}", "{{Tab/Elsa and Meili, Assassin Sisters' Dark Diary}}"
)
p.save(summary="Tab/KILL 是不存在的模板，换挂正确 tab", bot=True)
print("OK KILL4")

# 删重复模板（先查 en 同名）
en = pywikibot.Site("en", "re0")
print(
    "en Tab/The Great Spirit Puck 存在:",
    pywikibot.Page(en, "Template:Tab/The Great Spirit Puck").exists(),
)

dup = pywikibot.Page(site, "Template:Tab/The Great Spirit Puck")
assert not list(dup.embeddedin(filter_redirects=False)), "仍有引用"
dup.delete(
    reason="与 Tab/The Great Spirit Puck's Side Story 逐字节重复且零引用", prompt=False
)
print("deleted Template:Tab/The Great Spirit Puck")
