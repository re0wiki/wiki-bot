"""实际显示红链审计：渲染 HTML 提取，绕过 Special:WantedPages 的探测污染。只读，匿名可达。

背景：Module:Init 的 tab() 对每个注册后缀做 mw.title.exists 探测、Tab 模板做
prev/next 探测、Init 的 category() 输出矩阵分类——存在性探测与 #ifexist 同源，
登记进 pagelinks/categorylinks，WantedPages 由此被「不显示」的探测目标填满
（实测 top-1000 中 946 探测子页 + 46 矩阵分类）。登记是缓存失效的设计需求，
Scribunto 无免登记探测 API，源头改不掉；且 querypage API 封顶 1000。

「实际显示的红链」的唯一权威是渲染后 HTML。Fandom 红链标记（SEO 防爬定制）：
<span class="new" title="目标（页面不存在）" data-uncrawlable-url="base64…">文本</span>
——不是 <a>、没有 href；旧 parser cache 路径下亦可能出现 <a class="new"> 与
<a class="newcategory">（页脚红分类），故 class 与标签名两种形态都覆盖。

做法：内容命名空间（0/4/10/14）非重定向页逐页 action=parse&prop=text|categorieshtml，
按红链目标聚合显示位置，正文红链与页脚分类红链分开统计。输出
logs/redlinks_audit.json + logs/redlinks_audit.md。
全量约 2800 次 parse 请求，~25 分钟；解析失败的页非零退出并重跑即可。

注意：分类页（ns14）的 {{Tab/Content}} 折叠导航表裸链全量前缀×后缀矩阵分类，
未建页的会作为正文红链出现——设计内行为，是否处理人工裁决。
"""

import json
import re
from collections import defaultdict
from datetime import UTC, datetime
from html import unescape
from pathlib import Path

from tqdm import tqdm

import pywikibot

RED_TAG = re.compile(r'<(?:a|span)\b[^>]*class="[^"]*\bnew(?:category)?\b[^"]*"[^>]*>')
TITLE_ATTR = re.compile(r'title="([^"]*)"')
RED_SUFFIX = "（页面不存在）"

OUT_JSON = "logs/redlinks_audit.json"
OUT_MD = "logs/redlinks_audit.md"


def red_targets(html: str) -> set[str]:
    """渲染 HTML 中的红链目标集（title 属性，剥「（页面不存在）」后缀）。"""
    out = set()
    for tag in RED_TAG.findall(html):
        m = TITLE_ATTR.search(tag)
        if not m:
            continue
        t = unescape(m.group(1))
        out.add(t.removesuffix(RED_SUFFIX))
    return out


NAMESPACES = (0, 4, 10, 14)  # 主 / Project / Template / Category


def ns_titles(site) -> list[str]:
    """内容命名空间非重定向页标题全集（list=allpages 分页，匿名上限 500/批）。"""
    titles = []
    for ns in NAMESPACES:
        cont = {}
        while True:
            data = site.simple_request(
                action="query",
                list="allpages",
                apnamespace=str(ns),
                apfilterredir="nonredirects",
                aplimit="max",
                formatversion="2",
                **cont,
            ).submit()
            titles += [p["title"] for p in data["query"]["allpages"]]
            if "continue" not in data:
                break
            cont = data["continue"]
    return titles


def fmt_pages(pages: set[str]) -> str:
    ordered = sorted(pages)
    shown = "、".join(f"`{p}`" for p in ordered[:10])
    return shown + (f" 等 {len(ordered)} 页" if len(ordered) > 10 else "")


def main():
    site = pywikibot.Site("zh", "re0")
    titles = ns_titles(site)
    print(
        f"内容命名空间 {NAMESPACES} 非重定向页 {len(titles)}，逐页解析渲染 HTML",
        flush=True,
    )

    body: dict[str, set[str]] = defaultdict(set)  # 正文红链目标 -> 显示它的页面
    footer: dict[str, set[str]] = defaultdict(set)  # 页脚分类红链目标 -> 页面
    failed = []
    for title in tqdm(titles, desc="parse"):
        try:
            data = site.simple_request(
                action="parse",
                page=title,
                prop="text|categorieshtml",
                formatversion="2",
            ).submit()
            parsed = data["parse"]
        except (pywikibot.exceptions.Error, KeyError) as e:
            failed.append(f"{title} ({e!r})")
            continue
        for t in red_targets(parsed.get("text", "")):
            body[t].add(title)
        for t in red_targets(parsed.get("categorieshtml", "")):
            footer[t].add(title)

    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    result = {
        "generated_at": ts,
        "pages_scanned": len(titles),
        "pages_failed": failed,
        "body_redlinks": {t: sorted(ps) for t, ps in sorted(body.items())},
        "footer_redcats": {t: sorted(ps) for t, ps in sorted(footer.items())},
    }
    for out in (OUT_JSON, OUT_MD):
        Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    def section(items: dict[str, set[str]]) -> list[str]:
        lines = []
        for t, ps in sorted(items.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            lines.append(f"- `{t}` ← {fmt_pages(ps)}")
        return lines or ["（无）"]

    md = "\n".join(
        [
            f"# 实际显示红链审计（{ts}）",
            "",
            f"扫描命名空间 {NAMESPACES} 非重定向页 {len(titles)}，解析失败 {len(failed)}。",
            "数据源是渲染后 HTML 的红链元素，不含 Init/Tab 存在性探测目标。",
            "",
            f"## 正文红链（{len(body)} 个目标）",
            "",
            *section(body),
            "",
            f"## 页脚分类红链（{len(footer)} 个目标）",
            "",
            *section(footer),
            "",
        ]
    )
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"\n正文红链 {len(body)} 个目标，页脚分类红链 {len(footer)} 个目标")
    print(f"报告: {OUT_MD}  数据: {OUT_JSON}")
    if failed:
        print(f"解析失败 {len(failed)} 页（报告不完整，重跑）: {failed[:10]}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
