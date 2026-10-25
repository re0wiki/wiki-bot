"""报告输出目录从空运行目录自举的回归测试（不触 wiki）。"""

import json
import runpy
from pathlib import Path

from repo_loader import REPO_ROOT, load_module

import pywikibot
from pywikibot.data import api

rl = load_module("redlinks_audit", "src/tools/redlinks_audit.py")


class EmptySite:
    def allpages(self, namespace):
        return []

    def simple_request(self, **params):
        class Request:
            def submit(self):
                return {"query": {"allpages": []}}

        return Request()


class EmptyRequest:
    def __init__(self, site, parameters):
        pass

    def submit(self):
        return {"query": {"pages": {}}}


def test_redlinks_report_creates_missing_output_directory(tmp_path, monkeypatch):
    out_json = tmp_path / "logs" / "redlinks_audit.json"
    out_md = tmp_path / "logs" / "redlinks_audit.md"
    monkeypatch.setattr(rl, "OUT_JSON", str(out_json))
    monkeypatch.setattr(rl, "OUT_MD", str(out_md))
    monkeypatch.setattr(rl.pywikibot, "Site", lambda *args: EmptySite())
    rl.main()
    assert json.loads(out_json.read_text(encoding="utf-8"))["pages_scanned"] == 0
    assert out_md.exists()


def test_template_usage_recheck_creates_missing_output_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(pywikibot, "Site", lambda *args: EmptySite())
    monkeypatch.setattr(api, "Request", EmptyRequest)
    runpy.run_path(str(REPO_ROOT / "src" / "tools" / "recheck_template_usage.py"))
    outputs = list(Path("logs").glob("template_usage_recheck_*.json"))
    assert len(outputs) == 1
    assert json.loads(outputs[0].read_text(encoding="utf-8")) == {}
