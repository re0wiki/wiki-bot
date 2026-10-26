"""NekoQuote 入库后全链失败的重试语义（离线）。"""

import json
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
import src.scripts.re0_nekoquote as auto
from src.nekoquote import bootstrap, chain, merge
from src.nekoquote import state as nq_state


def test_auto_retries_pending_chain_before_advancing(monkeypatch, tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    state = data / "sync_state.json"
    initial = {"source": "fxtwitter_v2", "last_original_id": "100"}
    state.write_text(json.dumps(initial), encoding="utf-8")
    (data / "tweets.json").write_text("{}", encoding="utf-8")
    pending = data / "chain_pending.json"

    monkeypatch.setattr(auto, "DATA", data)
    monkeypatch.setattr(auto, "STATE", state)
    monkeypatch.setattr(auto, "PENDING", pending, raising=False)
    monkeypatch.setattr(auto.bootstrap, "needed", lambda: False)
    monkeypatch.setattr(auto.pwb, "handle_args", lambda *args: None)
    monkeypatch.setattr(auto.pwb, "info", lambda *args: None)

    def fetch_quotes(session, *, stop_id=None, stop_before=None):
        assert stop_id == "100"
        assert stop_before is None
        return {"200": "日文"}, "200"

    monkeypatch.setattr(auto, "fetch_quotes", fetch_quotes)
    calls = []

    def fail_chain():
        calls.append("fail")
        raise SystemExit("injected chain failure")

    monkeypatch.setattr(auto, "run_chain", fail_chain)
    with pytest.raises(SystemExit, match="injected"):
        auto.main()
    assert json.loads(state.read_text(encoding="utf-8")) == initial
    assert pending.exists()

    monkeypatch.setattr(auto, "run_chain", lambda: calls.append("success"))
    auto.main()
    assert calls == ["fail", "success"]
    assert json.loads(state.read_text(encoding="utf-8")) == {
        "source": "fxtwitter_v2",
        "last_original_id": "200",
    }
    assert not pending.exists()


def test_fetch_failure_preserves_state(monkeypatch, tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    state = data / "sync_state.json"
    initial = {"source": "fxtwitter_v2", "last_original_id": "100"}
    state.write_text(json.dumps(initial), encoding="utf-8")
    (data / "tweets.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(auto, "DATA", data)
    monkeypatch.setattr(auto, "STATE", state)
    monkeypatch.setattr(auto, "PENDING", data / "chain_pending.json", raising=False)
    monkeypatch.setattr(auto.bootstrap, "needed", lambda: False)
    monkeypatch.setattr(auto.pwb, "handle_args", lambda *args: None)
    monkeypatch.setattr(auto.pwb, "info", lambda *args: None)
    calls = []
    monkeypatch.setattr(auto, "run_chain", lambda: calls.append("chain"))

    def fetch_quotes(session, *, stop_id=None, stop_before=None):
        raise RuntimeError("injected network failure")

    monkeypatch.setattr(auto, "fetch_quotes", fetch_quotes)
    with pytest.raises(RuntimeError, match="injected network failure"):
        auto.main()

    assert calls == []
    assert json.loads(state.read_text(encoding="utf-8")) == initial
    assert not (data / "chain_pending.json").exists()


def test_fbk_state_migrates_with_backfill(monkeypatch, tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    state = data / "sync_state.json"
    state.write_text(json.dumps({"last_id": "discord-watermark"}), encoding="utf-8")
    (data / "tweets.json").write_text('{"300": {"text": "已收"}}', encoding="utf-8")

    monkeypatch.setattr(auto, "DATA", data)
    monkeypatch.setattr(auto, "STATE", state)
    monkeypatch.setattr(auto, "PENDING", data / "chain_pending.json", raising=False)
    monkeypatch.setattr(auto.bootstrap, "needed", lambda: False)
    monkeypatch.setattr(auto.pwb, "handle_args", lambda *args: None)
    monkeypatch.setattr(auto.pwb, "info", lambda *args: None)
    calls = []
    monkeypatch.setattr(auto, "run_chain", lambda: calls.append("chain"))

    fetch_calls = []

    def fetch_quotes(session, *, stop_id=None, stop_before=None):
        fetch_calls.append((stop_id, stop_before))
        if len(fetch_calls) == 1:
            assert stop_id is None
            assert stop_before == auto.MIGRATION_SINCE
        else:
            assert stop_id == "300"
            assert stop_before is None
        return {"300": "不应覆盖", "200": "新推"}, "300"

    monkeypatch.setattr(auto, "fetch_quotes", fetch_quotes)
    auto.main()
    auto.main()

    assert fetch_calls == [(None, auto.MIGRATION_SINCE), ("300", None)]
    assert calls == ["chain"]
    assert json.loads(state.read_text(encoding="utf-8")) == {
        "source": "fxtwitter_v2",
        "last_original_id": "300",
    }
    tweets = json.loads((data / "tweets.json").read_text(encoding="utf-8"))
    assert tweets["300"]["text"] == "已收"
    assert tweets["200"] == {
        "text": "新推",
        "author": "nezumiironyanko",
        "src": "fxtwitter_v2",
    }


def test_bootstrap_seeds_latest_original_without_backfill(monkeypatch, tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    state = data / "sync_state.json"
    (data / "tweets.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(auto, "DATA", data)
    monkeypatch.setattr(auto, "STATE", state)
    monkeypatch.setattr(auto, "PENDING", data / "chain_pending.json", raising=False)
    monkeypatch.setattr(auto.bootstrap, "needed", lambda: True)
    calls = []
    monkeypatch.setattr(auto.bootstrap, "run", lambda: calls.append("bootstrap"))
    monkeypatch.setattr(auto, "run_chain", lambda: calls.append("chain"))
    monkeypatch.setattr(auto.pwb, "handle_args", lambda *args: None)
    monkeypatch.setattr(auto.pwb, "info", lambda *args: None)
    monkeypatch.setattr(auto, "latest_original_id", lambda session: "900")

    def fetch_quotes(session, *, stop_id=None, stop_before=None):
        assert stop_id == "900"
        assert stop_before is None
        return {}, "900"

    monkeypatch.setattr(auto, "fetch_quotes", fetch_quotes)
    auto.main()

    assert calls == ["bootstrap"]
    assert json.loads(state.read_text(encoding="utf-8")) == {
        "source": "fxtwitter_v2",
        "last_original_id": "900",
    }
    assert json.loads((data / "tweets.json").read_text(encoding="utf-8")) == {}


def test_bootstrap_seed_retries_while_state_is_missing(monkeypatch, tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    state = data / "sync_state.json"
    (data / "tweets.json").write_text("{}", encoding="utf-8")
    complete = {"value": False}

    monkeypatch.setattr(auto, "DATA", data)
    monkeypatch.setattr(auto, "STATE", state)
    monkeypatch.setattr(auto, "PENDING", data / "chain_pending.json", raising=False)
    monkeypatch.setattr(auto.bootstrap, "needed", lambda: not complete["value"])
    calls = []

    def bootstrap_run():
        complete["value"] = True
        calls.append("bootstrap")

    def latest_original_id(session):
        calls.append("latest")
        if calls.count("latest") == 1:
            raise RuntimeError("injected seed failure")
        return "900"

    monkeypatch.setattr(auto.bootstrap, "run", bootstrap_run)
    monkeypatch.setattr(auto, "latest_original_id", latest_original_id)
    monkeypatch.setattr(auto, "run_chain", lambda: calls.append("chain"))
    monkeypatch.setattr(auto.pwb, "handle_args", lambda *args: None)
    monkeypatch.setattr(auto.pwb, "info", lambda *args: None)

    def fetch_quotes(session, *, stop_id=None, stop_before=None):
        assert stop_id == "900"
        assert stop_before is None
        return {}, "900"

    monkeypatch.setattr(auto, "fetch_quotes", fetch_quotes)
    with pytest.raises(RuntimeError, match="injected seed failure"):
        auto.main()
    assert not state.exists()

    auto.main()

    assert calls == ["bootstrap", "latest", "latest"]
    assert json.loads(state.read_text(encoding="utf-8")) == {
        "source": "fxtwitter_v2",
        "last_original_id": "900",
    }


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


def test_write_json_is_atomic_on_replace_failure(monkeypatch, tmp_path):
    path = tmp_path / "state.json"
    path.write_text('{"old": 1}', encoding="utf-8")

    def fail_replace(src, dst):
        raise OSError("injected replace failure")

    monkeypatch.setattr(nq_state.os, "replace", fail_replace)
    with pytest.raises(OSError, match="injected"):
        nq_state.write_json(path, {"new": 2})
    assert json.loads(path.read_text(encoding="utf-8")) == {"old": 1}
    assert not list(tmp_path.glob("*.tmp"))


def test_chain_rejects_incomplete_baseline(monkeypatch, tmp_path):
    monkeypatch.setattr(
        bootstrap, "COMPLETE", tmp_path / "lua_base.complete", raising=False
    )

    def unexpected_run(*args, **kwargs):
        raise AssertionError("基线不完整时不应启动任何子流程")

    monkeypatch.setattr(chain.subprocess, "run", unexpected_run)
    with pytest.raises(SystemExit, match="基线不完整"):
        chain.run_chain()


class SyncFile:
    def __init__(self, path, barrier):
        self.path = path
        self.barrier = barrier

    def read_text(self, encoding):
        value = self.path.read_text(encoding=encoding)
        try:
            self.barrier.wait(timeout=0.2)
        except threading.BrokenBarrierError:
            pass
        return value

    def write_text(self, value, encoding):
        return self.path.write_text(value, encoding=encoding)

    def __getattr__(self, name):
        return getattr(self.path, name)

    def __fspath__(self):
        return str(self.path)


class FakeData:
    def __init__(self, root, tweets):
        self.root = root
        self.tweets = tweets

    def __truediv__(self, name):
        return self.tweets if name == "tweets.json" else self.root / name

    def mkdir(self, **kwargs):
        return self.root.mkdir(**kwargs)


def test_concurrent_ingress_does_not_lose_tweets(monkeypatch, tmp_path):
    data_root = tmp_path / "data"
    data_root.mkdir()
    tweets_path = data_root / "tweets.json"
    tweets_path.write_text("{}", encoding="utf-8")
    data = FakeData(data_root, SyncFile(tweets_path, threading.Barrier(2)))
    state = data_root / "sync_state.json"
    state.write_text(
        json.dumps({"source": "fxtwitter_v2", "last_original_id": "100"}),
        encoding="utf-8",
    )
    pending = data_root / "chain_pending.json"

    monkeypatch.setattr(auto, "DATA", data)
    monkeypatch.setattr(auto, "STATE", state)
    monkeypatch.setattr(auto, "PENDING", pending, raising=False)
    monkeypatch.setattr(auto.bootstrap, "needed", lambda: False)
    monkeypatch.setattr(auto.pwb, "handle_args", lambda *args: None)
    monkeypatch.setattr(auto.pwb, "info", lambda *args: None)
    monkeypatch.setattr(auto, "run_chain", lambda: None)

    def fetch_quotes(session, *, stop_id=None, stop_before=None):
        tid = "201" if threading.current_thread().name == "worker-a" else "202"
        return {tid: "日文"}, tid

    monkeypatch.setattr(auto, "fetch_quotes", fetch_quotes)
    errors = []

    def run_worker():
        try:
            auto.main()
        except (Exception, SystemExit) as exc:  # noqa: BLE001 - 异常带回主线程断言
            errors.append(exc)

    workers = [
        threading.Thread(target=run_worker, name="worker-a"),
        threading.Thread(target=run_worker, name="worker-b"),
    ]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=20)
    assert not errors and all(not worker.is_alive() for worker in workers)
    assert set(json.loads(tweets_path.read_text(encoding="utf-8"))) == {"201", "202"}
