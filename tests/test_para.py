"""para fix 的 previous/next 参数删除规则测试（离线，不触 wiki）。"""

import importlib
import re
from typing import Any

fx = importlib.import_module("pywikibot.fixes")

# user_fixes 定义在 user-fixes.py，由 pwb/pywikibot/fixes.py 末尾 exec 进自己的
# globals，静态检查不可见，故经 __dict__ 取（同 test_translation.py 模式）。
user_fixes: dict[str, Any] = fx.__dict__["user_fixes"]


def apply_para(text: str) -> str:
    """模拟 replace.py 引擎：顺序应用全部 replacements（regex + nocase）。"""
    for pat, repl in user_fixes["para"]["replacements"]:
        text = re.sub(pat, repl, text, flags=re.IGNORECASE)
    return text


def test_plain_line_removed():
    src = "{{Infobox anime\n| name = X\n| previous = [[动画:第79集|Episode 79]]\n| next = [[动画:第81集|Episode 81]]}}\n"
    out = apply_para(src)
    assert out == "{{Infobox anime\n| name = X\n}}\n"


def test_closing_braces_preserved():
    src = "{{Infobox anime\n| name = X\n| next = [[动画:第81集|Episode 81]]}}\n"
    assert apply_para(src) == "{{Infobox anime\n| name = X\n}}\n"


def test_empty_value_attached_braces():
    # 动画:第85集 / 动画:第四季圆盘5卷 的实存形态：| next =}}
    src = "{{Infobox bd\n| name = X\n| next =}}\n"
    assert apply_para(src) == "{{Infobox bd\n| name = X\n}}\n"


def test_empty_value_then_next_param_not_swallowed():
    # 佩特拉 page5 型（en 侧实存）：|Next = 空值独占一行，下一行是其他参数
    src = "{{Infobox book\n| next = \n| cover = X\n}}\n"
    assert apply_para(src) == "{{Infobox book\n| cover = X\n}}\n"


def test_no_space_variant():
    src = "{{Infobox anime\n| name=X\n|previous=[[动画:第79集]]\n}}\n"
    # 既有的 Name→name 归一规则顺带把 | name=X 改成 | name =X，属预期行为
    assert apply_para(src) == "{{Infobox anime\n| name =X\n}}\n"


def test_similar_param_names_untouched():
    # Infobox character 的合法字段，不得误伤
    src = "{{Infobox character\n| previous_affiliation = [[术语:王国]]\n| next_episode = x\n}}\n"
    assert apply_para(src) == src
