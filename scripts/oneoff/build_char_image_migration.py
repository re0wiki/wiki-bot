"""只读：生成迁移数据 logs/char_image_migration.json。

- live 清单：模拟 Module:Character image 逻辑，逐角色页穷举候选文件名，命中实际存在文件的
  按模块顺序记录（真实文件名 + caption）。
- 显式参数：精确扫描这些页是否已设置 image_a/n/g/c（影响迁移写法）。
- 补充清单：3 张未使用的非重复死文件。
"""

import json
import re
from collections import defaultdict

import pywikibot

site = pywikibot.Site("zh", "re0")

fmts = ["gif", "png", "jpg", "jpeg", "webp"]
subs = {
    "a": ["TV/OVA", "SP"],
    "c": [
        "第1章", "第2章", "第3章", "第4章", "第5章", "第6章", "第7章", "第8章", "第9章",
        "冰结之绊", "剑鬼恋歌",
    ],
    "g": [
        "INFINITY", "Death or Kiss", "Lost in Memories", "虚假的王选候补",
        "禁书与谜之精灵", "公主连结", "素晴Fd",
    ],
    "n": ["大塚真一郎", "枫月诚", "イセ川ヤスタカ"],
}
tabs = {"a": "动画", "c": "漫画", "g": "游戏", "n": "文库"}

# real file titles, normalized -> actual title (with ns stripped)
existing = {}
for p in site.allpages(namespace=6, total=20000):
    t = p.title(with_ns=False)
    if "角色介绍图" in t and not p.isRedirectPage():
        existing[t.replace(" ", "_").lower()] = t


def gen(name):
    for sec, sublist in subs.items():
        for sub in sublist:
            sub_ = "TV_OVA" if sub == "TV/OVA" else sub
            for fmt in fmts:
                fn = f"{name} {tabs[sec]} {sub_}角色介绍图.{fmt}"
                key = fn.replace(" ", "_").lower()
                yield sec, key, sub


live = defaultdict(lambda: defaultdict(list))
for p in pywikibot.Page(site, "Template:Infobox character").embeddedin(
    namespaces=[0], filter_redirects=False
):
    title = p.title()
    if not title.startswith("角色:") or "/" in title:
        continue
    name = title[3:]
    for sec, key, sub in gen(name):
        if key in existing:
            live[title][sec].append((existing[key], sub))

# explicit image_a/n/g/c params on live pages
param_pat = re.compile(r"^\|\s*(image_[acgn])\s*=\s*(.*?)\s*$", re.M)
explicit = {}
for title in live:
    text = pywikibot.Page(site, title).text
    found = {m.group(1): m.group(2) for m in param_pat.finditer(text) if m.group(2)}
    if found:
        explicit[title] = found

# 补充清单（用户决策）
supplement = {
    "角色:佩特拉·莱特": {"g": [("佩特拉 游戏 虚假的王选候补角色介绍图.jpg", "虚假的王选候补")]},
    "角色:安娜塔西亚·合辛": {"g": [("安娜塔西亚 游戏 虚假的王选候补角色介绍图.jpg", "虚假的王选候补")]},
    "角色:爱蜜莉雅": {"a": [("爱蜜莉雅 动画 たけはらみのる角色介绍图.png", "SP")]},
}

out = {
    "live": {t: {s: v for s, v in sorted(ss.items())} for t, ss in sorted(live.items())},
    "explicit": explicit,
    "supplement": supplement,
}
with open("logs/char_image_migration.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

print("live pages:", len(live), "images:", sum(len(v) for ss in live.values() for v in ss.values()))
print("live pages with EXPLICIT image_[acgn] params:", len(explicit))
for t, ps in sorted(explicit.items()):
    print("  ", t, {k: v[:60] for k, v in ps.items()})
print("supplement pages:", list(supplement))
