"""把 en 站主空间分类经 wiki 上映射同步到 zh 页面源码（re0_category）。

映射表在 wiki 上（不进仓库，人工维护）：
- 主映射：zh 中文分类页源码里的 [[en:Category:X]] → en 名 X 映射到该页分类名；
- 交叉校验：en 名分类页（Category:X）挂 {{Category redirect|中文名}}，
  与主映射不一致即冲突——进报告，不猜测。

同步（zh 侧驱动，与 audit_langlinks 同向；每轮全量 diff、幂等、无本地状态）：
1. zh 主空间非重定向页两阶段取源码 + prop=categories（50/批同一请求）；
2. 无 [[en:X]] 链接的页不同步（zh 原创页等，见 docs/wiki-structure.md）；
3. desired = 映射(en 页 prop=categories&redirects=1 的分类) − 不同步集合 −
   Init 覆盖集（INIT_CATS：映射目标属 Init 前缀×后缀矩阵的不写入，逐页检查
   registered、缺失进报告页 == Init 覆盖缺失 == 节——缺失即页面未归位/缺前缀，
   归 move/人工；本任务在 move 之前运行，同周期新搬运页会短暂出现一轮，
   持续存在才需人工）− 页外带入分类
   （registered − 源码行：模板已提供的不写源码行，避免双重来源；Init 前缀分类
   机制保留，与本任务互补——Init 管标题可判定的结构基线，本任务管 en 数据驱动
   的内容分类）；
4. 受管集合 = 映射键 ∪ 映射值：源码中受管分类行整体按 desired 重写
   （en 名残留行随之归一），不受管的源码分类行（人工添加、
   新搬运待整理/机翻待校对等）不碰；
5. 不同步集合 = Category:自动清空分类 成员 ∪ TRACKING_CATEGORIES：
   en 名分类页挂 [[Category:自动清空分类]] 即声明不同步（优先于 interwiki
   映射——分类页的 en 链接同时是读者导航，语义 1:N 的如 图库↔Image Gallery
   保留链接但不同步），且其 en 名源码残留行一律清除（本任务吸收原
   cat-image-gallery/cat-relationships 两专职任务的清空职能）；
   TRACKING_CATEGORIES 是 en 站 MW 追踪分类（解析器带入、非内容），
   完整清单再生成规程见常量注释；
6. 未映射 en 分类与映射冲突写报告页 REPORT_PAGE（有变更才编辑）。

人工不要手动增删页面底部的受管分类行（下轮会被改回）——与译名工作流同型，
改分类 = 改 wiki 上的映射页。zh 侧分类改名 = 移动中文分类页 + 改 en 名页的
redirect 目标，下轮本任务把成员页源码行全部改写为新名。

不做：分类树组织（人工大致随 en，见 docs/wiki-structure.md）；transferbot 与
LLM 翻译管线不处理分类（搬运/翻译时剥除，由本任务下轮补上，留一笔编辑记录
便于观察运行状态）。取数依赖 en prop=categories 派生表（en 分类多由模板带入，
扫源码无效），单页取数失败/缺失时保持该页现状不删。
"""

import re
from collections import Counter

import pywikibot as pwb
from pywikibot import config
from pywikibot.tools import first_upper

SUMMARY = "机器人：自英文站同步分类"
REPORT_PAGE = "User:IchiSanNi/cat_sync"
REPORT_SUMMARY = "机器人：更新分类同步报告"

# 不同步信号：en 名分类页源码挂 [[Category:自动清空分类]]（zh 站既有惯例，
# 见该分类页说明），在映射扫描同一趟源码里检出。
AUTOEMPTY_CAT = "自动清空分类"
AUTOEMPTY_RE = re.compile(
    r"\[\[(?:Category|分类|分類):自动清空分类\s*(?:\|[^\]]*)?\]\]"
)

