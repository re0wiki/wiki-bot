"""一次性：抽查 Custom-* 消息内容，确认取值与导航链接目标的关系。"""

import json
import re

import pywikibot
from pywikibot.data import api

site = pywikibot.Site("zh", "re0")

# 抽查若干消息的 zh-hant 内容
samples = [
    "MediaWiki:Custom-エミリア/zh-hant",
    "MediaWiki:Custom-ナツキ·スバル/zh-hant",
    "MediaWiki:Custom-大罪魔女/zh-hant",
    "MediaWiki:Custom-Camp related/zh-hant",
    "MediaWiki:Custom-メイド&執事/zh-hant",
    "MediaWiki:Custom-Navigation Character/zh-hant",
    "MediaWiki:Custom-聖域/zh-hant",
    "MediaWiki:Custom-鉄の牙傭兵団/zh-hant",
]
req = api.Request(
    site=site,
    parameters={
        "action": "query",
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "titles": "|".join(samples),
    },
)
data = req.submit()
for page in data["query"]["pages"].values():
    if "revisions" in page:
        print(page["title"], "=>", repr(page["revisions"][0]["slots"]["main"]["*"]))
    else:
        print(page["title"], "=> MISSING")

# 导航中 Custom- 标签有无链接目标的分布
src = pywikibot.Page(site, "Project:Wiki-navigation").text
linked, bare = {}, []
for line in src.splitlines():
    if not line.startswith("*") or " " not in line:
        continue
    stem = line.split(" ", 1)[1]
    m = re.match(r"\[\[([^\]|]+)\|(Custom-[^\]]+)\]\]", stem)
    if m:
        linked[m.group(2)] = m.group(1)
    elif "Custom-" in stem:
        bare.append(stem)
print("\n带链接的 Custom- 标签:", len(linked), "| 裸标签:", len(bare))
for b in sorted(set(bare)):
    print("  bare:", b)

# 带链接标签里 target 词干（简体）与 zh-hant 消息内容的一致性抽查
keys = sorted(linked)[:8]
titles = [f"MediaWiki:{k}/zh-hant" for k in keys]
req = api.Request(
    site=site,
    parameters={
        "action": "query",
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "titles": "|".join(titles),
    },
)
data = req.submit()
content_by_title = {}
for page in data["query"]["pages"].values():
    if "revisions" in page:
        content_by_title[page["title"]] = page["revisions"][0]["slots"]["main"]["*"]
print("\n一致性抽查（target 词干 vs zh-hant 内容）:")
for k in keys:
    t = linked[k]
    stem = t.split(":", 1)[1] if ":" in t else t
    val = content_by_title.get(f"MediaWiki:{k}/zh-hant", "MISSING")
    print(f"  {k} | target={stem} | zh-hant={val!r}")

with open("logs_tmp_nav_linked.json", "w", encoding="utf-8") as f:
    json.dump(
        {"linked": linked, "bare": sorted(set(bare))}, f, ensure_ascii=False, indent=1
    )
