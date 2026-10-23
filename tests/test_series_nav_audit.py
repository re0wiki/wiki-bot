"""src/tools/series_nav_audit.py 的纯函数测试（不触碰 wiki）。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from repo_loader import load_module

sna = load_module("series_nav_audit", "src/tools/series_nav_audit.py")

EN_BOOK = """{{Re:Zero Light Novel Volumes
|Name = X
|Previous = [[Re:Zero Tanpenshuu Volume {prev}|Volume {prev}]]
|Next = {{next}}
}}"""


def IDENTITY(t):
    return t


def _pages(*pairs):
    return {t: {"en": en, "tabs": set()} for t, en in pairs}


# region subpage_root
def test_subpage_root_plain():
    assert sna.subpage_root("Re:Zero Tanpenshuu Volume 14/Synopsis") == (
        "Re:Zero Tanpenshuu Volume 14",
        "/Synopsis",
    )


def test_subpage_root_spaces_preserved_in_suffix():
    """词根查询要剥首尾空白；后缀保持原写法（与 zh 页 en 链接写法一致）。"""
    root, suffix = sna.subpage_root("The Dragon Nation / Story 1")
    assert root == "The Dragon Nation"
    assert suffix == "/ Story 1"


def test_subpage_root_multi_level():
    root, suffix = sna.subpage_root("A/B/C")
    assert root == "A" and suffix == "/B/C"


# region _prevnext_pairs
def test_prevnext_pairs_basic():
    pairs = sna._prevnext_pairs(EN_BOOK.format(prev=13, next=""))
    assert pairs == [("previous", "Re:Zero Tanpenshuu Volume 13")]


def test_prevnext_pairs_skip_nonlink_value():
    assert sna._prevnext_pairs("| next = }}") == []
    assert sna._prevnext_pairs("| previous = TBA") == []


# region iter_prevnext
def test_iter_main_page_plain():
    pages = _pages(("小说:短篇集第13卷", "Re:Zero Tanpenshuu Volume 13"))
    en_content = {"Re:Zero Tanpenshuu Volume 13": EN_BOOK.format(prev=12, next="")}
    out = list(sna.iter_prevnext(pages, en_content, IDENTITY))
    assert out == [("小说:短篇集第13卷", "previous", "Re:Zero Tanpenshuu Volume 12")]


def test_iter_subpage_derives_from_root():
    """梗概子页：自身 en 页无 prev/next → 取根页，目标加 /Synopsis。"""
    pages = _pages(
        ("小说:短篇集第14卷/梗概", "Re:Zero Tanpenshuu Volume 14/Synopsis"),
        ("小说:短篇集第14卷", "Re:Zero Tanpenshuu Volume 14"),
    )
    en_content = {
        "Re:Zero Tanpenshuu Volume 14/Synopsis": "==故事==\n正文",
        "Re:Zero Tanpenshuu Volume 14": EN_BOOK.format(prev=13, next=""),
    }
    out = list(sna.iter_prevnext(pages, en_content, IDENTITY))
    assert (
        "小说:短篇集第14卷/梗概",
        "previous",
        "Re:Zero Tanpenshuu Volume 13/Synopsis",
    ) in out
    assert ("小说:短篇集第14卷", "previous", "Re:Zero Tanpenshuu Volume 13") in out


def test_iter_subpage_own_chain_wins():
    """合集故事子页自身带 prev/next（故事链）时不从根页派生。"""
    pages = _pages(("小说:亲竜之国/故事①", "The Dragon Nation / Story 1"))
    en_content = {
        "The Dragon Nation / Story 1": "| next = [[The Dragon Nation / Story 2]]}}",
        "The Dragon Nation": "| next = [[The Dragon Nation / Story 0]]}}",
    }
    out = list(sna.iter_prevnext(pages, en_content, IDENTITY))
    assert out == [("小说:亲竜之国/故事①", "next", "The Dragon Nation / Story 2")]


def test_iter_subpage_own_en_missing_derives():
    """自身 en 页不存在（红链）时同样从根页派生。"""
    pages = _pages(("小说:短篇集第14卷/梗概", "Re:Zero Tanpenshuu Volume 14/Synopsis"))
    en_content = {"Re:Zero Tanpenshuu Volume 14": EN_BOOK.format(prev=13, next="")}
    out = list(sna.iter_prevnext(pages, en_content, IDENTITY))
    assert out == [
        (
            "小说:短篇集第14卷/梗概",
            "previous",
            "Re:Zero Tanpenshuu Volume 13/Synopsis",
        )
    ]


def test_iter_subpage_en_link_not_subpage_unaffected():
    """zh 子页但 en 链接不是子页：维持原样直取，不派生。"""
    pages = _pages(("术语:X/图库", "X"))
    en_content = {"X": EN_BOOK.format(prev=1, next="")}
    out = list(sna.iter_prevnext(pages, en_content, IDENTITY))
    assert out == [("术语:X/图库", "previous", "Re:Zero Tanpenshuu Volume 1")]


def test_iter_root_without_prevnext_no_checks():
    """根页无 prev/next（角色/游戏）→ 子页不产生检查项。"""
    pages = _pages(("角色:某/梗概", "Some Character/Synopsis"))
    en_content = {
        "Some Character/Synopsis": "正文",
        "Some Character": "{{Character}}",
    }
    assert list(sna.iter_prevnext(pages, en_content, IDENTITY)) == []


def test_iter_no_en_link_skipped():
    pages = _pages(("小说:原创页/梗概", ""))
    assert list(sna.iter_prevnext(pages, {}, IDENTITY)) == []
