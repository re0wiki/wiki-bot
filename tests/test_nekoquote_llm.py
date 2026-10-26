"""NekoQuote LLM 截断与重试行为（离线，不调用外部 API）。"""

import json
import re
import runpy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
import src.nekoquote as pkg
from src.nekoquote import llm


class FakeResponse:
    status_code = 200

    def __init__(self, content: str, finish_reason: str):
        self.content = content
        self.finish_reason = finish_reason

    def json(self):
        return {
            "choices": [
                {
                    "message": {"content": self.content, "reasoning_content": ""},
                    "finish_reason": self.finish_reason,
                }
            ]
        }


def _config(provider):
    return "https://example.invalid", "key", "model"


def test_partial_length_response_is_not_returned(monkeypatch):
    monkeypatch.setattr(llm, "get_config", _config)
    monkeypatch.setattr(
        llm.requests,
        "post",
        lambda *args, **kwargs: FakeResponse("0\t被截断", "length"),
    )
    with pytest.raises(RuntimeError, match="length"):
        llm._chat_openai("text", "system", 32768, 3, "kimi")


def test_kimi_length_at_cap_does_not_retry(monkeypatch):
    monkeypatch.setattr(llm, "get_config", _config)
    calls = []

    def post(url, headers, json, timeout):
        calls.append(json["max_tokens"])
        return FakeResponse("", "length")

    monkeypatch.setattr(llm.requests, "post", post)
    monkeypatch.setattr(llm.time, "sleep", lambda seconds: None)
    with pytest.raises(RuntimeError, match="length"):
        llm._chat_openai("text", "system", 32768, 3, "kimi")
    assert calls == [32768]


def test_length_does_not_escalate_token_limit(monkeypatch):
    monkeypatch.setattr(llm, "get_config", _config)
    calls = []

    def post(url, headers, json, timeout):
        calls.append(json["max_tokens"])
        return FakeResponse("", "length")

    monkeypatch.setattr(llm.requests, "post", post)
    with pytest.raises(RuntimeError, match="length"):
        llm._chat_openai("text", "system", 1000, 1, "other")
    assert calls == [1000]


def test_run_batch_splits_length_errors(monkeypatch, tmp_path):
    (tmp_path / "lua_base").mkdir()
    (tmp_path / "tweets.json").write_text("{}", encoding="utf-8")
    (tmp_path / "zh.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(pkg, "DATA", tmp_path)
    monkeypatch.setattr(llm, "get_config", _config)
    ns = runpy.run_module("src.nekoquote.translate")
    run_batch = ns["run_batch"]
    calls = []

    def fake_chat(prompt, **kwargs):
        calls.append(prompt)
        if len(calls) == 1:
            raise getattr(llm, "LengthError", RuntimeError)("finish_reason=length")
        ids = re.findall(r"(?m)^(\d+)\t", prompt)
        return "\n".join(f"{i}\t译文" for i in ids)

    monkeypatch.setitem(run_batch.__globals__, "chat", fake_chat)
    result = run_batch([("a", "甲"), ("b", "乙")], "")
    assert result == {"a": "译文", "b": "译文"}
    assert len(calls) == 3


def test_new_translation_records_provider_and_model(monkeypatch, tmp_path):
    (tmp_path / "lua_base").mkdir()
    tid = "2105311705297846272"  # 2026-10-01
    (tmp_path / "tweets.json").write_text(
        json.dumps({tid: {"text": "原文", "author": "nezumiironyanko"}}),
        encoding="utf-8",
    )
    (tmp_path / "zh.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(pkg, "DATA", tmp_path)
    monkeypatch.setattr(
        llm,
        "get_config",
        lambda provider: ("https://example.invalid", "key", "k3.1-pro"),
    )
    monkeypatch.setattr(llm, "chat", lambda *args, **kwargs: "0\t译文")
    monkeypatch.delitem(sys.modules, "src.nekoquote.translate", raising=False)
    runpy.run_module("src.nekoquote.translate")
    record = json.loads((tmp_path / "zh.json").read_text(encoding="utf-8"))[tid]
    assert record["zh"] == "译文"
    assert record["provider"] == "kimi"
    assert record["model"] == "k3.1-pro"
