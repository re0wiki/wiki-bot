"""LLM 翻译管线的机械部分：选页、备料、核验、打标记。

设计文档：docs/llm-translation.md。翻译本身由 agent 完成，不在本脚本内。

用法（仓库根目录）：
    uv run python src/tools/llm_translate.py refresh   # 重建选页队列（约 5 分钟，低频）
    uv run python src/tools/llm_translate.py prepare   # 取队首备料
    uv run python src/tools/llm_translate.py stamp <slug>  # 打印编辑应用的标准摘要与同步标记
    uv run python src/tools/llm_translate.py done <slug> [理由]  # 核验 wiki 编辑
    uv run python src/tools/llm_translate.py skip <slug> [理由]  # 无需内容编辑（打标记）

同步状态的唯一载体是条目源码末尾的 HTML 注释标记：
    <!-- LLM: revid <en_revid>; <ISO 时间> -->   （已同步到 en 该版本）
revid 为 - 表示无 en 源（zh 源码无 en 链接，或 en 页不存在）。
编辑（done）与跳过（skip/auto-skip）统一以标记落账——不怕本地状态丢失，格式变更
只是普通编辑。本脚本对 wiki 的写入只有一处：skip/auto-skip 的机械打标记。

运行期数据全部在 .cache/llm_translate/（gitignored，跨运行状态——非 scratch）。
"""

import argparse
import json
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / ".cache" / "llm_translate"
WORK = DATA / "work"
QUEUE = DATA / "queue.json"

ZH_API = "https://rezero.fandom.com/zh/api.php"
EN_API = "https://rezero.fandom.com/api.php"
BOT = "IchiSanNi"
CATEGORY = "Category:待修撰"
# 管线处理过的条目必挂的分类（人类校对后手动摘除；再次处理会重新挂上）
PROOFREAD_CAT = "Category:机翻待校对"
# 标记名不随模型变；翻译用的模型型号记录在编辑摘要（人类可读、可扫描归因），
# 换模型只改这里
SUMMARY_PREFIX = "LLM(K3): revid "

S = requests.Session()

# en 源码行首/行尾的机械剥离
# 单行模板须容忍嵌套花括号（如 {{To do|…（{{#invoke:interwiki|get_en}}）…}}），
# 用 [^{}]* 会把这类行漏判为非模板——页首剥离会静默丢弃它们
TEMPLATE_LINE = re.compile(r"^\{\{.*\}\}\s*$")
CATEGORY_LINE = re.compile(r"^\[\[Category:[^\]]*\]\]\s*$", re.IGNORECASE)
LANGLINK_LINE = re.compile(r"^\[\[[a-z][a-z-]*:[^\]]*\]\]\s*$")
# 重定向页源码行（#REDIRECT / #重定向 / #重新導向）——不入管线、不打标记
REDIRECT_LINE = re.compile(r"^\s*#(REDIRECT|重定向|重新導向)", re.IGNORECASE)
# 内链 / 模板提取（校验用）
WIKILINK = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")
TEMPLATE_NAME = re.compile(r"\{\{([^{}|]+)")
EN_LINK = re.compile(r"\[\[en:([^\]|]+)")
# 同步状态标记（条目源码末尾的 HTML 注释，唯一状态载体）：
# <!-- LLM: revid <N|->; <ISO 时间> -->（已同步到 en 版本 N；- 表示无 en 源）
# K3 为旧格式标记，仍识别，下次处理时原位换新
MARKER_RE = re.compile(r"<!--\s*(?:LLM|K3): revid (\d+|-); (\S+) -->")


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


def now_iso():
    return datetime.now(UTC).isoformat(timespec="seconds")


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


def scan_markers(titles):
    """批量抓 zh 源码解析同步标记 → {title: 标记时间}（20/批防响应过大）。"""
    out = {}
    for i in range(0, len(titles), 20):
        r = api(
            ZH_API,
            prop="revisions",
            titles="|".join(titles[i : i + 20]),
            rvprop="content",
            rvslots="main",
        )
        for p in r["query"]["pages"]:
            if "missing" in p:
                continue
            m = MARKER_RE.search(p["revisions"][0]["slots"]["main"]["content"])
            if m:
                out[p["title"]] = m.group(2)
    return out


