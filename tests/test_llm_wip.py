"""llm_translate 的 wip 自动收尾与 done 核验测试（离线，api/工作目录打桩）。"""

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
MARKER = "<!-- LLM: revid 100; 2026-01-01T00:00:00+00:00 -->"


def make_work(tmp_path, monkeypatch):
    """建假 work 目录（meta/zh/conv 三件）并把模块的 WORK 指过去。"""
    work = tmp_path / "work"
    work.mkdir()
    slug = "角色_测试"
    (work / f"{slug}.meta.json").write_text(
        json.dumps(META, ensure_ascii=False), encoding="utf-8"
    )
    (work / f"{slug}.zh.txt").write_text("{{Init}}\n\n旧文。\n", encoding="utf-8")
    (work / f"{slug}.conv.txt").write_text("新文。\n", encoding="utf-8")
    monkeypatch.setattr(lt, "WORK", work)
    return work


def stub_api(monkeypatch, rev):
    """打桩 api()：返回给定最新修订（rev=None 表示页面已删除）。"""
    page = {"missing": True} if rev is None else {"revisions": [rev]}
    monkeypatch.setattr(lt, "api", lambda *a, **k: {"query": {"pages": [page]}})


def make_rev(revid, user, content, comment=""):
    return {
        "revid": revid,
        "user": user,
        "comment": comment,
        "slots": {"main": {"content": content}},
    }


def test_resolve_wip_no_edit_discards(tmp_path, monkeypatch, capsys):
    """agent 未编辑成（revid 与 meta 一致）→ 丢弃备料。"""
    work = make_work(tmp_path, monkeypatch)
    stub_api(monkeypatch, make_rev(90, lt.BOT, "旧文。"))
    lt.resolve_wip()
    assert not list(work.iterdir())
    assert "agent 未编辑成" in capsys.readouterr().out


def test_resolve_wip_human_edit_discards(tmp_path, monkeypatch, capsys):
    """prepare 后有人类编辑 → 丢弃备料（重备基线自动吸收）。"""
    work = make_work(tmp_path, monkeypatch)
    stub_api(monkeypatch, make_rev(95, "Nekomeow151", "人类改动。"))
    lt.resolve_wip()
    assert not list(work.iterdir())
    assert "有人类编辑" in capsys.readouterr().out


def test_resolve_wip_missing_page_discards(tmp_path, monkeypatch, capsys):
    """页面已删除 → 丢弃备料。"""
    work = make_work(tmp_path, monkeypatch)
    stub_api(monkeypatch, None)
    lt.resolve_wip()
    assert not list(work.iterdir())
    assert "页面已删除" in capsys.readouterr().out


def test_resolve_wip_bad_marker_refuses(tmp_path, monkeypatch):
    """管线摘要的编辑却标记缺失/不匹配 → 怪异态，保留现场响亮退出。"""
    work = make_work(tmp_path, monkeypatch)
    stub_api(
        monkeypatch,
        make_rev(
            101,
            lt.BOT,
            "编辑了但没标记。",
            comment="LLM(K3): revid 100（5.0 年无人类编辑）",
        ),
    )
    with pytest.raises(SystemExit, match="wip 异常"):
        lt.resolve_wip()
    assert list(work.iterdir())  # 现场保留


def test_resolve_wip_incidental_loop_edit_discards(tmp_path, monkeypatch, capsys):
    """循环任务的偶发编辑（无标记、无 stamp 摘要）→ 视为未编辑成，丢弃重备。"""
    work = make_work(tmp_path, monkeypatch)
    stub_api(
        monkeypatch,
        make_rev(
            101,
            lt.BOT,
            "旧文（被 fix 任务顺改）。",
            comment="机器人：自动替换文本 (-a +b)",
        ),
    )
    lt.resolve_wip()
    assert not list(work.iterdir())
    assert "未编辑成" in capsys.readouterr().out


def test_resolve_wip_done_crash_auto_verifies(tmp_path, monkeypatch, capsys):
    """编辑完成但 done 未跑（标记匹配）→ 自动补跑核验，通过则清场。"""
    work = make_work(tmp_path, monkeypatch)
    new_text = f"{{{{Init}}}}\n\n新文。\n\n[[Category:机翻待校对]]\n{MARKER}\n"
    stub_api(monkeypatch, make_rev(101, lt.BOT, new_text))
    monkeypatch.setattr(lt, "notify_line", lambda meta: "NOTIFY: stub")
    lt.resolve_wip()
    assert not list(work.iterdir())
    out = capsys.readouterr().out
    assert "核验通过" in out and "NOTIFY: stub" in out


# ------------------------------------------------------------ verify_edit

GOOD_NEW = f"{{{{Init}}}}\n\n新文。\n\n[[Category:机翻待校对]]\n{MARKER}\n"


def test_verify_edit_pass(tmp_path, monkeypatch):
    """agent 的合规编辑通过核验。"""
    make_work(tmp_path, monkeypatch)
    stub_api(monkeypatch, make_rev(101, lt.BOT, GOOD_NEW))
    lt.verify_edit("角色_测试", META)  # 不抛 SystemExit 即通过


def test_verify_edit_missing_category_fails(tmp_path, monkeypatch):
    """漏挂机翻待校对分类 → 响亮退出。"""
    make_work(tmp_path, monkeypatch)
    bad = GOOD_NEW.replace("[[Category:机翻待校对]]\n", "")
    stub_api(monkeypatch, make_rev(101, lt.BOT, bad))
    with pytest.raises(SystemExit, match="机翻待校对"):
        lt.verify_edit("角色_测试", META)


def test_verify_edit_no_edit_fails(tmp_path, monkeypatch):
    """zh 页自 prepare 以来无新编辑 → 响亮退出。"""
    make_work(tmp_path, monkeypatch)
    stub_api(monkeypatch, make_rev(90, lt.BOT, "旧文。"))
    with pytest.raises(SystemExit, match="无新编辑"):
        lt.verify_edit("角色_测试", META)


def test_verify_edit_head_change_fails(tmp_path, monkeypatch):
    """页首模板块被改动 → 响亮退出。"""
    make_work(tmp_path, monkeypatch)
    bad = GOOD_NEW.replace("{{Init}}", "{{Init}}\n{{To do}}")
    stub_api(monkeypatch, make_rev(101, lt.BOT, bad))
    with pytest.raises(SystemExit, match="页首"):
        lt.verify_edit("角色_测试", META)
