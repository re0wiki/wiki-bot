"""一次性：盘点 MediaWiki:Custom-* 消息与导航源中 Custom- 标签的使用情况。"""

import json
import re
from collections import defaultdict

from pywikibot.data import api

import pywikibot

site = pywikibot.Site("zh", "re0")

# 1) 列出所有 MediaWiki:Custom-* 页面（含 /变体子页）
pages = []
cont = {}
while True:
    req = api.Request(
        site=site,
        parameters={
            "action": "query",
            "list": "allpages",
            "apnamespace": 8,
            "apprefix": "Custom-",
            "aplimit": "max",
            **cont,
        },
    )
    data = req.submit()
    pages += [p["title"] for p in data["query"]["allpages"]]
    if "continue" not in data:
        break
    cont = data["continue"]

groups = defaultdict(list)
for t in pages:
    base, _, variant = t.partition("/")
    groups[base.removeprefix("MediaWiki:")].append(variant or "(base)")

print("Custom-* 页面总数:", len(pages), "| base 消息数:", len(groups))
variant_stats = defaultdict(int)
non_en = []
for base, variants in sorted(groups.items()):
    for v in variants:
        variant_stats[v] += 1
    # 判断是否含中日文字符
    if re.search(r"[぀-ヿ一-鿿]", base.removeprefix("Custom-")):
        non_en.append(base)
print("变体分布:", dict(variant_stats))
print("非英文名的 base 数:", len(non_en))
for b in non_en:
    print("  ", b, sorted(groups[b]))

# 2) 导航源中的 Custom- 标签与中文标签
src = pywikibot.Page(site, "Project:Wiki-navigation").text
labels = []
for line in src.splitlines():
    if not line.startswith("*") or " " not in line:
        continue
    stem = line.split(" ", 1)[1]
    m = re.match(r"\[\[[^\]|]+\|([^\]]+)\]\]", stem)
    label = m.group(1) if m else (stem.split("|", 1)[1] if "|" in stem else None)
    if label is None:
        label = stem.split("|", 1)[0] if "|" not in stem else stem
        labels.append(("no-display", stem))
        continue
    labels.append(("label", label))

custom = sorted({x for _, x in labels if x.startswith("Custom-")})
cjk_plain = sorted(
    {x for _, x in labels if not x.startswith("Custom-") and re.search(r"[一-鿿]", x)}
)
other = sorted(
    {
        x
        for _, x in labels
        if not x.startswith("Custom-") and not re.search(r"[一-鿿]", x)
    }
)
print(
    "\n导航标签统计: Custom-",
    len(custom),
    "| 含汉字非Custom",
    len(cjk_plain),
    "| 其他",
    len(other),
)
print("\n导航引用了但消息不存在的 Custom- 标签:")
missing = [c for c in custom if c not in groups]
for c in missing:
    print("  ", c)
print("\n存在消息但导航未引用的 Custom- 消息:")
unused = [b for b in groups if b not in custom]
for b in unused:
    print("  ", b, sorted(groups[b]))

with open("logs_tmp_nav_labels.json", "w", encoding="utf-8") as f:
    json.dump(
        {
            "groups": dict(groups),
            "custom": custom,
            "cjk_plain": cjk_plain,
            "other": other,
        },
        f,
        ensure_ascii=False,
        indent=1,
    )
print("\n(明细已存 logs_tmp_nav_labels.json)")
