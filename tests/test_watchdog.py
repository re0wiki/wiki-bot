"""src/tools/recent_changes_watchdog.py 的纯函数测试（不触碰 wiki）。"""

import json
import os

import pytest
from repo_loader import load_module

wd = load_module("rc_watchdog", "src/tools/recent_changes_watchdog.py")


def test_state_file_at_repo_root():
    """脚本在 src/tools/ 下，STATE_FILE 必须解析到仓库根的 .cache/——
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


def test_group_consecutive_splits_on_revision_gap():
    """被过滤编辑夹在中间时不得用合并 diff 掩盖该修订。"""
    changes = [
        _change(1, "A", "页1", 10, 9),
        _change(2, "A", "页1", 12, 11),
    ]
    groups = wd.group_consecutive(changes)
    assert len(groups) == 2
    assert [(g["from_rev"], g["to_rev"]) for g in groups] == [(9, 10), (11, 12)]


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


def test_fetch_new_changes_accepts_reached_waterline(monkeypatch):
    change = _change(100, "A", "页1", 10, 9)
    change["ns"] = 0
    monkeypatch.setattr(
        wd,
        "_get",
        lambda params: {
            "query": {
                "recentchanges": [
                    {**change, "rcid": 102, "revid": 12, "old_revid": 11},
                    change,
                ]
            }
        },
    )
    assert len(wd.fetch_new_changes(100)) == 2


def test_main_refuses_to_advance_when_waterline_not_reached(tmp_path, monkeypatch):
    state_file = tmp_path / "rc_watchdog.json"
    original = {"last_rcid": 100, "last_run": 123}
    state_file.write_text(json.dumps(original), encoding="utf-8")
    monkeypatch.setattr(wd, "STATE_FILE", str(state_file))
    change = {
        **_change(101, "A", "页1", 11, 10),
        "ns": 0,
        "bot": False,
        "newlen": 20,
        "oldlen": 10,
        "timestamp": "2026-01-01T00:00:00Z",
        "comment": "",
    }
    monkeypatch.setattr(
        wd, "_get", lambda params: {"query": {"recentchanges": [change]}}
    )
    with pytest.raises(RuntimeError, match="旧水位线"):
        wd.main()
    assert json.loads(state_file.read_text(encoding="utf-8")) == original
