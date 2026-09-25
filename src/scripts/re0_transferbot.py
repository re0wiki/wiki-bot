"""把 en 主空间有、zh 主空间没有的页面批量搬运到 zh（高效版 transferbot）。

pywikibot 自带 transferbot（-lang:en -tolang:zh -start）逐页迭代 en 主空间
并逐页 targetpage.exists() 单独查询，~2500-4000 请求/轮、15-16 分钟
（2026-08-13 实测，见 docs/todo.md）。本脚本：
1. en/zh 主空间标题集各 500/批拉取（~30 请求）内存比对出缺失页；
2. 缺失页的 en 内容 50/批取回，剥除底部分类行（en 分类在 zh 必为红链，
   zh 分类由 Module:Init 按标题前缀自动打），按 fork 补丁同款格式加页首
   （{{Init}}{{To do}} + 来源链接 + [[Category:新搬运待整理]]）后创建；
3. 缺失但已被 zh 页面源码 [[en:X]] 链接覆盖的 en 页不搬内容——内容已由
   该 zh 页收录，改建「en 标题 → zh 目标页」的重定向（防 Game Canon 类
   重复搬运：zh 对应页在异名标题下时标题集比对发现不了）；
4. 创建前对缺失清单做一次 zh 侧批量复核，防比对间隙的竞争。

与原任务的边界一致：只覆盖 ns 0（原 -start 即主空间，fork 的 ns 8/828
排除分支用不到）；en 重定向不搬（原生成器不含重定向）；zh 同名重定向
视为已存在（原 exists() 语义）。
"""

import re

import pywikibot as pwb
from pywikibot import config, pagegenerators
from pywikibot.tools import first_upper

HEADER = "{{Init}}\n{{To do}}\n"
FOOTER_CATEGORY = "\n[[Category:新搬运待整理]]"

CAT_LINE_RE = re.compile(r"(?m)^\[\[Category:[^\n]*\]\]\n?")
EN_LINK_RE = re.compile(r"\[\[en:([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")


def normalize(title: str) -> str:
    """归一到 MediaWiki 规范标题（下划线转空格、首字母大写）。"""
    return first_upper(title.replace("_", " ").strip())


def strip_en_categories(en_text: str) -> str:
    """剥除 en 源码的分类行（en 分类在 zh 必为红链；zh 分类由 Init 自动打）。"""
    return CAT_LINE_RE.sub("", en_text)


def build_text(en_text: str, title: str) -> str:
    """fork 补丁同款：页首 {{Init}}{{To do}} + 原文 + 来源链接 + 待整理分类。"""
    return f"{HEADER}{strip_en_categories(en_text)}\n[[en:{title}]]{FOOTER_CATEGORY}"


def build_summary(title: str) -> str:
    """fork 补丁同款摘要（i18n transferbot-summary 的 zh 文案）。"""
    return f"自[[en:{title}]]搬运页面"


def build_redirect_summary(title: str, target: str) -> str:
    return f"[[en:{title}]]的内容已由[[{target}]]收录，建重定向"


def collect_covered(zh) -> dict[str, str]:
    """zh 正文页源码 [[en:X]] 覆盖图：en 标题（归一）→ zh 页面标题。

    重定向页携带的链接不算覆盖（属 audit_langlinks 的 redirect_with_link
    缺陷类，链接应已在最终目标页上）。
    """
    covered = {}
    gen = zh.allpages(namespace=0, filterredir=False)
    for p in pagegenerators.PreloadingGenerator(gen, groupsize=50):
        if m := EN_LINK_RE.search(p.text):
            covered[normalize(m.group(1))] = p.title()
    return covered


def recheck_missing(zh, titles: list[str]) -> list[str]:
    """竞争防护：创建前 zh 侧批量复核存在性（通常 1 次请求）。"""
    return [
        p["title"]
        for i in range(0, len(titles), 50)
        for p in zh.simple_request(
            action="query",
            prop="info",
            titles="|".join(titles[i : i + 50]),
            formatversion="2",
            format="json",
        ).submit()["query"]["pages"]
        if p.get("missing")
    ]


if __name__ == "__main__":
    pwb.handle_args()  # -always 等忽略：不询问；-s 走下方分支
    en = pwb.Site("en", "re0")
    zh = pwb.Site()
    en_titles = {
        normalize(p.title()) for p in en.allpages(namespace=0, filterredir=False)
    }
    zh_titles = {normalize(p.title()) for p in zh.allpages(namespace=0)}
    missing = sorted(en_titles - zh_titles)
    pwb.info(f"en {len(en_titles)} 页，zh {len(zh_titles)} 页，缺失 {len(missing)} 页")
    if missing:
        # zh [[en:X]] 覆盖图：缺失标题里已被覆盖的改建重定向，不搬内容
        covered = collect_covered(zh)
        still_missing = recheck_missing(zh, missing)
        to_redirect = [t for t in still_missing if t in covered]
        to_copy = [t for t in still_missing if t not in covered]
        pwb.info(f"搬运 {len(to_copy)} 页，建重定向 {len(to_redirect)} 页")
        for title in to_redirect:
            if config.simulate:
                pwb.info(f"将建重定向 {title} -> {covered[title]}")
                continue
            page = pwb.Page(zh, title)
            page.text = f"#REDIRECT [[{covered[title]}]]"
            page.save(summary=build_redirect_summary(title, covered[title]), bot=True)
            pwb.info(f"已建重定向 {title} -> {covered[title]}")
        # 批量取 en 内容（50/批）
        for i in range(0, len(to_copy), 50):
            data = en.simple_request(
                action="query",
                prop="revisions",
                rvprop="content",
                rvslots="main",
                titles="|".join(to_copy[i : i + 50]),
                formatversion="2",
                format="json",
            ).submit()
            for p in data["query"]["pages"]:
                title = p["title"]
                if "missing" in p:
                    pwb.warning(f"en 页 {title} 不存在（比对间隙被删？），跳过")
                    continue
                if config.simulate:
                    pwb.info(f"将搬运 {title}")
                    continue
                page = pwb.Page(zh, title)
                page.text = build_text(
                    p["revisions"][0]["slots"]["main"]["content"], title
                )
                page.save(summary=build_summary(title), bot=True)
                pwb.info(f"已搬运 {title}")
