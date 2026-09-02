"""as-is 迁移收尾（asis_comment_migration.py 的后续修正）：

1. MediaWiki:Conversiontable/zh-hant：482 处 `<span class="as-is">X</span>`
   → `<!--as-is-->X<!--/as-is-->`。span 是编辑者猜测的误用（从未被 keep 覆盖）；
   正确语义是只保护繁体目标（台版译名），简体键名留给译名任务自动更新。
   注释在目标内安全：转换照常生效，注释透传为惰性 HTML 注释（已实证）。
   其中 卢克尼卡 一条已在受控试验中先行转换，故此处应剩 481 处。
2. Template:Seirei / Template:Yousei：空注释对拆词写法
   `精<!--as-is--><!--/as-is-->灵` → 整词包裹 `<!--as-is-->精灵<!--/as-is-->`
   （注释可行内使用，旧的拆词写法是 div 时代的技术限制产物）。
3. 三个 /doc 页的机制说明文字同步修正。

少量页面、人工可审，不用 bot flag。默认干跑，`--apply` 实际写入。
"""

import argparse
import re
import sys

import pywikibot

SPAN_RE = re.compile(r'<span class="as-is">([\s\S]*?)</span>')
MARKER_RE = re.compile(r"<!--(/?)as-is-->")

CONVERSIONTABLE = "MediaWiki:Conversiontable/zh-hant"
EXPECTED_REMAINING_SPANS = 481

# 模板：空注释对拆词 → 整词包裹
EMPTY_PAIR_RE = re.compile(r"(.)<!--as-is--><!--/as-is-->(.)")

DOC_EDITS: dict[str, list[tuple[str, str]]] = {
    "Template:Seirei/doc": [
        (
            "模板源码中的 <code>&lt;!--as-is--&gt;&lt;!--/as-is--&gt;</code> 注释对用于防止 bot 译名归一任务改动本词。",
            "模板源码以 <code>&lt;!--as-is--&gt;…&lt;!--/as-is--&gt;</code> 注释对包裹，防止 bot 译名归一任务改动本词。",
        ),
    ],
    "Template:Yousei/doc": [
        (
            "模板源码中的 <code>&lt;!--as-is--&gt;&lt;!--/as-is--&gt;</code> 注释对用于防止 bot 译名归一任务改动本词。",
            "模板源码以 <code>&lt;!--as-is--&gt;…&lt;!--/as-is--&gt;</code> 注释对包裹，防止 bot 译名归一任务改动本词。",
        ),
    ],
    "Module:Wiki-navigation/doc": [
        (
            "须直接写展开后的内容（如 {{T|Seirei}} 已内联为 <code><nowiki>精<!--as-is--><!--/as-is-->灵</nowiki></code>）。",
            "须直接写展开后的内容。",
        ),
    ],
}

SUMMARIES = {
    CONVERSIONTABLE: "转换规则目标的 span 误用改为 as-is 注释对（只保护繁体目标，简体键名随译名任务自动更新）",
    "Template:Seirei": "as-is 标记改为整词包裹（注释可行内使用，无需拆词）",
    "Template:Yousei": "as-is 标记改为整词包裹（注释可行内使用，无需拆词）",
}


def check_balance(text: str) -> bool:
    depth = 0
    for m in MARKER_RE.finditer(text):
        depth += -1 if m.group(1) else 1
        if not 0 <= depth <= 1:
            return False
    return depth == 0


def transform(title: str, text: str) -> str:
    new = text
    if title == CONVERSIONTABLE:
        spans = SPAN_RE.findall(new)
        assert len(spans) == EXPECTED_REMAINING_SPANS, (
            f"span 数 {len(spans)} != {EXPECTED_REMAINING_SPANS}"
        )
        assert not re.search(r"<span[^>]*as-is", SPAN_RE.sub("", new)), (
            "存在变体 span 写法"
        )
        new = SPAN_RE.sub(lambda m: f"<!--as-is-->{m.group(1)}<!--/as-is-->", new)
    elif title in ("Template:Seirei", "Template:Yousei"):
        assert len(EMPTY_PAIR_RE.findall(new)) == 1, f"{title} 空注释对数量异常"
        new = EMPTY_PAIR_RE.sub(r"<!--as-is-->\1\2<!--/as-is-->", new, count=1)
    for old, replacement in DOC_EDITS.get(title, []):
        assert new.count(old) == 1, f"文档原文不匹配: {title} :: {old[:50]!r}"
        new = new.replace(old, replacement)

    remainder = MARKER_RE.sub("", new)
    remainder = re.sub(r"&lt;!--/?as-is--&gt;", "", remainder)
    assert "as-is" not in remainder, f"残留未识别的 as-is 写法: {title}"
    assert check_balance(new), f"标记不配平或嵌套: {title}"
    return new


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="实际写入（默认干跑）")
    args = parser.parse_args()

    site = pywikibot.Site("zh", "re0")
    if args.apply:
        site.login()
        assert site.user() == "IchiSanNi"

    titles = [CONVERSIONTABLE, "Template:Seirei", "Template:Yousei", *DOC_EDITS]
    for title in titles:
        p = pywikibot.Page(site, title)
        new = transform(title, p.text)
        assert new != p.text, f"{title} 变换后无变化（预期外）"
        if not args.apply:
            print(f"WOULD EDIT {title} ({len(p.text)} -> {len(new)})")
            continue
        p.text = new
        p.save(
            summary=SUMMARIES.get(title, "as-is 机制说明文字同步"),
            bot=False,
            minor=False,
        )
        print(f"SAVED {title}")


if __name__ == "__main__":
    main()
    sys.exit(0)
