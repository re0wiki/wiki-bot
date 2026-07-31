"""检查 Template:Init 的引用覆盖：主空间非重定向条目数 vs Init 引用数。

只读。输出：总数对比 + 未引用 Init 的主空间条目清单。
"""

import os

os.environ.pop("PYTHONPATH", None)

from pywikibot.data import api

import pywikibot

site = pywikibot.Site("zh", "re0")

# ── 1. Template:Init 的重定向别名（引用别名页不会计入 Init 的 embeddedin） ──
print("== Template:Init 的重定向别名 ==")
bl = api.QueryGenerator(
    site=site,
    action="query",
    list="backlinks",
    bltitle="Template:Init",
    blfilterredir="redirects",
    bllimit="max",
)
aliases = [p["title"] for p in bl]
print(aliases or "（无）")


# ── 2. 主空间全部非重定向页面 ───────────────────────────────
def all_mainspace(filterredir):
    gen = api.QueryGenerator(
        site=site,
        action="query",
        generator="allpages",
        gapnamespace=0,
        gapfilterredir=filterredir,
        gaplimit="max",
    )
    return [p["title"] for p in gen]


articles = all_mainspace("nonredirects")
redirects = all_mainspace("redirects")
print(f"\n主空间非重定向页面: {len(articles)}")
print(f"主空间重定向页面:   {len(redirects)}")
print(f"主空间总页面:       {len(articles) + len(redirects)}")

# ── 3. Template:Init 的引用（embeddedin，不限 namespace） ──
gen = api.QueryGenerator(
    site=site,
    action="query",
    generator="embeddedin",
    geititle="Template:Init",
    geilimit="max",
)
init_pages: dict[int, list[str]] = {}
for p in gen:
    ns = p["ns"]
    init_pages.setdefault(ns, [])
    init_pages[ns].append(p["title"])

print("\n== Template:Init 引用分布（按 namespace） ==")
for ns in sorted(init_pages):
    print(f"ns={ns}: {len(init_pages[ns])}")

# 别名引用也统计一下
alias_users: dict[str, list[str]] = {}
for alias in aliases:
    g = api.QueryGenerator(
        site=site,
        action="query",
        generator="embeddedin",
        geititle=alias,
        geilimit="max",
    )
    users = [p["title"] for p in g]
    if users:
        alias_users[alias] = users
print(f"\n== 别名引用 ==\n{alias_users or '（无）'}")

# ── 4. 主空间未引用 Init 的条目 ─────────────────────────────
used = set(init_pages.get(0, []))
for users in alias_users.values():
    # 只统计主空间使用者
    used |= {
        t
        for t in users
        if ":" not in t
        or t.split(":", 1)[0]
        not in {
            "Template",
            "Module",
            "MediaWiki",
            "Category",
            "File",
            "Help",
            "Project",
            "User",
            "MediaWiki talk",
            "Special",
        }
    }
missing = sorted(set(articles) - used)
print(f"\n主空间引用 Init（含别名）: {len(used & set(articles))}")
print(f"主空间未引用 Init 的条目: {len(missing)}")
for t in missing:
    print(f"  - {t}")
