"""部署：变更月表 + 新非空月表 /doc 补骨架 + 主模块同步（全部对 lua_live 快照差量）。"""

import pywikibot

from . import DATA

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

# 主模块重生成（data_names 已程序化，直接推 emit 产物）
main_src = (DATA / "main.lua").read_text(encoding="utf-8")
p = pywikibot.Page(site, "Module:NekoQuote")
if p.text != main_src:
    p.text = main_src
    p.save(summary="语录主模块同步", bot=True)
print("主模块 ✓")

# 变更月表 = emit 与上次部署快照（lua_live）不一致的
changed = []
for f in sorted((DATA / "lua").glob("*.lua")):
    live = DATA / "lua_live" / f.name
    if not live.exists() or live.read_text(encoding="utf-8") != f.read_text(
        encoding="utf-8"
    ):
        changed.append(f.stem)
print(f"变更月表 {len(changed)} 张（vs 上次部署）")

for m in changed:
    content = (DATA / "lua" / f"{m}.lua").read_text(encoding="utf-8")
    p = pywikibot.Page(site, f"Module:NekoQuote/{m}")
    p.text = content
    p.save(summary="语录月表增量更新", bot=True)
    # /doc：新非空月表补骨架（统一 Template:NekoQuoteDoc）
    d = pywikibot.Page(site, f"Module:NekoQuote/{m}/doc")
    if "{{NekoQuoteDoc}}" not in d.text:
        d.text = "{{NekoQuoteDoc}}"
        d.save(summary="语录 /doc 骨架", bot=True)
    print(f"  {m} ✓", flush=True)
print("完成")
