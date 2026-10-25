"""一次性：图库标签存量清理（para 误伤残留 + en 弃用旧名 + 单次出现标签）。

en 在用 ≥2 处的标签已进 user-fixes.py gallery fix 常驻表，本脚本只处理不进表
的部分。只改写 tabber 标签行（`|-| X =` 与 tabber 块内裸 `X =` 行），逐标签计数
并与普查基线对账。

用法：`uv run python src/oneoff/gallery_label_cleanup.py`（`-s` 干跑只打印不写）。
"""

import collections
import re
import sys

import pywikibot
from pywikibot import pagegenerators

# 一次性映射（依据 2026-10 图库标签普查 + en 对照）
REPLACE = {
    # fix:para 误伤残留：|-| Light Novel = / |-| Manga = 被打成小写参数名
    "novel": "小说",
    "comic": "漫画",
    # en 已改名的旧标签
    "Shinmeitan": "剑鬼恋歌",  # en 现名 Love Song
    "Daigoshou": "第5章",  # en 现名 Arc 5
    "Daininshou": "第2章",  # en 仅剩 Volcanica/Image Gallery 1 处
    "The Frozen Bond OVA": "OVA2",  # Bonds of Ice 别名
    # 单次出现的游戏内部分类标签
    "Character Illustrations": "角色插画",
    "Character illustration cards": "角色插画卡",
    "Memorias": "回忆",
    "Characters": "角色卡",
    # 术语:魔法/图库 元素 tab
    "Fire": "火",
    "Water": "水",
    "Wind": "风",
    "Earth": "土",
    "Yin": "阴",
    "Yang": "阳",
    "Spirit": "精灵",
}

# 普查基线（对账用，允许漂移只告警）
EXPECTED = {
    "novel": 23,
    "comic": 10,
    "Shinmeitan": 9,
    "Daigoshou": 5,
    "Daininshou": 2,
    "The Frozen Bond OVA": 1,
    "Character Illustrations": 1,
    "Character illustration cards": 1,
    "Memorias": 1,
    "Characters": 1,
    "Fire": 1,
    "Water": 1,
    "Wind": 1,
    "Earth": 1,
    "Yin": 1,
    "Yang": 1,
    "Spirit": 1,
}

SIMULATE = "-s" in sys.argv or "--simulate" in sys.argv


def replace_pipe_label(line, counts):
    m = re.match(r"^(\s*\|-\|\s*)(.*?)(\s*=.*)$", line)
    if m and m.group(2) in REPLACE:
        counts[m.group(2)] += 1
        line = m.group(1) + REPLACE[m.group(2)] + m.group(3)
    return line


def replace_bare_label(line, counts):
    m = re.match(r"^(\s*)([^=]*?)(\s*=.*)$", line)
    if not m:
        return line
    label = m.group(2).strip()
    if label in REPLACE and not any(c in label for c in "<>{}[]|"):
        counts[label] += 1
        line = m.group(1) + REPLACE[label] + m.group(3)
    return line


def process_line(line, expect_label, counts):
    s = line.strip()
    if "<tabber" in s or "#tag:tabber" in s:
        return line, True
    if s.startswith("|-|"):
        return replace_pipe_label(line, counts), False
    if s.startswith("{{!}}-{{!}}"):
        return line, True
    if expect_label and "=" in s and not s.startswith(("<", "{", "|")):
        return replace_bare_label(line, counts), False
    return line, expect_label


def process_text(text: str):
    """逐行重写 tabber 标签；返回 (新文本, 计数器)。"""
    counts = collections.Counter()
    out = []
    expect_label = False  # 下一普通行是 tabber 块内裸标签行
    for line in text.split("\n"):
        line, expect_label = process_line(line, expect_label, counts)
        out.append(line)
    return "\n".join(out), counts


def process_pages(pages):
    total = collections.Counter()
    edited = 0
    for page in pagegenerators.PreloadingGenerator(pages, groupsize=50):
        try:
            text = page.text
        except pywikibot.exceptions.Error as e:
            print(f"跳过 {page.title()}: {e}")
            continue
        new, counts = process_text(text)
        if new == text:
            continue
        edited += 1
        total.update(counts)
        diff = ", ".join(f"{k}→{REPLACE[k]}×{v}" for k, v in sorted(counts.items()))
        print(f"{'[干跑] ' if SIMULATE else ''}{page.title()}: {diff}")
        if not SIMULATE:
            page.text = new
            page.save(
                summary="图库标签归一：一次性清理存量（para 旧伤/en 弃用旧名/单次标签）",
                bot=True,
            )
    return total, edited


def print_report(total, edited):
    print(
        f"\n{'[干跑] ' if SIMULATE else ''}编辑页数: {edited}，替换总数: {sum(total.values())}"
    )
    print("\n对账（实际 vs 普查基线）:")
    for label in REPLACE:
        actual, expected = total.get(label, 0), EXPECTED[label]
        mark = "" if actual == expected else "  ⚠ 漂移"
        print(f"  {label}: {actual} vs {expected}{mark}")


def main():
    site = pywikibot.Site("zh", "re0")
    if not SIMULATE:
        site.login()
        assert site.user() == "IchiSanNi"
    cat = pywikibot.Category(site, "Category:图库")
    pages = pagegenerators.CategorizedPageGenerator(cat, recurse=True)
    total, edited = process_pages(pages)
    print_report(total, edited)


if __name__ == "__main__":
    main()
