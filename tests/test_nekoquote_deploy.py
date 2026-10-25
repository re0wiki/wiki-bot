"""NekoQuote 月表部署的三方基线与失败恢复（离线，不触 wiki）。"""

import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import pywikibot as pwb
from pywikibot.exceptions import EditConflictError, PageCreatedConflictError

sys.path.insert(0, str(Path(__file__).parents[1]))
import src.nekoquote as pkg

MONTH = "Module:NekoQuote/2026-01"
DOC = MONTH + "/doc"


def run_deploy(
    monkeypatch,
    tmp_path,
    online: str | None,
    live: str | None,
    local: str,
    *,
    doc: str | None = "{{NekoQuoteDoc}}",
    wiki: dict | None = None,
    behavior: dict | None = None,
):
    (tmp_path / "lua").mkdir(exist_ok=True)
    (tmp_path / "lua_live").mkdir(exist_ok=True)
    (tmp_path / "main.lua").write_text("MAIN\n", encoding="utf-8")
    (tmp_path / "lua" / "2026-01.lua").write_text(local, encoding="utf-8")
    if live is not None:
        (tmp_path / "lua_live" / "2026-01.lua").write_text(live, encoding="utf-8")
    monkeypatch.setattr(pkg, "DATA", tmp_path)

    # API 读到的页面没有文件尾换行；保存时 MediaWiki 同样会剥掉它。
    wiki = {"Module:NekoQuote": "MAIN"} if wiki is None else wiki
    wiki.setdefault("Module:NekoQuote", "MAIN")
    if online is not None:
        wiki.setdefault(MONTH, online)
    if doc is not None:
        wiki.setdefault(DOC, doc)
    behavior = {} if behavior is None else behavior
    saved = []
    revisions = {title: 1 for title in wiki}

    class FakeSite:
        def login(self):
            return None

        def user(self):
            return "IchiSanNi"

    class FakePage:
        def __init__(self, site, title):
            self.title = title
            self.text = wiki.get(title, "")
            self.revid = revisions.get(title)

        @property
        def latest_revision(self):
            return SimpleNamespace(revid=self.revid)

        def exists(self):
            return self.title in wiki

        def save(self, **kwargs):
            if self.title == MONTH and behavior.pop("create_race", False):
                wiki[self.title] = "CONCURRENT HUMAN EDIT"
                revisions[self.title] = revisions.get(self.title, 0) + 1
                if kwargs.get("createonly"):
                    raise PageCreatedConflictError(1)
            if self.title == MONTH and behavior.pop("edit_race", False):
                wiki[self.title] = "CONCURRENT HUMAN EDIT"
                revisions[self.title] += 1
            if kwargs.get("createonly") and self.title in wiki:
                raise PageCreatedConflictError(1)
            if "baserevid" in kwargs and kwargs["baserevid"] != revisions.get(
                self.title
            ):
                raise EditConflictError(1)
            if self.title == DOC and behavior.pop("fail_doc_once", False):
                raise RuntimeError("injected doc failure")
            wiki[self.title] = self.text.rstrip("\n")
            revisions[self.title] = revisions.get(self.title, 0) + 1
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


def test_normal_update_ignores_mediawiki_trailing_newline_difference(
    monkeypatch, tmp_path
):
    code, wiki, saved = run_deploy(
        monkeypatch, tmp_path, "OLD DEPLOYED", "OLD DEPLOYED\n", "NEW LOCAL\n"
    )
    assert code == 0
    assert wiki[MONTH] == "NEW LOCAL"
    assert saved == [MONTH]


def test_online_drift_aborts_without_overwrite(monkeypatch, tmp_path):
    code, wiki, saved = run_deploy(
        monkeypatch, tmp_path, "HUMAN EDIT", "OLD DEPLOYED\n", "NEW LOCAL\n"
    )
    assert code == 1
    assert wiki[MONTH] == "HUMAN EDIT"
    assert saved == []


def test_snapshot_lag_with_matching_online_is_noop(monkeypatch, tmp_path):
    code, _, saved = run_deploy(
        monkeypatch, tmp_path, "NEW LOCAL", "OLD DEPLOYED\n", "NEW LOCAL\n"
    )
    assert code == 0
    assert saved == []


def test_existing_page_without_baseline_aborts(monkeypatch, tmp_path):
    code, wiki, saved = run_deploy(
        monkeypatch, tmp_path, "HUMAN EDIT", None, "NEW LOCAL\n"
    )
    assert code == 1
    assert wiki[MONTH] == "HUMAN EDIT"
    assert saved == []


def test_new_page_creation_race_aborts_without_overwrite(monkeypatch, tmp_path):
    code, wiki, saved = run_deploy(
        monkeypatch,
        tmp_path,
        None,
        None,
        "NEW LOCAL",
        behavior={"create_race": True},
    )
    assert code == 1
    assert wiki[MONTH] == "CONCURRENT HUMAN EDIT"
    assert MONTH not in saved


def test_existing_page_edit_race_aborts_without_overwrite(monkeypatch, tmp_path):
    code, wiki, saved = run_deploy(
        monkeypatch,
        tmp_path,
        "OLD",
        "OLD\n",
        "NEW\n",
        behavior={"edit_race": True},
    )
    assert code == 1
    assert wiki[MONTH] == "CONCURRENT HUMAN EDIT"
    assert MONTH not in saved


def test_doc_failure_is_retried_when_month_matches_snapshot(monkeypatch, tmp_path):
    wiki = {}
    behavior = {"fail_doc_once": True}
    with pytest.raises(RuntimeError, match="injected doc failure"):
        run_deploy(
            monkeypatch,
            tmp_path,
            "OLD",
            "OLD",
            "NEW",
            doc=None,
            wiki=wiki,
            behavior=behavior,
        )
    assert wiki[MONTH] == "NEW"
    assert DOC not in wiki

    code, wiki, saved = run_deploy(
        monkeypatch,
        tmp_path,
        "OLD",
        "OLD",
        "NEW",
        doc=None,
        wiki=wiki,
        behavior=behavior,
    )
    assert code == 0
    assert wiki[DOC] == "{{NekoQuoteDoc}}"
    assert saved == [DOC]
