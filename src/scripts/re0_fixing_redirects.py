"""把源码中指向重定向的 [[链接]] 改写为最终目标（高效版 fixing_redirects）。

pywikibot 自带 fixing_redirects 对每页每个链接逐条发 API 查询
（实测 ~6 请求/页、单轮 ~1.5 万请求，2026-08-13 触发 Cloudflare 429，
见 docs/cloudflare-429.md）。本脚本与页面数线性、与链接数无关：
1. site.allpages(filterredir=True, content=True) 批量拉重定向页源码
   （50 页/批，~8k 重定向 ≈ 160 次），从 #REDIRECT 行本地解析重定向表
   （不碰 Fandom 派生表——allredirects 只回 fromid，且派生表有脏数据前科）；
2. 生成器 preload 批量拉正文页源码（50 页/批，2600 页 ≈ 52 次；注意
   -start: 生成器本身不含重定向页，所以重定向表必须单独拉）；
3. 链接从源码解析 [[...]]（不用 prop=links：{{Init}} 等模板的存在性探测
   会进链入链出表造成虚增，且只有源码字面链接才可能被改写）。
单轮总请求 ~210 次 + 少量写（原 ~1.5 万）。

改写规则移植自 pywikibot fixing_redirects.replace_links（保留显示文本）。
不做：已删页面的 moved_target 处理（本站无删在用重定向的习惯）。
不碰：重定向页自身（#REDIRECT 行归 redirect-do）、分类/文件/媒体链接
（不带冒号前缀的不在 links 表，原脚本也不处理）。
"""

import regex as re

import pywikibot as pwb
from pywikibot import config
from pywikibot.pagegenerators import GeneratorFactory
from pywikibot.textlib import isDisabled
from pywikibot.tools import first_lower, first_upper

SUMMARY = "机器人：修正重定向"

# 与 jobs/starts.py 的 ns_more 同步（main/project/template/category/module/mediawiki）
REDIRECT_NAMESPACES = (0, 4, 10, 14, 828, 8)


def is_interwiki(site, title: str) -> bool:
    """isInterwikiLink 的无网络替代：只比对第一个冒号前缀，不构造目标 Site。

    site.isInterwikiLink 会为命中的跨站前缀构造目标 APISite，其 __init__
    固定 login(cookie_only=True) 发 userinfo 请求——本站 interwikimap 有
    135 个外站前缀（wikipedia/wp 等指向 en.wikipedia.org，2026-09-05 实测
    墙内不可达，每轮运行触发 SSL 重试直至崩溃）。语义与 Link.parse_site
    等价（同样只看第一个冒号前缀）。
    """
    t = title.lstrip(": ")
    if ":" not in t:
        return False
    prefix = t[: t.index(":")].lower()
    if site.namespaces.lookup_name(prefix):
        return False
    if prefix in site.family.langs:
        return prefix != site.code
    return prefix in {e["prefix"] for e in site.siteinfo["interwikimap"]}


def normalize(title: str) -> str:
    """归一到 MediaWiki 规范标题（下划线转空格、首字母大写）。"""
    return first_upper(title.replace("_", " ").strip())


def extract_redirects(pages) -> dict[str, tuple[str, str | None]]:
    """从预载页面内容提取重定向表 {重定向标题: (目标标题, 锚点)}（未解链）。"""
    raw = {}
    for page in pages:
        m = page.site.redirect_regex.match(page.text)
        if not m:
            continue
        title, _, frag = m[1].partition("#")
        if is_interwiki(page.site, title):
            continue  # 跨站重定向目标，不改写指向它的链接
        raw[page.title()] = (normalize(title), frag or None)
    return raw


def resolve_chains(
    raw: dict[str, tuple[str, str | None]],
) -> dict[str, tuple[str, str | None]]:
    """传递闭包：{重定向标题: (最终标题, 锚点)}。环（含自环）整链丢弃。

    链上锚点取首个出现的（A→B#f1、B→C 时 A 的意图是 B#f1，改写为 C#f1）。
    双重重定向本是 redirect-do 每天修的对象，链通常极短。
    """
    out = {}
    for start in raw:
        seen = set()
        cur = start
        frag = None
        while cur in raw and cur not in seen:
            seen.add(cur)
            cur, f = raw[cur]
            if frag is None:
                frag = f
        if cur in seen:
            continue
        out[start] = (cur, frag)
    return out


def build_skip_prefixes(site) -> set[str]:
    """分类/文件/媒体命名空间的所有名字（小写）：不带冒号前缀的这类链接不改写。"""
    prefixes = set()
    for ns_id in (-2, 6, 14):
        ns = site.namespaces[ns_id]
        names = [ns.custom_name, ns.canonical_name, *ns.aliases]
        prefixes.update(n.lower() for n in names if n)
    return prefixes


