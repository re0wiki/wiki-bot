"""LLM 翻译管线的机械部分：选页、备料、校验、发布。

设计文档：docs/llm-translation.md。翻译本身由 agent 完成，不在本脚本内。

用法（仓库根目录）：
    PYTHONPATH= .venv/Scripts/python.exe scripts/tools/llm_translate.py refresh   # 重建选页队列（约 3 分钟，低频）
    PYTHONPATH= .venv/Scripts/python.exe scripts/tools/llm_translate.py prepare   # 取队首备料
    PYTHONPATH= .venv/Scripts/python.exe scripts/tools/llm_translate.py publish <slug>  # 校验并写入
    PYTHONPATH= .venv/Scripts/python.exe scripts/tools/llm_translate.py skip <slug> [理由]  # agent 判断不宜翻译

运行期数据全部在 logs/llm_translate/（gitignored）。
"""

import argparse
import json
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "logs" / "llm_translate"
WORK = DATA / "work"
QUEUE = DATA / "queue.json"
STATE = DATA / "state.json"

ZH_API = "https://rezero.fandom.com/zh/api.php"
EN_API = "https://rezero.fandom.com/api.php"
BOT = "IchiSanNi"
CATEGORY = "Category:待修撰"
TODO_MARKED = "{{To do|由 K3 翻译自英文站，待校对润色}}"
SUMMARY_PREFIX = "K3翻译: revid "

S = requests.Session()

# en 源码行首/行尾的机械剥离
# 单行模板须容忍嵌套花括号（如 {{To do|…（{{#invoke:interwiki|get_en}}）…}}），
# 用 [^{}]* 会把这类行漏判为非模板——页首剥离会静默丢弃它们
TEMPLATE_LINE = re.compile(r"^\{\{.*\}\}\s*$")
CATEGORY_LINE = re.compile(r"^\[\[Category:[^\]]*\]\]\s*$", re.IGNORECASE)
LANGLINK_LINE = re.compile(r"^\[\[[a-z][a-z-]*:[^\]]*\]\]\s*$")
# 内链 / 模板提取（校验用）
WIKILINK = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")
TEMPLATE_NAME = re.compile(r"\{\{([^{}|]+)")
EN_LINK = re.compile(r"\[\[en:([^\]|]+)")
SUMMARY_REVID = re.compile(r"K3翻译: revid (\d+)")


def api(base, **params):
    params.update({"action": "query", "format": "json", "formatversion": "2"})
    for attempt in range(3):
        try:
            r = S.get(base, params=params, timeout=60).json()
            if "error" in r:
                raise RuntimeError(r["error"].get("info", r["error"]))
            time.sleep(0.2)  # Cloudflare 礼貌间隔
            return r
        except Exception as e:
            if attempt == 2:
                raise
            print(f"retry ({e})", file=sys.stderr)
            time.sleep(2)
    raise AssertionError


def get_page(base, title):
    """返回 (content, revid, timestamp)；页面不存在返回 (None, None, None)。"""
    r = api(
        base,
        prop="revisions",
        titles=title,
        rvprop="ids|timestamp|content",
        rvslots="main",
    )
    p = r["query"]["pages"][0]
    if "missing" in p:
        return None, None, None
    rev = p["revisions"][0]
    return rev["slots"]["main"]["content"], rev["revid"], rev["timestamp"]


def slugify(title):
    return re.sub(r"[^\w-]+", "_", title).strip("_")


