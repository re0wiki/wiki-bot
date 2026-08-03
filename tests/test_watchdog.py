"""scripts/recent_changes_watchdog.py 的纯函数测试（不触碰 wiki）。"""

from repo_loader import load_module

wd = load_module("rc_watchdog", "scripts/recent_changes_watchdog.py")


def _change(rcid, user, title, revid, old_revid, type_="edit"):
    return {
        "rcid": rcid,
        "user": user,
        "title": title,
        "revid": revid,
        "old_revid": old_revid,
        "type": type_,
    }


def test_group_consecutive_merges_adjacent():
    changes = [
        _change(1, "A", "页1", 10, 9),
        _change(2, "A", "页1", 11, 10),
        _change(3, "A", "页1", 12, 11),
    ]
    groups = wd.group_consecutive(changes)
    assert len(groups) == 1
    assert groups[0]["from_rev"] == 9
    assert groups[0]["to_rev"] == 12
    assert groups[0]["rcids"] == [1, 2, 3]


def test_group_consecutive_splits_on_interleaving():
    """中间隔着他人编辑时必须拆组，否则合并区间会藏进他人改动。"""
    changes = [
        _change(1, "A", "页1", 10, 9),
        _change(2, "B", "页1", 11, 10),
        _change(3, "A", "页1", 12, 11),
    ]
    groups = wd.group_consecutive(changes)
    assert len(groups) == 3
    assert [g["user"] for g in groups] == ["A", "B", "A"]


def test_group_consecutive_new_page_detection():
    assert wd.group_consecutive([_change(1, "A", "页1", 10, 0, "new")])[0]["is_new"]
    assert wd.group_consecutive([_change(1, "A", "页1", 10, 0)])[0]["is_new"]
    assert not wd.group_consecutive([_change(1, "A", "页1", 10, 9)])[0]["is_new"]


def test_parse_diff_multivalue_class_and_inline_marks():
    """td class 是多值（diff-addedline diff-side-added），ins/del 转 ⟦⟧/〔〕。"""
    body = (
        '<td class="diff-deletedline diff-side-deleted">旧〔x〕文本</td>'
        '<td class="diff-addedline diff-side-added">新<ins>增</ins>文本</td>'
        '<td class="diff-context">不变</td>'
    )
    lines = wd.parse_diff(body)
    assert ("-", "旧〔x〕文本") in lines
    assert ("+", "新⟦增⟧文本") in lines
    assert all("不变" not in v for _, v in lines)


def test_extract_link_targets_skips_prefixes_and_anchors():
    lines = [
        "+ [[角色:菜月·昴]] 与 [[术语:魔女教#历史|魔女教]]",
        "+ [[File:a.png]] [[Category:角色]] [[wikipedia:Re:Zero]] [[http://x]]",
    ]
    targets = wd.extract_link_targets(lines)
    assert targets == {"角色:菜月·昴", "术语:魔女教"}


def test_extract_link_targets_strips_inline_marks():
    """⟦⟧/〔〕 行内标记必须剥离，否则已存在页面会被误判为红链。"""
    lines = [
        "+ [[术语:邪⟦龍討滅戰⟧|邪⟦龍討滅戰⟧]]",
        "+ [[角色:菜月·雷吉〔利格鲁〕⟦尔⟧|菜月·雷吉尔]]",
    ]
    assert wd.extract_link_targets(lines) == {"术语:邪龍討滅戰", "角色:菜月·雷吉尔"}


def test_extract_link_targets_resolves_subpage_links():
    """[[/子页]] 必须相对当前页解析，否则已存在子页被误判为红链。"""
    lines = ["+ 其餘差異详情請见 [[/改动]]。"]
    assert wd.extract_link_targets(lines, "设定集、画集:Re:zeropedia") == {
        "设定集、画集:Re:zeropedia/改动"
    }
    # 无 page_title 时无法解析，跳过而不是误报
    assert wd.extract_link_targets(lines) == set()
