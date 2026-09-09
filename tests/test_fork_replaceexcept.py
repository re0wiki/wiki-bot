"""fork 定制 replaceExcept 快速路径的回归测试（rebase 上游时的行为锚点）。

textlib.replaceExcept 在 marker 为空且不 allowoverlap 时走快速路径：
异常区间预计算一次（合并排序）、编辑后区间随 delta 平移，
而不是原版「每个候选匹配 × 每个异常正则」的全文重扫。
行为与原版一致；NekoQuote 月表（jq/jt 行密集）上 10x+ 加速。
"""

import re

from pywikibot import textlib

JQ = re.compile(r'(?m)^\s*(?:jq|jt)\s*=\s*"(?:[^"\\]|\\.)*"')


def rep(text, old, new, **kw):
    return textlib.replaceExcept(text, re.compile(old), new, [JQ], **kw)


def test_protected_line_untouched():
    text = 'q = "加護",\njq = "加護です",'
    assert rep(text, "加護", "加护") == 'q = "加护",\njq = "加護です",'


def test_edit_before_span_shifts_it():
    """保护区前的编辑改变长度后，后面的保护区仍然有效。"""
    text = '碧翠丝丝\njq = "加護",\nq = "加護"'
    out = rep(
        text, r"加護|碧翠丝丝", lambda m: "加护" if "加" in m.group() else "碧翠丝"
    )
    assert out == '碧翠丝\njq = "加護",\nq = "加护"'


def test_multiple_spans():
    text = 'jq = "加護一",\nq = "加護",\njt = "加護二",'
    assert rep(text, "加護", "加护") == 'jq = "加護一",\nq = "加护",\njt = "加護二",'


def test_count_limit():
    text = "加護 加護 加護"
    assert rep(text, "加護", "加护", count=2) == "加护 加护 加護"


def test_group_reference_replacement():
    assert rep("加護", "(加)護", r"\g<1>护") == "加护"


def test_callable_replacement():
    assert rep("加護", "加護", lambda m: "加护") == "加护"


def test_no_match_fast_return():
    assert rep("无目标", "加護", "加护") == "无目标"
