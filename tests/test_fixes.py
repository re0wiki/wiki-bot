"""user-fixes.py 的 fix 配置回归测试（离线）。

user-fixes.py 由 pwb/pywikibot/fixes.py 末尾 exec 进自己的 globals（同 re0_move
的加载路径），user_fixes 字典从 pywikibot.fixes 取。
"""

import regex as re

from pywikibot import textlib
from pywikibot.fixes import user_fixes  # ty: ignore[unresolved-import]


def apply_fix(fix_name: str, text: str, exceptions: list[str]) -> str:
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
