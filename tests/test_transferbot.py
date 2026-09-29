"""src/scripts/re0_transferbot.py 的纯函数测试（不触碰 wiki）。"""

from repo_loader import load_module

tb = load_module("re0_transferbot", "src/scripts/re0_transferbot.py")


def test_normalize():
    assert tb.normalize("_foo bar_ ") == "Foo bar"


def test_build_text_matches_fork_patch():
    text = tb.build_text("正文", "Rem")
    assert text.startswith("{{Init}}\n{{To do}}\n正文")
    assert text.endswith("[[en:Rem]]\n[[Category:新搬运待整理]]")


def test_build_summary_matches_fork_i18n():
    assert tb.build_summary("Rem") == "自[[en:Rem]]搬运页面"


def test_build_text_strips_en_categories():
    """en 源码的分类行在搬运时剥除（en 分类在 zh 必为红链）。"""
    text = tb.build_text("正文\n[[Category:Foo]]\n[[Category:Bar| ]]\n", "Rem")
    assert "Category:Foo" not in text
    assert "Category:Bar" not in text
    assert text.endswith("[[en:Rem]]\n[[Category:新搬运待整理]]")


def test_strip_en_categories_keeps_content():
    assert tb.strip_en_categories("a\nb\n") == "a\nb\n"
