"""user-fixes.py 的 fix 配置回归测试（离线）。

user-fixes.py 由 pwb/pywikibot/fixes.py 末尾 exec 进自己的 globals（同 re0_move
的加载路径），user_fixes 字典从 pywikibot.fixes 取。
"""

import regex as re

from pywikibot import textlib
from pywikibot.fixes import user_fixes  # ty: ignore[unresolved-import]


def apply_fix(fix_name: str, text: str, exceptions: list[str | re.Pattern]) -> str:
    """复刻 replace.py 的应用路径：逐条替换 + inside-tags 豁免（base 为 nocase）。"""
    out = text
    for old, new in user_fixes[fix_name]["replacements"]:
        out = textlib.replaceExcept(
            out, re.compile(old, re.IGNORECASE), new, exceptions
        )
    return out


def test_date_fix_skips_gallery_filenames():
    """<gallery> 裸文件名与 [[File:]] 内的日期不是散文，不转换。

    实证 bug（2026-09-25）：`Monthly Comic Alive July 2026 Cover.png` 被
    Month YYYY 规则改成 `2026-07`，文件名与实际文件错位变红链。
    """
    inside = user_fixes["date"]["exceptions"]["inside-tags"]
    assert "gallery" in inside and "file" in inside
    # file/interwiki 的 regex 需 site 对象，离线行为测试只用 gallery
    text = "<gallery>\nMonthly Comic Alive July 2026 Cover.png\n</gallery>\n发售于 July 2026。"
    out = apply_fix("date", text, ["gallery"])
    assert "July 2026 Cover.png" in out  # gallery 内不动
    assert "发售于 2026-07。" in out  # 散文照常转换


def test_translation_skips_category_links():
    """分类名位置整体不归一：分类行归 re0_category 管理，软重定向目标同理。

    实证（2026-10，wiki 侧观测）：精灵→{{Seirei or Elf}} 命中 [[Category:精灵]]
    与 {{Category redirect|精灵}}（模板化分类名不登记成员、重定向失效），
    category sync 还原、cosmetic 再删，主空间 15 页三任务循环两天数百次编辑，
    分类空间 5 页丢失父分类行、2 个 en 名分类页重定向目标被模板化。
    """
    inside = user_fixes["translation"]["exceptions"]["inside"]
    exceptions = ["keep"] + [re.compile(p, re.IGNORECASE) for p in inside]
    text = (
        "他召唤了精灵。\n"
        "[[Category:精灵]]\n"
        "[[Category:精靈|排序键]]\n"
        "[[:Category:精灵|分类链接]]\n"
        "{{Category redirect|精灵}}\n"
    )
    out = apply_fix("translation", text, exceptions)
    assert "他召唤了{{Seirei or Elf}}。" in out  # 散文照常归一
    assert "[[Category:精灵]]" in out
    assert "[[Category:精靈|排序键]]" in out
    assert "[[:Category:精灵|分类链接]]" in out
    assert "{{Category redirect|精灵}}" in out


def test_translation_skips_filename_but_normalizes_caption():
    inside = user_fixes["translation"]["exceptions"]["inside"]
    exceptions = ["keep"] + [re.compile(p, re.IGNORECASE) for p in inside]
    text = (
        "<gallery>\n贝阿托莉丝.png|贝阿托莉丝微笑\n</gallery>\n"
        "[[File:贝阿托莉丝.png|贝阿托莉丝微笑]]\n"
        "贝阿托莉丝是角色。"
    )
    out = apply_fix("translation", text, exceptions)
    assert out.count("贝阿托莉丝.png") == 2
    assert out.count("碧翠丝微笑") == 2
    assert "碧翠丝是角色" in out


def test_translation_skips_category_whitespace_and_aliases():
    inside = user_fixes["translation"]["exceptions"]["inside"]
    exceptions = ["keep"] + [re.compile(p, re.IGNORECASE) for p in inside]
    text = (
        "[[ Category:精灵]]\n"
        "[[Category :精灵]]\n"
        "[[:分類:精靈]]\n"
        "{{ Category redirect |精灵}}\n"
    )
    assert apply_fix("translation", text, exceptions) == text
