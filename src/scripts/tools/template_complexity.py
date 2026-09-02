"""分析 zh 站全部模板源码的复杂度，找出适合用 Lua Module 重写的候选。

只读。输出到 logs/template_complexity.json 并打印排序后的候选清单。
复杂度指标：
- parser function 数量（#if/#ifeq/#switch/#expr/#ifexist/#time/#invoke 等）
- 嵌套深度（{{ }} 括号深度最大值）
- 源码长度
- 是否已走 Module（含 #invoke）
"""

import json
import os
import re
from typing import Any

os.environ.pop("PYTHONPATH", None)

import pywikibot
from pywikibot.data import api

site = pywikibot.Site("zh", "re0")

gen = api.QueryGenerator(
    site=site,
    action="query",
    generator="allpages",
    gapnamespace=10,
    gaplimit="max",
    prop="revisions",
    rvprop="content",
    rvslots="main",
)

pages = {}
for info in gen:
    revs = info.get("revisions")
    text = revs[0]["slots"]["main"]["*"] if revs else ""
    pages[info["title"]] = text

PARSER_RE = re.compile(r"\{\{\s*(#\w+)\s*[:|}]")
INVOKE_RE = re.compile(r"\{\{\s*#invoke\s*:", re.IGNORECASE)


def max_depth(text):
    depth = best = 0
    i = 0
    while i < len(text) - 1:
        two = text[i : i + 2]
        if two == "{{":
            depth += 1
            best = max(best, depth)
            i += 2
        elif two == "}}":
            depth = max(0, depth - 1)
            i += 2
        else:
            i += 1
    return best


rows: list[dict[str, Any]] = []
for title, text in pages.items():
    short = title.split(":", 1)[1]
    if "/" in short:  # 只看顶层模板
        continue
    funcs = PARSER_RE.findall(text)
    rows.append(
        {
            "title": title,
            "len": len(text),
            "parser_funcs": len(funcs),
            "func_kinds": sorted({f.lower() for f in funcs}),
            "max_depth": max_depth(text),
            "uses_module": bool(INVOKE_RE.search(text)),
            "n_templates_called": len(re.findall(r"\{\{(?![#!])", text)),
        }
    )

# 复杂度分：parser function 数量*3 + 嵌套深度*2 + 长度/200
for r in rows:
    r["score"] = r["parser_funcs"] * 3 + r["max_depth"] * 2 + r["len"] / 200

rows.sort(key=lambda r: -r["score"])

os.makedirs("logs", exist_ok=True)
with open("logs/template_complexity.json", "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=1)

print(f"{'模板':<28} {'长度':>6} {'函数':>4} {'深度':>4} {'Module':>6}  函数种类")
for r in rows[:30]:
    print(
        f"{r['title'][:27]:<28} {r['len']:>6} {r['parser_funcs']:>4} "
        f"{r['max_depth']:>4} {r['uses_module']!s:>6}  {','.join(r['func_kinds'])}"
    )
print(
    "\n零 parser function 且零嵌套的简单模板数:",
    sum(1 for r in rows if r["parser_funcs"] == 0 and r["max_depth"] <= 2),
)
