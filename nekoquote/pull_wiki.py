"""wiki 月表现态回写本地源数据：lua_base 文件 + zh.json 译文字段。

月表条目两个来源都只在构建期读本地数据——lua_base 零变换重放、zh.json 经
merge_raw 重新生成（见 build.py）——因此 wiki 侧直接改月表（如 {{Seirei or Elf}}
复核消歧）不落回本地，下轮增量同步重建即回潮。wiki 侧改完后跑
`uv run python -m nekoquote.pull_wiki`。

zh.json 字段归属与 merge_raw 对称：条目 t → 回答推记录的 zh；条目 q → 提问推
记录（tweets.json 里该推 reply_to 指向的非长月推）的 qzh。
"""

import json
import re

import pywikibot
from pywikibot import pagegenerators

from . import DATA
from .build import STATUS_RE, fget, parse_table

MONTH_RE = re.compile(r"^NekoQuote/(\d{4}-\d{2})$")


def unescape(quote: str, raw: str) -> str:
    """build.esc 的逆操作：先保护 \\\\ 再解引号转义，最后还原。"""
    return (
        raw.replace("\\\\", "\x00").replace("\\" + quote, quote).replace("\x00", "\\")
    )


def main() -> None:
    site = pywikibot.Site("zh", "re0")  # 只读，无需登录
    zh_path = DATA / "zh.json"
    zh = json.loads(zh_path.read_text(encoding="utf-8"))
    tw = json.loads((DATA / "tweets.json").read_text(encoding="utf-8"))
    base = DATA / "lua_base"

    pages = {}
    for p in site.allpages(prefix="NekoQuote/", namespace=828):
        m = MONTH_RE.match(p.title(with_ns=False))
        if m:
            pages[m.group(1)] = p

    updated = n_base = 0
    preloaded = pagegenerators.PreloadingGenerator(pages.values())
    for month, p in zip(pages, preloaded, strict=True):
        # lua_base 月份整文件刷新（wiki 月表是唯一权威副本；对齐 emit 的尾换行约定）
        bf = base / f"{month}.lua"
        if bf.exists():
            text = p.text if p.text.endswith("\n") else p.text + "\n"
            if bf.read_text(encoding="utf-8") != text:
                bf.write_text(text, encoding="utf-8")
                n_base += 1
        for fields, _ in parse_table(p.text):
            m = STATUS_RE.search(fget(fields, "src") or "")
            if not m or m.group(1) not in zh:
                continue
            tid = m.group(1)
            # q 字段的宿主是提问推记录（与 build.merge_raw 的 qid 判据一致）
            qid = tw.get(tid, {}).get("reply_to")
            qid = (
                qid
                if qid in tw and tw[qid].get("author") != "nezumiironyanko"
                else None
            )
            targets = {"t": (zh[tid], "zh")}
            if qid:
                targets["q"] = (zh.setdefault(qid, {}), "qzh")
            for name, quote, raw in fields:
                rec_key = targets.get(name)
                if rec_key is None:
                    continue
                rec, key = rec_key
                v = unescape(quote, raw)
                if v and v != rec.get(key):
                    print(
                        f"  {month} {tid} {key}: {str(rec.get(key))[:60]!r}"
                        f" -> {v[:60]!r}"
                    )
                    rec[key] = v
                    updated += 1
    if updated:
        zh_path.write_text(json.dumps(zh, ensure_ascii=False), encoding="utf-8")
    print(f"lua_base 刷新 {n_base} 张，zh.json 回写 {updated} 处")


if __name__ == "__main__":
    main()
