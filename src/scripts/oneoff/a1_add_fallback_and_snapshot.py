"""A1 步骤②+③：Infobox character 加 name_zh_tw fallback + 样本页改前快照。"""

import json
import os

import pywikibot
from pywikibot.data import api

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

# ② 模板 fallback
tpl = pywikibot.Page(site, "Template:Infobox character")
old = """  <data source="another translation">
    <label>台版译名</label>
  </data>"""
new = """  <data source="name_zh_tw">
    <label>台版译名</label>
    <default>{{{another translation|}}}</default>
  </data>"""
assert tpl.text.count(old) == 1, "模板体匹配失败"
tpl.text = tpl.text.replace(old, new)
tpl.save(
    summary="参数名归一：another translation → name_zh_tw（先加 fallback，fix:para 全站归一后摘除）"
)
print("模板 fallback 已加")

# ③ 样本页快照（台版译名非空的代表页）
SAMPLES = [
    "角色:菜月·昴",
    "角色:爱蜜莉雅",
    "角色:雷姆",
    "角色:碧翠丝",
    "角色:莱茵哈鲁特",
    "角色:培提奇乌斯·罗曼尼康帝",
]
snaps = {}
for title in SAMPLES:
    r = api.Request(
        site=site,
        parameters={
            "action": "parse",
            "format": "json",
            "page": title,
            "prop": "text",
            "disablelimitreport": "1",
        },
    ).submit()
    snaps[title] = r["parse"]["text"]["*"]
    assert "台版译名" in snaps[title], f"{title} 快照里没渲染台版译名？"
    print(f"snapshot {title} ok（台版译名已渲染）")

os.makedirs("logs", exist_ok=True)
with open("logs/a1_snapshots_before.json", "w", encoding="utf-8") as f:
    json.dump(snaps, f, ensure_ascii=False)
print("DONE")