def creation_ts(title):
    """创建时间（无人类编辑的 bot 搬运页的冷度）。"""
    r = api(
        ZH_API,
        prop="revisions",
        titles=title,
        rvdir="newer",
        rvlimit="1",
        rvprop="ids|timestamp|user",
    )
    rev = r["query"]["pages"][0]["revisions"][0]
    assert rev.get("user") == BOT, f"{title} 无人类编辑但创建者是 {rev.get('user')}"
    return rev["timestamp"]


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
        queue.append({"title": t, "cold": creation_ts(t)})
        if (i + 1) % 50 == 0:
            print(f"orphans: {i + 1}/{len(orphans)}")

    # 已打标页的标记时间参与冷度取 max：打标（编辑或 skip）意味着「截至该时间
    # zh 与 en 已确认同步」，视为热页排队尾，避免反复追踪 en 微小更新而挤占
    # 从未翻过的远古条目
    markers = scan_markers([q["title"] for q in queue])
    for q in queue:
        if q["title"] in markers:
            q["cold"] = max(q["cold"], markers[q["title"]])
    if markers:
        print(f"marked pages re-dated: {len(markers)}")

    queue.sort(key=lambda q: q["cold"])
    save_json(QUEUE, queue)
    print(
        f"queue saved: {len(queue)} pages, coldest {queue[0]['cold'][:10]} {queue[0]['title']}"
    )


# ---------------------------------------------------------------- prepare


def split_en_body(en_text):
    """剥离 en 页首模板行与页尾分类/语言链接/导航区，返回正文。"""
    lines = en_text.splitlines()
    while lines and (TEMPLATE_LINE.match(lines[0]) or not lines[0].strip()):
        lines.pop(0)
    while lines and (
        CATEGORY_LINE.match(lines[-1])
        or LANGLINK_LINE.match(lines[-1])
        or not lines[-1].strip()
    ):
        lines.pop()
    # 页尾导航区（==Navigation== + navbox 群）：navbox 全在 template-remove 清单，
    # zh 的系列导航由 Tab/* 承担，不带入
    while lines and (TEMPLATE_LINE.match(lines[-1]) or not lines[-1].strip()):
        lines.pop()
    if lines and re.fullmatch(r"==\s*Navigation\s*==", lines[-1], re.IGNORECASE):
        lines.pop()
        while lines and not lines[-1].strip():
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
    """en 内链目标 → zh 最终目标（zh 同名页跟随重定向）。返回 (mapping, unresolved)。

    # 锚点对 API 是非法标题字符（查询会静默落空），按裸标题查询，
    命中后把锚点接回最终目标。
    """
    targets = {
        m.group(1).strip()
        for m in WIKILINK.finditer(body)
        if not re.match(r"(?i)(Category|File|Image):", m.group(1))
        and not re.match(r"[a-z][a-z-]*:", m.group(1))
    }
    mapping, unresolved = {}, []
    bases = sorted({t.split("#", 1)[0] for t in targets})
    base_final = {}  # 裸标题 → zh 最终目标
    for i in range(0, len(bases), 50):
        batch = bases[i : i + 50]
        r = api(ZH_API, prop="info", titles="|".join(batch), redirects="1")
        pages = r["query"]["pages"]
        resolved = {p.get("title") for p in pages if "missing" not in p}
        # redirects=1 后 pages 里是最终目标标题；按规范化标题回挂到 en 目标
        norm = {n["to"]: n["from"] for n in r["query"].get("normalized", [])}
        reds = {rd["from"]: rd["to"] for rd in r["query"].get("redirects", [])}
        for b in batch:
            final = reds.get(norm.get(b, b), norm.get(b, b))
            if final in resolved:
                base_final[b] = final
    for t in sorted(targets):
        base, sep, anchor = t.partition("#")
        if base in base_final:
            mapping[t] = base_final[base] + (sep + anchor if sep else "")
        else:
            unresolved.append(t)
    return mapping, sorted(set(unresolved))


