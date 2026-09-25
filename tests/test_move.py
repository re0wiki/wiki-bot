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


# region TITLE_PATTERNS（整题模式规则）
def test_ln_volume():
    assert mv.resolve_move("Re:Zero Light Novel Volume 46") == ("小说:46卷", None)


def test_tanpenshuu_volume_synopsis_subpage():
    """系列题名规则与子页后缀规则组合生效。"""
    assert mv.resolve_move("Re:Zero Tanpenshuu Volume 14/Synopsis") == (
        "小说:短篇集第14卷/梗概",
        None,
    )


def test_manga_chapter_and_parts():
    assert mv.resolve_move("Manga Arc 4 Chapter 72") == ("漫画:第4章第72话", None)
    assert mv.resolve_move("Manga Arc 4 Chapter 70 Part 1") == (
        "漫画:第4章第70话前篇",
        None,
    )
    assert mv.resolve_move("Manga Arc 4 Chapter 70 Part 2") == (
        "漫画:第4章第70话后篇",
        None,
    )


def test_manga_part3_plus_not_moved():
    """Part 3+ 无 zh 先例，留人工。"""
    assert mv.resolve_move("Manga Arc 4 Chapter 70 Part 3") == (None, None)


def test_manga_volume():
    assert mv.resolve_move("Manga Arc 4 Volume 14") == ("漫画:第4章第14卷", None)


def test_subpage_suffix():
    assert mv.resolve_move("Arbalest/Image Gallery") == ("Arbalest/图库", None)
    assert mv.resolve_move("Hector/Relationships") == ("Hector/关系", None)


def test_pattern_move_bypasses_prefix_guard():
    """模式规则本身即前缀映射（Re:→小说:），不触发伪命名空间守卫。"""
    _, skip = mv.resolve_move("Re:Zero Light Novel Volume 46")
    assert skip is None


# endregion


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


# region is_leftover（本轮移动遗留的重定向识别）
def test_leftover_exact_source():
    assert mv.is_leftover("Tornel", ["Tornel"])


def test_leftover_subpage_of_moved_source():
    """movesubpages 联动后，旧子页标题是遗留重定向。"""
    assert mv.is_leftover("Tornel/Image Gallery", ["Tornel"])
    assert mv.is_leftover(
        "Re:Zero Light Novel Volume 46/Synopsis",
        ["Re:Zero Light Novel Volume 46"],
    )


def test_not_leftover_for_mere_string_prefix():
    """仅共享字符串前缀、无子页关系的不算遗留。"""
    assert not mv.is_leftover("Tornel2", ["Tornel"])
    assert not mv.is_leftover("Tornel2/Image Gallery", ["Tornel"])


def test_not_leftover_for_unrelated_title():
    assert not mv.is_leftover("角色:Tornel/图库", ["Tornel"])
    assert not mv.is_leftover("Tornel", [])


# endregion


# region classify_prefix（en 分类集合 → zh 伪前缀）
def test_classify_character():
    assert mv.classify_prefix({"Characters", "Human", "Male"}) == "角色"


def test_classify_terminology():
    assert mv.classify_prefix({"Terminology"}) == "术语"
    assert mv.classify_prefix({"Battles", "Kingdom of Lugunica"}) == "术语"
    assert mv.classify_prefix({"Cities", "Locations"}) == "术语"
    assert mv.classify_prefix({"Organizations"}) == "术语"


def test_classify_character_beats_shared_cats():
    """种族/阵营等角色属性分类同时在 Terminology 树下：Characters 直接命中优先。"""
    assert mv.classify_prefix({"Characters", "Demi-Human", "Emilia Camp"}) == "角色"


def test_classify_novel():
    assert mv.classify_prefix({"Re:Zero Volumes", "Side Story"}) == "小说"
    assert mv.classify_prefix({"Story Arcs", "Arc 4"}) == "小说"


def test_classify_manga():
    assert mv.classify_prefix({"Arc 4 Manga Chapters"}) == "漫画"
    assert mv.classify_prefix({"Bonds of Ice Chapters"}) == "漫画"


def test_classify_anime():
    assert mv.classify_prefix({"Episodes", "Season 1"}) == "动画"
    assert mv.classify_prefix({"Season 2 BD Volumes", "Re:Zero BD"}) == "动画"


def test_classify_music_beats_anime():
    """歌曲页带季分类（动画树）：Music 优先（zh 歌曲全归 音乐:）。"""
    assert mv.classify_prefix({"Music", "Season 1"}) == "音乐"


def test_classify_game():
    assert mv.classify_prefix({"Re:Zero Games"}) == "游戏"


def test_classify_disambiguation_excluded():
    assert mv.classify_prefix({"Disambiguations"}) is None
    assert mv.classify_prefix({"Disambiguations", "Characters"}) is None


def test_classify_conflict_returns_none():
    """小说×漫画等多命中：跳过留人工（含 BD 圆盘的 动画×小说）。"""
    assert mv.classify_prefix({"Re:Zero Volumes", "Arc 4 Manga Chapters"}) is None
    assert (
        mv.classify_prefix({"Re:Zero BD", "Season 1 BD Volumes", "BD Volumes"}) is None
    )


def test_classify_unmapped_returns_none():
    assert mv.classify_prefix(set()) is None
    assert mv.classify_prefix({"Browse"}) is None
    # 角色属性分类但无 Characters 直接命中：差集净化，不误判术语
    assert mv.classify_prefix({"Human", "Male"}) is None


# endregion


# region _resolve_api_title（API normalized/redirects 链解析）
def test_resolve_api_title_plain():
    assert mv._resolve_api_title("A", {}, {}) == "A"


def test_resolve_api_title_normalized_and_redirect_chain():
    norm = {"demi-human": "Demi-human"}
    red = {"Demi-human": "Demi-Human", "Demi-Human": "Half-Human"}
    assert mv._resolve_api_title("demi-human", norm, red) == "Half-Human"


def test_resolve_api_title_redirect_loop_terminates():
    assert mv._resolve_api_title("A", {}, {"A": "B", "B": "A"}) in {"A", "B"}


# endregion
