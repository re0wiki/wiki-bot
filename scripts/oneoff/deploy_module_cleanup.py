"""批量部署 Module 卫生修复（用户已批准）：

- Title / AutoTab / Auto ruby / Infobox book / NoteTA / Utils 6 个模块换源码
- 删除 Module:Set 与其 /doc（孤儿模块）
- 部署前后 parse 对比渲染等价（角色:菜月·昴、Infobox book 引用页、NoteTA 引用页、R 调用片段）

只写 zh 站，手动编辑（无 bot flag）。幂等：内容相同则跳过保存。
"""

import os
import re

os.environ.pop("PYTHONPATH", None)

import pywikibot
from pywikibot.data import api

site = pywikibot.Site("zh", "re0")

MODULES = ["Title", "AutoTab", "Auto ruby", "Infobox book", "NoteTA", "Utils"]


def parse_html(**params):
    req = api.Request(
        site=site, parameters={"action": "parse", "prop": "text", **params}
    )
    html = req.submit()["parse"]["text"]["*"]
    html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
    # PortableInfobox 的 tab id 带每次 parse 随机的哈希后缀，归一化后再比较
    return re.sub(r"pi-tab(panel)?-[0-9a-f]+-", r"pi-tab\1-", html)


def snapshot():
    """采集对照渲染（模块编辑前）。"""
    snaps = {}

    # Init 链（Title/AutoTab/Utils）
    snaps["page:角色:菜月·昴"] = parse_html(page="角色:菜月·昴")

    # Infobox book：取第一个主空间引用页
    tpl = pywikibot.Page(site, "Template:Infobox book")
    book_page = next(iter(tpl.embeddedin(namespaces=0, total=1)))
    snaps[f"page:{book_page.title()}"] = parse_html(page=book_page.title())

    # NoteTA：全部引用页
    mod = pywikibot.Page(site, "Module:NoteTA")
    for p in mod.embeddedin(total=10):
        snaps[f"page:{p.title()}"] = parse_html(page=p.title())

    # Auto ruby：模板调用片段（romaji 留空走自动转换）
    snaps["snippet:R"] = parse_html(
        text="{{R|菜月·昴||ナツキ・スバル|}}", contentmodel="wikitext"
    )

    return snaps


def check(snaps, label):
    fails = 0
    for key, before in snaps.items():
        kind, _, name = key.partition(":")
        after = (
            parse_html(page=name)
            if kind == "page"
            else parse_html(
                text="{{R|菜月·昴||ナツキ・スバル|}}", contentmodel="wikitext"
            )
        )
        err = "scribunto-error" in after or "Lua错误" in after
        same = after == before
        fails += err or not same
        print(
            f"{'OK ' if (same and not err) else 'FAIL'} [{label}] {key}: 渲染{'等价' if same else '有差异'}{'，有 Lua 错误！' if err else ''}"
        )
    return fails


# ── 前置断言 ──────────────────────────────────────────────
set_mod = pywikibot.Page(site, "Module:Set")
assert sum(1 for _ in set_mod.embeddedin(total=10)) == 0, "Module:Set 仍有引用"
for ns, name in [(828, "Module"), (10, "Template")]:
    gen = api.QueryGenerator(
        site=site,
        action="query",
        generator="allpages",
        gapnamespace=ns,
        gapprefix="CGroup",
        gaplimit="max",
    )
    assert sum(1 for _ in gen) == 0, f"{name}:CGroup 存在，NoteTA 简化前提不成立"

print("采集编辑前渲染快照...")
snaps = snapshot()
print(f"快照 {len(snaps)} 项\n")

# ── 应用编辑 ──────────────────────────────────────────────
site.login()
assert site.user() == "IchiSanNi"

SUMMARIES = {
    "Title": "删除调试日志（parse_title 的 mw.logObject）",
    "AutoTab": "删除调试日志；更新头部注释（存在性探测为必要开销，作为 Init 依赖保留）",
    "Auto ruby": "删除调试日志；参数加 nil 防御",
    "Infobox book": "卫生修复：函数 local 化、Module:Title 大小写、语言表有序化（日期并列时渲染确定）、删调试日志",
    "NoteTA": "移除 CGroup 死路径（本站无 CGroup 页面）、函数 local 化、清理移植残留注释",
    "Utils": "精简注释（去除 ChatGPT 问答实录）",
}

for m in MODULES:
    with open(f"logs/modules/new/{m}.lua", encoding="utf-8") as f:
        new_src = f.read()
    p = pywikibot.Page(site, "Module:" + m)
    if p.text.strip() == new_src.strip():
        print(f"跳过 Module:{m}（已是最新）")
        continue
    p.text = new_src
    p.save(summary=SUMMARIES[m])
    print(f"已保存 Module:{m}")

for t in ["Module:Set", "Module:Set/doc"]:
    p = pywikibot.Page(site, t)
    if p.exists():
        p.delete(
            reason="孤儿模块（embeddedin=0、无人 require），死代码清理", prompt=False
        )
        print(f"已删除 {t}")
    else:
        print(f"跳过 {t}（不存在）")

# ── 编辑后对比 ────────────────────────────────────────────
print("\n部署后渲染对比：")
fails = check(snaps, "after")
print(f"\n{'ALL CHECKS PASSED' if fails == 0 else f'{fails} 项异常'}")
