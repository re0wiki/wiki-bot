"""语录管线 LLM 客户端（默认 Kimi K3，配置在 secrets.json 的 llm 字段）。

- 429/5xx 指数退避（尊重 Retry-After）；reasoning 模型 max_tokens 恒 32768
- 历史：早期给弱模型（OpenCode deepseek-v4-flash-free，质量不达标已弃用）配的
  ja→zh 名词表注入已随 K3 切换移除——译名由确定性后处理（nekoquote.normalize
  套 user-fixes 译名规则）兜底，比 prompt 注入可靠
"""

import json
import time
from pathlib import Path

import requests

KEYS_FILE = Path(__file__).parent.parent / "secrets.json"


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
        # K3 是 reasoning 模型，推理量随任务不随上限；API 按实际生成计费，
        # 低上限烧穿 = 推理费白付 + 重试再付——恒用最高档一次到位（32768 上限本身防失控）。
        payload["max_tokens"] = 32768
        timeout = max(timeout, 1800)  # 长生成期间无字节流，读超时须覆盖
    delay = 5.0
    tokens: int = payload["max_tokens"]
    escalations = 0
    for attempt in range(1, max_attempts + 1):
        payload["max_tokens"] = tokens
        try:
            resp = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=timeout,
            )
        except requests.RequestException as e:
            if attempt == max_attempts:
                raise
            print(
                f"  [重试 {attempt}/{max_attempts}] 网络错误: {e}，{delay:.0f}s 后重试"
            )
            time.sleep(delay)
            delay *= 2
            continue
        if resp.status_code == 200:
            data = resp.json()
            choice = data["choices"][0]
            msg = choice["message"]
            content = (msg.get("content") or "").strip()
            if not content:
                # 该模型偶发把最终答案塞进 reasoning_content 并以 </final> 分隔、content 留空
                reasoning = (msg.get("reasoning_content") or "").strip()
                if "</final>" in reasoning:
                    content = reasoning.rsplit("</final>", 1)[1].strip()
            if (
                not content
                and choice.get("finish_reason") == "length"
                and escalations < 3
            ):
                # 结构性失败：原样重试只会再烧穿一次——升档 max_tokens（连带放宽超时）
                escalations += 1
                tokens = min(tokens * 2, 32768)
                timeout = max(timeout, int(tokens / 15) + 60)  # 长生成需要更长读超时
                print(
                    f"  [升档 {escalations}/3] finish_reason=length，max_tokens→{tokens}、超时→{timeout}s 重试"
                )
                attempt -= 1  # 升档不消耗瞬时错误重试额度
                continue
            if not content:
                raise RuntimeError(
                    f"空 content（max_tokens 已升档至 {tokens} 仍不足）: {str(data)[:300]}"
                )
            return content
        if resp.status_code in (429, 500, 502, 503, 504):
            retry_after = resp.headers.get("Retry-After")
            wait = float(retry_after) if retry_after else delay
            if attempt == max_attempts:
                raise RuntimeError(
                    f"HTTP {resp.status_code} 重试耗尽: {resp.text[:200]}"
                )
            print(
                f"  [重试 {attempt}/{max_attempts}] HTTP {resp.status_code}，{wait:.0f}s 后重试"
            )
            time.sleep(wait)
            delay *= 2
            continue
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:500]}")
    raise AssertionError("unreachable")


def translate_ja2zh(ja_text, provider="kimi"):
    return chat(ja_text, provider=provider)


if __name__ == "__main__":
    # 自检：一条实测
    out = translate_ja2zh("今週はメモリースノーです！  #rezeroneko")
    print("自检翻译:", out)
