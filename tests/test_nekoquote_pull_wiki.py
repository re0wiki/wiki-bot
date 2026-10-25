"""NekoQuote wiki 回写的删除语义（离线）。"""

import json
import runpy
import sys
from pathlib import Path

import pywikibot as pwb

sys.path.insert(0, str(Path(__file__).parents[1]))
import src.nekoquote as pkg
from src.nekoquote import build, llm, pull_wiki

TID = "2105311705297846272"  # 2026-10-01
QID = "456"
SRC = f"https://twitter.com/nezumiironyanko/status/{TID}"


def test_empty_translation_is_removed():
    zh = {TID: {"zh": "旧译"}}
    tw = {TID: {"text": "原文", "author": "nezumiironyanko"}}
    fields = [("src", '"', SRC), ("jt", '"', "原文"), ("t", '"', "")]
    assert pull_wiki.writeback_entry("2026-10", fields, zh, tw) == (1, 0)
    assert "zh" not in zh[TID]


def test_missing_fields_are_removed_and_not_rebuilt(monkeypatch, tmp_path):
    zh = {TID: {"zh": "旧译"}, QID: {"qzh": "提问译文"}}
    tw = {
        TID: {
            "text": "原文",
            "author": "nezumiironyanko",
            "reply_to": QID,
        },
        QID: {"text": "提问", "author": "fan"},
    }
    fields = [("src", '"', SRC)]
    assert pull_wiki.writeback_entry("2026-10", fields, zh, tw) == (2, 2)
    assert "text" not in tw[TID] and "text" not in tw[QID]
    assert "zh" not in zh[TID] and "qzh" not in zh[QID]

    monkeypatch.setattr(build, "DATA", tmp_path)
    (tmp_path / "tweets.json").write_text(json.dumps(tw), encoding="utf-8")
    (tmp_path / "zh.json").write_text(json.dumps(zh), encoding="utf-8")
    buckets = {}
    assert build.merge_raw(buckets, set()) == 1
    names = [name for name, _, _ in buckets["2026-10"][0]["fields"]]
    assert names == ["src"]


def test_new_wiki_translation_creates_updates_and_deletes_local_record():
    zh = {}
    tw = {TID: {"text": "原文", "author": "nezumiironyanko"}}

    fields = [("src", '"', SRC), ("jt", '"', "原文"), ("t", '"', "人工译文")]
    assert pull_wiki.writeback_entry("2026-10", fields, zh, tw) == (1, 0)
    assert zh[TID]["zh"] == "人工译文"

    fields[-1] = ("t", '"', "修订译文")
    assert pull_wiki.writeback_entry("2026-10", fields, zh, tw) == (1, 0)
    assert zh[TID]["zh"] == "修订译文"

    assert pull_wiki.writeback_entry("2026-10", fields[:-1], zh, tw) == (1, 0)
    assert "zh" not in zh[TID]
    assert zh[TID]["zh_deleted"] is True


def run_translate_without_llm(monkeypatch, tmp_path, tw, zh):
    (tmp_path / "lua_base").mkdir(exist_ok=True)
    (tmp_path / "tweets.json").write_text(json.dumps(tw), encoding="utf-8")
    (tmp_path / "zh.json").write_text(json.dumps(zh), encoding="utf-8")
    monkeypatch.setattr(pkg, "DATA", tmp_path)
    monkeypatch.setattr(build, "DATA", tmp_path)
    monkeypatch.setattr(
        llm,
        "get_config",
        lambda provider: ("https://example.invalid", "key", "model"),
    )

    def unexpected_chat(*args, **kwargs):
        raise AssertionError("被人工删除的译文不应重新调用 LLM")

    monkeypatch.setattr(llm, "chat", unexpected_chat)
    monkeypatch.delitem(sys.modules, "src.nekoquote.translate", raising=False)
    runpy.run_module("src.nekoquote.translate")