# en 站 MW 追踪分类（解析器带入、非内容分类，一律豁免同步与报告）。
# 清单 = en Special:TrackingCategories 正表（2026-09-30 浏览器渲染实测，
# 36 条；Fandom api.php 无 list=trackingcategories 模块，/wiki/ HTML 路径有
# Cloudflare 挑战，只能渲染获取）。MW 升级新增追踪分类时以报告页漏出的
# 未映射条目为信号，人工补入本表。
TRACKING_CATEGORIES: frozenset[str] = frozenset(
    {
        "Hidden categories",
        "Indexed pages",
        "Noindexed pages",
        "Pages containing omitted template arguments",
        "Pages transcluding nonexistent sections",
        "Pages using ISBN magic links",
        "Pages using deprecated categorytree parameters",
        "Pages using deprecated enclose attributes",
        "Pages using deprecated source tags",
        "Pages using duplicate arguments in template calls",
        "Pages using the EasyTimeline extension",
        "Pages where expansion depth is exceeded",
        "Pages where node count is exceeded",
        "Pages where template include size is exceeded",
        "Pages where the unstrip depth limit is exceeded",
        "Pages where the unstrip size limit is exceeded",
        "Pages which use = as a template",
        "Pages with TemplateStyles errors",
        "Pages with broken file links",
        "Pages with ignored display titles",
        "Pages with image sizes containing extra px",
        "Pages with invalid behavior switches",
        "Pages with invalid language codes",
        "Pages with math errors",
        "Pages with math render errors",
        "Pages with non-numeric formatnum arguments",
        "Pages with reference errors",
        "Pages with script errors",
        "Pages with syntax highlighting errors",
        "Pages with template loops",
        "Pages with too many expensive parser function calls",
        "Pages that use a deprecated format of the chem tags",
        "Pages that use a deprecated format of the math tags",
        "Pages that use extended references",
        "Scribunto modules with errors",
        "TemplateStyles stylesheets with errors",
    }
)


# Init 覆盖分类：运行时从 wiki 侧 Module:Title/Module:Init 源码解析
# （前缀/后缀数组与无前缀回退词的唯一权威在 wiki，仓库不存副本）。
# 解析失败即响亮报错——wiki 侧格式变更必须人工感知。
def parse_init_cats(module_title_src: str, module_init_src: str) -> frozenset[str]:
    """Module:Title 的 prefixes/suffixes 数组 + Module:Init 的回退词 →
    Init 覆盖分类全集（前缀 ∪ 回退词 ∪ 前缀×后缀矩阵）。"""

    def array(name: str) -> list[str]:
        m = re.search(rf"local {name} = \{{([^}}]*)\}}", module_title_src)
        assert m, f"Module:Title 的 {name} 数组解析失败"
        items = re.findall(r"'([^']+)'", m.group(1))
        assert items, f"Module:Title 的 {name} 数组为空"
        return items

    m = re.search(r"else\s*c = '([^']+)'", module_init_src)
    assert m, "Module:Init 的无前缀回退词解析失败"
    prefixes, suffixes = array("prefixes"), array("suffixes")
    return frozenset(
        [*prefixes, m.group(1), *(p + s for p in prefixes for s in suffixes)]
    )


