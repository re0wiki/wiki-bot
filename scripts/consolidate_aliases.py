"""别名收敛（2026-07-28，用户确认）：

1. BV 为正：全站 {{AV}} 改 {{BV}}（21 处），删重定向 Template:AV；BV/doc 摘掉别名行
2. QUOTE ← Quote/big 内容，删 Quote/big
3. Quote ← Quote/small 内容，删 Quote/small
4. Tab/Quote 链接更新
删除前存档 logs/。
"""

import json
import re

from pywikibot.data import api

import pywikibot

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

# ---- 1. 全站 {{AV}} -> {{BV}} ----
pat = re.compile(r"\{\{\s*(subst:\s*)?[Aa]V\s*(?=[|}<])")
renamed = []
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
            if title in ("Template:AV", "Template:BV") or title.startswith(
                "Template:BV/"
            ):
                continue
            text = (
                pg.get("revisions", [{}])[0]
                .get("slots", {})
                .get("main", {})
                .get("*", "")
            )
            if not pat.search(text):
                continue
            p = pywikibot.Page(site, title)
            new = pat.sub(lambda m: "{{" + (m.group(1) or "") + "BV ", p.text)
            assert new != p.text
            p.text = new
            p.save(summary="模板改名：AV -> BV（规范名，B站现行 ID 格式）", bot=True)
            renamed.append(title)
            print(f"renamed {title}")
        if "continue" in data:
            params.update(data["continue"])
            data = api.Request(site=site, parameters=params).submit()
        else:
            break
print(f"AV->BV renamed {len(renamed)} pages")
assert len(renamed) == 21, len(renamed)

# ---- 2+3. 内容并入正主 ----
for canonical, sub in [("QUOTE", "Quote/big"), ("Quote", "Quote/small")]:
    src = pywikibot.Page(site, f"Template:{sub}")
    dst = pywikibot.Page(site, f"Template:{canonical}")
    assert dst.isRedirectPage()
    dst.text = src.text
    dst.save(
        summary=f"{sub} 并入 {canonical}：{canonical} 由重定向转为模板本体", bot=True
    )
    print(f"updated Template:{canonical}")

# ---- 4. Tab/Quote ----
tab = pywikibot.Page(site, "Template:Tab/Quote")
text = tab.text
assert "[[Template:Quote/big]]" in text and "[[Template:Quote/small]]" in text
text = text.replace("[[Template:Quote/big]]", "[[Template:QUOTE]]")
text = text.replace("[[Template:Quote/small]]", "[[Template:Quote]]")
tab.text = text
tab.save(summary="别名收敛：分页链接指向正主 QUOTE / Quote", bot=True)
print("updated Template:Tab/Quote")

# ---- BV/doc 摘别名行 ----
doc = pywikibot.Page(site, "Template:BV/doc")
text = doc.text
OLD = ";别名\n{{T|AV}}\n"
assert OLD in text
doc.text = text.replace(OLD, "")
doc.save(summary="别名 AV 已删除（统一为 BV）", bot=True)
print("updated Template:BV/doc")

# ---- 删除别名/子页（存档） ----
archive = {}
for t in ["Template:AV", "Template:Quote/big", "Template:Quote/small"]:
    p = pywikibot.Page(site, t)
    assert p.exists()
    archive[t] = p.text
with open("logs/deleted_aliases_2026-07-28.json", "w", encoding="utf-8") as f:
    json.dump(archive, f, ensure_ascii=False, indent=1)
for t, reason in [
    ("Template:AV", "别名收敛：统一为 BV，用量已由 jobs 模板替换接管"),
    ("Template:Quote/big", "已并入 Template:QUOTE"),
    ("Template:Quote/small", "已并入 Template:Quote"),
]:
    p = pywikibot.Page(site, t)
    p.delete(reason=reason, prompt=False)
    print(f"deleted {t}")
print("DONE")
