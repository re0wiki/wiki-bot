"""第二轮剩余部分：character 摘 fallback + 5 个 /doc 参数名同步。

round2_remove_fallbacks.py 的前 8 个模板已保存，本脚本只做剩余部分。
"""

import os
import re

os.environ.pop("PYTHONPATH", None)

import pywikibot

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"


def edit(title: str, replacements: list[tuple[str, str, int]], summary: str) -> None:
    page = pywikibot.Page(site, title)
    text = page.text
    for pat, repl, n in replacements:
        text, cnt = re.subn(pat, repl, text)
        assert cnt == n, f"{title}: {pat!r} 命中 {cnt} 次，预期 {n}"
    page.text = text
    page.save(summary=summary)
    print(f"saved {title} ({sum(n for _, _, n in replacements)} 处)")


def fb_line(name: str) -> str:
    return rf"\n[ \t]*<default>\{{\{{\{{{re.escape(name)}\|\}}\}}\}}</default>"


SUM1 = "摘除旧参数名 fallback（fix:para 已全站归一，旧名零使用）"

CHAR_FALLBACKS = [
    "Alias",
    "Nickname",
    "Race",
    "Gender",
    "Age",
    "Birthday",
    "Hair Color",
    "Eye Color",
    "Height",
    "Weight",
    "Affiliation",
    "Previous Affiliation",
    "Occupation",
    "Previous Occupation",
    "Status",
    "Relatives",
    "Magic",
    "Divine Protection",
    "Authority",
    "Weapon",
    "Equipment",
    "Anime",
    "Light Novel",
    "Game",
    "Manga",
    "Japanese Voice",
    "English Voice",
    "another translation",
]
edit(
    "Template:Infobox character",
    [(fb_line(f), "", 1) for f in CHAR_FALLBACKS]
    + [
        # title：{{#if:{{{Name|}}}|{{{Name}}}|{{PAGENAME}}}} → {{PAGENAME}}
        (
            r"<default>\{\{#if:\{\{\{Name\|\}\}\}\|\{\{\{Name\}\}\}\|\{\{PAGENAME\}\}\}\}</default>",
            "<default>{{PAGENAME}}</default>",
            1,
        ),
        # name_ja_kanji：#if 包裹的 Kanji 兜底整行摘除（langconv 闭合 }- 后接 #if 闭合 }}）
        (
            r"\n[ \t]*<default>\{\{#if:\{\{\{Kanji\|\}\}\}\|-\{<span lang=\"ja\">\{\{\{Kanji\}\}\}</span>\}-\}\}</default>",
            "",
            1,
        ),
        # romaji 默认链摘除 Kanji 兜底
        (
            r"\{\{\{name_ja_kana\|\{\{\{name_ja_kanji\|\{\{\{Kanji\}\}\}\}\}\}\}\}\}",
            "{{{name_ja_kana|{{{name_ja_kanji|}}}}}}",
            1,
        ),
        # 其他 section 摘除 image/Image 双写
        (r"\{\{\{image\|\}\}\}\{\{\{Image\|\}\}\}", "{{{image|}}}", 1),
        (
            r"\{\{#tag:gallery\|\{\{\{image\|\}\}\}\}\}\{\{#tag:gallery\|\{\{\{Image\|\}\}\}\}\}",
            "{{#tag:gallery|{{{image|}}}}}",
            1,
        ),
    ],
    SUM1,
)

# ── /doc 参数名同步（pre 示例 + templatedata 键）────────────
SUM2 = "参数名归一同步：语法/示例/templatedata 改用新名"


def doc_repl(pairs):
    out = []
    for old, new, n_pipe, n_json in pairs:
        out.append((rf"\|\s*{re.escape(old)}\s*=", f"| {new} =", n_pipe))
        out.append((rf'"{re.escape(old)}"', f'"{new}"', n_json))
    return out


edit(
    "Template:Infobox bd/doc",
    doc_repl(
        [
            ("Number", "number", 2, 2),
            ("Previous", "previous", 1, 2),
            ("Next", "next", 1, 2),
        ]
    ),
    SUM2,
)
edit(
    "Template:Infobox music/doc",
    doc_repl(
        [
            ("Singer", "singer", 2, 2),
            ("Composition", "composition", 2, 2),
            ("Arrangement", "arrangement", 2, 2),
            ("Lyric", "lyric", 2, 2),
            ("Length", "length", 2, 2),
        ]
    ),
    SUM2,
)
edit(
    "Template:Infobox game/doc",
    doc_repl(
        [
            ("Developers", "developers", 2, 2),
            ("Publishers", "publishers", 2, 2),
            ("Platform", "platform", 2, 2),
            ("Genre", "genre", 2, 2),
            ("Modes", "modes", 1, 2),
        ]
    ),
    SUM2,
)
edit(
    "Template:Infobox event/doc",
    doc_repl(
        [
            ("Rōmaji", "name_ja_romaji", 2, 2),
            ("Date", "date", 2, 2),
            ("Place", "place", 2, 2),
            ("Result", "result", 2, 2),
            ("Also known as", "also_known_as", 1, 2),
        ]
    ),
    SUM2,
)
edit(
    "Template:Infobox battle/doc",
    doc_repl(
        [
            ("rōmaji", "name_ja_romaji", 2, 2),
            ("also known as", "also_known_as", 1, 2),
        ]
    ),
    SUM2,
)
print("ALL DONE")
