"""as-is 保护标记迁移：<div class="as-is"> 与 <!--nobot--> → <!--as-is--> 注释对。

背景：fork 的 keep 正则已改为匹配注释对 `<!--as-is-->…<!--/as-is-->`
（机制变更动机：div 是块级元素、不能保护行内片段且渲染进 DOM）。
本脚本一次性改写 wiki 上的存量标记：

- 通用：`<div class="as-is">…</div>`（含 `class =` 空格变体）→ `<!--as-is-->…<!--/as-is-->`
- 通用：`<!--nobot-->` → `<!--as-is--><!--/as-is-->`（空注释对 = 点标记，拆词语义不变）
  【后续修正：拆词是 div 时代的技术限制产物，注释可行内使用——
  Seirei/Yousei 已由 asis_followup.py 改为整词包裹 `<!--as-is-->精灵<!--/as-is-->`】
- MediaWiki:Conversiontable/zh-hant：整页外包注释对
  （页内 `<span class="as-is">` 从未被 keep 正则覆盖，是繁体维护者的注记，保留不动）
  【后续修正：整页外包连带保护了简体键名，且 span 系编辑者误用——
  已由 asis_followup.py 改为仅给繁体目标包注释对、清除全部 span】
- 文档页（Wiki-navigation 页首、Ringa/doc、Seirei/doc、Yousei/doc、
  Module:Wiki-navigation/doc）：机制说明文字同步改写（DOC_EDITS）

断言（任一失败则跳过该页并报告，零静默放过）：
- 通用替换后不得残留任何 as-is/nobot 字样（新标记本身除外）；
- 新标记线性扫描配平、不嵌套；
- div 区域内容不得含嵌套的 as-is div。

用法：干跑 `uv run python src/oneoff/asis_comment_migration.py`，
实际写入加 `--apply`（bot flag，需登录）。
"""

import argparse
import re
import sys

import pywikibot

SUMMARY = "保护标记迁移：<div class=as-is> 与 <!--nobot--> 统一改写为 <!--as-is--><!--/as-is--> 注释对"

DIV_RE = re.compile(r'<div\s+class\s*=\s*"as-is"\s*>([\s\S]*?)</div>')
MARKER_RE = re.compile(r"<!--(/?)as-is-->")
ESCAPED_MARKER_RE = re.compile(r"&lt;!--/?as-is--&gt;")

# 文档页中允许残留的 as-is 字样（对机制名的引用，非标记本身）。
ALLOWED_RESIDUAL: dict[str, str] = {"Template:Ringa/doc": "<code>as-is</code>"}

# 文档页的机制说明文字改写（原文均已 HTML 转义或在 nowiki 中，通用正则碰不到）。
DOC_EDITS: dict[str, list[tuple[str, str]]] = {
    "ReZero Wiki:Wiki-navigation": [
        (
            (
                '# 简体中文值不要包 <code><nowiki><div class="as-is"></nowiki></code>'
                "——bot 的译名归一任务会按译名表自动修正；繁体值应包上 as-is 以防被归一成简体。"
            ),
            (
                "# 简体中文值不要包保护标记——bot 的译名归一任务会按译名表自动修正；繁体值应包 "
                "<code><nowiki><!--as-is--></nowiki></code> 与 <code><nowiki><!--/as-is--></nowiki></code> "
                "注释对以防被归一成简体。"
            ),
        ),
    ],
    "Module:Wiki-navigation/doc": [
        (
            "（如 {{T|Seirei}} 已内联为 <code><nowiki>精<!--nobot-->灵</nowiki></code>）",
            "（如 {{T|Seirei}} 已内联为 <code><nowiki>精<!--as-is--><!--/as-is-->灵</nowiki></code>）",
        ),
    ],
    "Template:Ringa/doc": [
        (
            (
                '模板体仍包在 <code>&lt;div class="as-is"&gt;</code>（防 bot 改动注记文本）'
                "与 <code>&lt;onlyinclude&gt;</code> 中。"
            ),
            (
                "模板体仍包在 <code>&lt;!--as-is--&gt;…&lt;!--/as-is--&gt;</code> 注释对"
                "（防 bot 改动注记文本）与 <code>&lt;onlyinclude&gt;</code> 中。"
            ),
        ),
    ],
    "Template:Seirei/doc": [
        (
            "模板源码中的 <code>&lt;!--nobot--&gt;</code> 注释用于防止 bot 译名归一任务改动本词。",
            (
                "模板源码中的 <code>&lt;!--as-is--&gt;&lt;!--/as-is--&gt;</code> 注释对"
                "用于防止 bot 译名归一任务改动本词。"
            ),
        ),
    ],
    "Template:Yousei/doc": [
        (
            "模板源码中的 <code>&lt;!--nobot--&gt;</code> 注释用于防止 bot 译名归一任务改动本词。",
            (
                "模板源码中的 <code>&lt;!--as-is--&gt;&lt;!--/as-is--&gt;</code> 注释对"
                "用于防止 bot 译名归一任务改动本词。"
            ),
        ),
    ],
}

