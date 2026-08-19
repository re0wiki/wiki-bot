"""删除转义元模板 !、=、!!（2026-07-28，用户确认三个全删）。

! 和 = 自 MW 1.24/1.39 起是内置 magic word（Fandom 跑 1.43.9），实测 {{!}} {{=}} 不产生
transclusion，模板是死代码；!! 无 magic word 但零引用，随族一起删。
删除后验证：magic word 解析不变 + 抽查图库页/信息框页渲染。
"""

import json

import pywikibot
from pywikibot.data import api

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

PAGES = ["Template:!", "Template:!/doc", "Template:=", "Template:!!", "Template:!!/doc"]
archive = {}
for t in PAGES:
    p = pywikibot.Page(site, t)
    assert p.exists(), t
    archive[t] = p.text
with open("logs/deleted_escape_templates_2026-07-28.json", "w", encoding="utf-8") as f:
    json.dump(archive, f, ensure_ascii=False, indent=1)

for t in PAGES:
    p = pywikibot.Page(site, t)
    p.delete(
        reason="转义元模板废弃：{{!}}/{{=}} 自 MW 1.24/1.39 起为内置 magic word，!! 零引用随族清理",
        prompt=False,
    )
    print(f"deleted {t}")

# ---- 验证 1：magic word 仍生效 ----
for code, expect in [("{{!}}", "|"), ("{{=}}", "=")]:
    r = api.Request(
        site=site,
        parameters={
            "action": "parse",
            "text": code,
            "title": "API 测试",
            "contentmodel": "wikitext",
            "prop": "text|templates",
            "format": "json",
        },
    ).submit()["parse"]
    inner = r["text"]["*"].split('dir="ltr">', 1)[-1].split("<!--")[0]
    ok = expect in inner and not r.get("templates")
    print(f"删除后 {code} -> {inner.strip()!r} magic word 生效={ok}")

# ---- 验证 2：抽查真实页面渲染 ----
for title in ["角色:爱蜜莉雅/图库", "角色:菜月·昴/图库", "角色:爱蜜莉雅"]:
    p = pywikibot.Page(site, title)
    if not p.exists():
        print(f"{title} 不存在，跳过")
        continue
    r = api.Request(
        site=site,
        parameters={"action": "parse", "page": title, "prop": "text", "format": "json"},
    ).submit()["parse"]
    html = r["text"]["*"]
    broken = "Template:!" in html or "[[Template:" in html
    print(f"{title}: tabber标记数={html.count('tabber')} 疑似红链={broken}")
print("DONE")
