"""例外参数归一 步骤①②③：快照 → 模板 fallback/直改 → QA 页与模板。

- Caption → caption：7 个信息框加 fallback（83 页在用）
- Name_en → subtitle：game 直改（0 页在用；与 name_en「英译」字段区分）
- QA 的 EQ/EA/JQ/JA → 小写：先快照，改唯一使用页 存档:菲莉丝/问答，再直改模板
快照存 logs/round4_snapshots_before.json。
"""

import json
import re

import pywikibot
from pywikibot.data import api

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

# ── ③ 快照（任何改动前）────────────────────────────────────
# 找 6 个 Caption 使用页
pat_cap = re.compile(r"\|\s*Caption\s*=")
samples = []
params = {
    "action": "query",
    "format": "json",
    "generator": "allpages",
    "gapnamespace": "0",
    "gaplimit": "50",
    "prop": "revisions",
    "rvprop": "content",
    "rvslots": "main",
}
data = api.Request(site=site, parameters=params).submit()
while True:
    for pg in data.get("query", {}).get("pages", {}).values():
        text = (
            pg.get("revisions", [{}])[0].get("slots", {}).get("main", {}).get("*", "")
        )
        if pat_cap.search(text):
            samples.append(pg["title"])
    if len(samples) >= 40 or "continue" not in data:
        break
    params.update(data["continue"])
    data = api.Request(site=site, parameters=params).submit()
# 均匀取 6 个
samples = [samples[i * len(samples) // 6] for i in range(6)]
samples.append("存档:菲莉丝/问答")
print(f"快照页: {samples}")

snaps = {}
for title in samples:
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
    snaps[title] = r["parse"]["text"]["*"]
with open("logs/round4_snapshots_before.json", "w", encoding="utf-8") as f:
    json.dump(snaps, f, ensure_ascii=False)
print("快照已存")


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


# ── ② Caption fallback（7 个信息框）────────────────────────
SUM = "参数名归一：Caption → caption（先加 fallback，fix:para 全站归一后摘除）"
FB = '<caption source="caption"><default>{{{Caption|}}}</default></caption>'
for name in ("anime", "bd", "event", "game", "music"):
    edit(
        f"Template:Infobox {name}",
        [('        <caption source="Caption"/>', f"        {FB}", 1)],
        SUM,
    )
for name in ("seiyu", "staff"):
    edit(
        f"Template:Infobox {name}",
        [('    <caption source="Caption"></caption>', f"    {FB}", 1)],
        SUM,
    )

# ── ② game Name_en → subtitle（零用量，直改）──────────────
edit(
    "Template:Infobox game",
    [('    <title source="Name_en">', '    <title source="subtitle">', 1)],
    "参数名归一：Name_en → subtitle（副标题；零使用页直改，与 name_en「英译」字段区分）",
)

# ── ② QA：先改唯一使用页，再直改模板 ──────────────────────
qa_page = pywikibot.Page(site, "存档:菲莉丝/问答")
text = qa_page.text
total = 0
for old, new in [("EQ", "eq"), ("EA", "ea"), ("JQ", "jq"), ("JA", "ja")]:
    text, n = re.subn(rf"\|\s*{old}\s*=", f"| {new} =", text)
    total += n
assert total > 0
qa_page.text = text
qa_page.save(summary=f"QA 参数名小写化（EQ/EA/JQ/JA → eq/ea/jq/ja，{total} 处）")
print(f"saved 存档:菲莉丝/问答 ({total} 处)")

qa_tpl = pywikibot.Page(site, "Template:QA")
text = qa_tpl.text
for old, new in [("EQ", "eq"), ("EA", "ea"), ("JQ", "jq"), ("JA", "ja")]:
    text, n1 = re.subn(rf"\{{\{{\{{{old}\|\}}\}}\}}", f"{{{{{{{new}|}}}}}}", text)
    text, n2 = re.subn(rf"\{{\{{\{{{old}\}}\}}\}}", f"{{{{{{{new}}}}}}}", text)
    assert n1 + n2 == 2, f"{old}: 命中 {n1 + n2} 次，预期 2"
qa_tpl.text = text
qa_tpl.save(summary="QA 参数名小写化（EQ/EA/JQ/JA → eq/ea/jq/ja；显示标签不变）")
print("saved Template:QA")
print("DONE")
