"""src/scripts/re0_tab_sync.py 的纯函数测试（不触碰 wiki）。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from repo_loader import load_module

ts = load_module("re0_tab_sync", "src/scripts/re0_tab_sync.py")

# 含 `}}{{Tab` 粘连行与 '''加粗''' 章行的真实形态（Template:Tab/Manga Arc 4 Volume）
MANGA_VOL_TAB = """{{Tab
|[[漫画:第1章第1卷|第1章]]
|[[漫画:第2章第1卷|第2章]]
|[[漫画:第3章第1卷|第3章]]
|'''第4章'''
}}{{Tab
|[[漫画:第4章第1卷|1]]
|[[漫画:第4章第12卷|12]]
|[[漫画:第4章第13卷|13]]
}}<noinclude>[[Category:分页模板]]</noinclude>"""

# 含前篇/后篇双条目的话数模板（Template:Tab/Manga Arc 4 Chapter 的缩样）
CHAPTER_TAB = """{{Tab
|[[漫画:第3章第1话|第3章]]
|'''第4章'''
}}
{{Tab
|[[漫画:第4章第19话前篇|19]]
|[[漫画:第4章第19话后篇|后]]
|[[漫画:第4章第20话|20]]
|[[漫画:第4章第71话|71]]
}}<noinclude>[[Category:分页模板]]</noinclude>"""

LN_TAB = """{{Tab
|[[小说:44卷|44]]
|[[小说:45卷|45]]
}}<noinclude>[[Category:分页模板]]</noinclude>"""


# region insert_tabs
def test_insert_tabs_after_todo():
    src = "{{Init}}\n{{To do}}\n{{Infobox book\n| name = X\n}}"
    assert ts.insert_tabs(src, ["Manga Arc 4 Volume"]) == (
        "{{Init}}\n{{To do}}\n{{Tab/Manga Arc 4 Volume}}\n{{Infobox book\n| name = X\n}}"
    )


def test_insert_tabs_no_todo():
    src = "{{Init}}\n{{Infobox book\n}}"
    assert ts.insert_tabs(src, ["LN"]) == "{{Init}}\n{{Tab/LN}}\n{{Infobox book\n}}"


def test_insert_tabs_glued_todo_anchors_after_init():
    """To do 与后文粘连（无独立行）时锚到 Init 后。"""
    src = "{{Init}}\n{{To do}}{{#infobox\n}}"
    assert (
        ts.insert_tabs(src, ["LN"]) == "{{Init}}\n{{Tab/LN}}\n{{To do}}{{#infobox\n}}"
    )


def test_insert_tabs_with_params():
    src = "{{Init|a=b}}\n{{To do|翻译中}}\n正文"
    assert (
        ts.insert_tabs(src, ["LN"])
        == "{{Init|a=b}}\n{{To do|翻译中}}\n{{Tab/LN}}\n正文"
    )


def test_insert_tabs_unknown_header():
    assert ts.insert_tabs("{{ hatnote }}\n{{Init}}\n", ["LN"]) is None
    assert ts.insert_tabs("", ["LN"]) is None


# region 序号/骨架工具
def test_parse_serial():
    assert ts._parse_serial("漫画:第4章第14卷") == ("漫画:第4章第", 14, "卷")
    assert ts._parse_serial("漫画:第4章第19话后篇") == ("漫画:第4章第", 19, "话后篇")
    assert ts._parse_serial("小说:45卷") == ("小说:", 45, "卷")
    assert ts._parse_serial("动画:第一季") is None
    # 序号必须取完整数字段（贪婪词干会在段内截断：45 → 词干带 4、序号 5）
    assert ts._parse_serial("小说:145卷")[1] == 145


def test_base_tail():
    assert ts._base_tail("话前篇") == "话"
    assert ts._base_tail("话後篇") == "话"
    assert ts._base_tail("卷") == "卷"


def test_series_key():
    assert ts._series_key("Manga Arc 4 Chapter 71") == "Manga Arc 4 Chapter #"
    assert ts._series_key("Re:Zero Season 2 Episode 50") == "Re:Zero Season 2 Episode #"
    # 季号保留在键内：跨季即不同键（全掩码骨架会丢失该边界）
    assert ts._series_key("Re:Zero Season 3 Episode 1") == "Re:Zero Season 3 Episode #"
    assert (
        ts._series_key("Manga Arc 4 Chapter 70 Part 1")
        == "Manga Arc 4 Chapter 70 Part #"
    )


# region insert_entry
def test_insert_entry_after_anchor_glued_template():
    """粘连模板尾插：锚 13 卷后插 14 卷，其余字节不动。"""
    out = ts.insert_entry(MANGA_VOL_TAB, "漫画:第4章第13卷", "漫画:第4章第14卷", "next")
    assert out is not None
    assert "|[[漫画:第4章第13卷|13]]\n|[[漫画:第4章第14卷|14]]\n}}" in out
    assert "}}{{Tab" in out  # 粘连保持原样
    assert out.count("[[") == MANGA_VOL_TAB.count("[[") + 1


def test_insert_entry_between_split_pair_and_next():
    """锚是后篇（显示文本非序号）也能定位，插入其后。"""
    src = CHAPTER_TAB.replace("|[[漫画:第4章第20话|20]]\n", "")
    out = ts.insert_entry(src, "漫画:第4章第19话后篇", "漫画:第4章第20话", "next")
    assert out is not None
    assert (
        "|[[漫画:第4章第19话后篇|后]]\n|[[漫画:第4章第20话|20]]\n|[[漫画:第4章第71话|71]]"
        in out
    )


def test_insert_entry_append_at_block_end():
    out = ts.insert_entry(CHAPTER_TAB, "漫画:第4章第71话", "漫画:第4章第72话", "next")
    assert out is not None
    assert "|[[漫画:第4章第71话|71]]\n|[[漫画:第4章第72话|72]]\n}}" in out


def test_insert_entry_ln():
    out = ts.insert_entry(LN_TAB, "小说:45卷", "小说:46卷", "next")
    assert out is not None
    assert "|[[小说:45卷|45]]\n|[[小说:46卷|46]]\n}}" in out


def test_insert_entry_previous_direction():
    src = "{{Tab\n|[[小说:44卷|44]]\n|[[小说:46卷|46]]\n}}"
    out = ts.insert_entry(src, "小说:46卷", "小说:45卷", "previous")
    assert out == "{{Tab\n|[[小说:44卷|44]]\n|[[小说:45卷|45]]\n|[[小说:46卷|46]]\n}}"


def test_insert_entry_wrong_direction_order_rejected():
    """序号方向与链不一致（en 链回环/乱序）→ 拒绝。"""
    assert ts.insert_entry(LN_TAB, "小说:45卷", "小说:44卷", "next") is None
    assert ts.insert_entry(LN_TAB, "小说:44卷", "小说:45卷", "previous") is None


def test_insert_entry_split_target_rejected():
    """拆分篇目标（双条目写法）转人工。"""
    assert (
        ts.insert_entry(CHAPTER_TAB, "漫画:第4章第71话", "漫画:第4章第72话后篇", "next")
        is None
    )


def test_insert_entry_comment_block_rejected():
    src = "{{Tab\n|[[小说:44卷|44]]\n|[[小说:45卷|45]]\n<!--暂未搬运--><!--|[[小说:46卷|46]]-->\n}}"
    assert ts.insert_entry(src, "小说:45卷", "小说:46卷", "next") is None


def test_insert_entry_duplicate_anchor_rejected():
    """锚在模板中出现多次（如章行+内容行各一次）→ 歧义拒绝。"""
    src = (
        "{{Tab\n|[[漫画:第3章第1话|第3章]]\n}}\n"
        "{{Tab\n|[[漫画:第3章第1话|1]]\n|[[漫画:第3章第2话|2]]\n}}"
    )
    assert (
        ts.insert_entry(src, "漫画:第3章第1话", "漫画:第3章第0话", "previous") is None
    )


def test_insert_entry_nonnumeric_display_no_proof():
    """OVA 类显示文本非序号的块：无数字显示佐证 → 拒绝。"""
    src = "{{Tab\n|[[动画:OVA1|OVA1]]\n|[[动画:OVA2|OVA2]]\n}}"
    assert ts.insert_entry(src, "动画:OVA2", "动画:OVA3", "next") is None


def test_insert_entry_cross_stem_rejected():
    assert ts.insert_entry(LN_TAB, "小说:45卷", "漫画:第4章第46卷", "next") is None


def test_insert_entry_unclosed_block():
    src = "{{Tab\n|[[小说:44卷|44]]\n|[[小说:45卷|45]]\n"
    assert ts.insert_entry(src, "小说:45卷", "小说:46卷", "next") is None


# region pick_template
def test_pick_template_unique():
    """话/卷词尾不同，锚定不会选错模板。"""
    srcs = {"Manga Arc 4 Volume": MANGA_VOL_TAB, "Manga Arc 4 Chapter": CHAPTER_TAB}
    tab, why = ts.pick_template(srcs, "漫画:第4章第13卷", "漫画:第4章第14卷", "next")
    assert tab == "Manga Arc 4 Volume" and why is None


def test_pick_template_no_hit():
    tab, why = ts.pick_template({"LN": LN_TAB}, "小说:47卷", "小说:48卷", "next")
    assert tab is None and "无唯一锚定位" in why


def test_pick_template_ambiguous():
    srcs = {"A": LN_TAB, "B": LN_TAB}
    tab, why = ts.pick_template(srcs, "小说:45卷", "小说:46卷", "next")
    assert tab is None and "多个模板" in why


# region mount_candidates / append_candidates
def _pages(tabs_by_page, en_by_page=None):
    return {
        t: {"en": (en_by_page or {}).get(t, ""), "tabs": tabs}
        for t, tabs in tabs_by_page.items()
    }


def test_mount_candidates_unanimous():
    pages = _pages(
        {"P": {"Tab/LN"}, "Q": {"Tab/LN"}, "R": set(), "X": set()},
        {"P": "Volume 1", "Q": "Volume 2", "R": "Volume 3", "X": "Volume 4"},
    )
    checks = [
        {"zh_target": "P"},
        {"zh_target": "Q"},
        {"zh_target": "R"},
        {"zh_target": None},
    ]
    tabs, why = ts.mount_candidates("X", checks, pages, {"Tab/LN": {"P", "Q"}})
    assert tabs == ["Tab/LN"] and why is None


def test_mount_candidates_disagree():
    pages = _pages(
        {"P": {"Tab/S2"}, "Q": {"Tab/S4"}, "X": set()},
        {"P": "Episode 50", "Q": "Episode 52", "X": "Episode 51"},
    )
    checks = [{"zh_target": "P"}, {"zh_target": "Q"}]
    tabs, why = ts.mount_candidates("X", checks, pages, {})
    assert tabs is None and "不一致" in why


def test_mount_candidates_series_key_filter():
    """跨季边界的邻居（en 系列键不同）不投票：全被过滤 → 转人工而非挂错。"""
    pages = _pages(
        {"P": {"Tab/S2"}, "X": set()},
        {"P": "Re:Zero Season 2 Episode 50", "X": "Re:Zero Season 3 Episode 1"},
    )
    tabs, why = ts.mount_candidates("X", [{"zh_target": "P"}], pages, {})
    assert tabs is None and "无同系列键" in why


def test_mount_candidates_no_tabbed_neighbor():
    pages = _pages({"A": set(), "X": set()}, {"A": "Volume 1", "X": "Volume 2"})
    tabs, why = ts.mount_candidates("X", [{"zh_target": "A"}], pages, {})
    assert tabs is None and "无同系列键" in why


def test_mount_candidates_linkset_guard():
    """候选模板链接集不含任何邻居 → 拒绝（同源校验）。"""
    pages = _pages({"A": {"Tab/LN"}, "X": set()}, {"A": "Volume 1", "X": "Volume 2"})
    tabs, why = ts.mount_candidates(
        "X", [{"zh_target": "A"}], pages, {"Tab/LN": {"无关页"}}
    )
    assert tabs is None and "链接集" in why


def test_append_candidates_two_hop():
    pages = _pages({"P": {"Tab/S2"}, "动画:第二季": {"Tab/S2", "Tab/Extra"}})
    tab_links = {"Tab/S2": {"动画:第二季", "动画:第49集"}}
    cands = ts.append_candidates("P", pages, tab_links)
    assert cands == ["Tab/Extra", "Tab/S2"]


# region 占位注释激活
EX_TAB = """{{Tab
|[[小说:狮子王所见之梦/梗概|Ex1 狮子王所见之梦]]
|[[小说:绯色姬谭/梗概|Ex5 绯色姬谭]]
<!--|[[小说:劍鬼戰歌/梗概|Ex6 劍鬼戰歌]]-->
}}<noinclude>[[Category:分页模板]]</noinclude>"""


def test_activate_placeholder_redirect_target():
    """占位目标经重定向归一后存在 → 去注释并改指终态，显示文本保留。"""
    out, activated = ts.activate_placeholders(
        EX_TAB, {"小说:劍鬼戰歌/梗概": "小说:剑鬼战歌/梗概"}
    )
    assert activated == ["小说:剑鬼战歌/梗概"]
    assert "|[[小说:剑鬼战歌/梗概|Ex6 劍鬼戰歌]]\n" in out
    assert "<!--" not in out.split("}}")[0]


def test_activate_placeholder_redlink_stays():
    """目标不存在 → 占位保持注释，逐字节不动。"""
    out, activated = ts.activate_placeholders(EX_TAB, {})
    assert activated == [] and out == EX_TAB


def test_activate_placeholder_with_note_prefix():
    """SOP 的 <!--暂未搬运--> 前注形态。"""
    src = "{{Tab\n|[[小说:1卷/梗概|1]]\n<!--暂未搬运--><!--|[[小说:2卷/梗概|2]]-->\n}}"
    out, activated = ts.activate_placeholders(src, {"小说:2卷/梗概": "小说:2卷/梗概"})
    assert activated == ["小说:2卷/梗概"]
    assert out == "{{Tab\n|[[小说:1卷/梗概|1]]\n|[[小说:2卷/梗概|2]]\n}}"


def test_activate_placeholder_no_display():
    src = "{{Tab\n<!--|[[小说:9卷/梗概]]-->\n}}"
    out, activated = ts.activate_placeholders(src, {"小说:9卷/梗概": "小说:9卷/梗概"})
    assert out == "{{Tab\n|[[小说:9卷/梗概]]\n}}"
    assert activated == ["小说:9卷/梗概"]


def test_activate_placeholder_non_entry_comment_untouched():
    """含链接的说明注释不是占位行，不激活。"""
    src = "{{Tab\n<!-- 注：[[小说:X]] 待议 -->\n|[[小说:Y|Y]]\n}}"
    out, activated = ts.activate_placeholders(src, {"小说:X": "小说:X"})
    assert activated == [] and out == src
