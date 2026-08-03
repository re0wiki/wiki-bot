"""只读：B/C 组信息收集。

1. User:IchiSanNi / User:Devil233-bot 的 {{Bot}} 调用参数
2. Blur/doc 的 templatedata 写法先例
3. seiyu/staff/anime 引用页清单与计数
4. seiyu/doc、staff/doc、Quote/doc、Infobox anime/doc 现状
"""

import os

os.environ.pop("PYTHONPATH", None)

import re

import pywikibot

site = pywikibot.Site("zh", "re0")

print("=== 1. Bot 调用方 ===")
for t in ["User:IchiSanNi", "User:Devil233-bot"]:
    text = pywikibot.Page(site, t).text
    m = re.search(r"\{\{[Bb]ot.*?\}\}", text, re.DOTALL)
    print(f"  {t}: {m.group(0) if m else '(未找到)'}")

print("\n=== 2. Blur/doc templatedata 先例 ===")
print(pywikibot.Page(site, "Template:Blur/doc").text)

print("\n=== 3. 引用量 ===")
for t in ["Template:Infobox seiyu", "Template:Infobox staff", "Template:Infobox anime"]:
    p = pywikibot.Page(site, t)
    pages = sorted(p.embeddedin(namespaces=0), key=lambda x: x.title())
    print(f"  {t}: {len(pages)} 页")
    for x in pages:
        print(f"    {x.title()}")

print("\n=== 4. doc 现状 ===")
for t in [
    "Template:Infobox seiyu/doc",
    "Template:Infobox staff/doc",
    "Template:Quote/doc",
    "Template:Infobox anime/doc",
]:
    print(f"\n----- {t} -----")
    print(pywikibot.Page(site, t).text)
