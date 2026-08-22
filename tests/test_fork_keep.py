"""fork 定制 keep 标记的回归测试（rebase 上游时的行为锚点）。

keep 是 textlib 的异常类别，匹配 `<!--as-is-->…<!--/as-is-->` 注释对，
挂进 fixes.py 与 user-fixes.py 各 fix 的 exceptions，保护内容不被 bot 改动。
注释零渲染、可行内使用，行内内容整词包裹即可。
"""

from pywikibot import textlib

KEEP = textlib.get_regexes("keep")[0]


def spans(text: str) -> list[tuple[int, int]]:
    return [m.span() for m in KEEP.finditer(text)]


def test_region():
    assert spans("<!--as-is-->内容<!--/as-is-->") == [(0, 27)]


def test_multiple_regions():
    text = "a<!--as-is-->x<!--/as-is-->b<!--as-is-->y<!--/as-is-->c"
    assert len(spans(text)) == 2


def test_inline_word_wrap():
    """行内整词包裹（如模板 Seirei 的 `<!--as-is-->精灵<!--/as-is-->`）。"""
    m = KEEP.search("直接写<!--as-is-->精灵<!--/as-is-->即可")
    assert m is not None and m.group() == "<!--as-is-->精灵<!--/as-is-->"


def test_whitespace_tolerant():
    assert len(spans("<!-- as-is -->内容<!-- /as-is -->")) == 1


def test_inner_comment_does_not_terminate():
    text = "<!--as-is-->内有普通注释<!-- foo -->结束<!--/as-is-->"
    assert spans(text) == [(0, len(text))]


def test_unclosed_marker_not_protected():
    assert spans("<!--as-is-->未闭合") == []
    assert spans("<!--/as-is-->只有闭合") == []


def test_legacy_div_not_protected():
    """旧 div 写法已废弃，不再被 keep 匹配。"""
    assert spans('<div class="as-is">内容</div>') == []
