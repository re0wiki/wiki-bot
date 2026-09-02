"""一次性批量：全站内容页 | name_ja_kanji = → | name_ja =（8 个信息框引用页）。"""

import json
import re

import pywikibot
from pywikibot.data import api

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

TEMPLATES = ["book", "character", "anime", "music", "bd", "game", "event", "battle"]
PARAM_RE = re.compile(r"(?im)^([ \t]*\|)[ \t]*name_ja_kanji[ \t]*=")

# 1) 枚举引用页（主空间）
titles = set()
for t in TEMPLATES:
    cont = {}
    while True:
        req = api.Request(
            site=site,
            parameters={
                "action": "query",
                "list": "embeddedin",
                "eititle": f"Template:Infobox {t}",
                "einamespace": 0,
                "eilimit": "max",
                "format": "json",
                **cont,
            },
        )
        d = req.submit()
        titles.update(p["title"] for p in d["query"]["embeddedin"])
        if "continue" in d:
            cont = d["continue"]
        else:
            break
titles = sorted(titles)
print(f"引用页合计 {len(titles)}")

# 2) 批量取源码
pages = {}
for i in range(0, len(titles), 25):
    req = api.Request(
        site=site,
        parameters={
            "action": "query",
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "titles": "|".join(titles[i : i + 25]),
            "format": "json",
            "formatversion": "2",
        },
    )
    for p in req.submit()["query"]["pages"]:
        if "revisions" in p:
            pages[p["title"]] = p["revisions"][0]["slots"]["main"]["content"]
print(f"取回源码 {len(pages)}")

# 3) 逐页改写
edited, skipped = [], []
for title, txt in pages.items():
    norm = txt.replace("\r\n", "\n").replace("\r", "\n")
    if norm.lstrip().startswith("#"):
        skipped.append((title, "redirect"))
        continue
    if "name_ja_kanji" not in norm:
        skipped.append((title, "no-field"))
        continue
    new, n = PARAM_RE.subn(r"\1 name_ja =", norm)
    leftover = new.count("name_ja_kanji")
    if leftover:
        skipped.append((title, f"leftover={leftover}"))
        print(
            f"!! {title}: 替换 {n} 行后仍残留 {leftover} 处 name_ja_kanji，跳过待人工"
        )
        continue
    p = pywikibot.Page(site, title)
    p.text = new
    p.save(
        summary="信息框参数改名：name_ja_kanji → name_ja（字段实为日文名原文，名不副实）",
        bot=True,
    )
    edited.append((title, n))
    print(f"OK {title} ({n}行)")

with open("logs/rename_name_ja_result.json", "w", encoding="utf-8") as f:
    json.dump(
        {"edited": edited, "skipped": skipped},
        f,
        ensure_ascii=False,
        indent=1,
    )
print(f"\n完成：编辑 {len(edited)}，跳过 {len(skipped)}")
for t, why in skipped:
    print(f"  跳过 {t}: {why}")
