"""验证 Module 审查中的疑点（只读）。

1. {{BV}} 实际渲染出 data-bv 还是 data-av（Bili.lua 的 sub(id,0,0) 疑点）
2. 4 个 50 字符的鼠色猫语录数据子模块内容
3. Module:CGroup 是否存在（NoteTA 的死路径）
4. 各 Module 的被引用情况（#invoke 计数）
"""

import os
import re

os.environ.pop("PYTHONPATH", None)

from pywikibot.data import api

import pywikibot

site = pywikibot.Site("zh", "re0")

print("===== 1. BV 渲染验证 =====")
req = api.Request(
    site=site,
    action="parse",
    text="{{BV|BV1jt4y1D714|1}}",
    contentmodel="wikitext",
    prop="text",
)
html = req.submit()["parse"]["text"]["*"]
m1 = re.search(r'data-\w+="[^"]*"', html)
m2 = re.search(r"data-bv|data-av", html)
assert m1 and m2  # 验证脚本：解析结果必须含 data-* 属性
print(
    m1.group(0),
    "|",
    m2.group(0),
)

print("\n===== 2. 微型数据子模块 =====")
for t in [
    "鼠色猫语录/Web连载网站上评论",
    "鼠色猫语录/动画实况解说",
    "鼠色猫语录/帕克",
    "鼠色猫语录/福尔图娜",
]:
    p = pywikibot.Page(site, "Module:" + t)
    print(f"--- {t} ---")
    print(repr(p.text))

print("\n===== 3. CGroup 检查 =====")
gen = api.QueryGenerator(
    site=site,
    action="query",
    generator="allpages",
    gapnamespace=828,
    gapprefix="CGroup",
    gaplimit="max",
)
print("Module:CGroup* 页面数:", sum(1 for _ in gen))

print("\n===== 4. Module 被引用情况（全命名空间 #invoke / transclusion） =====")
for m in [
    "AutoTab",
    "Auto ruby",
    "Bili",
    "Character image",
    "Infobox book",
    "Init",
    "Interwiki",
    "Kana2Romaji",
    "NoteTA",
    "Set",
    "Tab",
    "Title",
    "Utils",
    "WikitextLC",
    "鼠色猫语录",
]:
    p = pywikibot.Page(site, "Module:" + m)
    n = sum(1 for _ in p.embeddedin(total=5000))
    print(f"Module:{m:<20} embeddedin={n}")