# ---------------------------------------------------------------- en→zh 机械转换
# 本地复刻 replace.py 的应用路径（re.compile + nocase + replaceExcept 例外），
# 让 fix 表规则与 jobs 模板名映射离线作用于 en 源码——LLM 只翻 prose，
# 结构转换不靠 LLM 注意力。划分标准见 AGENTS.md「新增自动化」节。

_UF = None  # user-fixes.py 模块（lazy）
_SITE = None  # zh site 对象（lazy，仅供 interwiki 例外正则取 family 语言列表）


def _uf():
    global _UF
    if _UF is None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "user_fixes", ROOT / "user-fixes.py"
        )
        assert spec and spec.loader
        _UF = importlib.util.module_from_spec(spec)
        _UF.__dict__["fixes"] = {}  # 正常由 pwb/pywikibot/fixes.py exec 时注入
        spec.loader.exec_module(_UF)
    return _UF


def _zh_site():
    global _SITE
    if _SITE is None:
        import pywikibot

        _SITE = pywikibot.Site("zh", "re0")  # 惰性构造，不触网
    return _SITE


def apply_fix(text, fix):
    """复刻 replace.py：regex/nocase 编译 + inside-tags 例外，逐条应用。"""
    from pywikibot import textlib

    exceptions = fix.get("exceptions", {}).get("inside-tags", [])
    flags = re.IGNORECASE if fix.get("nocase") else 0
    for old, new in fix["replacements"]:
        pattern = re.compile(old if fix.get("regex") else re.escape(old), flags)
        text = textlib.replaceExcept(text, pattern, new, exceptions, site=_zh_site())
    return text


def convert_template_names(text):
    """en 模板名 → zh 模板名（jobs.jobs._template_replacements 为唯一事实源）。"""
    if str(ROOT) not in sys.path:  # 脚本方式运行时 sys.path[0] 是 src/tools
        sys.path.insert(0, str(ROOT))
    from src.jobs.jobs import _template_replacements

    for old, new in _template_replacements:
        text = re.sub(rf"\{{\{{\s*{re.escape(old)}(?=\s*[|}}])", "{{" + new, text)
    return text


def convert_links(text, mapping):
    """en 内链目标 → zh 最终目标（resolve_links 的映射）；显示文字留给 agent 翻译。"""

    def repl(m):
        target, pipe = m.group(1).strip(), m.group(2)
        if target in mapping:
            return f"[[{mapping[target]}{pipe or '|' + target}]]"
        return m.group(0)

    return re.sub(r"\[\[([^\]|]+)(\|[^\]]*)?\]\]", repl, text)


CJK = re.compile(r"[一-鿿]")
# 合并时永不从 zh 现文带回的参数（fix:para 的删除对象，防复活）
MERGE_DROP = {"previous", "next"}


def find_infoboxes(text):
    """括号平衡提取全部 {{Infobox ...}} 块 → [(start, end, name)]。"""
    out = []
    for m in re.finditer(r"\{\{\s*(Infobox [^{}|]*?)\s*(?=[|}\n])", text):
        depth, i = 0, m.start()
        while i < len(text) - 1:
            two = text[i : i + 2]
            if two == "{{":
                depth += 1
                i += 2
            elif two == "}}":
                depth -= 1
                i += 2
                if depth == 0:
                    out.append((m.start(), i, m.group(1).strip()))
                    break
            else:
                i += 1
    return out


def parse_params(block):
    """信息框块 → (头行, [(参数名小写, 原始行列表)], 尾行)；值可多行（gallery 等）。"""
    lines = block.split("\n")
    params = []
    for line in lines[1:-1]:
        pm = re.match(r"^\|[ \t]*([A-Za-z_][\w -]*?)[ \t]*=", line)
        if pm:
            params.append((pm.group(1).lower(), [line]))
        elif params:
            params[-1][1].append(line)  # 续行（含空行）归前一参数
    return lines[0], params, lines[-1]


