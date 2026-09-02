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
