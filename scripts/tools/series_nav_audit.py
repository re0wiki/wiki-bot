"""系列导航（Tab/*）与 en 站 Previous/Next 链的一致性审计。只读，匿名可达。

用途：en 站新增/合并/拆分系列内容（剧集、漫画话数、短篇、音乐）后，
zh 侧的 Tab 覆盖不会自动跟随——本工具产出待办清单。用法与背景见
docs/series-nav-sync.md。

两项检查：
1. 覆盖（coverage）：en 每个 previous/next 目标的 zh 对应页，必须出现在
   该页 {{Tab/…}} 的链接集合内（分层 Tab 两跳判定：本页 Tab 链接的季/章
   总页自带下一层 Tab）。
2. 拆分对应（splits）：zh 前/中/后篇拆分页与 en Part N 结构一一对应
   （篇数一致、前→Part 1、中→Part 2、后→末位 Part）。

注意：en→zh 映射用 zh 页源码的 [[en:…]] 建立（langlinks 派生表不可靠）；
参数值匹配用 [ \\t]* 而非 \\s*（\\s 吃换行，空值行会吞下一行）。
"""

import re
from collections import defaultdict

import pywikibot
from pywikibot.data import api

RE_EN_LINK = re.compile(r"\[\[en:([^\]|]+)")
RE_PREVNEXT = re.compile(
    r"^\s*\|\s*(previous|next)\s*=[ \t]*(.*)$", re.IGNORECASE | re.MULTILINE
)
RE_LINK = re.compile(r"\[\[([^\]|#]+)")
RE_TAB = re.compile(r"\{\{\s*Tab/([^}|]+)")
RE_SPLIT = re.compile(r"^(.*?)(（前篇）|（中篇）|（后篇）|（後篇）|前篇|后篇|後篇)$")
RE_PART = re.compile(r"^(.*?)\s+Part\s+(\d+)$")

# 拆分后缀 → 期望的 Part 序号（-1 = 末位）
SUFFIX_ORDER = {
    "（前篇）": 1,
    "前篇": 1,
    "（中篇）": 2,
    "（后篇）": -1,
    "（後篇）": -1,
    "后篇": -1,
    "後篇": -1,
}


def norm(t: str) -> str:
    t = t.strip().replace("_", " ")
    return (t[0].upper() + t[1:]) if t else t


def chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def batch_query(site, titles):
    """≤50 titles/批取源码（读路径匿名可达上限），redirects=1 归一。

    返回 (title->content, redirect_from->to, missing_set)。
    """
    contents, redirs, missing = {}, {}, set()
    for batch in chunks(sorted(titles), 50):
        data = api.Request(
            site=site,
            parameters={
                "action": "query",
                "prop": "revisions",
                "rvprop": "content",
                "rvslots": "main",
                "format": "json",
                "formatversion": "2",
                "redirects": "1",
                "titles": "|".join(batch),
            },
        ).submit()
        q = data.get("query", {})
        for r in q.get("redirects", []):
            redirs[norm(r["from"])] = norm(r["to"])
        for pg in q.get("pages", []):
            t = norm(pg.get("title", ""))
            if "missing" in pg:
                missing.add(t)
            else:
                revs = pg.get("revisions") or []
                contents[t] = revs[0]["slots"]["main"]["content"] if revs else ""
    return contents, redirs, missing


def exists_batch(site, titles):
    """≤50 titles/批存在性检查，返回已归一的存在标题集。"""
    existing = set()
    for batch in chunks(sorted(titles), 50):
        data = api.Request(
            site=site,
            parameters={
                "action": "query",
                "prop": "info",
                "format": "json",
                "formatversion": "2",
                "redirects": "1",
                "titles": "|".join(batch),
            },
        ).submit()
        q = data.get("query", {})
        for pg in q.get("pages", []):
            if "missing" not in pg:
                existing.add(norm(pg["title"]))
    return existing


def scan_zh(site):
    """扫 zh 主空间全部内容页，返回 (页面信息, en→zh 映射, 拆分词干组)。"""
    pages = {}  # zh_title -> {"en": str, "tabs": set[str]}
    en2zh = {}
    split_groups = defaultdict(dict)  # 词干 -> {后缀: zh_title}
    for p in site.allpages(namespace=0, content=True):
        t = p.title()
        if p.isRedirectPage():
            continue
        m = RE_EN_LINK.search(p.text)
        en_link = norm(m.group(1)) if m else ""
        pages[t] = {
            "en": en_link,
            "tabs": {norm(x) for x in RE_TAB.findall(p.text)},
        }
        if en_link:
            en2zh.setdefault(en_link, t)
        sm = RE_SPLIT.match(t)
        if sm:
            split_groups[sm.group(1)][sm.group(2)] = t
    return pages, en2zh, split_groups


