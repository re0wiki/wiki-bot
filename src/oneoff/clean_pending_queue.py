"""新搬运待整理队列一次性清理（2026-09 存量）。

- 红链分类删除：en 搬运带入的分类在 zh 全为红链（zh 分类由 Module:Init 按标题
  前缀自动打；未来搬运由 re0_transferbot 剥分类行根治，本脚本清存量）。分类存在性
  经 API 批量复核，[[Category:新搬运待整理]] 本身保留。
- Filore Camp：en 成员 navbox 表格 {{Filore Camp}} → zh 成员列表。成员取自
  en:Template:Filore Camp 的 CharMug* 调用（Filore/Heinkel/Tiga/Sakura），
  链接目标硬编码为对应 zh 角色页，运行前逐页验证存在性，缺失即响亮中止。

用法：uv run python src/oneoff/clean_pending_queue.py        # 实际写入
      uv run python src/oneoff/clean_pending_queue.py -s       # 干跑
"""

import re
import sys

import pywikibot as pwb
from pywikibot import pagegenerators

SIMULATE = "-s" in sys.argv or "--simulate" in sys.argv

CAT_RE = re.compile(r"(?m)^\[\[Category:([^\]|]+)(?:\|[^\]]*)?\]\]\n?")
KEEP_CATS = {"新搬运待整理"}

# en:Template:Filore Camp 的 CharMug* 成员（en 侧固定模板，无参）→ zh 角色页
FILORE_MEMBERS = [
    "角色:菲尔欧蕾·卢克尼卡",  # Filore Lugunica
    "角色:亨克尔·阿斯特雷亚",  # Heinkel Astrea
    "角色:狄加·拉雷恩",  # Tiga Rauleon
    "角色:莎克拉·艾雷梅特",  # Sakura Element
]


def verified_members(zh) -> str:
    """成员列表 wikitext；目标页逐页验证存在性，缺失响亮中止。"""
    for title in FILORE_MEMBERS:
        if not pwb.Page(zh, title).exists():
            raise RuntimeError(f"{title} 不存在，成员列表目标无法确认")
    return "\n".join(f"* [[{t}]]" for t in FILORE_MEMBERS)


def main() -> None:
    zh = pwb.Site("zh", "re0")
    cat = pwb.Category(zh, "Category:新搬运待整理")
    pages = list(pagegenerators.PreloadingGenerator(cat.articles(), groupsize=50))
    print(f"队列 {len(pages)} 页")

    # 1. 收集全部手写分类并批量复核存在性
    all_cats = sorted(
        {m.group(1).strip() for p in pages for m in CAT_RE.finditer(p.text)} - KEEP_CATS
    )
    missing_cats = set()
    for i in range(0, len(all_cats), 50):
        data = zh.simple_request(
            action="query",
            prop="info",
            titles="|".join(f"Category:{c}" for c in all_cats[i : i + 50]),
            formatversion="2",
            format="json",
        ).submit()
        for p in data["query"]["pages"]:
            if p.get("missing"):
                missing_cats.add(p["title"].split(":", 1)[1])
    print(
        f"手写分类 {len(all_cats)} 个，红链 {len(missing_cats)} 个：{sorted(missing_cats)}"
    )

    # 2. Filore Camp 成员列表（目标页先验证存在性）
    filore_list = verified_members(zh)

    # 3. 逐页应用
    for page in pages:
        old = page.text
        new = CAT_RE.sub(
            lambda m: "" if m.group(1).strip() in missing_cats else m.group(0), old
        )
        if page.title() == "Filore Camp" and "{{Filore Camp}}" in new:
            new = new.replace("{{Filore Camp}}", filore_list)
        if new == old:
            continue
        if SIMULATE:
            removed = len(CAT_RE.findall(old)) - len(CAT_RE.findall(new))
            print(
                f"[SIMULATE] {page.title()}：删分类 {removed} 处"
                + ("，Filore Camp navbox 改列表" if "{{Filore Camp}}" in old else "")
            )
            continue
        summary = "清理 en 搬运残留：移除红链分类"
        if "{{Filore Camp}}" in old:
            summary += "；Filore Camp 成员 navbox 改列表"
        page.text = new
        page.save(summary=summary, bot=True)
        print(f"已清理 {page.title()}")


if __name__ == "__main__":
    main()
