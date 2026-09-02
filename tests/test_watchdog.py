"""src/scripts/tools/recent_changes_watchdog.py 的纯函数测试（不触碰 wiki）。"""

import os

from repo_loader import load_module

wd = load_module("rc_watchdog", "src/scripts/tools/recent_changes_watchdog.py")


def test_state_file_at_repo_root():
    """脚本在 src/scripts/tools/ 下，STATE_FILE 必须解析到仓库根的 .cache/——
    曾因目录分层重构少退一级，水位线写到 src/scripts/.cache/ 导致断档。"""
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert wd.STATE_FILE == os.path.join(repo_root, ".cache", "rc_watchdog.json")


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
