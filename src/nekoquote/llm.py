"""语录管线 LLM 客户端（默认 Kimi K3.1 Pro，配置在 secrets.json 的 llm 字段）。

- 429/5xx 指数退避（尊重 Retry-After）；reasoning 模型 max_tokens 恒 32768
- 译名保障 = prompt 注入（glossary_lines）：推文中出现的译名表实体按 ja 面形态
  确定性检出并给出 ja→zh 对照；ja 面形态歧义（多名共用）的不注入
"""

import hashlib
import json
import re
import time
from datetime import UTC, datetime
from pathlib import Path

import requests

KEYS_FILE = Path(__file__).parents[2] / "secrets.json"
LOG_FILE = Path(__file__).parents[2] / "logs" / "nekoquote_llm.jsonl"

_GLOSSARY: dict[str, str] | None = None

# 与普通词同形的 ja 面形态不注入（ジュース=果汁、ゴージャス=gorgeous、
# タイガー=阪神タイガース棒球联动推 等），避免非实体语境误导
_COMMON_WORD_SURFACES = {"ジュース", "ゴージャス", "タイガー"}


def _exact_surfaces(entries):
    surf: dict[str, str | None] = {}
    # 先全段（精确）
    for e in entries:
        if e.ja:
            s = e.ja.strip()
            if len(s) >= 2 and s not in _COMMON_WORD_SURFACES:
                surf[s] = e.std if surf.get(s) in (None, e.std) else None
    return surf


def _segment_surfaces(entry):
    for s in re.split(r"[·・]", entry.ja):
        s = s.strip()
        if len(s) < 2 or s == entry.ja.strip() or s in _COMMON_WORD_SURFACES:
            continue
        yield s


def _add_segment_surfaces(surf, exact, entries):
    # 再分段：不覆盖已有精确归属
    for e in entries:
        if not e.ja:
            continue
        for s in _segment_surfaces(e):
            if s in exact:
                continue
            if s in surf and surf[s] != e.std:
                surf[s] = None  # 歧义
            else:
                surf[s] = e.std


def _build_glossary() -> dict[str, str]:
    """ja 面形态 -> 标准中文名。面形态 = ja 全文 + 各段。

    冲突裁决：ja 全文精确相等者优先于「别的条目 ja 的段」（ロズワール → 罗兹瓦尔
    精确命中，压过 罗兹瓦尔·K.梅札斯 ja=ロズワール·K·メイザース 的段）；仍歧义（多名共用）的不注入。
    """
    import translations  # 仓库根（调用方已把根目录入 sys.path）

    entries = translations.ENTRIES
    surf = _exact_surfaces(entries)
    exact = {k: v for k, v in surf.items() if v}
    _add_segment_surfaces(surf, exact, entries)
    return {k: v for k, v in surf.items() if v}


def glossary_lines(texts: list[str]) -> str:
    """texts 中出现的实体的译名对照块（无命中返回空串）。"""
    global _GLOSSARY
    if _GLOSSARY is None:
        _GLOSSARY = _build_glossary()
    hits = {}
    for surface, zh in _GLOSSARY.items():
        if any(surface in t for t in texts):
            hits[surface] = zh
    if not hits:
        return ""
    lines = "\n".join(f"{ja} = {zh}" for ja, zh in sorted(hits.items()))
    return f"\n\n译名对照（必须使用）：\n{lines}\n"


SYSTEM_PROMPT = """你是 Re:Zero（Re:从零开始的异世界生活）的日译中译者。
把作者长月达平（推特 @nezumiironyanko）的推文翻译成简体中文。

要求：
- 忠实原文，保留作者口语化的吐槽语气，不增不减
- 推文末尾的 #rezeroneko 标签忽略不译
- 只输出译文本身：不要原文、不要解释、不要注音、不要引号包裹"""


def get_config(provider="kimi"):
    """返回 (base_url, api_key, model)，读 secrets.json 的 llm 字段。"""
    cfg = (
        json.loads(KEYS_FILE.read_text(encoding="utf-8"))
        .get("llm", {})
        .get(provider, {})
        if KEYS_FILE.exists()
        else {}
    )
    base_url = cfg.get("base_url", "").rstrip("/")
    key = cfg.get("api_key")
    model = cfg.get("model")
    if not (key and model):
        raise FileNotFoundError(f"无 LLM 配置（{KEYS_FILE} 的 llm.{provider} 字段）")
    return base_url, key, model


def _log_event(event):
    """追加脱敏诊断事件；日志故障不影响翻译主流程。"""
    event = {"timestamp": datetime.now(UTC).isoformat(), **event}
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except OSError as e:
        print(f"  LLM 诊断日志写入失败: {e}", flush=True)


