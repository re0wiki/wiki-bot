"""P8-D3 合流部署：变更月表 + 新非空月表 /doc 补 invoke + 主模块 204 全月注册。"""

from pathlib import Path

import pywikibot

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

# 主模块重生成（data_names 已程序化，直接推 emit 产物）
main_src = Path("logs/p8/main.lua").read_text(encoding="utf-8")
p = pywikibot.Page(site, "Module:NekoQuote")
if p.text != main_src:
    p.text = main_src
    p.save(summary="P8 合流：主模块同步", bot=True)
print("主模块 ✓")

# 变更月表 = emit 与上次部署快照（lua_live）不一致的
changed = []
for f in sorted(Path("logs/p8/lua").glob("*.lua")):
    live = Path("logs/p8/lua_live") / f.name
    if not live.exists() or live.read_text(encoding="utf-8") != f.read_text(
        encoding="utf-8"
    ):
        changed.append(f.stem)
print(f"变更月表 {len(changed)} 张（vs 上次部署）")

for m in changed:
    content = (Path("logs/p8/lua") / f"{m}.lua").read_text(encoding="utf-8")
    p = pywikibot.Page(site, f"Module:NekoQuote/{m}")
    p.text = content
    p.save(summary="P8 合流：月表增量更新（构建器重放）", bot=True)
    # /doc：新非空月表补骨架（统一 Template:NekoQuoteDoc）
    d = pywikibot.Page(site, f"Module:NekoQuote/{m}/doc")
    if "{{NekoQuoteDoc}}" not in d.text:
        d.text = "{{NekoQuoteDoc}}"
        d.save(summary="P8 合流：/doc 骨架", bot=True)
    print(f"  {m} ✓", flush=True)
print("完成")