# 分类命名空间写法集合（与 site.namespaces[14] 的 canonical/别名手工同步）：
# Category 为 canonical，分类/分類 为简繁别名。行首冒号形式（[[:Category:X]]）
# 是内联链接而非归类，排除；行前有空格是 preformatted 文本，本就不构成归类。
CAT_LINE_RE = re.compile(
    r"(?m)^\[\[(?!:)(?:Category|分类|分類):([^\]\|\n]+)(?:\|[^\]\n]*)?\]\][ \t]*\r?\n?"
)
# 页尾语言链接块的行首语言码（re0 family 11 个外语码，
# 与 families/re0_family.py 手工同步）。
LANGLINK_LINE_RE = re.compile(r"(?m)^\[\[(?:pt-br|de|en|es|fr|it|ko|nl|pl|ru|uk):")
# 与 re0_transferbot 同款（两处手工同步）：取首个 en 链接作为跨站对应。
EN_LINK_RE = re.compile(r"\[\[en:([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
EN_CAT_LINK_RE = re.compile(r"\[\[en:Category:([^\]|]+)(?:\|[^\]]*)?\]\]")
CAT_RD_RE = re.compile(
    r"\{\{\s*[Cc]ategory[ _]redirect\s*\|\s*([^}|]+?)\s*(?:\|[^}]*)?\}\}"
)


def normalize(title: str) -> str:
    """归一到 MediaWiki 规范标题（下划线转空格、首字母大写）。

    与 re0_transferbot/re0_fixing_redirects 的同款函数三处手工同步。
    """
    return first_upper(title.replace("_", " ").strip())


def parse_en_link(text: str) -> str | None:
    """页面源码里的首个 en 链接目标（归一化）；无则 None。"""
    m = EN_LINK_RE.search(text)
    return normalize(m.group(1)) if m else None


def find_autoempty(cat_pages: dict[str, str]) -> set[str]:
    """挂 [[Category:自动清空分类]] 的分类页名（归一化）：不同步 + 残留清空。"""
    return {
        normalize(name) for name, text in cat_pages.items() if AUTOEMPTY_RE.search(text)
    }


def build_mapping(
    cat_pages: dict[str, str],
) -> tuple[dict[str, str], list[str], list[str]]:
    """从分类页源码建映射。返回 (映射, 冲突清单, 提示清单)。

    cat_pages: {分类名（不含 Category: 前缀）: 源码}。
    冲突：interwiki 与 category redirect 不一致、同一 en 名被多个中文页声称、
    单页多个不同 en 链接。提示：redirect 缺页/缺 redirect/redirect 无 interwiki
    对应——均是映射维护的待办信号。
    """
    mapping: dict[str, str] = {}
    redirects: dict[str, str] = {}
    conflicts: list[str] = []
    for name, text in cat_pages.items():
        en_links = {normalize(x) for x in EN_CAT_LINK_RE.findall(text)}
        if len(en_links) > 1:
            conflicts.append(f"Category:{name} 有多个 en 链接: {sorted(en_links)}")
        for en_name in en_links:
            if en_name in mapping and mapping[en_name] != name:
                conflicts.append(
                    f"{en_name} 被多个分类声称: {mapping[en_name]} 与 {name}"
                )
            mapping.setdefault(en_name, name)
        if m := CAT_RD_RE.search(text):
            redirects[name] = normalize(m.group(1))
    hints = []
    for en_name, zh_name in sorted(mapping.items()):
        if en_name in redirects:
            if redirects[en_name] != zh_name:
                conflicts.append(
                    f"{en_name}: interwiki 映射到 {zh_name}，"
                    f"redirect 指 {redirects[en_name]}"
                )
        elif en_name in cat_pages:
            hints.append(
                f"Category:{en_name} 存在但缺 <nowiki>{{Category redirect}}</nowiki>"
            )
        else:
            hints.append(
                f"Category:{en_name} 待建"
                f"（挂 <nowiki>{{{{Category redirect|{zh_name}}}}}</nowiki>）"
            )
    for name in sorted(redirects):
        if name not in mapping:
            hints.append(f"Category redirect {name} 无 interwiki 映射对应")
    return mapping, conflicts, hints


def resolve_en_cats(data: dict, requested: list[str]) -> dict[str, list[str] | None]:
    """fv=2 prop=categories 响应 → {请求标题: 分类名列表}（页缺失为 None）。

    请求标题经 normalized 与 redirects 两级映射到最终页（redirects=1 时
    响应页是重定向目标的分类）。
    """
    norm = {n["from"]: n["to"] for n in data["query"].get("normalized", [])}
    redir = {r["from"]: r["to"] for r in data["query"].get("redirects", [])}
    pages = {p["title"]: p for p in data["query"]["pages"]}
    out = {}
    for t0 in requested:
        t = norm.get(t0, t0)
        t = redir.get(t, t)
        p = pages.get(t)
        out[t0] = (
            None
            if p is None or "missing" in p
            else [c["title"].removeprefix("Category:") for c in p.get("categories", [])]
        )
    return out


def compute_sync(
    text: str,
    registered: set[str],
    en_cats: list[str],
    mapping: dict[str, str],
    managed: set[str] | frozenset[str],
    excluded: set[str] | frozenset[str],
    init_cats: set[str] | frozenset[str],
) -> tuple[str | None, set[str], set[str], list[str], list[str]]:
    """计算同步后的新源码。返回 (new_text|None, added, removed, unmapped, init_missing)。

    new_text 为 None 表示无需改动。unmapped 是缺映射且未豁免的 en 分类。
    excluded（自动清空分类成员 ∪ MW 追踪分类）优先于 mapping，其源码行
    一律清除（残留清空职能）。映射目标属 init_cats 的不写入，仅当
    registered 缺失时记入 init_missing 报告。
    """
    source_names = {m.group(1).strip() for m in CAT_LINE_RE.finditer(text)}
    non_source = set(registered) - source_names  # Init/模板带入，不写源码行
    desired = {
        mapping[c]
        for c in en_cats
        if c in mapping and c not in excluded and mapping[c] not in init_cats
    } - non_source
    init_missing = [
        mapping[c]
        for c in en_cats
        if c in mapping
        and c not in excluded
        and mapping[c] in init_cats
        and mapping[c] not in registered
    ]
    unmapped = [c for c in en_cats if c not in mapping and c not in excluded]
    current = {n for n in source_names if normalize(n) in managed}
    purged = {n for n in source_names if normalize(n) in excluded}
    if current == desired and not purged:
        return None, set(), set(), unmapped, init_missing
    removed = (current - desired) | purged
    added = desired - current
    insert_text = "".join(f"[[Category:{n}]]\n" for n in sorted(desired))
    # 删受管行与待清空行；在首个删除位插入 desired（保持块位置稳定）
    parts, cur, placed = [], 0, False
    for m in CAT_LINE_RE.finditer(text):
        name = normalize(m.group(1).strip())
        if name not in managed and name not in excluded:
            continue
        parts.append(text[cur : m.start()])
        if not placed:
            parts.append(insert_text)
            placed = True
        cur = m.end()
    parts.append(text[cur:])
    new_text = "".join(parts)
    if not placed:
        if lm := LANGLINK_LINE_RE.search(new_text):
            # 插在语言链接块前（en 站惯例：分类行在语言链接前）
            new_text = new_text[: lm.start()] + insert_text + new_text[lm.start() :]
        else:
            if not new_text.endswith("\n"):
                new_text += "\n"
            new_text += insert_text
    return new_text, added, removed, unmapped, init_missing


def build_report(
    unmapped: Counter,
    conflicts: list[str],
    hints: list[str],
    excluded: set[str] | frozenset[str],
    init_missing: dict[str, list[str]],
) -> str:
    """报告页内容（确定性输出，无变更不触发编辑）。"""
    lines = [
        "本页由分类同步任务自动维护（有变更才编辑）。",
        "",
        (
            "建立映射：在中文分类页加 <nowiki>[[en:Category:X]]</nowiki>，"
            "并建 en 名分类页挂 {{T|Category redirect|中文名}}。"
            "登记后下轮同步自动生效。"
        ),
        "",
        "== 不同步 ==",
        (
            "以下 en 分类不同步（en 名分类页挂了 [[:Category:自动清空分类]]"
            " 的为人工裁决，其余为 MediaWiki 追踪分类由脚本豁免）；"
            "其源码残留行会被自动清空。新增裁决：把 en 名分类页加入"
            " [[:Category:自动清空分类]]。不同步优先于 interwiki 映射"
            "（分类页的 en 链接同时是读者导航）。"
        ),
        "",
        *(f"* <nowiki>[[en:Category:{name}]]</nowiki>" for name in sorted(excluded)),
        "",
        "== 未映射分类 ==",
    ]
    if unmapped:
        lines += [
            f"* <nowiki>[[en:Category:{name}]]</nowiki>（{count} 个 en 页面使用）"
            for name, count in sorted(unmapped.items(), key=lambda kv: (-kv[1], kv[0]))
        ]
    else:
        lines.append("（无）")
    lines.append("== 映射冲突 ==")
    lines += [f"* {c}" for c in sorted(conflicts)] or ["（无）"]
    lines.append("== Init 覆盖缺失 ==")
    lines.append(
        "映射目标由 Init 按标题前缀×后缀带入的分类不写入源码；以下页面未登记"
        "对应分类——即未归位或缺前缀。同周期新搬运页会短暂出现一轮即消失"
        "（由 move 归位），持续存在的才需人工处理。"
    )
    lines += [
        f"* [[{page}]]（缺 {', '.join(sorted(cats))}）"
        for page, cats in sorted(init_missing.items())
    ] or ["（无）"]
    lines.append("== 维护提示 ==")
    lines += [f"* {h}" for h in sorted(hints)] or ["（无）"]
    return "\n".join(lines) + "\n"


def batched(site, titles: list[str], **params) -> list[tuple[list[str], dict]]:
    """titles= 50/批查询（wiki-access 两阶段配方的批内部分）。

    返回 [(本批 titles, 原始响应)]——响应只含本批页面，解析必须按本批对齐。
    """
    out = []
    for i in range(0, len(titles), 50):
        batch = titles[i : i + 50]
        data = site.simple_request(
            action="query",
            titles="|".join(batch),
            formatversion="2",
            format="json",
            **params,
        ).submit()
        out.append((batch, data))
    return out


if __name__ == "__main__":
    pwb.handle_args()  # -always 等忽略：不询问；-s 走 config.simulate 分支
    zh = pwb.Site()
    en = pwb.Site("en", "re0")

    # 1. 映射发现（zh 分类命名空间全量源码）+ 报告页的人工不同步清单
    cat_titles = [p.title() for p in zh.allpages(namespace=14)]
    cat_pages = {}
    for _batch, data in batched(
        zh, cat_titles, prop="revisions", rvprop="content", rvslots="main"
    ):
        for p in data["query"]["pages"]:
            if "revisions" in p:
                cat_pages[p["title"].removeprefix("Category:")] = p["revisions"][0][
                    "slots"
                ]["main"]["content"]
    mapping, conflicts, hints = build_mapping(cat_pages)
    managed = set(mapping) | set(mapping.values())
    excluded = find_autoempty(cat_pages) | TRACKING_CATEGORIES
    # Init 覆盖集：wiki 侧 Module 源码运行时解析（仓库零副本）
    init_cats: frozenset[str] = frozenset()
    for _batch, data in batched(
        zh,
        ["Module:Title", "Module:Init"],
        prop="revisions",
        rvprop="content",
        rvslots="main",
    ):
        mod_srcs = {
            p["title"]: p["revisions"][0]["slots"]["main"]["content"]
            for p in data["query"]["pages"]
            if "revisions" in p
        }
        init_cats = parse_init_cats(mod_srcs["Module:Title"], mod_srcs["Module:Init"])
    pwb.info(
        f"映射 {len(mapping)} 条，冲突 {len(conflicts)} 条，不同步 {len(excluded)} 条，"
        f"Init 覆盖 {len(init_cats)} 类"
    )

    # 2. zh 主空间非重定向页：两阶段取源码 + 已登记分类（同一批请求）
    zh_titles = [p.title() for p in zh.allpages(namespace=0, filterredir=False)]
    zh_pages: dict[str, tuple[str, set[str]]] = {}
    for _batch, data in batched(
        zh,
        zh_titles,
        prop="revisions|categories",
        rvprop="content",
        rvslots="main",
        cllimit="500",
    ):
        for p in data["query"]["pages"]:
            if "revisions" not in p:
                continue
            zh_pages[p["title"]] = (
                p["revisions"][0]["slots"]["main"]["content"],
                {c["title"].removeprefix("Category:") for c in p.get("categories", [])},
            )
    pwb.info(f"zh 主空间 {len(zh_pages)} 页")

    # 3. en 对应页分类（redirects=1 取最终目标）
    en_titles = sorted(
        {link for text, _ in zh_pages.values() if (link := parse_en_link(text))}
    )
    en_cats: dict[str, list[str] | None] = {}
    for batch, data in batched(
        en, en_titles, prop="categories", cllimit="500", redirects="1"
    ):
        en_cats.update(resolve_en_cats(data, batch))
    pwb.info(f"en 对应页 {len(en_cats)} 页")

    # 4. 逐页 diff + 写入（无 en 链接的页只做残留清空）
    unmapped: Counter = Counter()
    init_missing: dict[str, list[str]] = {}
    synced = 0
    for title, (text, registered) in zh_pages.items():
        link = parse_en_link(text)
        cats: list[str] = []
        if link is not None:
            got = en_cats.get(link)
            if got is None:
                pwb.warning(f"en 页 {link} 取数失败或已删除，{title} 保持现状")
                continue
            cats = got
        new_text, added, removed, page_unmapped, page_init_missing = compute_sync(
            text, registered, cats, mapping, managed, excluded, init_cats
        )
        unmapped.update(page_unmapped)
        if page_init_missing:
            init_missing[title] = page_init_missing
        if new_text is None:
            continue
        pwb.info(f"{title}: +{sorted(added)} -{sorted(removed)}")
        synced += 1
        if config.simulate:
            continue  # -s 干跑：改动已逐条打印
        page = pwb.Page(zh, title)
        page.text = new_text
        page.save(summary=SUMMARY, bot=True)
    pwb.info(f"同步 {synced} 页；未映射分类 {len(unmapped)} 类")

    # 5. 报告页（有变更才编辑）
    report = build_report(unmapped, conflicts, hints, excluded, init_missing)
    report_page = pwb.Page(zh, REPORT_PAGE)
    if report_page.text != report:
        if config.simulate:
            pwb.info(f"报告页 {REPORT_PAGE} 将更新")
        else:
            report_page.text = report
            report_page.save(summary=REPORT_SUMMARY, bot=True)
            pwb.info(f"报告页 {REPORT_PAGE} 已更新")
