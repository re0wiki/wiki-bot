"""一次性归一角色/术语主页面的 History 章节译名（2026-09 决议）。

角色: 主页面 == 背景/历史/角色经历/History == → == 经历 ==
术语: 主页面 == 背景/History/经历 ==          → == 历史 ==

只处理主页面（标题不含 /），精确匹配二级标题整行，且要求 en 对应源页面
确有 ==History== 章节（防止把译自 en ==Background== 的事件页「背景」误归一）。
无 en 链接 / en 无 History / 目标章节名已存在的页一律跳过并列报告。
站立规则 fix:heading_char/heading_term 覆盖今后的 History 原文残留；
本脚本处理既有中文异译，不加长期规则。

用法: uv run python src/oneoff/normalize_history_headings.py [-s]
"""

import re
import sys
from collections import defaultdict

import pywikibot
from pywikibot import pagegenerators

SIMULATE = "-s" in sys.argv

# 前缀 → (目标章节名, 可归一的旧写法)
PLAN = {
    "角色": ("经历", ("背景", "历史", "角色经历", "History")),
    "术语": ("历史", ("背景", "History", "经历")),
}

H2 = re.compile(r"^==\s*([^=\n]+?)\s*==\s*$", re.MULTILINE)
EN_LINK = re.compile(r"\[\[en:([^\]|]+)", re.IGNORECASE)
HIST_EN = re.compile(r"^==\s*History\s*==\s*$", re.MULTILINE | re.IGNORECASE)


def main():
    zh = pywikibot.Site("zh", "re0")
    en = pywikibot.Site("en", "re0")
    if not SIMULATE:
        zh.login()
        assert zh.user() == "IchiSanNi"

    # 第一阶段：扫 zh 主空间，收集候选
    cands = {}  # title -> (hits, en_title, zh_text)
    gen = pagegenerators.AllpagesPageGenerator(site=zh, namespace=0)
    for page in pagegenerators.PreloadingGenerator(gen, groupsize=50):
        t = page.title()
        if ":" not in t or "/" in t:
            continue
        prefix = t.split(":", 1)[0]
        if prefix not in PLAN:
            continue
        try:
            text = page.text
        except Exception as e:  # noqa: BLE001 - 单页失败不阻断全站扫描，打印后跳过
            print(f"读取失败跳过: {page.title()}: {e}")
            continue
        if text.lstrip().startswith("#REDIRECT"):
            continue
        target, olds = PLAN[prefix]
        heads = [m.group(1).strip() for m in H2.finditer(text)]
        hits = [o for o in olds if o in heads]
        if not hits:
            continue
        m = EN_LINK.search(text)
        cands[t] = (hits, m.group(1).split("#")[0] if m else None, text)

    # 第二阶段：批量取 en 源校验 History 对应
    en_titles = sorted({v[1] for v in cands.values() if v[1]})
    en_hist = set()
    for i in range(0, len(en_titles), 50):
        gen = iter([pywikibot.Page(en, t) for t in en_titles[i : i + 50]])
        for p in pagegenerators.PreloadingGenerator(gen, groupsize=50):
            try:
                if p.exists() and HIST_EN.search(p.text):
                    en_hist.add(p.title())
            except Exception as e:  # noqa: BLE001 - 单页失败不阻断批量校验，打印后跳过
                print(f"en 读取失败跳过: {p.title()}: {e}")
                continue

    # 第三阶段：归一或归入报告
    stats = defaultdict(list)
    for t, (hits, en_title, text) in sorted(cands.items()):
        target = PLAN[t.split(":", 1)[0]][0]
        if not en_title:
            stats["no_en_link"].append((t, hits))
            continue
        if en_title not in en_hist:
            stats["no_en_history"].append((t, hits, en_title))
            continue
        heads = [m.group(1).strip() for m in H2.finditer(text)]
        if target in heads:
            stats["collision"].append((t, hits))
            continue
        new = text
        for o in hits:
            new = re.sub(
                rf"^==\s*{re.escape(o)}\s*==\s*$",
                f"== {target} ==",
                new,
                flags=re.MULTILINE,
            )
        assert new != text
        stats["rename"].append((t, hits))
        if not SIMULATE:
            page = pywikibot.Page(zh, t)
            page.text = new
            page.save(
                f"章节名归一：{'/'.join(hits)} → {target}（History 译名决议）",
                bot=True,
            )

    print(f"\n=== {'DRY RUN ' if SIMULATE else ''}结果 ===")
    print(f"归一 {len(stats['rename'])} 页:")
    for t, hits in stats["rename"]:
        print(f"  {t}: {'/'.join(hits)}")
    print(f"跳过-无 en 链接 {len(stats['no_en_link'])} 页:")
    for t, hits in stats["no_en_link"]:
        print(f"  {t}: {'/'.join(hits)}")
    print(f"跳过-en 无 History 章节 {len(stats['no_en_history'])} 页:")
    for t, hits, e in stats["no_en_history"]:
        print(f"  {t} (en: {e}): {'/'.join(hits)}")
    print(f"跳过-撞名 {len(stats['collision'])} 页（需人工合并）:")
    for t, hits in stats["collision"]:
        print(f"  {t}: 已有目标章节 + {'/'.join(hits)}")


if __name__ == "__main__":
    main()
