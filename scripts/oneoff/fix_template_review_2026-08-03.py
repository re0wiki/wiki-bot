"""2026-08-03 模板复查发现的全部修复（docs/todo.md 待办 1-6）。

每页：精确匹配断言 → 替换 → 保存（bot=False，手动编辑不加 bot flag）。
失败即停，不静默跳过。
"""

import re
import sys

import pywikibot

DRY = "-s" in sys.argv

site = pywikibot.Site("zh", "re0")
if not DRY:
    site.login()
    assert site.user() == "IchiSanNi"

edits = []  # (title, [替换对 (old, new, count)], summary)

# ── 1. 行内模板尾部换行并入 noinclude ──────────────────────
NL = r"\r?\n"
for t in [
    "Elf",
    "Seirei",
    "Yousei",
    "加护",
    "Tooltip",
    "Seirei or Elf",
    "Yousei or Elf",
]:
    edits.append(
        (
            f"Template:{t}",
            [(re.compile(NL + r"<noinclude>"), "<noinclude>{NL}", 1)],
            "修复尾部换行被 transclude 导致行内多余空格（换行并入 noinclude）",
        )
    )

edits.append(
    (
        "Template:Ruby",
        [
            (
                re.compile(
                    NL
                    + re.escape("<noinclude>{{Documentation}}</noinclude>")
                    + NL
                    + re.escape("<noinclude>[[Category:注音模板]]</noinclude>")
                ),
                "<noinclude>{NL}{{Documentation}}{NL}[[Category:注音模板]]</noinclude>",
                1,
            )
        ],
        "修复尾部换行被 transclude（双 noinclude 合并，换行并入 noinclude）",
    )
)

edits.append(
    (
        "Template:Copy",
        [
            (
                re.compile(
                    re.escape("</noinclude>")
                    + NL
                    + re.escape("<noinclude>[[Category:格式模板]]</noinclude>")
                ),
                "[[Category:格式模板]]</noinclude>",
                1,
            )
        ],
        "修复双 noinclude 之间换行被 transclude（合并为一个 noinclude）",
    )
)

# ── 2. /doc 模板链接约定：{{[[Template:X|X]]}} → {{T|X}} ──
T_LINK = re.compile(r"\{\{\[\[Template:([^]|]+)\|[^]]*\]\]\}\}")
for t in [
    "Disambiguation",
    "Elf",
    "Kana2Romaji",
    "QA list",
    "Ringa",
    "Ruby-ja",
    "Seirei or Elf",
    "Seirei",
    "T category",
]:
    edits.append(
        (
            f"Template:{t}/doc",
            [(T_LINK, r"{{T|\1}}", 0)],  # 0 = 全部替换
            "文档约定：模板链接改用 {{T}}（替换 {{[[Template:X|X]]}} 写法）",
        )
    )

# ── 3. Blur 分类 ──────────────────────────────────────────
edits.append(
    (
        "Template:Blur",
        [(re.compile(re.escape("[[Category:模板]]")), "[[Category:格式模板]]", 1)],
        "分类修正：根 Category:模板 → Category:格式模板（与索引页分节一致）",
    )
)

# ── 4. 索引页 NoteTA 挪节 ─────────────────────────────────
edits.append(
    (
        "ReZero Wiki:模板",
        [
            (re.compile(r"\r?\n\* \{\{t\|NoteTA\}\} — 字词转换"), "", 1),
            (
                re.compile(
                    r"== 内容与作品 ==\r?\n作品设定相关的字词转换模板，全系列见 \[\[:Category:字词转换模板\]\]。"
                ),
                "== 字词转换 ==\n字词转换模板，全系列见 [[:Category:字词转换模板]]。",
                1,
            ),
            (
                re.compile(
                    r"(\* \{\{t\|Seirei\}\} / \{\{t\|Yousei\}\} / \{\{t\|Elf\}\} — 精灵／妖精／Elf 字词转换（译名复核通过后的正式形态）)"
                ),
                r"\1{NL}* {{t|NoteTA}} — 地区词转换（通用机制，非作品设定）",
                1,
            ),
        ],
        "NoteTA 移至字词转换节（与模板自身分类一致）",
    )
)

# ── 5. Twitter 兼容位置参数 + https ───────────────────────
edits.append(
    (
        "Template:Twitter",
        [
            (
                re.compile(
                    re.escape("[http://www.twitter.com/{{{#|}}}/ {{{#|}}} / Twitter]")
                ),
                "[https://twitter.com/{{{1|{{{#|}}}}}}/ {{{1|{{{#|}}}}}} / Twitter]",
                1,
            ),
        ],
        "兼容位置参数（原仅支持 |#=，位置参数静默失效）；http → https",
    )
)
edits.append(
    (
        "Template:Twitter/doc",
        [
            (
                re.compile(
                    re.escape(
                        "'''参数名为 <code>#</code>（井号）'''，调用时必须写成 <code>|#=用户名</code>。"
                    )
                ),
                "用户名写位置参数或历史兼容的 <code>|#=用户名</code> 均可。",
                1,
            ),
            (
                re.compile(re.escape('"#": {')),
                '"1": {{NL}\t\t\t"aliases": [{NL}\t\t\t\t"#"{NL}\t\t\t],',
                1,
            ),
            (
                re.compile(r'"paramOrder": \[\r?\n\t\t"#"\r?\n\t\],'),
                '"paramOrder": [{NL}\t\t"1"{NL}\t],',
                1,
            ),
        ],
        "文档同步：位置参数兼容（templatedata 主参数改为 1，# 列为别名）",
    )
)

# ── 6. Sandbox 清空为最小占位 ─────────────────────────────
edits.append(
    (
        "Template:Sandbox",
        [("WHOLE_PAGE", "<noinclude>{{Documentation}}</noinclude>", 1)],
        "清空为最小沙盒占位（原内容是过时的 67 集 Tab 硬编码测试），摘除格式模板分类",
    )
)

for title, subs, summary in edits:
    p = pywikibot.Page(site, title)
    old = p.text
    nl = "\r\n" if "\r\n" in old else "\n"
    new = old
    for pat, repl, count in subs:
        if pat == "WHOLE_PAGE":
            new = repl
            continue
        repl = repl.replace("{NL}", nl)
        new, n = pat.subn(repl, new, count=count if count else 0)
        expected = count if count else None
        if expected is not None:
            assert n == expected, f"{title}: 期望替换 {expected} 处，实际 {n} 处"
        else:
            assert n > 0, f"{title}: 未找到任何 {pat.pattern!r}"
    assert new != old, f"{title}: 内容无变化"
    if DRY:
        print(f"DRY {title}")
        print(f"  --- old tail ---  {old[-120:]!r}")
        print(f"  --- new tail ---  {new[-120:]!r}")
        continue
    p.text = new
    p.save(summary=summary, bot=False)
    print(f"OK  {title}", flush=True)

print("\n全部完成" if not DRY else "\n干跑通过", file=sys.stderr)
