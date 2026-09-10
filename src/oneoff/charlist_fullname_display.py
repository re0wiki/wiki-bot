"""角色列表里显示文本只有名的链接补全为全名（2026-09-10 一次性）。

规则：行首为 ``*`` 的列表行内，``[[角色:全名|名]]``——显示文本恰为全名按
``·`` 分段后的某一单段、且不等于全名——显示文本补全为全名（链接目标不变）。
「全名」= 链接目标去掉 ``#锚点`` 与尾部 `` (消歧)`` 括号。
非列表行不动；显示文本不是单段的（如 ``菜月昴`` 之于 ``菜月·昴``、
带括注的写法）不动；``角色:次要角色#人名`` 的锚点式链接不动。

用法（仓库根目录）：
    uv run python src/oneoff/charlist_fullname_display.py        # 干跑
    uv run python src/oneoff/charlist_fullname_display.py --apply
"""

import argparse
import re

import pywikibot
from pywikibot.data import api

# [[角色:目标|显示文本]]
LINK_RE = re.compile(r"\[\[角色:(?P<target>[^|\]]+)\|(?P<display>[^|\]]+)\]\]")
LIST_LINE_RE = re.compile(r"^\*+")
# 尾部「 (消歧)」括号，如 琉兹·梅埃尔 (复制体)
DISAMBIG_RE = re.compile(r"\s+\([^()]*\)$")

SUMMARY = "角色列表显示文本补全为全名"


def full_name(target: str) -> str:
    """链接目标 → 全名：去 #锚点、去尾部 (消歧) 括号。"""
    name = target.split("#", 1)[0]
    return DISAMBIG_RE.sub("", name)


def expand_line(line: str) -> tuple[str, int]:
    """列表行内把单段显示文本补全为全名；非列表行原样返回。"""
    if not LIST_LINE_RE.match(line):
        return line, 0

    hits = 0

    def repl(m: re.Match[str]) -> str:
        nonlocal hits
        target, display = m.group("target"), m.group("display")
        name = full_name(target)
        if display != name and display in name.split("·"):
            hits += 1
            return f"[[角色:{target}|{name}]]"
        return m.group(0)

    return LINK_RE.sub(repl, line), hits


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="实际写入（默认干跑）")
    args = ap.parse_args()

    site = pywikibot.Site("zh", "re0")
    if args.apply:
        site.login()
        assert site.user() == "IchiSanNi"

    # 全量取主空间源码（两阶段配方的库内封装，见 docs/wiki-access.md）
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
    pages: dict[str, str] = {}
    for p in gen:
        revs = p.get("revisions")
        if not revs:
            continue
        pages[p["title"]] = revs[0]["slots"]["main"]["content"]
    print(f"pages fetched: {len(pages)}")
    # 完整性兜底：主空间页数不应少于 siteinfo 统计的 articles 数
    stats = site.simple_request(
        action="query",
        meta="siteinfo",
        siprop="statistics",
        format="json",
        formatversion="2",
    ).submit()
    articles = stats["query"]["statistics"]["articles"]
    assert len(pages) >= articles, (
        f"只抓到 {len(pages)} 页，少于 articles={articles}，分页被截断"
    )

    changed_pages = 0
    changed_links = 0
    for title in sorted(pages):
        text = pages[title]
        new_lines = []
        page_hits = 0
        for line in text.split("\n"):
            new_line, n = expand_line(line)
            if n:
                page_hits += n
                print(f"  {title}:\n    - {line.strip()}\n    + {new_line.strip()}")
            new_lines.append(new_line)
        if not page_hits:
            continue
        changed_pages += 1
        changed_links += page_hits
        if args.apply:
            page = pywikibot.Page(site, title)
            page.text = "\n".join(new_lines)
            page.save(summary=SUMMARY, bot=True)
            print(f"  已保存 {title}")
    print(
        f"{'已修改' if args.apply else '干跑，将修改'} "
        f"{changed_pages} 页 / {changed_links} 处链接"
    )


if __name__ == "__main__":
    main()