CONVERSIONTABLE = "MediaWiki:Conversiontable/zh-hant"

SCAN_NS = (0, 2, 4, 8, 10, 828)


def div_sub(m: re.Match) -> str:
    inner = m.group(1)
    if DIV_RE.search(inner) or re.search(r'<div\s+class\s*=\s*"as-is"', inner):
        raise ValueError(f"嵌套 as-is div: {inner[:80]!r}")
    return f"<!--as-is-->{inner}<!--/as-is-->"


def check_balance(text: str) -> bool:
    """线性扫描新标记：配平、不嵌套。"""
    depth = 0
    for m in MARKER_RE.finditer(text):
        depth += -1 if m.group(1) else 1
        if not 0 <= depth <= 1:
            return False
    return depth == 0


def transform(title: str, text: str) -> str:
    if title == CONVERSIONTABLE:
        assert not DIV_RE.search(text) and "<!--nobot-->" not in text, (
            "转换表出现意外标记"
        )
        assert not MARKER_RE.search(text), "转换表已有注释标记"
        return f"<!--as-is-->\n{text}\n<!--/as-is-->"

    new = text
    for old, replacement in DOC_EDITS.get(title, []):
        assert new.count(old) == 1, f"文档原文不匹配: {title} :: {old[:50]!r}"
        new = new.replace(old, replacement)

    new = DIV_RE.sub(div_sub, new)
    new = new.replace("<!--nobot-->", "<!--as-is--><!--/as-is-->")

    remainder = MARKER_RE.sub("", new)
    remainder = ESCAPED_MARKER_RE.sub("", remainder)
    if allowed := ALLOWED_RESIDUAL.get(title):
        remainder = remainder.replace(allowed, "")
    assert "as-is" not in remainder, f"残留未识别的 as-is 写法: {title}"
    assert "nobot" not in remainder, f"残留未识别的 nobot 写法: {title}"
    assert check_balance(new), f"标记不配平或嵌套: {title}"
    return new


def verify_conversiontable(new: str) -> None:
    remainder = MARKER_RE.sub("", new)
    spans = re.findall(r'<span class="as-is">[\s\S]*?</span>', remainder)
    assert remainder.count("as-is") == len(spans), "转换表残留非 span 的 as-is"
    assert check_balance(new), "转换表标记不配平"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="实际写入（默认干跑）")
    args = parser.parse_args()

    site = pywikibot.Site("zh", "re0")
    if args.apply:
        site.login()
        assert site.user() == "IchiSanNi"

    def candidates():
        for ns_id in SCAN_NS:
            pages = list(site.allpages(namespace=ns_id))
            for p in site.preloadpages(iter(pages), content=True, groupsize=50):
                if p.isRedirectPage():
                    continue
                if "as-is" in p.text or "nobot" in p.text:
                    yield p

    changed, skipped = [], []
    for p in candidates():
        title = p.title()
        try:
            new = transform(title, p.text)
            if title == CONVERSIONTABLE:
                verify_conversiontable(new)
        except AssertionError as e:
            skipped.append(f"{title}: {e}")
            continue
        if new == p.text:
            skipped.append(f"{title}: 变换后无变化（预期外）")
            continue
        changed.append((p, new))

    print(
        f"\n=== {'APPLY' if args.apply else 'DRY RUN'}: {len(changed)} to change, {len(skipped)} skipped ==="
    )
    for s in skipped:
        print(f"SKIP {s}")

    for p, new in changed:
        if not args.apply:
            print(f"WOULD EDIT {p.title()} ({len(p.text)} -> {len(new)})")
            continue
        print(f"EDIT {p.title()}")
        p.text = new
        p.save(summary=SUMMARY, bot=True, minor=False)

    if skipped:
        sys.exit(1)


if __name__ == "__main__":
    main()
