"""只读审计：Tab/* 子页链接的作品页 vs 实际携带该 tab 调用的页面，找失配。

判例（2026-07-28 确立的挂载惯例，见 docs/templates.md「Tab 挂载惯例」）：
- 多块 tab 的块 0 是跨章/跨季导航块，其链接页不算应挂（每页只挂自己系列的 tab）
- Module:/MediaWiki: 页不渲染 wikitext，tab 挂在其 /doc 页——链接与携带都不算失配
- 链接标题经 pywikibot 归一化（[[:分类:X]]/[[分类:X]] -> Category:X），Category 页正常参与比对
- tab 内 <!-- --> 注释的链接不算应挂
- 红链仅报告（未搬运内容，不建页）
输出 logs/tab_placement_audit_2026-07-28.json + 控制台摘要。
"""

import json
import re

import pywikibot

site = pywikibot.Site("zh", "re0")

with open("logs/template_usage_full_2026-07-28.json", encoding="utf-8") as f:
    usage = json.load(f)

tabs = sorted(
    str(p.title(with_ns=False)) for p in site.allpages(prefix="Tab/", namespace=10)
)
print(f"Tab 子页: {len(tabs)}")

LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
BLOCK_RE = re.compile(r"\{\{Tab.*?\}\}", flags=re.DOTALL)
report = {}
for full in tabs:
    text = pywikibot.Page(site, f"Template:{full}").text
    assert text, f"{full} 取不到内容"
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"<noinclude>.*?</noinclude>", "", text, flags=re.DOTALL)
    blocks = BLOCK_RE.findall(text)
    if len(blocks) > 1:  # 多块 tab 块 0 = 导航块
        text = text.replace(blocks[0], "", 1)
    links = set()
    for m in LINK_RE.finditer(
        text
    ):  # 块外内容也算（Tab/Content 的分类矩阵是 wikitable）
        raw = m.group(1).strip()
        # 归一化：[[:分类:X]]/[[Category:X]]/[[分类:X]] -> Category:X
        t = pywikibot.Page(site, raw).title()
        if t.startswith(("File:", "Module:", "MediaWiki:")):
            continue
        # 裸 [[Category:X]] 是归类赋值（如 includeonly 注入），不是导航链接；
        # 只有 [[:分类:X]] 冒号内联形式才算（Tab/Content 矩阵）
        if t.startswith("Category:") and not raw.startswith(":"):
            continue
        links.add(t)
    carriers = {c for c in usage.get(full, []) if not c.endswith("/doc")}
    missing, redlink = [], []
    for t in sorted(links):
        if t in carriers:
            continue
        p = pywikibot.Page(site, t)
        if not p.exists():
            redlink.append(t)
        elif p.isRedirectPage():
            tgt = p.getRedirectTarget().title()
            if tgt not in carriers:
                missing.append(f"{t} (-> {tgt})")
        else:
            missing.append(t)
    extra = sorted(carriers - links)
    if missing or redlink or extra:
        report[full] = {"missing": missing, "redlink": redlink, "extra": extra}

with open("logs/tab_placement_audit_2026-07-28.json", "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=1)

bad = len(report)
print(f"失配 Tab: {bad}/{len(tabs)}")
for full, r in report.items():
    print(
        f"\n{full}: 缺 {len(r['missing'])} 红链 {len(r['redlink'])} 反向 {len(r['extra'])}"
    )
    for t in r["missing"][:5]:
        print(f"  缺: {t}")
    for t in r["redlink"][:3]:
        print(f"  红链: {t}")
    for t in r["extra"][:3]:
        print(f"  反向: {t}")