def param_value(lines):
    return "\n".join([lines[0].split("=", 1)[1], *lines[1:]]).strip()


def merge_infobox(conv_block, zh_block):
    """信息框字段级合并：en 转换骨架为基，zh 策展内容保留。

    - zh 同名参数值含中文（已策展）→ 保留 zh 行；英文残留/空值 → 用 en 转换值；
    - zh 独有参数行 → 块尾保留；
    - image 守卫：zh 有 image_a/n/g/c 分媒介图库时丢弃 en 的单 image 参数；
    - MERGE_DROP 与 character 的 name_ja_romaji 不参与合并（fix:para 删除对象）。
    """
    c_head, c_params, c_tail = parse_params(conv_block)
    _, z_params, _ = parse_params(zh_block)
    z_map = dict(z_params)
    is_character = "infobox character" in c_head.lower()
    z_image_split = any(
        z_map.get(n) and param_value(z_map[n])
        for n in ("image_a", "image_n", "image_g", "image_c")
    )

    def droppable(name):
        return name in MERGE_DROP or (is_character and name == "name_ja_romaji")

    out = []
    for name, lines in c_params:
        if droppable(name) or (name == "image" and z_image_split):
            continue
        z_lines = z_map.get(name)
        if z_lines and CJK.search(param_value(z_lines)):
            out.extend(z_lines)  # zh 已策展，保留
        else:
            out.extend(lines)
    c_names = {name for name, _ in c_params}
    for name, lines in z_params:
        if name not in c_names and not droppable(name):
            out.extend(lines)  # zh 独有字段（isbn_ko/painter/voice_zh_* 等）
    return "\n".join([c_head, *out, c_tail])


def merge_structure(conv, zh_text):
    """conv 骨架与 zh 现文的信息框字段级合并；zh 独有的信息框整块保留在骨架顶部。"""
    z_left = {name.lower(): (s, e) for s, e, name in find_infoboxes(zh_text)}
    for s, e, name in sorted(find_infoboxes(conv), reverse=True):
        z = z_left.pop(name.lower(), None)
        if z is not None:
            conv = conv[:s] + merge_infobox(conv[s:e], zh_text[z[0] : z[1]]) + conv[e:]
    if z_left:
        # en 无对应的信息框（zh 原创结构）整块前置保留
        conv = "\n".join(zh_text[s:e] for s, e in z_left.values()) + "\n" + conv
    return conv


def cosmetic(text, title):
    """cosmetic_changes 的本地复用：与循环任务同套件同语义（标题空格/列表空格/
    空段清理等），替代自造正则。toolkit 需 Page 对象（取 site/title/namespace，
    惰性构造不拉取内容）；title 须为真实页名（cleanUpLinks 的自链接判定用）。"""
    import pywikibot
    from pywikibot.cosmetic_changes import CANCEL, CosmeticChangesToolkit

    page = pywikibot.Page(_zh_site(), title)
    out = CosmeticChangesToolkit(page, ignore=CANCEL.METHOD).change(text)
    return out or text  # 无变化时返回 False


CONVERT_FIXES = ("para", "heading", "date", "misc", "anti-ve")


def convert_en_body(body, zh_text, mapping, title):
    """en 正文 → zh 半成品骨架：模板名/参数/标题/日期/格式归一 + 内链目标替换
    + 与 zh 现文的信息框字段级合并。译名归一不在此处——主循环的 fix:translation
    对最终成稿机械兜底。"""
    conv = convert_template_names(body)
    conv = cosmetic(conv, title)  # 标题空格归一由 cleanUpSectionHeaders 承担
    fixes = _uf().user_fixes
    for name in CONVERT_FIXES:
        conv = apply_fix(conv, fixes[name])
    conv = convert_links(conv, mapping)
    return merge_structure(conv, zh_text)


