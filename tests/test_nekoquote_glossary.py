"""译名注入 glossary 的纯函数测试（不触 LLM）。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from src.nekoquote.llm import glossary_lines


def test_glossary_hit_and_format():
    out = glossary_lines(["ラチンスに伝える際のスバルの躊躇い"])
    assert "ラチンス = 拉珍斯" in out
    assert "必须使用" in out


def test_glossary_echidna_forms_disambiguated():
    """强欲魔女与人工精灵的不同日文原名分别注入各自译名。"""
    out = glossary_lines(["エキドナと襟ドナの会話"])
    assert "\nエキドナ = 艾姬多娜\n" in out
    assert "\n襟ドナ = 围巾多娜\n" in out


def test_glossary_name_segments_injected():
    """全名原文中的姓与名分别注入（ナツキ=菜月、リゲル=雷吉尔）。"""
    out = glossary_lines(["ナツキ·リゲルの誕生日"])
    assert "\nナツキ = 菜月\n" in out
    assert "リゲル = 雷吉尔" in out


def test_glossary_no_hit():
    assert glossary_lines(["今日は良い天気ですね"]) == ""
