"""删除 Module:Infobox novel 与 Module:Infobox novel/doc（2026-07-29，用户确认）。

novel→book 改名残留：Module 内容为 shim `return require [[Module:Infobox book]]`，
零引用、全站无调用；en 站 Module 空间无 Infobox 模块，无搬运重引入风险。
删除前 wikitext 存档 logs/deleted_module_infobox_novel_2026-07-29.json。
"""

import json

import pywikibot

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

targets = ["Module:Infobox novel", "Module:Infobox novel/doc"]

archive = {}
for title in targets:
    p = pywikibot.Page(site, title)
    if not p.exists():
        print(f"跳过（不存在）: {title}")
        continue
    archive[title] = p.text
    p.delete(
        reason="Infobox 命名统一：novel→book 改名残留的零引用 shim（规范实现见 Module:Infobox book）",
        prompt=False,
    )
    print(f"已删除: {title}")

with open(
    "logs/deleted_module_infobox_novel_2026-07-29.json", "w", encoding="utf-8"
) as f:
    json.dump(archive, f, ensure_ascii=False, indent=2)
print("存档完成")
