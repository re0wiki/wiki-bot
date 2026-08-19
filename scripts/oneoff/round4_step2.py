"""例外参数归一 步骤⑤⑥⑦：复扫 → 摘 fallback + doc 同步 → 快照对比。

前置：fix:para 已正式跑完（round4_step1.py 已执行）。
"""

import json
import re

import pywikibot
from pywikibot.data import api

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

# ── ⑤ 复扫：Caption 与 QA 旧名零残留 ──────────────────────
pat_cap = re.compile(r"\|\s*Caption\s*=")
pat_qa = re.compile(r"\|\s*(EQ|EA|JQ|JA)\s*=")
residual = []
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
            # /doc 的语法示例是本脚本 ⑥ 的手动同步对象，不算残留
            if pg["title"].endswith("/doc"):
                continue
            text = (
                pg.get("revisions", [{}])[0]
                .get("slots", {})
                .get("main", {})
                .get("*", "")
            )
            if pat_cap.search(text) or pat_qa.search(text):
                residual.append(pg["title"])
        if "continue" in data:
            params.update(data["continue"])
            data = api.Request(site=site, parameters=params).submit()
        else:
            break
    print(f"ns {ns} rescanned, residual={len(residual)}", flush=True)
assert not residual, f"旧名残留: {residual}"
print("⑤ 旧名零残留确认")


def edit(title, replacements, summary):
    page = pywikibot.Page(site, title)
    text = page.text
    for old, new, n in replacements:
        cnt = text.count(old)
        assert cnt == n, f"{title}: {old!r} 命中 {cnt} 次，预期 {n}"
        text = text.replace(old, new)
    page.text = text
    page.save(summary=summary)
    print(f"saved {title}")


# ── ⑥ 摘 Caption fallback（7 个信息框）────────────────────
SUM1 = "参数名归一收尾：摘除 Caption fallback（全站已归一 caption）"
FB = '<caption source="caption"><default>{{{Caption|}}}</default></caption>'
for name in ("anime", "bd", "event", "game", "music"):
    edit(
        f"Template:Infobox {name}",
        [(f"        {FB}", '        <caption source="caption"/>', 1)],
        SUM1,
    )
for name in ("seiyu", "staff"):
    edit(
        f"Template:Infobox {name}",
        [(f"    {FB}", '    <caption source="caption"></caption>', 1)],
        SUM1,
    )

# ── ⑥ doc 同步 ─────────────────────────────────────────────
SUM2 = "参数名归一同步：Caption → caption"
for name in ("anime", "bd", "event", "music", "seiyu", "staff"):
    edit(
        f"Template:Infobox {name}/doc",
        [
            ("| Caption = ", "| caption = ", 1),
            ('"Caption": {', '"caption": {', 1),
            ('"Caption",', '"caption",', 1),
        ],
        SUM2,
    )
edit(
    "Template:Infobox game/doc",
    [
        ("| Caption = ", "| caption = ", 1),
        ('"Caption": {', '"caption": {', 1),
        ('"Caption",', '"caption",', 1),
        ("| Name_en = ", "| subtitle = ", 1),
        ("<code>Name_en</code>", "<code>subtitle</code>", 1),
        ('"Name_en": {', '"subtitle": {', 1),
        ('"Name_en",', '"subtitle",', 1),
    ],
    "参数名归一同步：Caption → caption；Name_en → subtitle（与 name_en「英译」区分）",
)

# QA/doc：参数小写化（显示标签 EQ 等保留）
page = pywikibot.Page(site, "Template:QA/doc")
text = page.text
for old, new in [("EQ", "eq"), ("EA", "ea"), ("JQ", "jq"), ("JA", "ja")]:
    text, n1 = re.subn(rf"\|{old}=", f"|{new}=", text)
    assert n1 == 2, f"QA/doc |{old}= 命中 {n1} 次，预期 2"
    text, n2 = re.subn(rf'"{old}": \{{', f'"{new}": {{', text)
    assert n2 == 1, f'QA/doc "{old}": {{ 命中 {n2} 次，预期 1'
    text = re.sub(rf'"{old}",', f'"{new}",', text)  # paramOrder（若有）
page.text = text
page.save(summary="QA 参数名小写化同步（EQ/EA/JQ/JA → eq/ea/jq/ja）")
print("saved Template:QA/doc")

# ── ⑦ 快照对比 ─────────────────────────────────────────────
with open("logs/round4_snapshots_before.json", encoding="utf-8") as f:
    before = json.load(f)


def norm(html: str) -> str:
    html = re.sub(r'data-source="[^"]*"', "", html)
    html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
    html = re.sub(r"pi-tab(panel)?-[0-9a-f]+", r"pi-tab\1", html)
    return html


ok = True
for title, old_html in before.items():
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
    same = norm(old_html) == norm(r["parse"]["text"]["*"])
    print(f"⑦ {title}: 渲染等价={same}")
    ok = ok and same
assert ok, "快照对比存在差异，需人工核查"
print("ALL DONE")
