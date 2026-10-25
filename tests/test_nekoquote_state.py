"""NekoQuote 入库后全链失败的重试语义（离线）。"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
import src.scripts.re0_nekoquote as auto
from src.nekoquote import merge


def test_auto_retries_pending_chain_before_advancing(monkeypatch, tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    root = tmp_path / "root"
    root.mkdir()
    (root / "secrets.json").write_text(
        '{"discord_bot_token":"offline-dummy"}', encoding="utf-8"
    )
    state = data / "sync_state.json"
    state.write_text(json.dumps({"last_id": "100"}), encoding="utf-8")
    (data / "tweets.json").write_text("{}", encoding="utf-8")
    pending = data / "chain_pending.json"

    monkeypatch.setattr(auto, "ROOT", root)
    monkeypatch.setattr(auto, "DATA", data)
    monkeypatch.setattr(auto, "STATE", state)
    monkeypatch.setattr(auto, "PENDING", pending, raising=False)
    monkeypatch.setattr(auto.bootstrap, "needed", lambda: False)
    monkeypatch.setattr(auto.pwb, "handle_args", lambda *args: None)
    monkeypatch.setattr(auto.pwb, "info", lambda *args: None)
    monkeypatch.setattr(auto, "fetch_new", lambda token, after: [{"id": "200"}])
    monkeypatch.setattr(auto, "extract", lambda msgs: {"200": "日文"})

    calls = []

    def fail_chain():
        calls.append("fail")
        raise SystemExit("injected chain failure")

    monkeypatch.setattr(auto, "run_chain", fail_chain)
    with pytest.raises(SystemExit, match="injected"):
        auto.main()
    assert json.loads(state.read_text(encoding="utf-8"))["last_id"] == "100"
    assert pending.exists()

    monkeypatch.setattr(auto, "run_chain", lambda: calls.append("success"))
    auto.main()
    assert calls == ["fail", "success"]
    assert json.loads(state.read_text(encoding="utf-8"))["last_id"] == "200"
    assert not pending.exists()


def test_manual_merge_retries_pending_chain(monkeypatch, tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "tweets.json").write_text("{}", encoding="utf-8")
    export = tmp_path / "export"
    export.mkdir()
    (export / "messages.json").write_text("[]", encoding="utf-8")
    pending = data / "chain_pending.json"

    monkeypatch.setattr(merge, "DATA", data)
    monkeypatch.setattr(merge, "PENDING", pending, raising=False)
    monkeypatch.setattr(merge, "extract", lambda msgs: {"200": "日文"})
    monkeypatch.setattr(sys, "argv", ["merge", str(export)])

    calls = []

    def fail_chain():
        calls.append("fail")
        raise SystemExit("injected chain failure")

    monkeypatch.setattr(merge, "run_chain", fail_chain)
    with pytest.raises(SystemExit, match="injected"):
        merge.main()
    assert pending.exists()

    monkeypatch.setattr(merge, "run_chain", lambda: calls.append("success"))
    merge.main()
    assert calls == ["fail", "success"]
    assert not pending.exists()
