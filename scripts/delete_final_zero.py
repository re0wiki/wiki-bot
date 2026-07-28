"""删除最后一批零引用模板（2026-07-28，用户确认）。

Delete（+/doc）、Ruby-zh-b、Ruby-zh-p、R/ja 全站 grep 双确认零引用；
连带删除空分类 Category:请求删除（0 成员，入链仅索引页与 Delete 自身）。
删除后打印索引页相关行供下一步更新。
"""

import json

import pywikibot

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

PAGES = [
    "Template:Delete",
    "Template:Delete/doc",
    "Template:Ruby-zh-b",
    "Template:Ruby-zh-p",
    "Template:R/ja",
    "Category:请求删除",
]
archive = {}
for t in PAGES:
    p = pywikibot.Page(site, t)
    assert p.exists(), t
    archive[t] = p.text
with open("logs/deleted_final_zero_2026-07-28.json", "w", encoding="utf-8") as f:
    json.dump(archive, f, ensure_ascii=False, indent=1)

for t in PAGES:
    p = pywikibot.Page(site, t)
    p.delete(reason="零引用模板清理：从未使用，随模板体系精简删除", prompt=False)
    print(f"deleted {t}")

idx_text = pywikibot.Page(site, "ReZero Wiki:模板").text
for line in idx_text.splitlines():
    if any(k in line for k in ("Delete", "Ruby-zh", "请求删除", "R/ja")):
        print("IDX:", repr(line))
print("DONE")