def add_marker(text, marker):
    """在正文末尾（语言链接块之前）放置同步标记；已有标记则原位替换。"""
    if MARKER_RE.search(text):
        return MARKER_RE.sub(marker, text)
    lines = text.splitlines()
    i = len(lines)
    while i > 0 and (LANGLINK_LINE.match(lines[i - 1]) or not lines[i - 1].strip()):
        i -= 1
    body = lines[:i]
    while body and not body[-1].strip():
        body.pop()
    tail = [line for line in lines[i:] if line.strip()]
    return "\n".join(body + [marker] + ([""] if tail else []) + tail) + "\n"


def stamp_page(title, revid, reason):
    """机械打同步标记（skip/auto-skip 的唯一 wiki 写入）。"""
    import pywikibot

    site = pywikibot.Site("zh", "re0")
    site.login()
    assert site.user() == BOT
    page = pywikibot.Page(site, title)
    text = page.text
    assert not REDIRECT_LINE.match(text), f"{title} 是重定向页，不打同步标记"
    page.text = add_marker(text, f"<!-- LLM: revid {revid}; {now_iso()} -->")
    # 标记改动读者不可见，但属低频单页编辑，与管线一致不带 bot flag
    page.save(
        summary=f"{SUMMARY_PREFIX}{revid} 同步标记：{reason}", bot=False, minor=False
    )


def real_colds(titles):
    """逐页计算实际冷度（每页最近一次非 IchiSanNi 编辑的时间），与 refresh 同规则。

    rvexcludeuser 由 API 侧精确排除 bot（连编多少次都不失真）；
    无人类编辑的搬运页取创建时间。
    （rvexcludeuser 仅限单页查询，故逐页请求——调用点本就每候选一次。）
    """
    out = {}
    for t in titles:
        r = api(
            ZH_API,
            prop="revisions",
            titles=t,
            rvprop="ids|timestamp|user",
            rvexcludeuser=BOT,
            rvlimit="1",
        )
        revs = r["query"]["pages"][0].get("revisions", [])
        out[t] = revs[0]["timestamp"] if revs else creation_ts(t)
    return out


def evaluate_candidate(item):
    """评估单个队列项：返回候选元组 / None（auto-skip/已同步）/ "drop"（剔出队列）。

    可能懒修复 item["cold"]。"""
    title = item["title"]
    zh_text, zh_revid, _ = get_page(ZH_API, title)
    if zh_text is None:
        return None
    if REDIRECT_LINE.match(zh_text):
        # 重定向页不是条目，不入管线——标记只落在正式条目页
        print(f"drop: {title}（重定向页，出队）")
        return "drop"
    marker = MARKER_RE.search(zh_text)
    mrev = marker.group(1) if marker else None
    m = EN_LINK.search(zh_text)
    en_title = m.group(1).strip() if m else None
    en_text = en_revid = None
    if en_title:
        en_text, en_revid, _ = get_page(EN_API, en_title)
    if en_text is None:
        # 无 en 源（zh 源码无 en 链接，或 en 页不存在）：revid 视为 -。
        # 复活统一走 revid 不一致——zh 原创页后来加了 en 链接、
        # 悬空链接的 en 页被创建，都是实际 revid 与标记的 - 不等
        if mrev == "-":
            return None
        reason = "en 页不存在" if en_title else "无 en 链接（zh 原创）"
        stamp_page(title, "-", reason)
        print(f"auto-skip: {title}（{reason}）")
        return None
    if marker is not None and mrev == str(en_revid):
        item["cold"] = max(item["cold"], marker.group(2))  # 懒修复：标记时间参与取 max
        return None  # 已同步且 en 未变化；revid 变化即自然落入处理（追更复活）
    body = split_en_body(en_text)
    if not any(
        len(line) > 20 and not line.startswith("=") for line in body.splitlines()
    ):
        stamp_page(title, en_revid, "en 无实质内容（仅标题骨架）")
        print(f"auto-skip: {title}（en 仅标题骨架）")
        return None
    item["cold"] = real_colds([title])[title] or item["cold"]
    return (item["cold"], title, zh_text, zh_revid, en_title, en_revid, body)


