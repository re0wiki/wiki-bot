"""wiki 月表现态回写本地源数据：lua_base 文件 + zh.json 译文字段 + tweets.json 原文字段。

月表条目两个来源都只在构建期读本地数据——lua_base 零变换重放、zh.json/tweets.json
经 merge_raw 重新生成（见 build.py）——因此 wiki 侧直接改月表（如 {{Seirei or Elf}}
复核消歧，fix:translation 也会命中月表 jt 字段里的「妖精」等词）不落回本地，
下轮增量同步重建即回潮。wiki 侧改完后跑 `uv run python -m src.nekoquote.pull_wiki`。

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
import shutil
import sys

import pywikibot
from pywikibot import pagegenerators

from . import DATA, build
from .build import STATUS_RE, fget, parse_table, strip_tco
from .state import state_lock, write_json

MONTH_RE = re.compile(r"^NekoQuote/(\d{4}-\d{2})$")
MENTION_RE = re.compile(r"^(@\w+\s*)+")
BR_RE = re.compile(r"\s*\r?\n\s*")


def unescape(quote: str, raw: str) -> str:
    """build.esc 的逆操作：先保护 \\ 再解引号转义，最后还原。"""
    return (
        raw.replace("\\\\", "\x00").replace("\\" + quote, quote).replace("\x00", "\\")
    )


def proc_jt(text: str) -> str:
    """build.raw_tweet_entry 的 jt 生成变换。"""
    return BR_RE.sub("<br/>", strip_tco(text.strip()))


def proc_jq(text: str) -> str:
    """build.merge_raw 的 jq 生成变换。"""
    return strip_tco(BR_RE.sub("<br/>", MENTION_RE.sub("", text).strip()))


def collect_pages(site) -> dict:
    """wiki 上全部 NekoQuote/YYYY-MM 月表页 {月份: Page}。"""
    pages = {}
    for p in site.allpages(prefix="NekoQuote/", namespace=828):
        m = MONTH_RE.match(p.title(with_ns=False))
        if m:
            pages[m.group(1)] = p
    return pages


def refresh_base(month: str, text: str, base) -> bool | None:
    """lua_base 月份整文件刷新（wiki 月表是唯一权威副本；对齐 emit 的尾换行约定）。

    其条目由 lua_base 零变换重放，不做逐字段回写（见模块 docstring）。
    返回 None=非 lua_base 月份，True=有刷新，False=无变化。
    """
    bf = base / f"{month}.lua"
    if not bf.exists():
        return None
    if not text.endswith("\n"):
        text += "\n"
    if bf.read_text(encoding="utf-8") == text:
        return False
    bf.write_text(text, encoding="utf-8")
    return True


def question_id(tid: str, tw: dict) -> str | None:
    """回答推对应的非长月提问推 id。"""
    qid = tw[tid].get("reply_to")
    return qid if qid in tw and tw[qid].get("author") != "nezumiironyanko" else None


def add_translation_target(targets, created, zh, tid, field, key, present):
    """登记一个 t/q 回写目标；wiki 有该字段时允许新建本地记录。"""
    if tid not in zh and field not in present:
        return
    if tid not in zh:
        zh[tid] = {}
        created.add(tid)
    targets[field] = (zh[tid], key, None)


def build_targets(tid, qid, present, zh, tw):
    """构造字段名 → (目标 dict, key, 由现 text 重建的期望值)。"""
    targets = {"jt": (tw[tid], "text", proc_jt(tw[tid].get("text", "")))}
    created = set()
    add_translation_target(targets, created, zh, tid, "t", "zh", present)
    if qid:
        add_translation_target(targets, created, zh, qid, "q", "qzh", present)
        targets["jq"] = (tw[qid], "text", proc_jq(tw[qid].get("text", "")))
    return targets, created


def absent_value_skipped(name, rec, key, deleted_key, present, value) -> bool:
    """字段缺失且本地无值时跳过；显式空值与已抑制记录另行处理。"""
    return (
        not value
        and key not in rec
        and (name not in present or (deleted_key and rec.get(deleted_key)))
    )


def unchanged_value(rec, expected, deleted_key, cur, value) -> bool:
    """值未变化且没有待解除的删除标记。"""
    return (
        value == cur
        and (value or expected is not None)
        and (deleted_key is None or not rec.get(deleted_key))
    )


def field_changed(month, tid, name, target, present) -> bool:
    """回写一个字段；返回值表示是否发生实质变化。"""
    rec, key, expected = target
    cur = rec.get(key) if expected is None else expected
    deleted_key = f"{key}_deleted" if expected is None else None
    if name in present:
        quote, raw = present[name]
        value = unescape(quote, raw)
    else:
        value = ""
    if absent_value_skipped(name, rec, key, deleted_key, present, value):
        return False
    if unchanged_value(rec, expected, deleted_key, cur, value):
        return False
    print(f"  {month} {tid} {name}: {str(cur)[:60]!r} -> {value[:60]!r}")
    if value:
        rec[key] = value
        if deleted_key:
            rec.pop(deleted_key, None)
    else:
        rec.pop(key, None)
        if deleted_key:
            # 与「从未翻译」区分：人工删除后不得由下一轮 translate 再生。
            rec[deleted_key] = True
    return True


def writeback_entry(month: str, fields: list, zh: dict, tw: dict) -> tuple[int, int]:
    """单条目字段回写（非 lua_base 月份）。返回 (zh.json 改动数, tweets.json 改动数)。"""
    m = STATUS_RE.search(fget(fields, "src") or "")
    if not m or m.group(1) not in tw:
        return 0, 0
    tid = m.group(1)
    present = {name: (quote, raw) for name, quote, raw in fields}
    targets, created = build_targets(tid, question_id(tid, tw), present, zh, tw)
    n_zh = n_tw = 0
    for name, target in targets.items():
        if not field_changed(month, tid, name, target, present):
            continue
        if target[2] is None:
            n_zh += 1
        else:
            n_tw += 1
    for created_tid in created:
        if not zh[created_tid]:
            del zh[created_tid]
    return n_zh, n_tw


def load_base_ids() -> set[str]:
    """lua_base 已覆盖的推 id。"""
    ids = set()
    for f in (DATA / "lua_base").glob("*.lua"):
        for fields, _ in parse_table(f.read_text(encoding="utf-8")):
            if m := STATUS_RE.search(fget(fields, "src") or ""):
                ids.add(m.group(1))
    return ids


def writeback_pages(pages, zh, tw):
    """逐月回写，返回线上文本、线上 raw id 与三类改动计数。"""
    online_pages = {}
    wiki_raw_ids = set()
    n_zh = n_tw = n_base = 0
    preloaded = pagegenerators.PreloadingGenerator(pages.values())
    for month, page in zip(pages, preloaded, strict=True):
        online = page.text if page.text.endswith("\n") else page.text + "\n"
        online_pages[month] = online
        refreshed = refresh_base(month, online, DATA / "lua_base")
        if refreshed is not None:
            n_base += refreshed
            continue
        for fields, _ in parse_table(page.text):
            if m := STATUS_RE.search(fget(fields, "src") or ""):
                wiki_raw_ids.add(m.group(1))
            changed_zh, changed_tw = writeback_entry(month, fields, zh, tw)
            n_zh += changed_zh
            n_tw += changed_tw
    return online_pages, wiki_raw_ids, n_zh, n_tw, n_base


def replay_diff(online_pages):
    """完整重建并返回 (线上不匹配月份, 本地独有月份)；清理失败返回 None。"""
    outdir = DATA / "lua"
    try:
        if outdir.exists():
            shutil.rmtree(outdir)
    except OSError as e:
        print(f"构建输出清理失败；未更新 lua_live: {e}")
        return None
    build.main()
    generated_months = {f.stem for f in outdir.glob("*.lua")}
    mismatched = [
        month
        for month, online in online_pages.items()
        if not (outdir / f"{month}.lua").exists()
        or (outdir / f"{month}.lua").read_text(encoding="utf-8") != online
    ]
    return mismatched, generated_months - online_pages.keys()


def refresh_live(online_pages) -> int:
    """重放保真后推进部署快照，返回更新月表数。"""
    live_dir = DATA / "lua_live"
    live_dir.mkdir(parents=True, exist_ok=True)
    n_live = 0
    for month, online in online_pages.items():
        live = live_dir / f"{month}.lua"
        if not live.exists() or live.read_text(encoding="utf-8") != online:
            live.write_text(online, encoding="utf-8")
            n_live += 1
    return n_live


def _main() -> int:
    site = pywikibot.Site("zh", "re0")  # 只读，无需登录
    zh_path = DATA / "zh.json"
    tw_path = DATA / "tweets.json"
    zh = json.loads(zh_path.read_text(encoding="utf-8"))
    tw = json.loads(tw_path.read_text(encoding="utf-8"))

    pages = collect_pages(site)
    online_pages, wiki_raw_ids, n_zh, n_tw, n_base = writeback_pages(pages, zh, tw)
    local_raw_ids = {
        tid for tid, rec in tw.items() if rec.get("author") == "nezumiironyanko"
    } - load_base_ids()
    missing = local_raw_ids - wiki_raw_ids
    if missing:
        print(
            f"wiki 月表缺少 {len(missing)} 条本地 raw 条目；未回写，先人工核对: "
            + ", ".join(sorted(missing)[:10])
        )
        return 1
    if n_zh:
        write_json(zh_path, zh)
    if n_tw:
        write_json(tw_path, tw)

    # 只有线上能由回写后的本地源完整重放，才可把它提升为部署基线。
    diff = replay_diff(online_pages)
    if diff is None:
        return 1
    mismatched, local_only = diff
    if mismatched or local_only:
        print(
            "本地源无法完整重放线上月表；未更新 lua_live: "
            + ", ".join(sorted(mismatched))
        )
        if local_only:
            print("本地生成但线上缺失的月表: " + ", ".join(sorted(local_only)))
        return 1

    n_live = refresh_live(online_pages)
    print(
        f"lua_base 刷新 {n_base} 张，lua_live 刷新 {n_live} 张，"
        f"zh.json 回写 {n_zh} 处，tweets.json 回写 {n_tw} 处"
    )
    return 0


def main() -> int:
    with state_lock(DATA):
        return _main()


if __name__ == "__main__":
    sys.exit(main())
