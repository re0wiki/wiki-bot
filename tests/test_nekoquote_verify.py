"""NekoQuote round-trip 校验的退出状态（离线，不触 wiki）。"""

import runpy
import sys
from pathlib import Path

import pywikibot as pwb

sys.path.insert(0, str(Path(__file__).parents[1]))
import src.nekoquote as pkg


def _run_verify(monkeypatch, tmp_path, base_text: str, lua_text: str) -> int:
    (tmp_path / "lua_base").mkdir()
    (tmp_path / "lua").mkdir()
    (tmp_path / "lua_base" / "2026-01.lua").write_text(base_text, encoding="utf-8")
    (tmp_path / "lua" / "2026-01.lua").write_text(lua_text, encoding="utf-8")
    monkeypatch.setattr(pkg, "DATA", tmp_path)

    class FakeSite:
        def login(self):
            return None

    monkeypatch.setattr(pwb, "Site", lambda *args, **kwargs: FakeSite())
    try:
        runpy.run_module("src.nekoquote.verify_rt", run_name="__main__")
    except SystemExit as exc:
        return int(exc.code or 0)
    return 0


def test_missing_baseline_entry_exits_nonzero(monkeypatch, tmp_path):
    base = '{\n  src = "baseline",\n}\n'
    assert _run_verify(monkeypatch, tmp_path, base, "") == 1


def test_complete_baseline_exits_zero(monkeypatch, tmp_path):
    entry = '{\n  src = "baseline",\n}\n'
    assert _run_verify(monkeypatch, tmp_path, entry, entry) == 0
