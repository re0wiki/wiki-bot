"""NekoQuote wiki 回写的删除语义（离线）。"""

import json
import runpy
import sys
from pathlib import Path

import pywikibot as pwb

sys.path.insert(0, str(Path(__file__).parents[1]))
import src.nekoquote as pkg
from src.nekoquote import build, pull_wiki

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
