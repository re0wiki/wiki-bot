"""src/scripts/re0_move.py 的纯函数测试（不触碰 wiki）。"""

import re

from repo_loader import load_module

mv = load_module("re0_move", "src/scripts/re0_move.py")


def test_no_change_returns_none():
    """标题已是标准名（含繁体标准名不动标题的规则差异不在此层）。"""
    assert mv.resolve_move("菜月·昴") == (None, None)


def test_alias_normalizes_to_standard():
    assert mv.resolve_move("菜月昴") == ("菜月·昴", None)
    assert mv.resolve_move("貝阿托莉絲") == ("碧翠丝", None)


def test_traditional_title_presimplified_before_rules():
    """繁体标题先归一简体再套规则：日文原名同字的繁体写法也能走到标准名。"""
    assert mv.resolve_move("术语:王族誘拐案") == ("术语:王族诱拐事件", None)


def test_no_rule_no_pure_variant_move():
    """规则未命中时不做纯繁简移动（既有繁体标题保持原样）。"""
    assert mv.resolve_move("小说:劍鬼戰歌") == (None, None)


def test_rules_exclude_template_producing_entries():
    """产出模板调用的 manual 规则（{{...}}）不能用于标题。"""
    assert all("{{" not in name for _, name in mv.RULES)


def test_prefix_change_is_skipped():
    rules = [(re.compile("术语"), "術語")]
    new, skip = mv.resolve_move("术语:魔女教", rules)
    assert new == "術語:魔女教"
    assert skip == "伪命名空间前缀变化"


def test_prefix_unchanged_is_allowed():
    """替换发生在词干而非前缀时正常归一。"""
    rules = [(re.compile("魔女"), "仙女")]
    new, skip = mv.resolve_move("术语:魔女教", rules)
    assert (new, skip) == ("术语:仙女教", None)


def test_illegal_chars_are_skipped():
    rules = [(re.compile("甲"), "乙#丙")]
    new, skip = mv.resolve_move("甲", rules)
    assert new == "乙#丙"
    assert skip == "新标题含非法字符"