def collect_checks(en_site, pages, en2zh):
    """从 en 页源码提取 prev/next 目标，逐条反查 zh 对应页。"""
    en_content, en_redir, en_missing = batch_query(en_site, set(en2zh))

    def resolve(t):
        return en_redir.get(t, t)

    en2zh_r = {resolve(k): v for k, v in en2zh.items()}

    checks = []
    for zh_title, info in pages.items():
        if not info["en"]:
            continue
        content = en_content.get(resolve(info["en"]))
        if content is None:
            continue
        for mm in RE_PREVNEXT.finditer(content):
            m = RE_LINK.search(mm.group(2))
            if not m:  # 空值/非链接值
                continue
            en_target = norm(m.group(1))
            checks.append(
                {
                    "zh_page": zh_title,
                    "direction": mm.group(1).lower(),
                    "en_target": en_target,
                    "zh_target": en2zh_r.get(resolve(en_target))
                    or en2zh_r.get(en_target),
                    "en_redlink": en_target in en_missing
                    or resolve(en_target) in en_missing,
                }
            )
    # 不在首批查询集内的 en 目标补一轮重定向归一后重查
    unresolved = {
        c["en_target"] for c in checks if c["zh_target"] is None and not c["en_redlink"]
    }
    if not unresolved:
        return checks
    _, redir2, missing2 = batch_query(en_site, unresolved)
    en_missing |= missing2
    for c in checks:
        if c["zh_target"] is None and c["en_target"] in redir2:
            c["zh_target"] = en2zh_r.get(redir2[c["en_target"]])
            c["en_redlink"] = redir2[c["en_target"]] in en_missing
    return checks


def load_tab_links(zh_site, pages):
    """全部 Tab 模板的链接集（zh 重定向归一到最终目标）。"""
    all_tabs = set().union(*(i["tabs"] for i in pages.values())) if pages else set()
    tab_src, _, _ = batch_query(zh_site, {f"Template:Tab/{t}" for t in all_tabs})
    tab_links = {}
    for t in all_tabs:
        src = tab_src.get(norm(f"Template:Tab/{t}"), "")
        tab_links[t] = {
            norm(x)
            for x in RE_LINK.findall(src)
            if not x.lower().startswith("template:")
        }
    all_link_targets = set().union(*tab_links.values()) if tab_links else set()
    _, zh_redir, _ = batch_query(zh_site, all_link_targets - set(pages.keys()))
    for t, links in tab_links.items():
        tab_links[t] = {zh_redir.get(x, x) for x in links}
    return tab_links


def classify_checks(pages, checks, tab_links):
    """逐条判定：直接覆盖 / 分层覆盖（两跳）/ N/A / 未覆盖。"""

    def direct(page):
        tabs = pages[page]["tabs"]
        return set().union(*(tab_links.get(t, set()) for t in tabs)) if tabs else set()

    def layered_via(page, target):
        """两跳分层：本页 Tab 链接的季/章总页，其 Tab 链接集包含 target。"""
        for link in direct(page):
            info = pages.get(link)
            if (
                info
                and info["tabs"]
                and target
                in set().union(*(tab_links.get(t, set()) for t in info["tabs"]))
            ):
                return link
        return None

    covered, layered, na, uncovered = [], [], [], []
    for c in checks:
        if c["en_redlink"]:
            na.append((c, "en 红链"))
        elif c["zh_target"] is None:
            na.append((c, "zh 无对应页"))
        elif not pages[c["zh_page"]]["tabs"]:
            uncovered.append((c, "页面无 Tab"))
        elif c["zh_target"] in direct(c["zh_page"]):
            covered.append(c)
        elif via := layered_via(c["zh_page"], c["zh_target"]):
            layered.append((c, via))
        else:
            uncovered.append((c, "目标不在 Tab 链接集（含两跳）"))
    return covered, layered, na, uncovered


def check_coverage(zh_site, en_site, pages, en2zh):
    """检查 1：en prev/next 目标的 Tab 覆盖。返回 (covered, layered, na, uncovered, 总数)。"""
    checks = collect_checks(en_site, pages, en2zh)
    tab_links = load_tab_links(zh_site, pages)
    return (*classify_checks(pages, checks, tab_links), len(checks))


