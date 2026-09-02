"""中文翻译：raw 推 ja→zh（Kimi K3，批量断点续跑）。
产物 zh.json：{tid: {"zh": 推文译文, "qzh": 提问推译文(如有)}}。无 key 时跳过（退出 0）。
"""

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))
from src.nekoquote import DATA
from src.nekoquote.llm import SYSTEM_PROMPT, chat

try:
    from src.nekoquote.llm import get_config

    get_config("kimi")
except FileNotFoundError as e:
    print(f"跳过翻译：{e}（新推将以日文上线，配置 key 后下轮自动补译）")
    raise SystemExit(0)

STATUS_RE = re.compile(r"status/(\d+)")
EPOCH = 1288834974657


def snowflake_month(tid):
    from datetime import datetime, timedelta, timezone

    ts = (int(tid) >> 22) + EPOCH
    return datetime.fromtimestamp(ts / 1000, tz=timezone(timedelta(hours=9))).strftime(
        "%Y-%m"
    )


# 既有 id 集合（与构建器同逻辑：lua_base src 里的链接）
existing_ids = set()
for f in sorted((DATA / "lua_base").glob("*.lua")):
    existing_ids.update(STATUS_RE.findall(f.read_text(encoding="utf-8")))

tw = json.loads((DATA / "tweets.json").read_text(encoding="utf-8"))
merged = {}
for tid, rec in tw.items():
    if rec.get("author") != "nezumiironyanko" or tid in existing_ids:
        continue
    mo = snowflake_month(tid)
    if not ("2010-01" <= mo <= "2026-12"):
        continue
    merged[tid] = rec
print(f"合流 raw 推 {len(merged)} 条")

# 待译：推文正文（非空）+ 提问推正文
done = (
    json.loads((DATA / "zh.json").read_text(encoding="utf-8"))
    if (DATA / "zh.json").exists()
    else {}
)
texts = {}  # 归一文本 -> None（去重池）
tid2text = {}
for tid, rec in merged.items():
    t = re.sub(r"\s*https?://(?:t\.co|a\.co)/\S+", "", rec["text"]).strip()
    t = re.sub(r"\s*\r?\n\s*", " ", t)
    if t:
        tid2text[tid] = t
        texts.setdefault(t)
qids = {}
for tid, rec in merged.items():
    qid = rec.get("reply_to")
    if qid and qid in tw and tw[qid].get("author") != "nezumiironyanko":
        qt = re.sub(r"^(@\w+\s*)+", "", tw[qid]["text"]).strip()
        qt = re.sub(r"\s*https?://(?:t\.co|a\.co)/\S+", "", qt)
        qt = re.sub(r"\s*\r?\n\s*", " ", qt)
        if qt:
            qids[qid] = qt

# 已有译文命中
text_zh = {}
for tid, r in done.items():
    if tid in tid2text and r.get("zh"):
        text_zh[tid2text[tid]] = r["zh"]
    if r.get("qzh") and tid in qids:
        pass
todo_texts = [t for t in texts if t not in text_zh]
todo_qs = {q: t for q, t in qids.items() if not done.get(q, {}).get("qzh")}
print(
    f"待译正文 {len(todo_texts)}（唯一文本 {len(texts)}，已有 {len(text_zh)}）；待译提问 {len(todo_qs)}"
)

BATCH = 50
BLOCKED = []


def run_batch(items, prompt_prefix):
    """items: [(key, text)]；返回 {key: zh}。缺漏重试后仍缺则报错；content_filter 二分隔离。"""
    lines = [f"{i}\t{t}" for i, (_, t) in enumerate(items)]
    prompt = (
        prompt_prefix
        + "\n\n每行输出「编号<TAB>译文」，不要输出其他内容：\n\n"
        + "\n".join(lines)
    )
    res = {}
    for attempt in range(6):
        try:
            out = chat(
                prompt,
                system=SYSTEM_PROMPT,
                max_tokens=32768,
                timeout=1800,
                provider="kimi",
            )
        except Exception as e:  # noqa: BLE001 content_filter 靠消息文本判定
            if "content_filter" in str(e):
                # 内容过滤：二分定位触线文本，单条隔离
                if len(items) == 1:
                    print(f"  !! 触线跳过: {items[0][1][:60]}", flush=True)
                    BLOCKED.append(items[0])
                    return {}
                half = len(items) // 2
                print(
                    f"  触线二分（{len(items)}→{half}+{len(items) - half}）", flush=True
                )
                return {
                    **run_batch(items[:half], prompt_prefix),
                    **run_batch(items[half:], prompt_prefix),
                }
            print(f"  批次异常 {e}，退避重试", flush=True)
            time.sleep(20 * (attempt + 1))
            continue
        for line in out.splitlines():
            m = re.match(r"^(\d+)\t(.+)$", line.strip())
            if m and int(m.group(1)) < len(items):
                res[int(m.group(1))] = m.group(2).strip()
        if len(res) == len(items):
            break
        print(f"  缺漏 {len(res)}/{len(items)}，重试", flush=True)
        time.sleep(10)
    if len(res) != len(items):
        missing = [items[i] for i in range(len(items)) if i not in res]
        if len(missing) <= 3:
            # 少量缺漏：逐条补
            for it in missing:
                res2 = run_batch([it], prompt_prefix)
                if res2:
                    res[items.index(it)] = res2[it[0]]
        if len(res) != len(items):
            raise SystemExit(f"批次持续缺漏 {len(res)}/{len(items)}")
    return {items[i][0]: v for i, v in res.items()}


PROMPT_T = "把以下作者推文逐条翻译成简体中文（编号与推文一一对应，推内换行已折叠为空格，译文保持单条一段）。"
PROMPT_Q = "把以下粉丝提问推文逐条翻译成简体中文（@前缀已剥除）。"

t0 = time.time()
batches = [todo_texts[i : i + BATCH] for i in range(0, len(todo_texts), BATCH)]
for bi, b in enumerate(batches):
    got = run_batch([(t, t) for t in b], PROMPT_T)
    text_zh.update(got)
    if bi % 5 == 4 or bi == len(batches) - 1:
        # 断点：把已知正文译文落到 tid 维度
        for tid, t in tid2text.items():
            if t in text_zh:
                done.setdefault(tid, {})["zh"] = text_zh[t]
        (DATA / "zh.json").write_text(
            json.dumps(done, ensure_ascii=False), encoding="utf-8"
        )
        print(
            f"正文 {bi + 1}/{len(batches)} 批，{(time.time() - t0) / 60:.1f}min",
            flush=True,
        )

qbatches = [list(todo_qs.items())[i : i + BATCH] for i in range(0, len(todo_qs), BATCH)]
for bi, b in enumerate(qbatches):
    got = run_batch(b, PROMPT_Q)
    for qid, zh in got.items():
        done.setdefault(qid, {})["qzh"] = zh
    (DATA / "zh.json").write_text(
        json.dumps(done, ensure_ascii=False), encoding="utf-8"
    )
    print(f"提问 {bi + 1}/{len(qbatches)} 批", flush=True)

for tid, t in tid2text.items():
    if t in text_zh:
        done.setdefault(tid, {})["zh"] = text_zh[t]
(DATA / "zh.json").write_text(json.dumps(done, ensure_ascii=False), encoding="utf-8")
(DATA / "zh_blocked.json").write_text(
    json.dumps(BLOCKED, ensure_ascii=False, indent=1), encoding="utf-8"
)
print(
    f"完成：{len(done)} 条记录，触线跳过 {len(BLOCKED)} 条，{(time.time() - t0) / 60:.1f}min"
)
