"""src/scripts/re0_move.py 的纯函数测试（不触碰 wiki）。"""

import re

from repo_loader import load_module

mv = load_module("re0_move", "src/scripts/re0_move.py")


def test_no_change_returns_none():
    """标题已是标准名（含繁体标准名不动标题的规则差异不在此层）。"""
    assert mv.resolve_move("菜月昴") == (None, None)


def test_alias_normalizes_to_standard():
    assert mv.resolve_move("菜月·昴") == ("菜月昴", None)
    assert mv.resolve_move("貝阿托莉絲") == ("碧翠丝", None)


def test_traditional_title_presimplified_before_rules():
    """繁体标题先归一简体再套规则：日文原名同字的繁体写法也能走到标准名。"""
    assert mv.resolve_move("术语:王族誘拐案") == ("术语:王族诱拐事件", None)


def test_pure_variant_move_when_title_has_traditional():
    """含繁体字的标题做纯繁简移动（fixing-redirects 会解析到繁体存储标题，
    不移则与 fix:translation 来回拉锯）。"""
    assert mv.resolve_move("小说:劍鬼戰歌") == ("小说:剑鬼战歌", None)


def test_pure_variant_move_with_identity_rule_hit():
    """名字规则恒等命中 + 其余部分繁体：同样移动。"""
    assert mv.resolve_move("术语:費瑟蘭姐妹") == ("术语:费瑟兰姐妹", None)


def test_t2s_only_prefix_change_is_allowed():
    """前缀仅被 t2s 归一（術語→术语）不是伪命名空间变化。"""
    assert mv.resolve_move("術語:某某") == ("术语:某某", None)


def test_rules_exclude_template_producing_entries():
    """产出模板调用的规则（manual 或模板目标的别名对）不能用于标题。"""
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


# region is_external_video（File 空间无有效扩展名 = Fandom 外部视频）
EXTS = {"png", "jpg", "mp4", "webm"}


def test_normal_file_not_external_video():
    assert not mv.is_external_video("利格鲁头像.png", EXTS)
    assert not mv.is_external_video("大塚真一郎 Art Works P123.JPG", {"jpg"})


def test_no_extension_is_external_video():
    assert mv.is_external_video(
        "MF文庫J『Ｒｅ：ゼロから始める異世界生活Ex5 緋色姫譚』発売CM", EXTS
    )


def test_dot_in_name_without_extension_is_external_video():
    """标题含点但尾部不是有效扩展名（如 YouTube 标题里的日期）也算视频。"""
    assert mv.is_external_video(
        "TVアニメ『Re-ゼロから始める異世界生活』2nd season PV｜2020.7.8 ON AIR START",
        EXTS,
    )


# endregion