def resolve_link(
    title: str,
    section: str,
    label: str | None,
    trail: str,
    final_title: str,
    final_frag: str | None,
    linktrail: str,
) -> str | None:
    """构造替换链接文本；None = 不改写。规则移植自上游 replace_links。

    与上游的一处有意差异：链接无锚点而重定向目标带锚点时，保留目标锚点
    （上游会丢弃）。
    """
    if section and final_frag:
        return None  # 双侧都有锚点，跳过（上游同款）
    link_text = label if label else title
    if trail:
        link_text += trail
    # 首字母大小写规则（对中文无影响）
    new_title = (
        final_title
        if link_text[0].isupper() or link_text[0].isdigit()
        else first_lower(final_title)
    )
    new_section = section or (f"#{final_frag}" if final_frag else "")
    if new_title == link_text and not new_section:
        return f"[[{new_title}]]"
    # 能用链接尾字符形式就不用管道链接
    if (
        not new_section
        and len(new_title) <= len(link_text)
        and first_upper(link_text[: len(new_title)]) == first_upper(new_title)
        and re.sub(linktrail, "", link_text[len(new_title) :]) == ""
    ):
        k = len(new_title)
        return f"[[{link_text[:k]}]]{link_text[k:]}"
    return f"[[{new_title}{new_section}|{link_text}]]"


def rewrite_links(
    text: str, rmap: dict[str, tuple[str, str | None]], site, skip_prefixes: set[str]
):
    """返回 (newtext, changes)，changes 是 (旧文本, 新文本) 列表。"""
    link_re = re.compile(
        r"\[\[(?P<title>[^\]\|#]*)(?P<section>#[^\]\|]*)?"
        r"(\|(?P<label>[^\]]*))?\]\](?P<trail>" + site.linktrail() + ")"
    )
    out = []
    curpos = 0
    changes = []
    for m in link_re.finditer(text):
        newlink = None
        title = m["title"].strip()
        if title and not isDisabled(text, m.start()) and not is_interwiki(site, title):
            had_colon = title.startswith(":")
            if had_colon:
                title = title[1:].lstrip()
            ns_prefix = title.split(":", 1)[0].lower() if ":" in title else None
            if had_colon or ns_prefix not in skip_prefixes:
                hit = rmap.get(normalize(title))
                if hit:
                    newlink = resolve_link(
                        title,
                        m["section"] or "",
                        m["label"],
                        m["trail"],
                        *hit,
                        site.linktrail(),
                    )
                    if newlink and had_colon:
                        newlink = "[[:" + newlink[2:]
        if newlink is None:
            continue
        out.append(text[curpos : m.start()])
        out.append(newlink)
        curpos = m.end()
        changes.append((m.group(0), newlink))
    if not changes:
        return text, changes
    out.append(text[curpos:])
    return "".join(out), changes


if __name__ == "__main__":
    factory = GeneratorFactory()
    factory.handle_args(
        pwb.handle_args()
    )  # -always 等无需处理：不询问，-s 由 API 层拦截
    site = pwb.Site()
    gen = factory.getCombinedGenerator(preload=True)
    assert gen is not None  # -start: 系列参数必定给出生成器
    redirect_pages = (
        p
        for ns in REDIRECT_NAMESPACES
        for p in site.allpages(namespace=ns, filterredir=True, content=True)
    )
    rmap = resolve_chains(extract_redirects(redirect_pages))
    pwb.info(f"重定向表 {len(rmap)} 条（闭包解析后）")
    pages: list[pwb.page.BasePage] = list(gen)
    pwb.info(f"扫描 {len(pages)} 页")
    skip_prefixes = build_skip_prefixes(site)
    fixed_pages = fixed_links = 0
    for page in pages:
        if normalize(page.title()) in rmap:
            continue  # 重定向页自身不碰（#REDIRECT 行归 redirect-do）
        newtext, changes = rewrite_links(page.text, rmap, site, skip_prefixes)
        if not changes:
            continue
        for old, new in changes:
            pwb.info(f"{page.title()}: {old} -> {new}")
        fixed_pages += 1
        fixed_links += len(changes)
        if config.simulate:
            continue  # -s 干跑：改动已逐条打印；保存前检查权限会触发登录而被模拟层拦截
        page.text = newtext
        page.save(summary=SUMMARY, bot=True)
    pwb.info(f"改写 {fixed_pages} 页 / {fixed_links} 处链接")
