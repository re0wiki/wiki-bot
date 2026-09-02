"""只读：扫描 Template 命名空间所有页面，找出未包 <nowiki> 的 -{ 出现位置。

输出：页面名 + 每次出现的上下文，标注是否在 <pre>/<code> 内（供人工判断字面 vs 功能性）。
跳过批 3 子代理正在写的 10 个 /doc（避免冲突，稍后补扫）。
"""

import os
import re

os.environ.pop("PYTHONPATH", None)

import pywikibot
from pywikibot.data import api

site = pywikibot.Site("zh", "re0")

BATCH3_DOCS = {
    f"Template:{n}/doc"
    for n in [
        "Clear",
        "Collapse",
        "MG",
        "Main",
        "QA list",
        "Ringa",
        "Tooltip",
        "Twitter",
        "WP",
        "加护",
    ]
}

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

NOWIKI_RE = re.compile(r"<nowiki>.*?</nowiki>", re.DOTALL | re.IGNORECASE)

hits = []
for info in gen:
    title = info["title"]
    if title in BATCH3_DOCS:
        continue
    revs = info.get("revisions")
    if not revs:
        continue
    text = revs[0]["slots"]["main"]["*"]
    # 抹掉 nowiki 包裹段后找 -{
    stripped = NOWIKI_RE.sub(lambda m: " " * (m.end() - m.start()), text)
    for m in re.finditer(r"-\{", stripped):
        s = max(0, m.start() - 80)
        e = min(len(text), m.end() + 80)
        ctx = text[s:e].replace("\n", "⏎")
        in_pre = text.rfind("<pre", 0, m.start()) > text.rfind("</pre>", 0, m.start())
        in_code = text.rfind("<code", 0, m.start()) > text.rfind(
            "</code>", 0, m.start()
        )
        hits.append((title, m.start(), in_pre, in_code, ctx))

print(f"共 {len(hits)} 处未包 nowiki 的 -{{：\n")
for title, pos, in_pre, in_code, ctx in hits:
    flags = []
    if in_pre:
        flags.append("pre")
    if in_code:
        flags.append("code")
    print(f"[{title}] @{pos} ({','.join(flags) or '裸'})")
    print(f"  …{ctx}…")
