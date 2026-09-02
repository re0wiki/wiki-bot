"""审计全站指向维基百科非中文站的链接。

扫描 zh 站主空间全部页面源码，找出 ``[[wikipedia:...]]`` 链接，
按目标语言分组列出。只读，不写 wiki。

用法：uv run python src/tools/audit_wikipedia_links.py
"""

import re
from collections import defaultdict

import pywikibot
from pywikibot.data import api

# [[wikipedia:en:X|Y]] / [[wikipedia:X]]（裸写 = en）/ [[wikipedia:zh:X]]
LINK_RE = re.compile(r"\[\[wikipedia:(?P<body>[^\]|]*)(?:\|[^\]]*)?\]\]")


def scan() -> tuple[dict[str, dict[str, set[str]]], int]:
    """全量扫描主空间源码，返回 (语言 -> 目标 -> 页面集, 抓取页数)。"""
    site = pywikibot.Site("zh", "re0")
    hits: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    total = 0
    # QueryGenerator 由 pywikibot 内部处理 continue 分页——手搓分页遇到过
    # Fandom 某批响应缺 continue 导致 764/2206 页静默截断
    gen = api.QueryGenerator(
        site=site,
        parameters={
            "action": "query",
            "generator": "allpages",
            "gapnamespace": "0",
            "gaplimit": "500",
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "format": "json",
            "formatversion": "2",
        },
    )
    for p in gen:
        revs = p.get("revisions")
        if not revs:
            continue
        total += 1
        text = revs[0]["slots"]["main"]["content"]
        for m in LINK_RE.finditer(text):
            body = m.group("body")
            # 判断是否带语言前缀：en:/ja:/zh: 等
            lang, _, target = body.partition(":")
            if not (re.fullmatch(r"[a-z][a-z-]*", lang) and target):
                lang, target = "en", body  # 裸写默认 en.wikipedia
            hits[lang][target].add(p["title"])
    return hits, total


def main() -> None:
    hits, total = scan()
    print(f"pages fetched: {total}")
    # 完整性兜底：主空间页数不应少于 siteinfo 统计的 articles 数
    site = pywikibot.Site("zh", "re0")
    stats = site.simple_request(
        action="query",
        meta="siteinfo",
        siprop="statistics",
        format="json",
        formatversion="2",
    ).submit()
    articles = stats["query"]["statistics"]["articles"]
    assert total >= articles, f"只抓到 {total} 页，少于 articles={articles}，分页被截断"

    for lang in sorted(hits):
        print(f"== wikipedia:{lang} == ({len(hits[lang])} 个目标)")
        for target in sorted(hits[lang]):
            pages = sorted(hits[lang][target])
            print(f"  {target}  <- {', '.join(pages)}")


if __name__ == "__main__":
    main()
