"""只读：C10/C12 改动前快照样本页的 parse HTML（渲染等价验证基线）。"""

import json
import os

os.environ.pop("PYTHONPATH", None)

from pywikibot.data import api

import pywikibot

site = pywikibot.Site("zh", "re0")

samples = [
    "声优:田中爱美",  # doc 示例，参数较全
    "声优:高桥李依",
    "制作人员:末广健一郎",
    "动画:第1集",
    "动画:OVA1",
    "动画:迷你动画第1集",
    "术语:王室疫病",  # Infobox event
    "音乐:Redo",  # Infobox music
]

snap = {}
for title in samples:
    req = api.Request(
        site=site,
        parameters={"action": "parse", "page": title, "prop": "text"},
    )
    data = req.submit()
    snap[title] = data["parse"]["text"]["*"]
    print(f"{title}: {len(snap[title])} chars")

os.makedirs("logs", exist_ok=True)
with open("logs/batch_bc_parse_snapshot.json", "w", encoding="utf-8") as f:
    json.dump(snap, f, ensure_ascii=False)
print("saved logs/batch_bc_parse_snapshot.json")