def write_work_files(best):
    """把队首候选的备料写进 work 目录（en 正文 / zh 现文 / conv 骨架 / meta），并打印摘要。"""
    cold, title, zh_text, zh_revid, en_title, en_revid, body = best
    mapping, unresolved = resolve_links(body)
    conv = convert_en_body(body, zh_text, mapping, title)
    head, zh_body, tail = split_zh_frame(zh_text)

    slug = slugify(title)
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / f"{slug}.body.en.txt").write_text(body, encoding="utf-8")
    (WORK / f"{slug}.zh.txt").write_text(zh_text, encoding="utf-8")
    (WORK / f"{slug}.conv.txt").write_text(conv, encoding="utf-8")
    save_json(
        WORK / f"{slug}.meta.json",
        {
            "title": title,
            "en_title": en_title,
            "en_revid": en_revid,
            "zh_revid": zh_revid,
            "cold": cold,
            "head": head,
            "tail": tail,
            "zh_body_len": len(zh_body),
            "link_map": mapping,
            "unresolved_links": unresolved,
        },
    )
    print(f"prepared: {title} (cold {cold[:10]}, en revid {en_revid})")
    print(
        f"  conv skeleton: {len(conv)} chars（en body {len(body)} chars, "
        f"links: {len(mapping)} resolved, {len(unresolved)} unresolved）"
    )
    print(
        f"  agent 以 {WORK / f'{slug}.conv.txt'} 为基础翻译 prose；zh 策展字段已机械保留"
    )


def cmd_prepare():
    queue = load_json(QUEUE, None)
    if queue is None:
        sys.exit("queue.json 不存在，先跑 refresh")
    wip = sorted(WORK.glob("*.meta.json"))
    if wip:
        sys.exit(
            f"已有待处理工作项: {[p.stem.rsplit('.', 2)[0] for p in wip]}，先处理再 prepare"
        )

    # walk：跳过已打标页；对未处理候选取实际冷度，陈旧冷度单调偏低（时间只往前走），
    # 故扫到「下一条陈旧冷度 ≥ 当前最优实际冷度」即可确定真队首；算出的实际冷度
    # 写回 queue.json 懒修复排序（每周全量 refresh 仍保留，处理分类新增等）
    best = None  # (real_cold, title, zh_text, zh_revid, en_title, en_revid, body)
    queue_dirty = False
    dropped = []
    i = 0
    while i < len(queue):
        item = queue[i]
        if best and item["cold"] >= best[0]:
            break
        i += 1
        old_cold = item["cold"]
        cand = evaluate_candidate(item)
        if cand == "drop":
            dropped.append(item["title"])
            queue_dirty = True
            continue
        queue_dirty |= item["cold"] != old_cold
        if cand and (best is None or cand[0] < best[0]):
            best = cand

    if dropped:
        queue = [q for q in queue if q["title"] not in dropped]
    if queue_dirty:
        queue.sort(key=lambda q: q["cold"])
        save_json(QUEUE, queue)
    if best is None:
        print("队列已空")
        return
    write_work_files(best)


# ---------------------------------------------------------------- done


def cold_dur(meta):
    """冷度时长字符串（摘要用，向其他编辑者说明自动处理该页的原因）。"""
    days = (datetime.now(UTC) - datetime.fromisoformat(meta["cold"])).days
    return f"{days / 365:.1f}年" if days >= 365 else f"{max(days // 30, 1)}个月"


def std_summary(meta):
    """标准编辑摘要（纯人类可读信息；机器校验只看源码里的同步标记）。"""
    return f"{SUMMARY_PREFIX}{meta['en_revid']}（{cold_dur(meta)}无人类编辑）"


def cat_pages(cat):
    """分类的 pages 数（categoryinfo 一次查询；分类不存在时 0）。"""
    r = api(ZH_API, prop="categoryinfo", titles=cat)
    return r["query"]["pages"][0].get("categoryinfo", {}).get("pages", 0)


