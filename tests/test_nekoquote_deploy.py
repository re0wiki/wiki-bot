"""NekoQuote 月表部署的三方基线（离线，不触 wiki）。"""

import runpy
import sys
from pathlib import Path

import pywikibot as pwb

sys.path.insert(0, str(Path(__file__).parents[1]))
import src.nekoquote as pkg


def run_deploy(monkeypatch, tmp_path, online: str, live: str | None, local: str):
    (tmp_path / "lua").mkdir()
    (tmp_path / "lua_live").mkdir()
    (tmp_path / "main.lua").write_text("MAIN\n", encoding="utf-8")
    (tmp_path / "lua" / "2026-01.lua").write_text(local, encoding="utf-8")
    if live is not None:
        (tmp_path / "lua_live" / "2026-01.lua").write_text(live, encoding="utf-8")
    monkeypatch.setattr(pkg, "DATA", tmp_path)

    wiki = {
        "Module:NekoQuote": "MAIN\n",
        "Module:NekoQuote/2026-01": online,
        "Module:NekoQuote/2026-01/doc": "{{NekoQuoteDoc}}",
    }
    saved = []

    class FakeSite:
        def login(self):
            return None

        def user(self):
            return "IchiSanNi"

    class FakePage:
        def __init__(self, site, title):
            self.title = title
            self.text = wiki.get(title, "")

        def exists(self):
            return self.title in wiki

        def save(self, **kwargs):
            wiki[self.title] = self.text
            saved.append(self.title)

    monkeypatch.setattr(pwb, "Site", lambda *args: FakeSite())
    monkeypatch.setattr(pwb, "Page", FakePage)
    try:
        runpy.run_module("src.nekoquote.deploy", run_name="__main__")
    except SystemExit as exc:
        code = int(exc.code or 0)
    else:
        code = 0
    return code, wiki, saved


def test_normal_update_is_allowed(monkeypatch, tmp_path):
    code, wiki, saved = run_deploy(
        monkeypatch, tmp_path, "OLD DEPLOYED\n", "OLD DEPLOYED\n", "NEW LOCAL\n"
    )
    assert code == 0
    assert wiki["Module:NekoQuote/2026-01"] == "NEW LOCAL\n"
    assert saved == ["Module:NekoQuote/2026-01"]


def test_online_drift_aborts_without_overwrite(monkeypatch, tmp_path):
    code, wiki, saved = run_deploy(
        monkeypatch, tmp_path, "HUMAN EDIT\n", "OLD DEPLOYED\n", "NEW LOCAL\n"
    )
    assert code == 1
    assert wiki["Module:NekoQuote/2026-01"] == "HUMAN EDIT\n"
    assert saved == []


def test_snapshot_lag_with_matching_online_is_noop(monkeypatch, tmp_path):
    code, _, saved = run_deploy(
        monkeypatch, tmp_path, "NEW LOCAL\n", "OLD DEPLOYED\n", "NEW LOCAL\n"
    )
    assert code == 0
    assert saved == []


def test_existing_page_without_baseline_aborts(monkeypatch, tmp_path):
    code, wiki, saved = run_deploy(
        monkeypatch, tmp_path, "HUMAN EDIT\n", None, "NEW LOCAL\n"
    )
    assert code == 1
    assert wiki["Module:NekoQuote/2026-01"] == "HUMAN EDIT\n"
    assert saved == []
