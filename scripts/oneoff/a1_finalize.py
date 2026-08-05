"""A1 步骤⑤⑥⑦：复扫零残留 → 摘 fallback + doc 补 name_zh_tw → 快照对比。

前置：fix:para 已正式跑完。
"""

import json
import re

from pywikibot.data import api

import pywikibot

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

# ── ⑤ 全命名空间复扫旧名零残留 ─────────────────────────────
pat_old = re.compile(r"\|\s*another translation\s*=", re.IGNORECASE)
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
            text = (
                pg.get("revisions", [{}])[0]
                .get("slots", {})
                .get("main", {})
                .get("*", "")
            )
            if pat_old.search(text):
                residual.append(pg["title"])
        if "continue" in data:
            params.update(data["continue"])
            data = api.Request(site=site, parameters=params).submit()
        else:
            break
    print(f"ns {ns} rescanned, residual={len(residual)}", flush=True)
assert not residual, f"旧名残留: {residual}"
print("⑤ 旧名零残留确认")

# ── ⑥ 摘 fallback + doc 补 name_zh_tw ──────────────────────
tpl = pywikibot.Page(site, "Template:Infobox character")
old = """  <data source="name_zh_tw">
    <label>台版译名</label>
    <default>{{{another translation|}}}</default>
  </data>"""
new = """  <data source="name_zh_tw">
    <label>台版译名</label>
  </data>"""
assert tpl.text.count(old) == 1, "fallback 块匹配失败"
tpl.text = tpl.text.replace(old, new)
tpl.save(summary="参数名归一收尾：摘除 another translation fallback（全站已零残留）")
print("⑥ 模板 fallback 已摘")

doc = pywikibot.Page(site, "Template:Infobox character/doc")
# templatedata：nickname 块后插入 name_zh_tw；paramOrder 同步
old_td = '\t\t"nickname": {\n\t\t\t"label": "昵称",\n\t\t\t"aliases": [\n\t\t\t\t"Nickname"\n\t\t\t],\n\t\t\t"description": ""\n\t\t},\n'
new_td = (
    old_td
    + '\t\t"name_zh_tw": {\n\t\t\t"label": "台版译名",\n\t\t\t"description": "台湾中文版译名（与通用译名不同时填写）"\n\t\t},\n'
)
assert doc.text.count(old_td) == 1, "templatedata nickname 块匹配失败"
text = doc.text.replace(old_td, new_td)
old_po = '\t\t"nickname",\n'
assert text.count(old_po) == 1, f"paramOrder nickname 匹配 {text.count(old_po)} 次"
text = text.replace(old_po, '\t\t"nickname",\n\t\t"name_zh_tw",\n')
doc.text = text
doc.save(summary="templatedata 补 name_zh_tw（台版译名）参数声明")
print("⑥ doc 已补 name_zh_tw")

# ── ⑦ 快照对比（normalize data-source 属性）────────────────
with open("logs/a1_snapshots_before.json", encoding="utf-8") as f:
    before = json.load(f)


def norm(html: str) -> str:
    html = re.sub(r'data-source="[^"]*"', "", html)
    html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
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
    new_html = r["parse"]["text"]["*"]
    same = norm(old_html) == norm(new_html)
    has_field = "台版译名" in new_html
    print(f"⑦ {title}: 渲染等价={same} 台版译名渲染={has_field}")
    ok = ok and same and has_field
assert ok, "快照对比存在差异，需人工核查"
print("ALL DONE")
