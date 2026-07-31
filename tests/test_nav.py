"""scripts/re0_nav.py 的纯函数测试（Wiki-navigation 编译规则）。"""

from repo_loader import load_module

nav = load_module("re0_nav", "scripts/re0_nav.py")


def test_non_star_line_dropped():
    assert nav.compile_line("# 注释") == ""
    assert nav.compile_line("普通文本") == ""


def test_plain_stem_gets_separator():
    assert nav.compile_line("* 角色:菜月·昴") == "**** |角色:菜月·昴"


def test_piped_stem_kept():
    assert nav.compile_line("** 小说:文库正传|小说") == "***** 小说:文库正传|小说"


def test_brackets_stripped():
    assert nav.compile_line("* [[角色:菜月·昴|昴]]") == "**** 角色:菜月·昴|昴"


def test_compile_nav_adds_header_and_skips_empty():
    src = "* A\n非星号行\n** B|b\n"
    out = nav.compile_nav(src)
    head, *lines = out.splitlines()
    assert "自动生成" in head
    assert lines == ["**** |A", "***** B|b"]