def load_json(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


# ---------------------------------------------------------------- refresh


def category_members():
    members, cont = [], {}
    while True:
        r = api(
            ZH_API,
            list="categorymembers",
            cmtitle=CATEGORY,
            cmnamespace="0",
            cmlimit="500",
            **cont,
        )
        members += [m["title"] for m in r["query"]["categorymembers"]]
        if "continue" not in r:
            return members
        cont = r["continue"]


def cmd_refresh():
    members = category_members()
    print(f"members: {len(members)}")

    # 全站主空间人类修订流：每页最近一次非 bot 编辑
    latest, cont, n = {}, {}, 0
    while True:
        r = api(
            ZH_API,
            list="allrevisions",
            arvnamespace="0",
            arvexcludeuser=BOT,
            arvprop="ids|timestamp",
            arvlimit="500",
            **cont,
        )
        for p in r["query"]["allrevisions"]:
            for rv in p.get("revisions", []):
                n += 1
                if p["title"] in members and p["title"] not in latest:
                    latest[p["title"]] = rv["timestamp"]
        if "continue" not in r:
            break
        cont = r["continue"]
    print(f"human revs scanned: {n}, pages with human edit: {len(latest)}")

    # 无人类编辑记录 = bot 搬运页，取创建时间
    queue = []
    for t in members:
        if t in latest:
            queue.append({"title": t, "cold": latest[t]})
    orphans = [t for t in members if t not in latest]
    for i, t in enumerate(orphans):
        r = api(
            ZH_API,
            prop="revisions",
            titles=t,
            rvdir="newer",
            rvlimit="1",
            rvprop="ids|timestamp|user",
        )
        rev = r["query"]["pages"][0]["revisions"][0]
        assert rev.get("user") == BOT, f"{t} 无人类编辑但创建者是 {rev.get('user')}"
        queue.append({"title": t, "cold": rev["timestamp"]})
        if (i + 1) % 50 == 0:
            print(f"orphans: {i + 1}/{len(orphans)}")

    # 已翻译页按翻译时间计冷度：翻译即同步了 en 最新人工改动，视为热页，
    # 避免反复追踪 en 微小更新而挤占从未翻过的远古条目
    state = load_json(STATE, {"skip": {}})
    translated_at = {
        t: e["translated_at"]
        for t, e in state["skip"].items()
        if isinstance(e, dict) and e.get("translated_at")
    }
    for q in queue:
        if q["title"] in translated_at:
            q["cold"] = translated_at[q["title"]]
    if translated_at:
        print(f"translated pages re-dated: {len(translated_at)}")

    queue.sort(key=lambda q: q["cold"])
    save_json(QUEUE, queue)
    print(
        f"queue saved: {len(queue)} pages, coldest {queue[0]['cold'][:10]} {queue[0]['title']}"
    )


# ---------------------------------------------------------------- prepare


def split_en_body(en_text):
    """剥离 en 页首模板行与页尾分类/语言链接，返回正文。"""
    lines = en_text.splitlines()
    while lines and (TEMPLATE_LINE.match(lines[0]) or not lines[0].strip()):
        lines.pop(0)
    while lines and (
        CATEGORY_LINE.match(lines[-1])
        or LANGLINK_LINE.match(lines[-1])
        or not lines[-1].strip()
    ):
        lines.pop()
    return "\n".join(lines).strip() + "\n"


def split_zh_frame(zh_text):
    """拆 zh 现文为 (页首模板块, 正文, 页尾语言链接块)。"""
    lines = zh_text.splitlines()
    head, i = [], 0
    while i < len(lines) and (TEMPLATE_LINE.match(lines[i]) or not lines[i].strip()):
        if TEMPLATE_LINE.match(lines[i]):
            head.append(lines[i])
        i += 1
    tail = []
    j = len(lines)
    while j > i and (LANGLINK_LINE.match(lines[j - 1]) or not lines[j - 1].strip()):
        if LANGLINK_LINE.match(lines[j - 1]):
            tail.insert(0, lines[j - 1])
        j -= 1
    return head, "\n".join(lines[i:j]).strip(), tail


def resolve_links(body):
    """en 内链目标 → zh 最终目标（zh 同名页跟随重定向）。返回 (mapping, unresolved)。"""
    targets = {
        m.group(1).strip()
        for m in WIKILINK.finditer(body)
        if not re.match(r"(?i)(Category|File|Image):", m.group(1))
        and not re.match(r"[a-z][a-z-]*:", m.group(1))
    }
    mapping, unresolved = {}, []
    targets = sorted(targets)
    for i in range(0, len(targets), 50):
        batch = targets[i : i + 50]
        r = api(ZH_API, prop="info", titles="|".join(batch), redirects="1")
        pages = r["query"]["pages"]
        resolved = {p.get("title") for p in pages if "missing" not in p}
        for p in pages:
            if "missing" in p:
                unresolved.append(p["title"])
        # redirects=1 后 pages 里是最终目标标题；按规范化标题回挂到 en 目标
        norm = {n["to"]: n["from"] for n in r["query"].get("normalized", [])}
        reds = {rd["from"]: rd["to"] for rd in r["query"].get("redirects", [])}
        for t in batch:
            t_norm = norm.get(t, t)
            final = reds.get(t_norm, t_norm)
            if final in resolved:
                mapping[t] = final
            elif t not in unresolved and t_norm in [u for u in unresolved]:
                unresolved.append(t)
    return mapping, sorted(set(unresolved))


def translated_rev(zh_title):
    """从 zh 历史摘要解析上次翻译对应的 (en revid, 翻译时间)（state 丢失时的恢复手段）。"""
    r = api(
        ZH_API,
        prop="revisions",
        titles=zh_title,
        rvprop="ids|comment|user|timestamp",
        rvlimit="50",
    )
    for rev in r["query"]["pages"][0].get("revisions", []):
        m = SUMMARY_REVID.search(rev.get("comment", ""))
        if m:
            return int(m.group(1)), rev["timestamp"]
    return None, None


def en_revids(titles):
    """批量取 en 页最新 revid（50/批，默认 rvlimit=1）。页面不存在时值为 None。"""
    out = {}
    titles = sorted(titles)
    for i in range(0, len(titles), 50):
        r = api(
            EN_API, prop="revisions", titles="|".join(titles[i : i + 50]), rvprop="ids"
        )
        for p in r["query"]["pages"]:
            out[p["title"]] = None if "missing" in p else p["revisions"][0]["revid"]
    return out


def revalidate_skips(state):
    """en 相关跳过项（dict 形态）批量复查 en revid，变化则复活。返回复活页数。"""
    entries = {t: e for t, e in state["skip"].items() if isinstance(e, dict)}
    if not entries:
        return 0
    current = en_revids([e["en_title"] for e in entries.values()])
    revived = 0
    for title, e in list(entries.items()):
        revid = current.get(e["en_title"])
        if revid is not None and revid != e["en_revid"]:
            del state["skip"][title]
            revived += 1
    return revived


def cmd_prepare():
    queue = load_json(QUEUE, None)
    if queue is None:
        sys.exit("queue.json 不存在，先跑 refresh")
    state = load_json(STATE, {"skip": {}})
    revived = revalidate_skips(state)
    if revived:
        print(f"en 更新复活: {revived} 页")
    wip = sorted(WORK.glob("*.meta.json"))
    if wip:
        sys.exit(
            f"已有待处理工作项: {[p.stem.rsplit('.', 2)[0] for p in wip]}，先翻译/发布/skip 再 prepare"
        )

    for item in queue:
        title = item["title"]
        entry = state["skip"].get(title)
        if isinstance(entry, str):  # 永久跳过（zh 原创等）
            continue
        if entry:  # en 相关跳过，revid 未变（变了已在上面复活）
            continue
        zh_text, zh_revid, _ = get_page(ZH_API, title)
        if zh_text is None:
            state["skip"][title] = "zh 页不存在"
            continue
        m = EN_LINK.search(zh_text)
        if not m:
            state["skip"][title] = "无 en 链接（zh 原创）"
            continue
        en_title = m.group(1).strip()
        en_text, en_revid, _ = get_page(EN_API, en_title)
        if en_text is None:
            state["skip"][title] = {
                "reason": "en 页不存在",
                "en_title": en_title,
                "en_revid": None,
            }
            continue
        tr_revid, tr_ts = translated_rev(title)
        if tr_revid == en_revid:
            state["skip"][title] = {
                "reason": "已翻译，en 未变化",
                "en_title": en_title,
                "en_revid": en_revid,
                "translated_at": tr_ts,
            }
            continue

        body = split_en_body(en_text)
        if not any(
            len(line) > 20 and not line.startswith("=") for line in body.splitlines()
        ):
            state["skip"][title] = {
                "reason": "en 无实质内容（仅标题骨架）",
                "en_title": en_title,
                "en_revid": en_revid,
            }
            print(f"auto-skip: {title}（en 仅标题骨架）")
            continue
        mapping, unresolved = resolve_links(body)
        head, zh_body, tail = split_zh_frame(zh_text)
        zh_flags = [
            name
            for name, pat in [("infobox", r"\{\{Infobox"), ("gallery", r"<gallery")]
            if re.search(pat, zh_body)
        ]

        slug = slugify(title)
        WORK.mkdir(parents=True, exist_ok=True)
        (WORK / f"{slug}.body.en.txt").write_text(body, encoding="utf-8")
        (WORK / f"{slug}.zh.txt").write_text(zh_text, encoding="utf-8")
        save_json(
            WORK / f"{slug}.meta.json",
            {
                "title": title,
                "en_title": en_title,
                "en_revid": en_revid,
                "zh_revid": zh_revid,
                "cold": item["cold"],
                "head": head,
                "tail": tail,
                "zh_body_len": len(zh_body),
                "zh_flags": zh_flags,
                "link_map": mapping,
                "unresolved_links": unresolved,
            },
        )
        save_json(STATE, state)
        print(f"prepared: {title} (cold {item['cold'][:10]}, en revid {en_revid})")
        print(
            f"  en body: {len(body)} chars, links: {len(mapping)} resolved, {len(unresolved)} unresolved"
        )
        print(
            f"  zh body replaced: {len(zh_body)} chars（人工内容请先过目 {WORK / f'{slug}.zh.txt'}）"
        )
        if zh_flags:
            print(f"  ⚠ zh 现文含 {zh_flags}——考虑只局部修补 prose 而非整页替换")
        return
    save_json(STATE, state)
    print("队列已空")


# ---------------------------------------------------------------- publish


def extract_templates(text):
    return {m.group(1).strip() for m in TEMPLATE_NAME.finditer(text)}


# 参数含这些子串的 To do 标注，其任务本身就是「重翻/校对翻译」，K3 翻译即完成 → 替换而非合并
TODO_FULFILLED = ("本页翻译结果不准确", "AI翻译")


def mark_todo(line):
    """页首 To do 注入 K3 标注。

    裸模板 → 替换为 K3 标注；参数是翻译任务类旧标注 → 替换（任务已完成）；
    其他参数 → 合并保留原说明；已含 K3 标注 → 不动（幂等）。
    """
    s = line.strip()
    if re.fullmatch(r"\{\{\s*To do\s*\}\}", s):
        return TODO_MARKED
    m = re.fullmatch(r"\{\{\s*To do\s*\|(.+)\}\}", s)
    if not m or "K3 翻译" in m.group(1):
        return line
    if any(k in m.group(1) for k in TODO_FULFILLED):
        return TODO_MARKED
    return "{{To do|" + m.group(1) + "；由 K3 翻译自英文站，待校对润色}}"


def cmd_publish(slug):
    meta = load_json(WORK / f"{slug}.meta.json", None)
    if meta is None:
        sys.exit(f"找不到 {slug}.meta.json，先跑 prepare")
    out_path = WORK / f"{slug}.body.zh.txt"
    if not out_path.exists():
        sys.exit(f"找不到译文 {out_path}")
    out = out_path.read_text(encoding="utf-8").strip() + "\n"
    en_body = (WORK / f"{slug}.body.en.txt").read_text(encoding="utf-8")

    # 护栏 1：结构不变量
    allowed_links = set(meta["link_map"].values()) | set(meta["unresolved_links"])
    allowed_links |= {
        m.group(1).strip()
        for m in WIKILINK.finditer(en_body)
        if re.match(r"(?i)(File|Image):", m.group(1))
    }
    bad_links = []
    for m in WIKILINK.finditer(out):
        t = m.group(1).strip()
        if re.match(r"(?i)Category:", t):
            bad_links.append(f"{t}（分类不应出现在正文）")
        elif re.match(r"(?i)(File|Image):", t):
            if t not in allowed_links:
                bad_links.append(t)
        elif re.match(r"[a-z][a-z-]*:", t):
            bad_links.append(f"{t}（语言链接不应出现在正文）")
        elif t not in allowed_links:
            bad_links.append(t)
    if bad_links:
        sys.exit("内链校验失败: " + ", ".join(bad_links))
    tpl_en, tpl_out = extract_templates(en_body), extract_templates(out)
    if tpl_en != tpl_out:
        sys.exit(f"模板校验失败: en={sorted(tpl_en)} out={sorted(tpl_out)}")

    # 护栏 2：人编冲突（prepare 之后 zh 页被任何人动过）
    _, zh_revid, _ = get_page(ZH_API, meta["title"])
    if zh_revid != meta["zh_revid"]:
        sys.exit(
            f"zh 页在 prepare 后有新编辑（{meta['zh_revid']} -> {zh_revid}），中止"
        )

    # 拼装：页首（To do 注入 K3 标注）+ 译文 + 页尾语言链接
    head = [mark_todo(line) for line in meta["head"]]
    parts = ["\n".join(head), "", out]
    if meta["tail"]:
        parts += ["\n".join(meta["tail"])]
    new_text = "\n".join(parts).rstrip() + "\n"

    # 摘要附冷度，向其他编辑者说明自动翻译的原因
    days = (datetime.now(UTC) - datetime.fromisoformat(meta["cold"])).days
    dur = f"{days / 365:.1f}年" if days >= 365 else f"{max(days // 30, 1)}个月"
    summary = f"{SUMMARY_PREFIX}{meta['en_revid']}（{dur}无人类编辑）"

    import pywikibot

    site = pywikibot.Site("zh", "re0")
    site.login()
    assert site.user() == BOT
    page = pywikibot.Page(site, meta["title"])
    page.text = new_text
    # 翻译不是需抑制通知的批量编辑，不加 bot flag
    page.save(summary=summary, bot=False, minor=False)
    print(f"saved: {meta['title']} (en:{meta['en_title']} revid {meta['en_revid']})")
    url = f"https://rezero.fandom.com/zh/wiki/{quote(meta['title'], safe='/:')}"
    print(
        f"NOTIFY: [[{meta['title']}]] {dur}无人类编辑，"
        f"已由 Bot 根据 [[en:{meta['en_title']}]] 自动更新 {url}"
    )
    state = load_json(STATE, {"skip": {}})
    state["skip"][meta["title"]] = {
        "reason": "已翻译，en 未变化",
        "en_title": meta["en_title"],
        "en_revid": meta["en_revid"],
        "translated_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    save_json(STATE, state)
    for f in WORK.glob(f"{slug}.*"):
        f.unlink()


def cmd_skip(slug, reason):
    """agent 判断不宜翻译时调用：按当前 en revid 记入跳过，en 更新后自动复活。"""
    meta = load_json(WORK / f"{slug}.meta.json", None)
    if meta is None:
        sys.exit(f"找不到 {slug}.meta.json")
    state = load_json(STATE, {"skip": {}})
    state["skip"][meta["title"]] = {
        "reason": reason,
        "en_title": meta["en_title"],
        "en_revid": meta["en_revid"],
    }
    save_json(STATE, state)
    for f in WORK.glob(f"{slug}.*"):
        f.unlink()
    print(f"skipped: {meta['title']}（{reason}，en revid {meta['en_revid']}）")


def cmd_status():
    queue = load_json(QUEUE, [])
    state = load_json(STATE, {"skip": {}})
    wip = sorted(p.stem.rsplit(".", 2)[0] for p in WORK.glob("*.meta.json"))
    perm = sum(1 for e in state["skip"].values() if isinstance(e, str))
    temp = sum(1 for e in state["skip"].values() if isinstance(e, dict))
    print(f"queue: {len(queue)}, skip: {perm} 永久 + {temp} en 跟踪, wip: {wip}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=["refresh", "prepare", "publish", "skip", "status"])
    ap.add_argument("slug", nargs="?")
    ap.add_argument("reason", nargs="?", default="en 无实质内容")
    args = ap.parse_args()
    if args.cmd == "refresh":
        cmd_refresh()
    elif args.cmd == "prepare":
        cmd_prepare()
    elif args.cmd == "publish":
        if not args.slug:
            ap.error("publish 需要 slug 参数")
        cmd_publish(args.slug)
    elif args.cmd == "skip":
        if not args.slug:
            ap.error("skip 需要 slug 参数")
        cmd_skip(args.slug, args.reason)
    else:
        cmd_status()
