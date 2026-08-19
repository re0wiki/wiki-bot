"""只读：全站模板用量复核（批量 wikitext grep，排除自身与自身 /doc 的引用）。

输出：真零引用模板清单 + 仅被自身文档引用的模板清单。
"""

import datetime
import json
import re

import pywikibot
from pywikibot.data import api

site = pywikibot.Site("zh", "re0")

# 1. 全部顶层模板（含重定向，重定向名也可能是调用名）
templates = []  # (title_without_ns, is_redirect, redirect_target_or_None)
for p in site.allpages(namespace=10):
    t = p.title(with_ns=False)
    if "/" in t:
        continue
    templates.append(t)
print(f"顶层模板 {len(templates)} 个")

# 2. 批量抓全站 wikitext
pages = {}  # title -> wikitext
for ns in (0, 2, 4, 6, 8, 10, 14, 828):
    params = {
        "action": "query",
        "format": "json",
        "generator": "allpages",
        "gapnamespace": str(ns),
        "gaplimit": "50",
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
    }
    data = api.Request(site=site, parameters=params).submit()
    while True:
        for pg in data.get("query", {}).get("pages", {}).values():
            rev = pg.get("revisions", [{}])[0]
            pages[pg["title"]] = rev.get("slots", {}).get("main", {}).get("*", "")
        if "continue" in data:
            params.update(data["continue"])
            data = api.Request(site=site, parameters=params).submit()
        else:
            break
    print(f"ns {ns} done, pages={len(pages)}", flush=True)

# 3. 逐模板统计（排除自身与自身子页）
result = {}
for t in templates:
    pat = re.compile(
        r"\{\{\s*(subst:\s*)?" + re.escape(t).replace(r"\ ", r"[ _]") + r"\s*[|}<]",
        re.IGNORECASE,
    )
    users = []
    for title, text in pages.items():
        if title == f"Template:{t}" or title.startswith(f"Template:{t}/"):
            continue
        if pat.search(text):
            users.append(title)
    result[t] = users

zero = {t: u for t, u in result.items() if not u}
print(f"\n=== 真零引用模板 {len(zero)} 个 ===")
for t in sorted(zero):
    p = pywikibot.Page(site, f"Template:{t}")
    note = ""
    if p.isRedirectPage():
        note = f" [重定向 -> {p.getRedirectTarget().title(with_ns=False)}]"
    print(f"  {t}{note}")

low = {t: u for t, u in result.items() if 0 < len(u) <= 2}
print(f"\n=== 引用 1-2 处的模板 {len(low)} 个 ===")
for t in sorted(low):
    print(f"  {t}: {low[t]}")

today = datetime.datetime.now(tz=datetime.UTC).date()
out = f"logs/template_usage_recheck_{today:%Y-%m-%d}.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(
        {t: u for t, u in sorted(result.items())}, f, ensure_ascii=False, indent=1
    )
print(f"\nsaved {out}")
