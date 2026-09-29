"""「注释与外部链接」合并节一次性拆分（2026-09 存量）。

合并节名是 noreferences 旧首选节名与 fix:heading 旧 References 映射的历史产物。
2026-09-25 用户裁决拆分：noreferences 首选节名已改「注释」（pwb fork 补丁）、
fix:heading 的 References 映射已改「注释」，新合并节不会再产生——故拆分为
一次性操作，不进循环任务（fix 表不保留永不命中的死规则）。

按节内容改名：纯注释（含 <references>）→ 注释；纯外部链接（含 http(s)://）→
外部链接；两者皆有（混合）跳过留人工。节体范围的判定与改名只动标题行，节体
原样保留。

实测分布（2026-09-25 干跑）：249 页改名（247 纯注释 → 注释、2 纯外部链接 →
外部链接：小说:1卷、游戏:虚假的王选候补）、1 页混合跳过（游戏:INFINITY）。

用法：uv run python src/oneoff/split_merged_note_sections.py        # 实际写入
      uv run python src/oneoff/split_merged_note_sections.py -s       # 干跑
"""

import re
import sys
from itertools import chain

import pywikibot as pwb
from pywikibot import pagegenerators

SIMULATE = "-s" in sys.argv or "--simulate" in sys.argv

# 节体止于下一标题行 / 表格起止行 / interwiki 或分类行 / 文末。
# 表格行也是边界：首页类表格排版页里「节」后面还挂着无关表格（含友情链接
# 的 http 链接），吞进来会把纯注释节误判成混合；interwiki 边界必须小写匹配
# （nocase 会把正文里的 [[File:...]] 行误当边界截断节体）。
SECTION_RE = re.compile(
    r"(?ms)^(==+ *)注释与外部链接( *==+[ \t]*\n)(.*?)(?=^=|^\{\||^\|\}|^\[\[(?:[a-z][a-z-]*|Category):|\Z)"
)
# 与 fix 表 generator_more 同范围：主/project/template/category/module/mediawiki
NAMESPACES = (0, 4, 10, 14, 828, 8)


def rename(m: re.Match) -> str:
    """合并节按内容改名；混合节原样返回（跳过）。"""
    body = m.group(3)
    has_links = bool(re.search(r"https?://", body))
    has_refs = "<references" in body
    if has_links and has_refs:
        return m.group(0)
    return m.group(1) + ("外部链接" if has_links else "注释") + m.group(2) + body


def main() -> None:
    zh = pwb.Site("zh", "re0")
    gen = chain.from_iterable(zh.allpages(namespace=ns) for ns in NAMESPACES)
    changed, skipped = 0, []
    for page in pagegenerators.PreloadingGenerator(gen, groupsize=50):
        if not SECTION_RE.search(page.text):
            continue
        new = SECTION_RE.sub(rename, page.text)
        if new == page.text:
            skipped.append(page.title())  # 混合节跳过
            continue
        changed += 1
        if SIMULATE:
            new_names = re.findall(r"(?m)^==+ *([^=\n]+?) *==+ *$", new)
            old_names = re.findall(r"(?m)^==+ *([^=\n]+?) *==+ *$", page.text)
            diff = [n for n in new_names if n not in old_names]
            print(f"[SIMULATE] {page.title()} -> {diff}")
            continue
        page.text = new
        page.save(summary="注释与外部链接合并节按内容拆分为 注释/外部链接", bot=True)
        print(f"已拆分 {page.title()}")
    print(f"共 {changed} 页改名，{len(skipped)} 页混合跳过：{skipped}")


if __name__ == "__main__":
    main()