def test_deleted_answer_is_not_regenerated_or_rebuilt(monkeypatch, tmp_path):
    zh = {TID: {"zh": "旧译"}}
    tw = {TID: {"text": "原文", "author": "nezumiironyanko"}}
    fields = [("src", '"', SRC), ("jt", '"', "原文")]
    assert pull_wiki.writeback_entry("2026-10", fields, zh, tw) == (1, 0)
    assert zh[TID]["zh_deleted"] is True

    run_translate_without_llm(monkeypatch, tmp_path, tw, zh)
    buckets = {}
    assert build.merge_raw(buckets, set()) == 1
    names = [name for name, _, _ in buckets["2026-10"][0]["fields"]]
    assert names == ["src", "jt"]


def test_deleted_question_is_not_regenerated_or_rebuilt(monkeypatch, tmp_path):
    zh = {TID: {"zh": "回答译文"}, QID: {"qzh": "旧提问译文"}}
    tw = {
        TID: {
            "text": "原文",
            "author": "nezumiironyanko",
            "reply_to": QID,
        },
        QID: {"text": "提问", "author": "fan"},
    }
    fields = [
        ("src", '"', SRC),
        ("jt", '"', "原文"),
        ("jq", '"', "提问"),
        ("t", '"', "回答译文"),
    ]
    assert pull_wiki.writeback_entry("2026-10", fields, zh, tw) == (1, 0)
    assert zh[QID]["qzh_deleted"] is True

    run_translate_without_llm(monkeypatch, tmp_path, tw, zh)
    buckets = {}
    assert build.merge_raw(buckets, set()) == 1
    names = [name for name, _, _ in buckets["2026-10"][0]["fields"]]
    assert "q" not in names
    assert "jq" in names and "t" in names


def test_explicit_empty_answer_without_record_is_suppressed(monkeypatch, tmp_path):
    zh = {}
    tw = {TID: {"text": "原文", "author": "nezumiironyanko"}}
    fields = [("src", '"', SRC), ("jt", '"', "原文"), ("t", '"', "")]
    assert pull_wiki.writeback_entry("2026-10", fields, zh, tw) == (1, 0)
    assert zh[TID]["zh_deleted"] is True and "zh" not in zh[TID]

    run_translate_without_llm(monkeypatch, tmp_path, tw, zh)
    buckets = {}
    build.merge_raw(buckets, set())
    names = [name for name, _, _ in buckets["2026-10"][0]["fields"]]
    assert "t" not in names


def test_explicit_empty_question_without_record_is_suppressed(monkeypatch, tmp_path):
    zh = {TID: {"zh": "回答译文"}}
    tw = {
        TID: {
            "text": "原文",
            "author": "nezumiironyanko",
            "reply_to": QID,
        },
        QID: {"text": "提问", "author": "fan"},
    }
    fields = [
        ("src", '"', SRC),
        ("jt", '"', "原文"),
        ("jq", '"', "提问"),
        ("q", '"', ""),
        ("t", '"', "回答译文"),
    ]
    assert pull_wiki.writeback_entry("2026-10", fields, zh, tw) == (1, 0)
    assert zh[QID]["qzh_deleted"] is True and "qzh" not in zh[QID]

    run_translate_without_llm(monkeypatch, tmp_path, tw, zh)
    buckets = {}
    build.merge_raw(buckets, set())
    names = [name for name, _, _ in buckets["2026-10"][0]["fields"]]
    assert "q" not in names and "t" in names


def run_pull_wiki_with_online(
    monkeypatch, tmp_path, tw, zh, online, live_text, before=None
):
    (tmp_path / "lua_base").mkdir(exist_ok=True)
    (tmp_path / "lua_live").mkdir(exist_ok=True)
    (tmp_path / "zh.json").write_text(json.dumps(zh), encoding="utf-8")
    (tmp_path / "tweets.json").write_text(json.dumps(tw), encoding="utf-8")
    (tmp_path / "lua_live" / "2026-10.lua").write_text(live_text, encoding="utf-8")

    class FakePage:
        text = online.rstrip("\n")

    monkeypatch.setattr(pkg, "DATA", tmp_path)
    monkeypatch.setattr(pull_wiki, "DATA", tmp_path)
    monkeypatch.setattr(build, "DATA", tmp_path)
    monkeypatch.setattr(pwb, "Site", lambda *args: object())
    monkeypatch.setattr(
        pull_wiki, "collect_pages", lambda site: {"2026-10": FakePage()}
    )
    monkeypatch.setattr(
        pull_wiki.pagegenerators, "PreloadingGenerator", lambda pages: pages
    )
    if before:
        before()
    return pull_wiki._main()


