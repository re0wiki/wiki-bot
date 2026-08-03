"""2026-08-03 模板复查（第二轮）全部修复（docs/todo.md 待办 A1-A3、B4-B6）。

每页：精确匹配断言 → 替换 → 保存（bot=False，手动编辑不加 bot flag）。
保存后 action=parse 渲染验证。失败即停，不静默跳过。
"""

import re
import sys

import pywikibot

DRY = "-s" in sys.argv

site = pywikibot.Site("zh", "re0")
if not DRY:
    site.login()
    assert site.user() == "IchiSanNi"

edits = []  # (title, [替换对 (old, new, count)]，count=0 表示全部替换且至少 1 处, summary)

# ── A1. /doc 模板链接约定：{{[[Template:X|X]]}} → {{T|X}} ──
T_LINK = re.compile(r"\{\{\[\[Template:([^]|]+)\|[^]]*\]\]\}\}")
for t in ["QUOTE", "Tooltip", "Yousei or Elf", "Yousei", "加护"]:
    edits.append((
        f"Template:{t}/doc",
        [(T_LINK, r"{{T|\1}}", 0)],
        "文档约定：模板链接改用 {{T}}（替换 {{[[Template:X|X]]}} 写法）",
    ))

# ── A2+B6. Documentation chrome 简体化 + 措辞统一（模板文件→模板文档）──
edits.append((
    "Template:Documentation",
    [
        ("'''模板文件'''", "'''模板文档'''", 1),
        ("編輯模板文件页面", "编辑模板文档", 1),
        ("這如何運作？", "这如何运作？", 1),
        ("此模板有時隱藏或不可見", "此模板有时隐藏或不可见", 1),
    ],
    "chrome 文本简体化（編輯/這如何運作/有時），「模板文件」统一为「模板文档」（与 /doc 约定用语一致）",
))

# ── A3. Documentation 自身补挂 {{Documentation}}（并入已有 noinclude）──
edits.append((
    "Template:Documentation",
    [(
        re.compile(r"<noinclude>(\r?\n)\[\[Category:元模板\]\]"),
        r"<noinclude>\1{{Documentation}}\1[[Category:元模板]]",
        1,
    )],
    "自身补挂 {{Documentation}}（/doc 此前孤儿化），并入已有 noinclude 内",
))

# ── B4. 索引：Seirei or Elf / Yousei or Elf 挪入字词转换节 ──
OR_LINE = "* {{t|Seirei or Elf}} / {{t|Yousei or Elf}} — 译名待复核标记（bot 把条目中直接书写的「精灵」「妖精」自动替换为该标记），引用页归入 [[:Category:需复核译名]]"
SIB_LINE = "* {{t|Seirei}} / {{t|Yousei}} / {{t|Elf}} — 精灵／妖精／Elf 字词转换（译名复核通过后的正式形态）"
edits.append((
    "ReZero Wiki:模板",
    [
        (re.compile(r"\r?\n" + re.escape(OR_LINE)), "", 1),
        (SIB_LINE, SIB_LINE + "{NL}" + OR_LINE, 1),
    ],
    "Seirei or Elf / Yousei or Elf 挪入字词转换节（与模板自身分类一致，同 NoteTA 先例）",
))

# ── B5. 索引：摘除 Sandbox 条目（已清空为最小占位、无分类）──
edits.append((
    "ReZero Wiki:模板",
    [(re.compile(r"\r?\n\* \{\{t\|Sandbox\}\} — 测试用"), "", 1)],
    "摘除 Sandbox 条目（已清空为最小占位并摘除分类，不再是可用格式模板）",
))

for title, subs, summary in edits:
    p = pywikibot.Page(site, title)
    old = p.text
    nl = "\r\n" if "\r\n" in old else "\n"
    new = old
    for pat, repl, count in subs:
        if isinstance(pat, str):
            pat = re.compile(re.escape(pat))
        repl = repl.replace("{NL}", nl)
        new, n = pat.subn(repl, new, count=count if count else 0)
        if count:
            assert n == count, f"{title}: 期望替换 {count} 处，实际 {n} 处"
        else:
            assert n > 0, f"{title}: 未找到任何 {pat.pattern!r}"
    assert new != old, f"{title}: 内容无变化"
    if DRY:
        print(f"DRY {title}")
        continue
    p.text = new
    p.save(summary=summary, bot=False)
    print(f"OK  {title}", flush=True)

if DRY:
    print("\n干跑通过", file=sys.stderr)
    sys.exit(0)

# ── 渲染验证 ────────────────────────────────────────────────
def parse_html(title):
    r = site.simple_request(action="parse", page=title, prop="text").submit()
    return r["parse"]["text"]["*"]


fails = []

# 1. Documentation 自身：chrome 简体 + 措辞 + 自渲染 /doc
h = parse_html("Template:Documentation")
for good in ["模板文档", "这如何运作？", "本模板用于把模板文档渲染进模板页"]:
    if good not in h:
        fails.append(f"Documentation 缺 {good!r}")
for bad in ["編輯", "這如何運作", "模板文件"]:
    if bad in h:
        fails.append(f"Documentation 仍含 {bad!r}")

# 2. 其他模板页 chrome 联动更新（经 transclusion）
h = parse_html("Template:R")
if "这如何运作？" not in h:
    fails.append("Template:R chrome 未联动更新")

# 3. 5 个 /doc：{{T}} 渲染为模板链接，无残留 {{[[
for t in ["QUOTE", "Tooltip", "Yousei or Elf", "Yousei", "加护"]:
    h = parse_html(f"Template:{t}/doc")
    if "{{[[" in h:
        fails.append(f"{t}/doc 仍含 {{{{[[")
    if "/wiki/Template:" not in h:
        fails.append(f"{t}/doc 未见模板链接")

# 4. 索引页：Sandbox 摘除、or-variants 挪节
idx = pywikibot.Page(site, "ReZero Wiki:模板").text
if "{{t|Sandbox}}" in idx:
    fails.append("索引仍含 Sandbox")
sec_conv = idx.split("== 字词转换 ==", 1)[1].split("==", 1)[0]
sec_maint = idx.split("== 页首与维护 ==", 1)[1].split("==", 1)[0]
if "Seirei or Elf" not in sec_conv:
    fails.append("字词转换节未见 Seirei or Elf")
if "Seirei or Elf" in sec_maint:
    fails.append("页首与维护节仍含 Seirei or Elf")

if fails:
    print("\n验证失败：")
    for f in fails:
        print(" -", f)
    sys.exit(1)
print("\n全部修复完成，渲染验证 12 项全过")
