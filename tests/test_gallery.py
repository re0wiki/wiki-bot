"""scripts/re0_gallery.py 的纯函数测试（不触碰 wiki）。

merge_galleries 曾是「生产验证稳定，能跑就别动」的无测试代码，
2026-07 抽为纯函数后补离线回归。
"""

from repo_loader import load_module

g = load_module("re0_gallery", "scripts/re0_gallery.py")


def test_counts_match_replaces_galleries_and_restores_templates():
    zh = "{{Infobox character}}\n<gallery>old1.png</gallery>\n<gallery>old2.png</gallery>\n[[Category:X]]"
    en = "{{Character}}\n<gallery>new1.png</gallery>\n<gallery>new2.png</gallery>\n[[Category:Y]]"
    res = g.merge_galleries(zh, en)
    assert res.text is not None and not res.is_tabber
    # zh 画廊被 en 覆盖、zh 模板原样保留、en 模板不混入
    assert "<gallery>new1.png</gallery>" in res.text
    assert "<gallery>new2.png</gallery>" in res.text
    assert "{{Infobox character}}" in res.text
    assert "{{Character}}" not in res.text
    assert "old1.png" not in res.text


def test_gallery_inside_zh_template_is_not_counted():
    """zh 模板里的 <gallery> 串在计数前已被模板备份剔除，不参与对齐。"""
    zh = "{{Note|<gallery>inner.png</gallery>}}\n<gallery>old.png</gallery>\n[[Category:X]]"
    en = "<gallery>new.png</gallery>\n[[Category:Y]]"
    res = g.merge_galleries(zh, en)
    assert res.text is not None
    assert "{{Note|<gallery>inner.png</gallery>}}" in res.text
    assert "<gallery>new.png</gallery>" in res.text
    assert "old.png" not in res.text


def test_count_mismatch_recovers_via_tabber_section():
    """数量不一致且 tabber 单页段可抽取时，整段同步 en 段。"""
    zh = "{{Tab}}\n<gallery>old.png</gallery>\n[[Category:X]]"
    en = "{{Tab}}\n<gallery>new1.png</gallery>\n<gallery>new2.png</gallery>\n[[Category:Y]]"
    res = g.merge_galleries(zh, en)
    assert res.text is not None and res.is_tabber
    assert "<gallery>new1.png</gallery>" in res.text
    assert "<gallery>new2.png</gallery>" in res.text
    # 段外内容（分类）保留 zh 原文
    assert "[[Category:X]]" in res.text


def test_count_mismatch_bad_format_returns_none():
    """tabber 段数不为 1（无 }}…[[ 结构）时无法整段同步，报错返回 None。"""
    zh = "<gallery>old.png</gallery>"
    en = "<gallery>new1.png</gallery>\n<gallery>new2.png</gallery>"
    res = g.merge_galleries(zh, en)
    assert res.text is None and not res.is_tabber
    assert "incorrect page format" in res.message


def test_count_mismatch_tabber_still_mismatch_returns_none():
    """整段同步后数量仍不一致（en 段外还有画廊），报错返回 None。"""
    zh = "{{Tab}}\n<gallery>old.png</gallery>\n[[Category:X]]"
    en = "{{Tab}}\n<gallery>new1.png</gallery>\n<gallery>new2.png</gallery>\n[[Category:Y]]\n<gallery>new3.png</gallery>"
    res = g.merge_galleries(zh, en)
    assert res.text is None and res.is_tabber
    assert "still mismatch" in res.message
