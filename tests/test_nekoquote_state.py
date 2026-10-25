"""NekoQuote 入库后全链失败的重试语义（离线）。"""

import json
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
import src.scripts.re0_nekoquote as auto
from src.nekoquote import merge
from src.nekoquote import state as nq_state


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


class FakeRoot:
    def __truediv__(self, name):
        assert name == "secrets.json"
        return SimpleNamespace(
            exists=lambda: True,
            read_text=lambda encoding: '{"discord_bot_token":"offline-dummy"}',
        )


def test_concurrent_ingress_does_not_lose_tweets(monkeypatch, tmp_path):
    data_root = tmp_path / "data"
    data_root.mkdir()
    tweets_path = data_root / "tweets.json"
    tweets_path.write_text("{}", encoding="utf-8")
    data = FakeData(data_root, SyncFile(tweets_path, threading.Barrier(2)))
    state = data_root / "sync_state.json"
    state.write_text(json.dumps({"last_id": "100"}), encoding="utf-8")
    pending = data_root / "chain_pending.json"

    monkeypatch.setattr(auto, "ROOT", FakeRoot())
    monkeypatch.setattr(auto, "DATA", data)
    monkeypatch.setattr(auto, "STATE", state)
    monkeypatch.setattr(auto, "PENDING", pending, raising=False)
    monkeypatch.setattr(auto.bootstrap, "needed", lambda: False)
    monkeypatch.setattr(auto.pwb, "handle_args", lambda *args: None)
    monkeypatch.setattr(auto.pwb, "info", lambda *args: None)
    monkeypatch.setattr(auto, "run_chain", lambda: None)

    def fetch_new(token, after):
        return [
            {"id": "201" if threading.current_thread().name == "worker-a" else "202"}
        ]

    monkeypatch.setattr(auto, "fetch_new", fetch_new)
    monkeypatch.setattr(auto, "extract", lambda msgs: {msgs[0]["id"]: "日文"})
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
