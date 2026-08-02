"""只读：确认 音乐:Redo 是否传 name_ja_kanji；并找一个传了该参数的 Infobox music 页面做 label 验证。"""

import os

os.environ.pop("PYTHONPATH", None)

import re

import pywikibot

site = pywikibot.Site("zh", "re0")

p = pywikibot.Page(site, "音乐:Redo")
m = re.search(r"\{\{Infobox music.*?\}\}", p.text, re.DOTALL)
print("Redo 调用块:")
print(m.group(0) if m else "(未找到)")

print("\n含 name_ja_kanji 的 music 引用页:")
tpl = pywikibot.Page(site, "Template:Infobox music")
for page in tpl.embeddedin(namespaces=0):
    if "name_ja_kanji" in page.text:
        print(f"  {page.title()}")