def notify_line(meta):
    todo, proof = cat_pages(CATEGORY), cat_pages(PROOFREAD_CAT)
    total = api(ZH_API, meta="siteinfo", siprop="statistics")["query"]["statistics"][
        "articles"
    ]
    stats = (
        f"待修撰 {todo} 条（占全站条目 {todo / max(total, 1) * 100:.1f}%）；"
        f"机翻待校对 {proof} 条（占待修撰 {proof / max(todo, 1) * 100:.1f}%）"
    )
    return (
        f"NOTIFY: [[{meta['title']}]] {cold_dur(meta)}无人类编辑，"
        f"已由 Bot 根据 [[en:{meta['en_title']}]] 自动更新。{stats}"
    )


def clean_work(slug):
    for f in WORK.glob(f"{slug}.*"):
        f.unlink()


def extract_templates(text):
    return {m.group(1).strip() for m in TEMPLATE_NAME.finditer(text)}


# 参数含这些子串的 To do 标注属翻译类（重翻/校对任务标注、K3 标注），
# 管线处理即完成、机翻标记由 Category:机翻待校对 承载 → 清理
TODO_FULFILLED = ("本页翻译结果不准确", "AI翻译", "由 K3 翻译自英文站，待校对润色")


def strip_todo(line):
    """页首 To do 清理：机翻标记由分类承载后，参数中的翻译类标注一律移除。

    按「；」分段丢弃翻译类标注段；清空则还原裸模板；
    其他参数（人工标注的无关任务）原样保留。
    """
    m = re.fullmatch(r"\{\{\s*To do\s*\|(.+)\}\}", line.strip())
    if not m:
        return line
    kept = [
        seg
        for seg in m.group(1).split("；")
        if not any(k in seg for k in TODO_FULFILLED)
    ]
    if kept == [m.group(1)]:
        return line
    if not kept:
        return "{{To do}}"
    return "{{To do|" + "；".join(kept) + "}}"


def cmd_done(slug):
    """一页处理完成：机械核验 agent 的 wiki 编辑。

    核验（均以 prepare 时的 zh 现文与 conv 骨架为基线）：
    - 最新编辑是本账号，源码含且仅含一个同步标记且 revid 与 meta 一致；
    - 页首模板块除 To do 翻译类标注清理外逐行不变；
    - 正文内链目标（按 页面/文件/分类/语言链接 分类）与模板调用
      不超出 link_map ∪ 未解析名 ∪ conv 骨架 ∪ zh 现文的白名单；
    - 正文末尾挂了 [[Category:机翻待校对]]（人类校对后手动摘除）。
    状态由源码标记承载，通过即输出 NOTIFY 行，无本地落盘。
    """
    meta = load_json(WORK / f"{slug}.meta.json", None)
    if meta is None:
        sys.exit(f"找不到 {slug}.meta.json，先跑 prepare")
    r = api(
        ZH_API,
        prop="revisions",
        titles=meta["title"],
        rvprop="ids|comment|user|timestamp|content",
        rvslots="main",
        rvlimit="1",
    )
    rev = r["query"]["pages"][0]["revisions"][0]
    if rev["revid"] == meta["zh_revid"]:
        sys.exit("zh 页自 prepare 以来无新编辑——先完成编辑再 done")
    if rev.get("user") != BOT:
        sys.exit(f"最新编辑非本账号（{rev.get('user')}）——人工编辑冲突，中止")
    want = str(meta["en_revid"])
    markers = MARKER_RE.findall(rev["slots"]["main"]["content"])
    if len(markers) != 1 or markers[0][0] != want:
        sys.exit(
            f"同步标记缺失或不匹配（期望 <!-- LLM: revid {want}; ... -->，"
            f"实际 {[f'revid {m[0]}' for m in markers]!r}）——"
            "把 stamp 子命令输出的标记行加入正文末尾再保存"
        )
    new_text = MARKER_RE.sub("", rev["slots"]["main"]["content"])

    zh_old = (WORK / f"{slug}.zh.txt").read_text(encoding="utf-8")
    conv = (WORK / f"{slug}.conv.txt").read_text(encoding="utf-8")
    old_head, old_body, _ = split_zh_frame(zh_old)
    new_head, new_body, _ = split_zh_frame(new_text)
    if new_head != [strip_todo(line) for line in old_head]:
        sys.exit("页首模板块被改动（唯一允许的改动是按规则清理 To do 的翻译类标注）")

    def link_targets(text):
        return {m.group(1).strip() for m in WIKILINK.finditer(text)}

    def classify(t):
        if re.match(r"(?i)Category:", t):
            return "cat"
        if re.match(r"(?i)(File|Image):", t):
            return "file"
        if re.match(r"[a-z][a-z-]*:", t):
            return "lang"
        return "page"

    old_links, conv_links = link_targets(old_body), link_targets(conv)
    allowed = {
        "cat": {t for t in old_links if classify(t) == "cat"} | {PROOFREAD_CAT},
        "file": {t for t in old_links | conv_links if classify(t) == "file"},
        "lang": {t for t in old_links if classify(t) == "lang"},
        "page": (
            {t for t in old_links if classify(t) == "page"}
            | set(meta["link_map"].values())
            | set(meta["unresolved_links"])
        ),
    }
    new_links = link_targets(new_body)
    bad = sorted(t for t in new_links if t not in allowed[classify(t)])
    if bad:
        sys.exit("内链校验失败: " + ", ".join(bad))
    if PROOFREAD_CAT not in {t for t in new_links if classify(t) == "cat"}:
        sys.exit(f"缺 [[{PROOFREAD_CAT}]]（管线处理过的条目必挂，加在正文末尾）")
    tpl_ok = extract_templates(conv) | extract_templates(old_body)
    tpl_bad = extract_templates(new_body) - tpl_ok
    if tpl_bad:
        sys.exit(f"模板校验失败: 新增 {sorted(tpl_bad)}")

    clean_work(slug)
    print(f"done: {meta['title']}（en revid {meta['en_revid']}）")
    print(notify_line(meta))


