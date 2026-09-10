"""译名表（user-fixes.py translation fix）的离线一致性测试。

不触碰 wiki；pywikibot.fixes 导入时会把 user-fixes.py exec 进自己的
globals，因此 translation_name_rules 等名字直接从 pywikibot.fixes 取。
"""

import importlib
from collections import Counter
from typing import Any

import regex as re
from repo_loader import load_module

fx = importlib.import_module("pywikibot.fixes")

# translation 机制定义在 user-fixes.py，由 pwb/pywikibot/fixes.py 末尾 exec 进
# 自己的 globals，静态检查不可见，故经 __dict__ 取。
p2st: Any = fx.__dict__["p2st"]
translation_name_rules: list[tuple[str, str]] = fx.__dict__["translation_name_rules"]

# RULES 直接复用 re0_move 的构建结果，不再本地重复构造。
RULES = load_module("re0_move", "src/scripts/re0_move.py").RULES


def normalize(title: str) -> str:
    """模拟 re0_move 的标题归一：顺序应用全部规则。"""
    for pat, name in RULES:
        title = pat.sub(lambda _, n=name: n, title)
    return title


def test_no_duplicate_names():
    dup = [k for k, v in Counter(translation_name_rules).items() if v > 1]
    assert not dup, f"translation_name_rules 存在重复条目: {dup}"


def test_standard_names_stable_under_full_rule_chain():
    """标准名在完整规则链下必须幂等。

    不幂等意味着另一条规则（通常是 manual 表）把该标准名又改掉了——
    此时主表条目是误导性的死规则（如「贝阿托莉丝」曾被 manual 表
    覆盖为「碧翠丝」），应删除或改为注释说明。
    """
    bad = [(n, normalize(n)) for _, n in translation_name_rules]
    bad = [(std, out) for std, out in bad if out != std]
    assert not bad, f"以下标准名会被规则链二次改写（死规则）: {bad}"



def test_beatrice_normalizes_to_official_name():
    """回归：「贝阿托莉丝」由 manual 表归一到官方简中「碧翠丝」。"""
    assert normalize("贝阿托莉丝") == "碧翠丝"
    assert normalize("貝阿托莉絲") == "碧翠丝"


def test_fix_unifies_traditional_to_simplified():
    """正文替换一律归一到简体标准名。"""
    replacements: Any = fx.fixes["translation"]["replacements"]
    new = "碧翠絲"
    for old, repl in replacements:
        new = re.compile(old).sub(repl, new)
    assert new == "碧翠丝"


def test_nekoquote_ja_fields_protected():
    """NekoQuote 月表的日文原文字段（jq/jt Lua 字符串）不被归一，中文字段正常归一。"""
    from pywikibot import textlib

    fix: Any = fx.fixes["translation"]
    # inside 异常是字符串（replace.py 自行编译）；textlib 里 str 是类别名，须先编译
    exceptions = [re.compile(p) for p in fix["exceptions"]["inside"]]
    text = 'q = "死神加護",\n        jq = "死神加護の傷を負っている",'
    for old, repl in fix["replacements"]:
        text = textlib.replaceExcept(
            text, re.compile(old), repl, exceptions, caseInsensitive=True
        )
    assert 'q = "死神加护"' in text
    assert 'jq = "死神加護の傷を負っている"' in text


def test_nekoquote_aliases_normalize():
    """回归：语录管线引入的译名变体归一（斯巴鲁/路易/碧翠子/记忆回廊/地狱狙击）。"""
    assert normalize("斯巴鲁") == "昴"
    assert (
        normalize("菜月·斯巴鲁") == "菜月昴"
    )  # 斯巴鲁 别名精确对先跑，名字规则收尾归一到底
    assert (
        normalize("法茨巴尔穆六世") == "法茨巴尔穆六世"
    )  # 回归：茨巴尔 不得误判为斯巴鲁
    assert normalize("路易·阿内芙") == "鲁伊·阿内芙"
    assert normalize("碧翠子") == "贝亚子"
    assert normalize("贝阿子") == "贝亚子"
    assert normalize("貝亞子") == "贝亚子"
    assert normalize("记忆的回廊") == "记忆回廊"
    assert normalize("地狱狙击") == "地狱·狙击"


translations = load_module("translations", "translations.py")
alias_texts = translations.alias_texts
ENTRIES = list(translations.ENTRIES)


