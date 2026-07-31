"""只读：全站统计所有模板的直接调用数，输出引用数恰好为 1 的清单。

覆盖全部 Template 命名空间页面（含子页），排除模板自身与自身 /doc。
"""

import json
import re
from collections import defaultdict

from pywikibot.data import api

import pywikibot

site = pywikibot.Site("zh", "re0")

# 全部模板页
templates = []
params = {
    "action": "query",
    "format": "json",
    "generator": "allpages",
    "gapnamespace": "10",
    "gaplimit": "50",
}
data = api.Request(site=site, parameters=params).submit()
while True:
    for pg in data.get("query", {}).get("pages", {}).values():
        templates.append(pg["title"][len("Template:") :])
    if "continue" in data:
        params.update(data["continue"])
        data = api.Request(site=site, parameters=params).submit()
    else:
        break
print(f"templates: {len(templates)}")

pats = {}
for name in templates:
    stem = name[0].upper() + name[1:]
    pats[name] = re.compile(
        r"\{\{\s*(subst:\s*)?["
        + stem[0].lower()
        + stem[0]
        + "]"
        + re.escape(stem[1:]).replace("\\ ", r"[ _]")
        + r"\s*[|}<]"
    )

uses = defaultdict(list)
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
            title = pg["title"]
            text = (
                pg.get("revisions", [{}])[0]
                .get("slots", {})
                .get("main", {})
                .get("*", "")
            )
            if not text:
                continue
            for name, pat in pats.items():
                if title == f"Template:{name}" or title == f"Template:{name}/doc":
                    continue
                if pat.search(text):
                    uses[name].append(title)
        if "continue" in data:
            params.update(data["continue"])
            data = api.Request(site=site, parameters=params).submit()
        else:
            break

with open("logs/template_usage_full_2026-07-28.json", "w", encoding="utf-8") as f:
    json.dump({k: v for k, v in sorted(uses.items())}, f, ensure_ascii=False, indent=1)

ones = {k: v for k, v in uses.items() if len(v) == 1}
print(f"\n=== 引用数=1（{len(ones)} 个）===")
for name, u in sorted(ones.items()):
    print(f"{name} -> {u[0]}")
