"""wiki 月表现态回写本地源数据：lua_base 文件 + zh.json 译文字段 + tweets.json 原文字段。

月表条目两个来源都只在构建期读本地数据——lua_base 零变换重放、zh.json/tweets.json
经 merge_raw 重新生成（见 build.py）——因此 wiki 侧直接改月表（如 {{Seirei or Elf}}
复核消歧，fix:translation 也会命中月表 jt 字段里的「妖精」等词）不落回本地，
下轮增量同步重建即回潮。wiki 侧改完后跑 `uv run python -m nekoquote.pull_wiki`。

字段归属与 merge_raw 对称（仅对 lua_base 之外的月份逐字段回写；lua_base 月份
由整文件刷新覆盖——其条目是 P8 时代管线生成的，加工逻辑与 raw_tweet_entry 不同，
逐字段比对必然误报）：
- t → zh.json 回答推记录的 zh；q → zh.json 提问推记录的 qzh
  （提问推 = tweets.json 里该推 reply_to 指向的非长月推）；
- jt → tweets.json 该推的 text；jq → tweets.json 提问推的 text
  （比较前先做与 build 相同的加工再比对，回写的是加工后文本——重放幂等）。
"""

import json
import re

import pywikibot
from pywikibot import pagegenerators

from . import DATA
from .build import STATUS_RE, fget, parse_table, strip_tco

MONTH_RE = re.compile(r"^NekoQuote/(\d{4}-\d{2})$")
MENTION_RE = re.compile(r"^(@\w+\s*)+")
BR_RE = re.compile(r"\s*\r?\n\s*")


def unescape(quote: str, raw: str) -> str:
    """build.esc 的逆操作：先保护 \\\\ 再解引号转义，最后还原。"""
    return (
        raw.replace("\\\\", "\x00").replace("\\" + quote, quote).replace("\x00", "\\")
    )


def proc_jt(text: str) -> str:
    """build.raw_tweet_entry 的 jt 生成变换。"""
    return BR_RE.sub("<br/>", strip_tco(text.strip()))


def proc_jq(text: str) -> str:
    """build.merge_raw 的 jq 生成变换。"""
    return strip_tco(BR_RE.sub("<br/>", MENTION_RE.sub("", text).strip()))


def main() -> None:
    site = pywikibot.Site("zh", "re0")  # 只读，无需登录
    zh_path = DATA / "zh.json"
    tw_path = DATA / "tweets.json"
    zh = json.loads(zh_path.read_text(encoding="utf-8"))
    tw = json.loads(tw_path.read_text(encoding="utf-8"))
    base = DATA / "lua_base"

    pages = {}
    for p in site.allpages(prefix="NekoQuote/", namespace=828):
        m = MONTH_RE.match(p.title(with_ns=False))
        if m:
            pages[m.group(1)] = p

    n_zh = n_tw = n_base = 0
    preloaded = pagegenerators.PreloadingGenerator(pages.values())
    for month, p in zip(pages, preloaded, strict=True):
        # lua_base 月份整文件刷新（wiki 月表是唯一权威副本；对齐 emit 的尾换行约定），
        # 其条目由 lua_base 零变换重放，不做逐字段回写（见 docstring）
        bf = base / f"{month}.lua"
        if bf.exists():
            text = p.text if p.text.endswith("\n") else p.text + "\n"
            if bf.read_text(encoding="utf-8") != text:
                bf.write_text(text, encoding="utf-8")
                n_base += 1
            continue
        for fields, _ in parse_table(p.text):
            m = STATUS_RE.search(fget(fields, "src") or "")
            if not m or m.group(1) not in tw:
                continue
            tid = m.group(1)
            # q/jq 字段的宿主是提问推记录（与 build.merge_raw 的 qid 判据一致）
            qid = tw[tid].get("reply_to")
            qid = (
                qid
                if qid in tw and tw[qid].get("author") != "nezumiironyanko"
                else None
            )
            # 字段名 → (目标 dict, key, 由现 text 重建的期望值)；期望值=None 表示纯 wiki 侧字段
            targets = {"jt": (tw[tid], "text", proc_jt(tw[tid]["text"]))}
            if tid in zh:
                targets["t"] = (zh[tid], "zh", None)
            if qid:
                targets["q"] = (zh.setdefault(qid, {}), "qzh", None)
                targets["jq"] = (tw[qid], "text", proc_jq(tw[qid]["text"]))
            for name, quote, raw in fields:
                hit = targets.get(name)
                if hit is None:
                    continue
                rec, key, expected = hit
                v = unescape(quote, raw)
                cur = rec.get(key) if expected is None else expected
                if v and v != cur:
                    print(f"  {month} {tid} {name}: {str(cur)[:60]!r} -> {v[:60]!r}")
                    rec[key] = v
                    if expected is None:
                        n_zh += 1
                    else:
                        n_tw += 1
    if n_zh:
        zh_path.write_text(json.dumps(zh, ensure_ascii=False), encoding="utf-8")
    if n_tw:
        tw_path.write_text(json.dumps(tw, ensure_ascii=False), encoding="utf-8")
    print(
        f"lua_base 刷新 {n_base} 张，zh.json 回写 {n_zh} 处，tweets.json 回写 {n_tw} 处"
    )


if __name__ == "__main__":
    main()
