"""系列导航 Tab 同步：新搬运页挂 Tab、Tab 模板补条目。

机械规则（不满足即转报告页 User:IchiSanNi/tab_sync，不猜）：
- 挂载：页面无 Tab 时，en prev/next 链上有 Tab 且 en 标题系列键（掩末位
  数字段）一致的 zh 邻居参与表决，集合全票一致才挂（空集 = 邻居也未整理，不参与表决），
  且候选模板链接集须含至少一个邻居页（同源校验）；插入页首 Init/To do 行块后。
- 补条目：锚定 en 链相邻页（即检查发起页自身）在模板中的条目行，next 插其后、
  previous 插其前。要求：zh_page 与 en 目标系列键一致（排除跨季/跨章边界）、
  目标与锚同词干同词尾（拆分篇词尾归一后比较，目标本身不得是拆分篇）、序号
  方向与链一致、锚行全模板唯一、所在块无注释、块内有同词干数字显示条目佐证
  显示文本可推导。候选模板 = 本页所挂 Tab ∪ 两跳父页的 Tab，唯一命中才执行。

审计逻辑复用 src/tools/series_nav_audit.py；规则与背景见
.agents/skills/series-nav-sync/SKILL.md。子页（如 小说:短篇集第14卷/梗概）
的 prev/next 由审计层从 en 主页面派生（目标加相同子页后缀），本脚本
无需特判——邻居即邻居子页，挂载/补条目规则同主页面。
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

import pywikibot as pwb
from pywikibot import config

# pwb 运行时 sys.path 只有 pwb/ 与脚本目录，仓库根需手动插入（re0_nekoquote 同款）
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.tools.series_nav_audit import (
    batch_query,
    check_splits,
    classify_checks,
    collect_checks,
    load_tab_links,
    norm,
    scan_zh,
)

SUMMARY = "机器人：同步系列导航 Tab"
REPORT_PAGE = "User:IchiSanNi/tab_sync"
REPORT_SUMMARY = "机器人：更新系列导航同步报告"
# 编辑轮上限：链式收敛（挂 46 卷后 47 卷才有邻居可抄）需多轮，末轮只审不写
MAX_ROUNDS = 3

RE_INIT = re.compile(r"^\{\{Init(\|[^\n}]*)?\}\}[ \t]*$")
RE_TODO = re.compile(r"^\{\{To do(\|[^\n}]*)?\}\}[ \t]*$")
RE_TAB_CALL = re.compile(r"\{\{\s*Tab/")
RE_LINK = re.compile(r"\[\[([^\]|#]+)")
RE_SERIAL = re.compile(r"^(.*\D)(\d+)(\D*)$")
# 条目行：|[[链接|显示]]（显示可缺省）
RE_ENTRY_LINE = re.compile(r"^\|\[\[(?P<link>[^\]|]+)(\|(?P<disp>[^\]|]*))?\]\][ \t]*$")
# 数字显示条目：|[[词干N词尾|N]]——相等用反向引用结构性保证
# （否则 漫画:第4章第14卷 会在 第4章 的 4 上错配）
RE_NUM_ENTRY = re.compile(
    r"^\|\[\[(?P<stem>[^\]|]*?)(?P<num>\d+)(?P<tail>[^\]|]*?)\|(?P=num)\]\][ \t]*$"
)
RE_TAB_OPEN = re.compile(r"^\s*\{\{\s*Tab\b")
RE_TAB_CLOSE = re.compile(r"^\s*\}\}")

# classify_checks 的未覆盖原因文案（同源文件内的字面量，改动需同步）
REASON_NO_TAB = "页面无 Tab"
REASON_NOT_IN_TAB = "目标不在 Tab 链接集（含两跳）"

# 拆分篇词尾（归一比较用；与 series_nav_audit.RE_SPLIT 同族）
_SPLIT_SUFFIXES = (
    "（前篇）",
    "前篇",
    "（中篇）",
    "中篇",
    "（后篇）",
    "（後篇）",
    "后篇",
    "後篇",
)


def _series_key(title: str) -> str:
    """系列键：仅掩末位数字段（条目序号），保留季/章号——跨季/跨章边界即不同键。

    全数字段掩码（骨架）会把 Season 2/3 抹成同形，丢失边界信息。
    """
    return re.sub(r"\d+(\D*)$", r"#\1", title)


def _parse_serial(title: str) -> tuple[str, int, str] | None:
    """标题拆 (词干, 序号, 词尾)：序号取最后一个数字段；无数字返回 None。"""
    m = RE_SERIAL.match(title)
    if not m:
        return None
    return m.group(1), int(m.group(2)), m.group(3)


def _base_tail(tail: str) -> str:
    """词尾去拆分篇后缀（话前篇 → 话）。"""
    for s in _SPLIT_SUFFIXES:
        if tail.endswith(s):
            return tail[: -len(s)]
    return tail


def insert_tabs(source: str, tabs: list[str]) -> str | None:
    """页首 Init/To do 行块后插入 {{Tab/X}} 行；页首形态不认识返回 None。

    To do 与信息框粘连（{{To do}}{{#… 同一行）时不是独立行，锚到 Init 后。
    """
    lines = source.splitlines(keepends=True)
    if not lines or not RE_INIT.match(lines[0].rstrip("\r\n")):
        return None
    pos = 1
    if pos < len(lines) and RE_TODO.match(lines[pos].rstrip("\r\n")):
        pos += 1
    block = "".join(f"{{{{Tab/{t}}}}}\n" for t in tabs)
    return "".join(lines[:pos]) + block + "".join(lines[pos:])


def _virtual_lines(source: str) -> tuple[list[str], list[tuple[int, int]]]:
    """把 `}}{{Tab` 粘连行拆成两条虚拟行，返回 (虚拟行, [(原行号, 行内列偏移)])。

    实测模板两种排版并存（}}{{Tab 粘连与 }} 换行 {{Tab），拆分后块解析统一；
    映射回原行使插入 diff 最小（不拆原行时整行插入，拆行时行内拼接）。
    """
    vlines: list[str] = []
    vmap: list[tuple[int, int]] = []
    for idx, line in enumerate(source.splitlines(keepends=True)):
        pos = line.find("}}{{Tab")
        if pos == -1:
            vlines.append(line)
            vmap.append((idx, 0))
        else:
            cut = pos + 2
            vlines.append(line[:cut] + "\n")
            vmap.append((idx, 0))
            vlines.append(line[cut:])
            vmap.append((idx, cut))
    return vlines, vmap


def _check_serials(
    anchor: str, target: str, direction: str
) -> tuple[str, int, str] | None:
    """序号校验，通过返回 (锚词干, 目标序号, 目标词尾)。

    目标须与锚同系列（词干相同、词尾归一后相同）且自身非拆分篇；
    序号方向须与链一致（防 en 链回环/乱序误插）。
    """
    pa, pt = _parse_serial(anchor), _parse_serial(target)
    if not pa or not pt:
        return None
    astem, anum, atail = pa
    tstem, tnum, ttail = pt
    if tstem != astem or ttail != _base_tail(atail) or ttail != _base_tail(ttail):
        return None
    if direction == "next" and tnum <= anum or direction == "previous" and tnum >= anum:
        return None
    return astem, tnum, ttail


def _locate_block(vlines: list[str], anchor: str) -> tuple[int, int, int] | None:
    """唯一锚行所在 {{Tab}} 块，返回 (锚行号, 块首行号, 块尾行号)。

    锚不唯一、不在块内、块未闭合、块含注释均返回 None。
    """
    anchors = [
        i
        for i, line in enumerate(vlines)
        if (m := RE_ENTRY_LINE.match(line.rstrip("\r\n"))) and m["link"] == anchor
    ]
    if len(anchors) != 1:
        return None
    a = anchors[0]
    lo = a
    while lo > 0 and not RE_TAB_OPEN.match(vlines[lo]):
        lo -= 1
    if not RE_TAB_OPEN.match(vlines[lo]):
        return None  # 锚不在任何 {{Tab}} 块内
    hi = a
    while hi < len(vlines) and not RE_TAB_CLOSE.match(vlines[hi]):
        hi += 1
    if hi >= len(vlines):
        return None  # 块未闭合，模板形态异常
    if any("<!--" in line for line in vlines[lo : hi + 1]):
        return None  # 含注释块放弃机械处理
    return a, lo, hi


def _has_num_proof(vlines: list[str], lo: int, hi: int, stem: str, tail: str) -> bool:
    """数字显示约定佐证：块内有同词干同词尾（归一）的数字显示条目，
    显示文本才可推导为序号（反例：OVA1|OVA1 类显示文本非序号）。
    """
    for k in range(lo + 1, hi):
        nm = RE_NUM_ENTRY.match(vlines[k].rstrip("\r\n"))
        if nm and nm["stem"] == stem and _base_tail(nm["tail"]) == tail:
            return True
    return False


def _insert_line(
    source: str, vmap: list[tuple[int, int]], pos: int, new_line: str
) -> str:
    """新行插到虚拟行位置 pos（经 vmap 映射回原行，粘连行做行内拼接）。"""
    lines = source.splitlines(keepends=True)
    orig_idx, col = vmap[pos] if pos < len(vmap) else (len(lines), 0)
    if col == 0:
        lines.insert(orig_idx, new_line)
    else:  # 粘连行内拼接：}}<新行>{{Tab
        line = lines[orig_idx]
        lines[orig_idx] = line[:col] + "\n" + new_line + line[col:]
    return "".join(lines)


def insert_entry(source: str, anchor: str, target: str, direction: str) -> str | None:
    """锚定插入 target 条目到模板源码；无法唯一机械定位返回 None。

    规则见模块 docstring「补条目」条。direction 为 en 链方向（next/previous）。
    """
    serials = _check_serials(anchor, target, direction)
    if serials is None:
        return None
    astem, tnum, ttail = serials
    vlines, vmap = _virtual_lines(source)
    block = _locate_block(vlines, anchor)
    if block is None:
        return None
    a, lo, hi = block
    if not _has_num_proof(vlines, lo, hi, astem, ttail):
        return None
    pos = a + 1 if direction == "next" else a
    return _insert_line(source, vmap, pos, f"|[[{target}|{tnum}]]\n")


def mount_candidates(
    zh_page: str, checks: list[dict], pages: dict, tab_links: dict
) -> tuple[list[str] | None, str | None]:
    """挂载候选：同系列键邻居 Tab 全票一致且链接集含邻居页，返回 (tab 列表, 原因)。"""
    own_skel = _series_key(pages[zh_page]["en"])
    tabsets = {}
    for c in checks:
        t = c["zh_target"]
        if t is None or not pages.get(t, {}).get("tabs"):
            continue
        if _series_key(pages[t]["en"]) != own_skel:
            continue  # 跨季/跨章边界的邻居不投票
        tabsets[t] = frozenset(pages[t]["tabs"])
    if not tabsets:
        return None, "en 链上无同系列键的有 Tab zh 邻居"
    distinct = set(tabsets.values())
    if len(distinct) > 1:
        detail = "；".join(f"{t} 挂 {'、'.join(sorted(s))}" for t, s in tabsets.items())
        return None, f"邻居 Tab 不一致（{detail}）"
    tabs = sorted(next(iter(distinct)))
    linkset = set().union(*(tab_links.get(t, set()) for t in tabs))
    if not any(t in linkset for t in tabsets):
        return None, f"候选模板 {'、'.join(tabs)} 的链接集不含任何邻居页"
    return tabs, None


def append_candidates(zh_page: str, pages: dict, tab_links: dict) -> list[str]:
    """补条目候选模板：本页所挂 Tab ∪ 两跳父页（本页 Tab 链接的带 Tab 页）所挂 Tab。"""
    cands = set(pages[zh_page]["tabs"])
    direct = set().union(*(tab_links.get(t, set()) for t in cands))
    for link in direct:
        info = pages.get(link)
        if info:
            cands |= info["tabs"]
    return sorted(cands)


def pick_template(
    srcs: dict[str, str], anchor: str, target: str, direction: str
) -> tuple[str | None, str | None]:
    """候选模板逐个试插，唯一命中返回 (模板名, None)，否则 (None, 原因)。"""
    hits = [
        t
        for t, src in srcs.items()
        if insert_entry(src, anchor, target, direction) is not None
    ]
    if len(hits) == 1:
        return hits[0], None
    if not hits:
        return None, "候选模板无唯一锚定位"
    return None, f"多个模板可插入: {'、'.join(hits)}"


def do_mount(zh, title: str, tabs: list[str], write: bool) -> str | None:
    """给页面挂 Tab。返回 None = 成功/干跑，否则失败原因。"""
    page = pwb.Page(zh, title)
    src = page.text  # 新鲜读取：扫描快照可能已被本轮写入改变
    if RE_TAB_CALL.search(src):
        return None  # 已有 Tab（人工或上轮已处理），视为解决
    new = insert_tabs(src, tabs)
    if new is None:
        return "页首无独立 Init 行"
    pwb.info(f"{title}: 挂 {'、'.join(tabs)}")
    if write and not config.simulate:
        page.text = new
        page.save(summary=SUMMARY, bot=True)
    return None


def do_append(
    zh, tab: str, anchor: str, target: str, direction: str, write: bool
) -> str | None:
    """给模板补条目。返回 None = 成功/干跑，否则失败原因。"""
    page = pwb.Page(zh, f"Template:Tab/{tab}")
    src = page.text
    if target in RE_LINK.findall(src):
        return None  # 已存在（含注释暂存），视为解决
    new = insert_entry(src, anchor, target, direction)
    if new is None:
        return "插入位无法唯一机械定位"
    pwb.info(f"Tab/{tab}: +[[{target}]]")
    if write and not config.simulate:
        page.text = new
        page.save(summary=SUMMARY, bot=True)
    return None


def process(uncovered: list, pages: dict, tab_links: dict, zh, write: bool):
    """一轮未覆盖清单的计划与执行，返回 (遗留报告项, 成功编辑数)。"""
    mount_groups: dict[str, list] = defaultdict(list)
    appends = []
    for c, reason in uncovered:
        if reason == REASON_NO_TAB:
            mount_groups[c["zh_page"]].append(c)
        else:
            appends.append(c)

    leftovers: list[str] = []
    edits = 0
    for title, cs in sorted(mount_groups.items()):
        tabs, why = mount_candidates(title, cs, pages, tab_links)
        if tabs is None:
            leftovers.append(f"[[{title}]]：挂 Tab —— {why}")
            continue
        why = do_mount(zh, title, tabs, write)
        if why is None:
            edits += 1
        else:
            leftovers.append(f"[[{title}]]：挂 {'、'.join(tabs)} —— {why}")
    for c in appends:
        zh_page, target = c["zh_page"], c["zh_target"]
        label = f"[[{zh_page}]] → [[{target}]]：补条目 —— "
        if _series_key(pages[zh_page]["en"]) != _series_key(c["en_target"]):
            leftovers.append(
                label + "跨系列边界（en 标题系列键不一致），需人工判定归属 Tab"
            )
            continue
        cands = append_candidates(zh_page, pages, tab_links)
        if not cands:
            leftovers.append(label + "本页与父页均无 Tab")
            continue
        srcs, _, _ = batch_query(zh, {f"Template:Tab/{t}" for t in cands})
        tab, why = pick_template(
            {
                t: src
                for t in cands
                if (src := srcs.get(norm(f"Template:Tab/{t}"))) is not None
            },
            zh_page,
            target,
            c["direction"],
        )
        if tab is None:
            assert why is not None  # pick_template 未命中必带原因
            leftovers.append(label + why)
            continue
        why = do_append(zh, tab, zh_page, target, c["direction"], write)
        if why is None:
            edits += 1
        else:
            leftovers.append(f"[[{zh_page}]] → [[{target}]]：补 Tab/{tab} —— {why}")
    return leftovers, edits


def build_report(leftovers: list[str], mismatches: list) -> str:
    """报告页内容（确定性输出，无变更不触发编辑）。"""
    lines = [
        "本页由系列导航同步任务自动维护（有变更才编辑）。",
        "",
        (
            "机械可判定的挂载/补条目已自动完成（同系列键邻居 Tab 全票一致才挂；"
            "锚定位唯一且显示文本可推导才补）。以下需人工处理，"
            "处理规则见系列导航同步 SOP。"
        ),
        "",
        "== 未覆盖（需人工） ==",
    ]
    lines += [f"* {item}" for item in sorted(leftovers)] or ["（无）"]
    lines.append("== 拆分对应失配 ==")
    if mismatches:
        for base, problems in mismatches:
            lines.append(f"* [[{base}]]")
            lines += [f"** {p}" for p in problems]
    else:
        lines.append("（无）")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    pwb.handle_args()  # -always 等忽略：不询问；-s 走 config.simulate 分支
    zh = pwb.Site()
    en = pwb.Site("en", "re0")

    leftovers = []
    pages = en2zh = split_groups = None
    for round_no in range(1, MAX_ROUNDS + 2):
        write = round_no <= MAX_ROUNDS
        pages, en2zh, split_groups = scan_zh(zh)
        checks = collect_checks(en, pages, en2zh)
        tab_links = load_tab_links(zh, pages)
        *_, uncovered = classify_checks(pages, checks, tab_links)
        pwb.info(
            f"第 {round_no} 轮：未覆盖 {len(uncovered)} / 检查 {len(checks)}"
            f"{'' if write else '（复核，不再写入）'}"
        )
        if not uncovered:
            leftovers = []
            break
        for c, reason in uncovered:
            pwb.info(
                f"  未覆盖 {c['zh_page']}: {c['direction']} "
                f"en:{c['en_target']} -> zh:{c['zh_target']}（{reason}）"
            )
        leftovers, edits = process(uncovered, pages, tab_links, zh, write)
        pwb.info(f"第 {round_no} 轮：写入 {edits} 项，遗留 {len(leftovers)} 项")
        if config.simulate or not write or edits == 0:
            break

    mismatches, n_groups = check_splits(en, pages, split_groups)
    pwb.info(f"拆分对应检查：{n_groups} 组，失配 {len(mismatches)} 组")

    report = build_report(leftovers, mismatches)
    report_page = pwb.Page(zh, REPORT_PAGE)
    old = report_page.text if report_page.exists() else ""
    if old != report:
        if config.simulate:
            pwb.info(f"报告页 {REPORT_PAGE} 将更新")
        else:
            report_page.text = report
            report_page.save(summary=REPORT_SUMMARY, bot=True)
            pwb.info(f"报告页 {REPORT_PAGE} 已更新")
