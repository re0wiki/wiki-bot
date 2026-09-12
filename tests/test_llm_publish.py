"""llm_translate 的 publish 子命令测试（离线，api/工作目录打桩，不触 wiki）。"""

import json

import pytest
from repo_loader import load_module

lt = load_module("llm_translate", "src/tools/llm_translate.py")

META = {
    "title": "角色:测试",
    "en_title": "Test",
    "en_revid": 100,
    "zh_revid": 90,
    "cold": "2020-01-01T00:00:00+00:00",
    "head": ["{{Init}}"],
    "tail": [],
    "zh_body_len": 3,
    "link_map": {},
    "unresolved_links": [],
}
SLUG = "角色_测试"


def make_work(tmp_path, monkeypatch, zh_text="{{Init}}\n\n旧文。\n"):
    work = tmp_path / "work"
    work.mkdir()
    (work / f"{SLUG}.meta.json").write_text(
        json.dumps(META, ensure_ascii=False), encoding="utf-8"
    )
    (work / f"{SLUG}.zh.txt").write_text(zh_text, encoding="utf-8")
    monkeypatch.setattr(lt, "WORK", work)
    return work


def stub_live(monkeypatch, content):
    """打桩 get_page 用的 api()：返回指定最新源码。"""
    rev = {
        "revid": 95,
        "timestamp": "2026-01-01T00:00:00Z",
        "slots": {"main": {"content": content}},
    }
    monkeypatch.setattr(
        lt, "api", lambda *a, **k: {"query": {"pages": [{"revisions": [rev]}]}}
    )


# ------------------------------------------------------------ ensure_proofread_cat


def test_proofread_cat_appended_before_langlink():
    out = lt.ensure_proofread_cat("正文。\n\n[[en:X]]\n")
    assert out == "正文。\n\n[[Category:机翻待校对]]\n\n[[en:X]]\n"


def test_proofread_cat_merges_into_existing_section():
    out = lt.ensure_proofread_cat("正文。\n\n[[Category:新搬运待整理]]\n\n[[en:X]]\n")
    assert "[[Category:新搬运待整理]]\n[[Category:机翻待校对]]" in out


def test_proofread_cat_already_present_noop():
    src = "正文。\n\n[[category:机翻待校对]]\n"  # 大小写不敏感
    assert lt.ensure_proofread_cat(src) == src


def test_proofread_cat_no_tail():
    assert lt.ensure_proofread_cat("正文。\n") == "正文。\n\n[[Category:机翻待校对]]\n"


# ------------------------------------------------------------ finalize_new_text


def test_finalize_stamps_marker_after_category_before_langlink():
    out = lt.finalize_new_text("正文。\n\n[[en:X]]\n", 100)
    assert out.count("<!-- LLM: revid 100;") == 1
    assert (
        out.index("[[Category:机翻待校对]]")  # 分类由 finalize 机械挂上
        < out.index("<!-- LLM: revid 100;")
        < out.index("[[en:X]]")
    )


def test_finalize_strips_agent_supplied_markers():
    src = "正文。\n<!-- K3: revid 90; 2020-01-01 -->\n<!-- LLM: revid 91; 2020-06-01 -->\n"
    out = lt.finalize_new_text(src, 100)
    assert "revid 90" not in out and "revid 91" not in out
    assert out.count("LLM: revid") == 1 and "revid 100" in out


# ------------------------------------------------------------ cmd_publish 前置校验


def test_publish_missing_new_file_aborts(tmp_path, monkeypatch):
    make_work(tmp_path, monkeypatch)
    with pytest.raises(SystemExit, match="new.txt"):
        lt.cmd_publish(SLUG)


def test_publish_baseline_mismatch_aborts(tmp_path, monkeypatch):
    work = make_work(tmp_path, monkeypatch)
    (work / f"{SLUG}.new.txt").write_text("新文。\n", encoding="utf-8")
    stub_live(monkeypatch, "{{Init}}\n\n被别人改过的文。\n")
    with pytest.raises(SystemExit, match="基线不一致"):
        lt.cmd_publish(SLUG)


def test_publish_missing_page_aborts(tmp_path, monkeypatch):
    work = make_work(tmp_path, monkeypatch)
    (work / f"{SLUG}.new.txt").write_text("新文。\n", encoding="utf-8")
    monkeypatch.setattr(
        lt, "api", lambda *a, **k: {"query": {"pages": [{"missing": True}]}}
    )
    with pytest.raises(SystemExit, match="不存在"):
        lt.cmd_publish(SLUG)
