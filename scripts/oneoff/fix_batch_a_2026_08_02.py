"""A 组修复（2026-08-02 全站模板复查待办）：

1. Template:Category redirect 的全角冒号 style:" -> style="
2. MediaWiki:Common.css @import 摘除 Gadget-Poll.css（已删）与 Gadget-Assert.css（孤儿）
3. 删除 MediaWiki:Gadget-Assert.css（断言体系漏网孤儿）
4. MediaWiki:ImportJS 摘除 dev:AjaxPoll.js（Poll 已清零）

写入前先做删前扫荡：assert-pass/assert-fail class、两个 CSS 页面名的全站残留引用。
"""

import os

os.environ.pop("PYTHONPATH", None)

from pywikibot.data import api

import pywikibot

site = pywikibot.Site("zh", "re0")

# ── 0. 删前扫荡（只读） ────────────────────────────────────
print("=== 删前扫荡 ===")
for term in ["Gadget-Poll.css", "Gadget-Assert.css", "assert-pass", "assert-fail"]:
    gen = api.QueryGenerator(
        site=site,
        action="query",
        list="search",
        srsearch=f'insource:"{term}"',
        srnamespace="0|2|4|6|8|10|14|828",
        srlimit="max",
    )
    hits = [p["title"] for p in gen]
    print(f'  insource:"{term}": {hits}')

site.login()
assert site.user() == "IchiSanNi", site.user()

# ── 1. Category redirect 全角冒号 ──────────────────────────
print("\n=== 1. Template:Category redirect ===")
p = pywikibot.Page(site, "Template:Category redirect")
old = p.text
assert 'style:"border: none;' in old, "全角冒号不在预期位置"
new = old.replace('style:"border: none;', 'style="border: none;')
assert new != old
p.text = new
p.save(summary='修复全角冒号：style:" → style="（属性失效）', bot=False)
print("  saved")

# ── 2. Common.css 摘除两个死 import ────────────────────────
print("\n=== 2. MediaWiki:Common.css ===")
p = pywikibot.Page(site, "MediaWiki:Common.css")
old = p.text
for dead in [
    "MediaWiki:Gadget-Poll.css|",
    "|MediaWiki:Gadget-Poll.css",
    "MediaWiki:Gadget-Poll.css",
]:
    if dead in old:
        old = old.replace(dead, "")
        print(f"  摘除 {dead}")
        break
else:
    raise AssertionError("Gadget-Poll.css 不在 Common.css 中")
for dead in [
    "MediaWiki:Gadget-Assert.css|",
    "|MediaWiki:Gadget-Assert.css",
    "MediaWiki:Gadget-Assert.css",
]:
    if dead in old:
        old = old.replace(dead, "")
        print(f"  摘除 {dead}")
        break
else:
    raise AssertionError("Gadget-Assert.css 不在 Common.css 中")
assert "Poll" not in old and "Assert" not in old
p.text = old
p.save(
    summary="摘除死引用：Gadget-Poll.css（已删除）、Gadget-Assert.css（断言体系孤儿，随删）",
    bot=False,
)
print("  saved")

# ── 3. 删除 Gadget-Assert.css ──────────────────────────────
print("\n=== 3. 删除 MediaWiki:Gadget-Assert.css ===")
p = pywikibot.Page(site, "MediaWiki:Gadget-Assert.css")
assert p.exists()
p.delete(
    reason="断言体系（Assert empty/eq、Module:assert）2026-07-26 已全删，此 CSS 为漏网孤儿",
    prompt=False,
)
assert not p.exists()
print("  deleted")

# ── 4. ImportJS 摘除 AjaxPoll ──────────────────────────────
print("\n=== 4. MediaWiki:ImportJS ===")
p = pywikibot.Page(site, "MediaWiki:ImportJS")
old = p.text
assert "dev:AjaxPoll.js\n" in old
new = old.replace("dev:AjaxPoll.js\n", "")
assert "AjaxPoll" not in new
p.text = new
p.save(summary="摘除 dev:AjaxPoll.js——Poll 模板已删、全站 ajax-poll 零命中", bot=False)
print("  saved")

print("\nALL DONE")