def test_pull_wiki_refreshes_replayable_live_snapshot(monkeypatch, tmp_path):
    tw = {TID: {"text": "原文", "author": "nezumiironyanko"}}
    online = build.emit_table([build.raw_tweet_entry(TID, tw[TID], None)])
    assert (
        run_pull_wiki_with_online(
            monkeypatch, tmp_path, tw, {TID: {"zh": "旧译"}}, online, "OLD\n"
        )
        == 0
    )
    assert (tmp_path / "lua_live" / "2026-10.lua").read_text(encoding="utf-8") == online


def test_unreplayable_online_edit_is_rejected_before_live_refresh(
    monkeypatch, tmp_path
):
    tw = {TID: {"text": "原文", "author": "nezumiironyanko"}}
    entry = build.raw_tweet_entry(TID, tw[TID], None)
    entry["fields"][0] = ("src", '"', entry["fields"][0][2] + " · 人工复核")
    online = build.emit_table([entry])
    assert (
        run_pull_wiki_with_online(monkeypatch, tmp_path, tw, {}, online, "OLD\n") == 1
    )
    assert (tmp_path / "lua_live" / "2026-10.lua").read_text(
        encoding="utf-8"
    ) == "OLD\n"


def test_stale_output_cleanup_failure_cannot_promote_live(monkeypatch, tmp_path):
    online = build.emit_table([build.raw_tweet_entry(TID, {"text": "线上独有"}, None)])

    def inject_stale_and_cleanup_failure():
        outdir = tmp_path / "lua"
        outdir.mkdir()
        (outdir / "2026-10.lua").write_text(online, encoding="utf-8")
        real_rmtree = pull_wiki.shutil.rmtree

        def fail_rmtree(path, ignore_errors=False):
            if Path(path) == outdir:
                if ignore_errors:
                    return
                raise OSError("injected stale cleanup failure")
            return real_rmtree(path, ignore_errors=ignore_errors)

        monkeypatch.setattr(pull_wiki.shutil, "rmtree", fail_rmtree)

    assert (
        run_pull_wiki_with_online(
            monkeypatch,
            tmp_path,
            {},
            {},
            online,
            "OLD\n",
            before=inject_stale_and_cleanup_failure,
        )
        == 1
    )
    assert (tmp_path / "lua_live" / "2026-10.lua").read_text(
        encoding="utf-8"
    ) == "OLD\n"


def test_missing_raw_entry_aborts_without_writing(monkeypatch, tmp_path):
    (tmp_path / "lua_base").mkdir()
    (tmp_path / "zh.json").write_text("{}", encoding="utf-8")
    (tmp_path / "tweets.json").write_text(
        json.dumps({TID: {"text": "原文", "author": "nezumiironyanko"}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(pkg, "DATA", tmp_path)

    class FakeSite:
        def allpages(self, **kwargs):
            return []

    monkeypatch.setattr(pwb, "Site", lambda *args: FakeSite())
    monkeypatch.delitem(sys.modules, "src.nekoquote.pull_wiki")
    try:
        runpy.run_module("src.nekoquote.pull_wiki", run_name="__main__")
    except SystemExit as exc:
        code = int(exc.code or 0)
    else:
        code = 0
    assert code == 1
    assert (
        json.loads((tmp_path / "tweets.json").read_text(encoding="utf-8"))[TID]["text"]
        == "原文"
    )
