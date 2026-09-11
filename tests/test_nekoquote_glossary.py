"""译名注入 glossary 的纯函数测试（不触 LLM）。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from src.nekoquote.llm import glossary_lines


def test_glossary_hit_and_format():
    out = glossary_lines(["ラチンスに伝える際のスバルの躊躇い"])
    assert "ラチンス = 拉珍斯" in out
    assert "必须使用" in out


def test_glossary_ambiguous_surface_dropped():
    """エキドナ 是两个不同角色的 ja 原名（强欲魔女 艾姬多娜 / 人工精灵 围巾多娜），不得注入。"""
    out = glossary_lines(["エキドナとの会話"])
    assert "\nエキドナ =" not in out


def test_glossary_surname_injected():
    """姓氏面注入（ナツキ=菜月），与 修德拉格/阿斯特雷亚 等姓氏条目一致。"""
    out = glossary_lines(["ナツキ·リゲルの誕生日"])
    assert "\nナツキ = 菜月\n" in out
    assert "ナツキ·リゲル = 雷吉尔" in out


def test_glossary_no_hit():
    assert glossary_lines(["今日は良い天気ですね"]) == ""
