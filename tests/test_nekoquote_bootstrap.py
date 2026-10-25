"""NekoQuote bootstrap 的完整性与失败恢复（离线）。"""

import sys
from pathlib import Path
from typing import ClassVar

import pytest

import pywikibot as pwb

sys.path.insert(0, str(Path(__file__).parents[1]))
from src.nekoquote import bootstrap


def test_partial_directory_is_not_complete(monkeypatch, tmp_path):
    base = tmp_path / "lua_base"
    base.mkdir()
    (base / "2026-01.lua").write_text("partial", encoding="utf-8")
    complete = tmp_path / "lua_base.complete"
    monkeypatch.setattr(bootstrap, "BASE", base)
    monkeypatch.setattr(bootstrap, "COMPLETE", complete, raising=False)
    assert bootstrap.needed()
    complete.write_text("{}", encoding="utf-8")
    assert not bootstrap.needed()


class FakePage:
    existing: ClassVar[set[str]] = set()
    fail_on: ClassVar[str | None] = None

    def __init__(self, site, title):
        self.month = title.rsplit("/", 1)[-1]
        self.text = "BASE"

    def exists(self):
        if self.month == self.fail_on:
            raise RuntimeError("injected read failure")
        return self.month in self.existing


def _setup(monkeypatch, tmp_path, existing, fail_on=None):
    monkeypatch.setattr(bootstrap, "DATA", tmp_path)
    monkeypatch.setattr(bootstrap, "BASE", tmp_path / "lua_base")
    monkeypatch.setattr(
        bootstrap, "COMPLETE", tmp_path / "lua_base.complete", raising=False
    )
    FakePage.existing = set(existing)
    FakePage.fail_on = fail_on
    monkeypatch.setattr(pwb, "Site", lambda *args: object())
    monkeypatch.setattr(pwb, "Page", FakePage)


def test_failure_does_not_publish_partial_baseline(monkeypatch, tmp_path):
    base = tmp_path / "lua_base"
    live = tmp_path / "lua_live"
    base.mkdir()
    live.mkdir()
    (base / "old.lua").write_text("OLD", encoding="utf-8")
    (live / "old.lua").write_text("OLD", encoding="utf-8")
    _setup(monkeypatch, tmp_path, {"2026-01", "2026-02"}, fail_on="2026-02")
    with pytest.raises(RuntimeError, match="injected"):
        bootstrap.run()
    assert not (base / "2026-01.lua").exists()
    assert (base / "old.lua").read_text(encoding="utf-8") == "OLD"
    assert (live / "old.lua").read_text(encoding="utf-8") == "OLD"
    assert bootstrap.needed()


def test_success_publishes_complete_baseline(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, {"2026-01"})
    bootstrap.run()
    expected = "BASE\n"
    assert (tmp_path / "lua_base" / "2026-01.lua").read_text(
        encoding="utf-8"
    ) == expected
    assert (tmp_path / "lua_live" / "2026-01.lua").read_text(
        encoding="utf-8"
    ) == expected
    assert (tmp_path / "lua_base.complete").exists()
    assert not bootstrap.needed()
