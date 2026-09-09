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
    """ナツキ 是 菜月家多人共用（昴/雷吉尔），不得注入。"""
    out = glossary_lines(["ナツキ·リゲルの誕生日"])
    assert "\nナツキ =" not in out
    assert "ナツキ·リゲル = 雷吉尔" in out


def test_glossary_no_hit():
    assert glossary_lines(["今日は良い天気ですね"]) == ""