def test_entries_no_duplicate_names():
    dup = [k for k, v in Counter(e.name for e in ENTRIES).items() if v > 1]
    assert not dup, f"ENTRIES 存在重名条目: {dup}"


def test_aliases_no_collision():
    """别名：不重复登记、不撞任何标准名。"""
    names = {e.name for e in ENTRIES}
    seen = {}
    bad = []
    for e in ENTRIES:
        for a in alias_texts(e):
            if a in names:
                bad.append(f"{a}（{e.name} 的别名）撞标准名")
            if a in seen:
                bad.append(f"{a} 重复登记于 {seen[a]} 与 {e.name}")
            seen[a] = e.name
    assert not bad, bad


def test_std_name_source_precedence():
    """优先级不变式（官简 > 官繁 > 民间）：
    标准名为官繁时不能有官简别名（否则官简应提升为标准名）。
    （「民间标准名不能有官方别名」暂缓启用：审查管线的模糊匹配可能漏配官简写法——
    弗鲁夫 即因「弗尔芙」未被匹配到而误标民间；启用前需先核完误标清单）
    """
    S = translations.Source
    bad = []
    for e in ENTRIES:
        for a in e.aliases:
            if e.source == S.OFFICIAL_HANT and a.source == S.OFFICIAL_HANS:
                bad.append(f"官繁标准名 {e.name} 有官简别名 {a.text}（应提升为标准名）")
    assert not bad, bad


def test_std_name_annotated():
    """标准名必须标注来源。"""
    bad = [e.name for e in ENTRIES if e.source is None]
    assert not bad, f"未标注来源: {bad}"


def test_variant_annotations_valid():
    """Variant 标注：source 必填且为 Source 枚举。"""
    bad = []
    for e in ENTRIES:
        for a in e.aliases:
            if not isinstance(a, translations.Variant):
                bad.append(f"{e.name} 的别名 {a} 未用 Variant 标注")
                continue
            if not isinstance(a.source, translations.Source):
                bad.append(f"{e.name} 的别名 {a.text} source={a.source!r}")
    assert not bad, bad


def test_pattern_matches_base_text():
    """一致性：pattern 必须能匹配其基准形态（别名 pattern 匹配 text，条目 pattern 匹配 name）。"""
    bad = [
        f"{e.name} 的别名 {a.text} pattern 不匹配"
        for e in ENTRIES
        for a in e.aliases
        if isinstance(a, translations.Variant)
        and a.pattern
        and not re.search(p2st(a.pattern), a.text)
    ] + [
        f"{e.name} 的 pattern 不匹配 name"
        for e in ENTRIES
        if e.pattern and not re.search(p2st(e.pattern), e.name)
    ]
    assert not bad, bad



def test_aliases_normalize_to_entry_name():
    """别名经完整规则链必须归一到所属条目名（否则规则间互相覆盖）。"""
    bad = [
        (a, e.name, normalize(a))
        for e in ENTRIES
        for a in alias_texts(e)
        if normalize(a) != e.name
    ]
    assert not bad, f"以下别名未归一到条目名: {bad}"


def test_all_entry_names_stable_under_full_rule_chain():
    """所有条目名（含 fuzzy=False）在完整规则链下幂等。"""
    bad = [(e.name, normalize(e.name)) for e in ENTRIES if normalize(e.name) != e.name]
    assert not bad, f"以下条目名会被规则链二次改写: {bad}"


def test_full_name_consistency():
    """full_name = 角色条目完整标题（全名或真名）：唯一；各段（名/姓，含 梵·阿斯特雷亚 这类带助词的姓）须在表中。"""
    all_entries = list(translations.ENTRIES)
    by_name = {e.name for e in all_entries}
    seen: dict[str, str] = {}
    for e in all_entries:
        if not e.full_name:
            continue
        assert e.full_name not in seen, (
            f"全名重复: {e.full_name}（{seen[e.full_name]} / {e.name}）"
        )
        seen[e.full_name] = e.name
        if "·" in e.full_name:
            given, _, sur = e.full_name.partition("·")
            assert given in by_name, f"{e.name}: full_name 的名段 {given} 不在表中"
            # 姓段可能是带助词/中间名的复合段（梵·阿斯特雷亚 / L·梅札斯）：整段或末段在表中即可
            assert sur in by_name or sur.rpartition("·")[2] in by_name, (
                f"{e.name}: full_name 的姓段 {sur} 不在表中"
            )
        else:
            assert e.full_name in by_name, f"{e.name}: full_name {e.full_name} 不在表中"
