"""只读审计：Tab/* 子页链接的作品页 vs 实际携带该 tab 调用的页面，找失配。

对每个 Tab/X：
- 从其 wikitext 提取所有 wikilink 目标（主空间作品页）
- 从 logs/template_usage_full_2026-07-28.json 取实际调用 {{Tab/X}} 的页面集
- 失配 = 链接了但未携带（缺失）；反向 = 携带了但未链接（异常）
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
report = {}
for name in tabs:
    full = name  # allpages 返回已含 Tab/ 前缀
    text = pywikibot.Page(site, f"Template:{full}").text
    assert text, f"{full} 取不到内容"
    links = set()
    for m in LINK_RE.finditer(text):
        t = m.group(1).strip()
        if t.startswith(("Category:", "File:", ":")):
            continue
        links.add(t)
    carriers = set(usage.get(full, []))
    missing, redlink = [], []
    for t in sorted(links):
        if t in carriers:
            continue
        p = pywikibot.Page(site, t)
        if not p.exists():
            redlink.append(t)
        elif p.isRedirectPage():
            # 重定向页不挂 tab，看目标页
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
