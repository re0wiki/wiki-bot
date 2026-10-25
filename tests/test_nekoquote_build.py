"""NekoQuote 构建器的月份边界（离线）。"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from src.nekoquote import build


def _snowflake(dt: datetime) -> str:
    return str((int(dt.timestamp() * 1000) - build.EPOCH) << 22)


def test_merge_raw_accepts_2027_tweet(monkeypatch, tmp_path):
    class FakeDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2027, 1, 1, tzinfo=tz)

    monkeypatch.setattr(build, "datetime", FakeDateTime)
    monkeypatch.setattr(build, "DATA", tmp_path)
    tid = _snowflake(datetime(2027, 1, 1, tzinfo=build.JST))
    (tmp_path / "tweets.json").write_text(
        json.dumps({tid: {"text": "test", "author": "nezumiironyanko"}}),
        encoding="utf-8",
    )
    buckets = {}
    assert build.merge_raw(buckets, set()) == 1
    assert list(buckets) == ["2027-01"]


def test_month_validation_rejects_future_but_accepts_current():
    now = datetime(2026, 12, 15, tzinfo=build.JST)
    assert build.is_valid_tweet_month("2026-12", now)
    assert not build.is_valid_tweet_month("2027-01", now)


def _merge_attribution(monkeypatch, tmp_path, zh_record):
    tid = _snowflake(datetime(2026, 10, 1, tzinfo=build.JST))
    (tmp_path / "tweets.json").write_text(
        json.dumps({tid: {"text": "原文", "author": "nezumiironyanko"}}),
        encoding="utf-8",
    )
    (tmp_path / "zh.json").write_text(json.dumps({tid: zh_record}), encoding="utf-8")
    monkeypatch.setattr(build, "DATA", tmp_path)
    buckets = {}
    build.merge_raw(buckets, set())
    return buckets["2026-10"][0]["fields"][0][2]


def test_legacy_translation_has_neutral_attribution(monkeypatch, tmp_path):
    src = _merge_attribution(monkeypatch, tmp_path, {"zh": "旧译"})
    assert " · 译：LLM" in src
    assert "K3.1 Pro" not in src


def test_translation_attribution_uses_recorded_model(monkeypatch, tmp_path):
    src = _merge_attribution(
        monkeypatch,
        tmp_path,
        {"zh": "译文", "provider": "kimi", "model": "k3.1-pro"},
    )
    assert " · 译：Kimi k3.1-pro" in src
