"""只读：列出引用数 0 和 1 的模板及用例（含别名交叉验证与调用上下文）。"""

import json
import re

import pywikibot

site = pywikibot.Site("zh", "re0")
with open("logs/template_usage_recheck_2026-07-28.json", encoding="utf-8") as f:
    data = json.load(f)

DELETED = {
    "StructuredQuote",
    "Infobox",
    "Infobox album",
    "Infobox episode",
    "Infobox item",
    "Infobox location",
    "Infobox quest",
    "Tocright",
}

zero = sorted(t for t, u in data.items() if not u and t not in DELETED)
one = sorted((t, u[0]) for t, u in data.items() if len(u) == 1 and t not in DELETED)


def info(t):
    p = pywikibot.Page(site, f"Template:{t}")
    rd = p.isRedirectPage()
    target = p.getRedirectTarget().title(with_ns=False) if rd else None
    # embeddedin 把重定向别名用量归到目标页；排除自身与自身子页
    n_emb = sum(
        1
        for r in p.embeddedin()
        if r.title() != f"Template:{t}" and not r.title().startswith(f"Template:{t}/")
    )
    return rd, target, n_emb


print("===== 引用数 0 =====")
for t in zero:
    rd, target, n_emb = info(t)
    note = f"重定向->{target}" if rd else ""
    print(f"{t}\t{note}\tembeddedin={n_emb}")

print("\n===== 引用数 1 =====")
for t, user in one:
    rd, target, n_emb = info(t)
    note = f"重定向->{target}" if rd else ""
    print(f"{t}\t{note}\tembeddedin={n_emb}\t用于: {user}")

print("\n===== 引用数 1 的调用上下文 =====")
for t, user in one:
    if t.startswith("Re:Zero"):
        continue
    try:
        text = pywikibot.Page(site, user).text
    except Exception as e:  # noqa: BLE001 - 一次性审计脚本，任何页面读取失败都跳过
        print(f"--- {t} @ {user}: 读取失败 {e}")
        continue
    pat = re.compile(
        r"\{\{\s*(?:subst:\s*)?" + re.escape(t).replace(r"\ ", r"[ _]") + r"\s*[|}<]",
        re.IGNORECASE,
    )
    m = pat.search(text)
    if not m:
        print(f"--- {t} @ {user}: （页面上未找到本名调用，可能是别名或经由其他模板）")
        continue
    start = max(0, m.start() - 80)
    ctx = text[start : m.end() + 120].replace("\n", "⏎")
    print(f"--- {t} @ {user}:\n…{ctx}…")