def cmd_stamp(slug):
    """打印编辑应使用的标准摘要（人类可读）与同步标记（正文末尾，done 核验后者）。"""
    meta = load_json(WORK / f"{slug}.meta.json", None)
    if meta is None:
        sys.exit(f"找不到 {slug}.meta.json，先跑 prepare")
    print(std_summary(meta))
    print(f"<!-- LLM: revid {meta['en_revid']}; {now_iso()} -->")


def cmd_skip(slug, reason):
    """无需内容编辑（en 无增量等）：机械打上同步标记（revid = prepare 时的 en 版本）。

    与 done 统一以源码标记落账——skip 同样确认了「截至此时 zh 与 en 同步」。
    """
    meta = load_json(WORK / f"{slug}.meta.json", None)
    if meta is None:
        sys.exit(f"找不到 {slug}.meta.json")
    stamp_page(meta["title"], meta["en_revid"], reason)
    clean_work(slug)
    print(f"skipped: {meta['title']}（{reason}，en revid {meta['en_revid']}）")


def cmd_status():
    queue = load_json(QUEUE, [])
    wip = sorted(p.stem.rsplit(".", 2)[0] for p in WORK.glob("*.meta.json"))
    print(f"queue: {len(queue)}, wip: {wip}（同步状态见各页源码标记）")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "cmd",
        choices=["refresh", "prepare", "stamp", "done", "skip", "status"],
    )
    ap.add_argument("slug", nargs="?")
    ap.add_argument("reason", nargs="?")
    args = ap.parse_args()
    if args.cmd == "refresh":
        cmd_refresh()
    elif args.cmd == "prepare":
        cmd_prepare()
    elif args.cmd == "status":
        cmd_status()
    else:
        if not args.slug:
            ap.error(f"{args.cmd} 需要 slug 参数")
        if args.cmd == "stamp":
            cmd_stamp(args.slug)
        elif args.cmd == "done":
            cmd_done(args.slug)
        else:
            cmd_skip(args.slug, args.reason or "en 无增量")
