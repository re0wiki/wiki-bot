"""一次性盘点脚本：zh 站模板命名空间全量清单 + 文档/分类覆盖情况。

只读。输出 JSON 到 logs/template_inventory.json。
"""

import json
import os
import re

os.environ.pop("PYTHONPATH", None)

from pywikibot.data import api

import pywikibot

site = pywikibot.Site("zh", "re0")

# ── 1. 模板命名空间全部页面 ─────────────────────────────────
gen = api.QueryGenerator(
    site=site,
    action="query",
    generator="allpages",
    gapnamespace=10,
    gaplimit="max",
    prop="revisions|categories",
    rvprop="content",
    rvslots="main",
    cllimit="max",
    clshow="!hidden",
)

pages = {}
for info in gen:
    # 带 generator 时 QueryGenerator 逐页 yield page dict
    title = info["title"]
    text = ""
    revs = info.get("revisions")
    if revs:
        text = revs[0]["slots"]["main"]["*"]
    cats = [c["title"] for c in info.get("categories", [])]
    pages[title] = {"text": text, "categories": cats}

print(f"模板命名空间总页面数: {len(pages)}")

tops = {t: v for t, v in pages.items() if "/" not in t.split(":", 1)[1]}
subs = {t: v for t, v in pages.items() if "/" in t.split(":", 1)[1]}
print(f"顶层模板: {len(tops)}  子页: {len(subs)}")

doc_subpages = {t for t in subs if t.rsplit("/", 1)[1] == "doc"}
print(f"/doc 子页: {len(doc_subpages)}")

# ── 2. 每个顶层模板的覆盖情况 ───────────────────────────────
NOINCLUDE_RE = re.compile(r"<noinclude>(.*?)</noinclude>", re.DOTALL | re.IGNORECASE)
DOC_HINT_RE = re.compile(r"用法|使用说明|参数|示例|说明|usage", re.IGNORECASE)
CAT_RE = re.compile(r"\[\[\s*[Cc]ategory\s*:\s*([^\]|]+)")

inventory = {}
for title, v in tops.items():
    text = v["text"]
    noincludes = "".join(NOINCLUDE_RE.findall(text))
    outside = NOINCLUDE_RE.sub("", text)
    cats_all = [c.strip() for c in CAT_RE.findall(text)]
    cats_in_noinclude = [c.strip() for c in CAT_RE.findall(noincludes)]
    cats_outside = [c.strip() for c in CAT_RE.findall(outside)]
    has_doc_page = f"{title}/doc" in doc_subpages
    uses_doc_tpl = "{{Documentation" in text or "{{documentation" in text
    inline_doc = bool(DOC_HINT_RE.search(noincludes))
    inventory[title] = {
        "len": len(text),
        "categories_from_api": v["categories"],
        "cats_in_wikitext": cats_all,
        "cats_leaked_outside_noinclude": cats_outside,
        "has_doc_subpage": has_doc_page,
        "uses_Documentation_tpl": uses_doc_tpl,
        "inline_doc_in_noinclude": inline_doc,
        "is_redirect": text.lstrip().lower().startswith("#redirect"),
    }


# ── 3. Category:模板 及其子分类 ─────────────────────────────
def cat_members(cat_title):
    cat = pywikibot.Category(site, cat_title)
    members, subcats = [], []
    for m in cat.members(total=2000):
        if m.namespace() == 14:
            subcats.append(m.title())
        else:
            members.append(m.title())
    return sorted(members), sorted(subcats)


tpl_cat_members, tpl_cat_subcats = cat_members("Category:模板")
subcat_detail = {}
for sc in tpl_cat_subcats:
    m, _ = cat_members(sc)
    subcat_detail[sc] = m

result = {
    "n_template_ns_pages": len(pages),
    "n_top_templates": len(tops),
    "n_subpages": len(subs),
    "inventory": inventory,
    "subpages_all": sorted(subs),
    "category_模板": {"members": tpl_cat_members, "subcats": tpl_cat_subcats},
    "subcat_members": subcat_detail,
}

os.makedirs("logs", exist_ok=True)
with open("logs/template_inventory.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=1)

# ── 4. 摘要统计 ─────────────────────────────────────────────
n_doc = sum(1 for v in inventory.values() if v["has_doc_subpage"])
n_uses_doc_tpl = sum(1 for v in inventory.values() if v["uses_Documentation_tpl"])
n_inline = sum(1 for v in inventory.values() if v["inline_doc_in_noinclude"])
n_any_doc = sum(
    1
    for v in inventory.values()
    if v["has_doc_subpage"]
    or v["uses_Documentation_tpl"]
    or v["inline_doc_in_noinclude"]
)
n_redirect = sum(1 for v in inventory.values() if v["is_redirect"])
n_categorized = sum(1 for v in inventory.values() if v["cats_in_wikitext"])
n_leak = sum(1 for v in inventory.values() if v["cats_leaked_outside_noinclude"])

print("\n===== 摘要 =====")
print(f"顶层模板          : {len(tops)}")
print(f"  其中重定向      : {n_redirect}")
print(f"有 /doc 子页      : {n_doc}")
print(f"用 Documentation  : {n_uses_doc_tpl}")
print(f"noinclude 内联文档: {n_inline}")
print(f"有任何文档        : {n_any_doc}")
print(f"缺任何文档        : {len(tops) - n_any_doc}")
print(f"wikitext 里有分类 : {n_categorized}")
print(f"分类泄漏(noinclude外): {n_leak}")
print(f"Category:模板 直属成员: {len(tpl_cat_members)}, 子分类: {len(tpl_cat_subcats)}")