def real_split_groups(split_groups, zh_en):
    """过滤假阳性：单成员组且 en 链接非 Part 页 → 后缀属作品名（如 蜜月背后篇）。"""
    return {
        base: members
        for base, members in split_groups.items()
        if len(members) > 1
        or RE_PART.match(zh_en.get(next(iter(members.values())), ""))
    }


def resolve_en_bases(groups, zh_en):
    """每组词干的 en 基名（裸页 en 链接优先，否则取成员链接去 Part 后缀）。"""
    group_en_base = {}
    for base, members in groups.items():
        en_base = zh_en.get(base)
        if not en_base:
            for zh_t in members.values():
                m = RE_PART.match(zh_en.get(zh_t, ""))
                if m:
                    en_base = m.group(1)
                    break
        group_en_base[base] = en_base
    return group_en_base


def member_problems(zh_t, suffix, zh_en, en_parts):
    """单个拆分页成员的序号/链接核对。"""
    link = zh_en.get(zh_t)
    if not link:
        return [f"{zh_t} 无 en 链接"]
    m = RE_PART.match(link)
    if not m:
        return [f"{zh_t} 的 en 链接 {link!r} 不是 Part 页"]
    expect, part_no = SUFFIX_ORDER[suffix], int(m.group(2))
    if expect > 0 and part_no != expect:
        return [f"{zh_t} -> Part {part_no}，期望 Part {expect}"]
    if expect == -1 and en_parts and part_no != max(en_parts):
        return [f"{zh_t} -> Part {part_no}，期望末位 Part {max(en_parts)}"]
    return []


def group_problems(base, members, en_base, en_existing, zh_en):
    """单组词干的全部失配问题。"""
    if not en_base:
        return ["整组无 en 链接"]
    en_parts = sorted(i for i in (1, 2, 3, 4) if f"{en_base} Part {i}" in en_existing)
    problems = []
    if not en_parts:
        problems.append(f"en 无 Part 页，zh 却拆成 {len(members)} 篇")
    elif len(members) != len(en_parts):
        problems.append(f"zh 拆 {len(members)} 篇 ≠ en 拆 {len(en_parts)} 篇")
    for suffix, zh_t in sorted(members.items()):
        problems.extend(member_problems(zh_t, suffix, zh_en, en_parts))
    return problems


def check_splits(en_site, pages, split_groups):
    """检查 2：zh 拆分页与 en Part 结构对应。返回 (失配清单, 组数)。"""
    zh_en = {t: i["en"] for t, i in pages.items() if i["en"]}
    groups = real_split_groups(split_groups, zh_en)
    group_en_base = resolve_en_bases(groups, zh_en)

    probe = set()
    for en_base in group_en_base.values():
        if en_base:
            probe.add(en_base)
            probe.update(f"{en_base} Part {i}" for i in (1, 2, 3, 4))
    en_existing = exists_batch(en_site, probe)

    mismatches = []
    for base, members in sorted(groups.items()):
        problems = group_problems(
            base, members, group_en_base[base], en_existing, zh_en
        )
        if problems:
            mismatches.append((base, problems))
    return mismatches, len(groups)


def main():
    zh = pywikibot.Site("zh", "re0")
    en = pywikibot.Site("en", "re0")

    pages, en2zh, split_groups = scan_zh(zh)
    print(f"zh 主空间内容页 {len(pages)}，带 en 链接 {len(en2zh)}", flush=True)

    covered, layered, na, uncovered, total = check_coverage(zh, en, pages, en2zh)
    print(
        f"\n== 覆盖检查：{total} 项 = 直接 {len(covered)} + 分层 {len(layered)} + N/A {len(na)} + 未覆盖 {len(uncovered)} =="
    )
    for c, reason in uncovered:
        print(
            f"  未覆盖 {c['zh_page']}: {c['direction']} en:{c['en_target']} -> zh:{c['zh_target']}（{reason}）"
        )
    for c, reason in na:
        print(f"  N/A {c['zh_page']}: {c['direction']} en:{c['en_target']}（{reason}）")

    mismatches, n_groups = check_splits(en, pages, split_groups)
    print(f"\n== 拆分对应检查：{n_groups} 组，失配 {len(mismatches)} 组 ==")
    for base, problems in mismatches:
        print(f"  {base}")
        for p in problems:
            print(f"    ✗ {p}")

    if uncovered or mismatches:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
