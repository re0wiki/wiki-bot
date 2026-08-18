"""译名表（user-fixes.py translation fix）的离线一致性测试。

不触碰 wiki；pywikibot.fixes 导入时会把 user-fixes.py exec 进自己的
globals，因此 translation_names 等名字直接从 pywikibot.fixes 取。
"""

import importlib
import re
from collections import Counter
from typing import Any

from repo_loader import load_module

fx = importlib.import_module("pywikibot.fixes")

# translation 机制定义在 user-fixes.py，由 pwb/pywikibot/fixes.py 末尾 exec 进
# 自己的 globals，静态检查不可见，故经 __dict__ 取。
p2o: Any = fx.__dict__["p2o"]
p2n: Any = fx.__dict__["p2n"]
get_repl_func: Any = fx.__dict__["get_repl_func"]
translation_names: list[str] = fx.__dict__["translation_names"]

# RULES 直接复用 re0_move 的构建结果，不再本地重复构造。
RULES = load_module("re0_move", "scripts/re0_move.py").RULES


def normalize(title: str) -> str:
    """模拟 re0_move 的标题归一：顺序应用全部规则。"""
    for pat, name in RULES:
        title = pat.sub(lambda _, n=name: n, title)
    return title


def test_no_duplicate_names():
    dup = [k for k, v in Counter(translation_names).items() if v > 1]
    assert not dup, f"translation_names 存在重复条目: {dup}"


def test_standard_names_stable_under_full_rule_chain():
    """标准名在完整规则链下必须幂等。

    不幂等意味着另一条规则（通常是 manual 表）把该标准名又改掉了——
    此时主表条目是误导性的死规则（如「贝阿托莉丝」曾被 manual 表
    覆盖为「碧翠丝」），应删除或改为注释说明。
    """
    bad = [(p2n(p), normalize(p2n(p))) for p in translation_names]
    bad = [(std, out) for std, out in bad if out != std]
    assert not bad, f"以下标准名会被规则链二次改写（死规则）: {bad}"


def test_p2n_strips_regex_constructs():
    assert p2n("安娜(斯)?塔西亚") == "安娜塔西亚"
    assert p2n("菜月·?昴") == "菜月·昴"
    assert p2n("丹克(尔)?肯") == "丹克肯"


def test_p2o_matches_alias_variants():
    """p2o 生成的正则应覆盖相似字符与繁体变体。"""
    pat = re.compile(p2o("碧翠丝"))
    for variant in ("碧翠丝", "碧翠絲"):
        assert pat.fullmatch(variant), variant


def test_beatrice_normalizes_to_official_name():
    """回归：「贝阿托莉丝」由 manual 表归一到官方简中「碧翠丝」。"""
    assert normalize("贝阿托莉丝") == "碧翠丝"
    assert normalize("貝阿托莉絲") == "碧翠丝"


def test_get_repl_func_preserves_traditional_standard():
    """正文替换对繁体标准名原样保留（与标题归一简体的差异点）。"""
    func = get_repl_func("碧翠丝")
    pat = re.compile("碧翠[丝絲]")
    assert pat.sub(func, "碧翠絲") == "碧翠絲"
    assert pat.sub(func, "碧翠丝") == "碧翠丝"