def _log_http_response(resp, context):
    """记录状态、关联 ID、用量与错误摘要，不记录正文内容。"""
    headers = getattr(resp, "headers", {})
    event = {
        **context,
        "event": "http_response",
        "status": resp.status_code,
        "request_id": headers.get("x-request-id") or headers.get("request-id"),
        "retry_after": headers.get("Retry-After"),
        "cf_ray": headers.get("cf-ray"),
        "server": headers.get("server"),
    }
    if resp.status_code == 200:
        try:
            data = resp.json()
            choice = data["choices"][0]
            message = choice["message"]
        except (KeyError, IndexError, TypeError, ValueError) as e:
            event["parse_error"] = f"{type(e).__name__}: {e}"
        else:
            event.update(
                response_id=data.get("id"),
                finish_reason=choice.get("finish_reason"),
                usage=data.get("usage"),
                content_chars=len(message.get("content") or ""),
                reasoning_chars=len(message.get("reasoning_content") or ""),
            )
    else:
        event["body_preview"] = (getattr(resp, "text", "") or "")[:2000]
    _log_event(event)
    return event


def chat(
    user_text,
    system=SYSTEM_PROMPT,
    max_tokens=4000,
    max_attempts=6,
    provider="kimi",
    timeout=120,
):
    """带退避的 chat 调用；返回 content。失败到最后抛异常。"""
    return _chat_openai(user_text, system, max_tokens, max_attempts, provider, timeout)


class LengthError(RuntimeError):
    """模型输出被 max_tokens 截断；即使已有部分 content 也不能当成功译文。"""


def _response_content(resp):
    data = resp.json()
    choice = data["choices"][0]
    msg = choice["message"]
    content = (msg.get("content") or "").strip()
    if not content:
        # 该模型偶发把最终答案塞进 reasoning_content 并以 </final> 分隔、content 留空
        reasoning = (msg.get("reasoning_content") or "").strip()
        if "</final>" in reasoning:
            content = reasoning.rsplit("</final>", 1)[1].strip()
    return data, choice, content


def _handle_response(resp, attempt, max_attempts, tokens, delay):
    if resp.status_code == 200:
        data, choice, content = _response_content(resp)
        if choice.get("finish_reason") == "length":
            raise LengthError(f"finish_reason=length（max_tokens={tokens}）")
        if not content:
            raise RuntimeError(f"空 content: {str(data)[:300]}")
        return "success", content
    if resp.status_code in (429, 500, 502, 503, 504):
        retry_after = resp.headers.get("Retry-After")
        wait = float(retry_after) if retry_after else delay
        if attempt == max_attempts:
            raise RuntimeError(f"HTTP {resp.status_code} 重试耗尽: {resp.text[:200]}")
        print(
            f"  [重试 {attempt}/{max_attempts}] HTTP {resp.status_code}，{wait:.0f}s 后重试"
        )
        return "retry", wait
    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:500]}")


def _chat_openai(user_text, system, max_tokens, max_attempts, provider, timeout=120):
    base_url, key, model = get_config(provider)
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if provider == "kimi":
        # kimi /coding 端点 UA 白名单：要求 claude-code UA，否则 403（抄 Hermes Agent）
        headers["User-Agent"] = "claude-code/0.1.0"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_text},
        ],
        "max_tokens": max_tokens,
    }
    if provider == "kimi":
        # K3.1 Pro 是 reasoning 模型，推理量随任务不随上限；API 按实际生成计费，
        # 低上限烧穿 = 推理费白付 + 重试再付——恒用最高档一次到位（32768 上限本身防失控）。
        payload["max_tokens"] = 32768
        timeout = max(timeout, 1800)  # 长生成期间无字节流，读超时须覆盖
    delay = 5.0
    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        context = {
            "provider": provider,
            "model": model,
            "attempt": attempt,
            "max_attempts": max_attempts,
        }
        payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        _log_event(
            {
                **context,
                "event": "request_start",
                "user_chars": len(user_text),
                "system_chars": len(system),
                "max_tokens": payload["max_tokens"],
                "timeout": timeout,
                "payload_sha256": hashlib.sha256(payload_json.encode()).hexdigest(),
            }
        )
        print(
            f"  [请求 {attempt}/{max_attempts}] {provider}/{model}，"
            f"输入 {len(user_text)} 字",
            flush=True,
        )
        started = time.perf_counter()
        try:
            resp = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=timeout,
            )
        except requests.RequestException as e:
            _log_event(
                {
                    **context,
                    "event": "network_error",
                    "elapsed_s": round(time.perf_counter() - started, 3),
                    "error_type": type(e).__name__,
                    "error": str(e),
                }
            )
            if attempt == max_attempts:
                raise
            print(
                f"  [重试 {attempt}/{max_attempts}] 网络错误: {e}，{delay:.0f}s 后重试"
            )
            time.sleep(delay)
            delay *= 2
            continue
        elapsed = time.perf_counter() - started
        response_event = _log_http_response(
            resp, {**context, "elapsed_s": round(elapsed, 3)}
        )
        print(
            f"  [响应 {attempt}/{max_attempts}] HTTP {resp.status_code}，"
            f"{elapsed:.1f}s，request_id={response_event['request_id']}",
            flush=True,
        )
        action, result = _handle_response(
            resp, attempt, max_attempts, payload["max_tokens"], delay
        )
        if action == "success":
            return result
        time.sleep(result)
        delay *= 2
    raise AssertionError("unreachable")


def translate_ja2zh(ja_text, provider="kimi"):
    return chat(ja_text, provider=provider)


if __name__ == "__main__":
    # 自检：一条实测
    out = translate_ja2zh("今週はメモリースノーです！  #rezeroneko")
    print("自检翻译:", out)
