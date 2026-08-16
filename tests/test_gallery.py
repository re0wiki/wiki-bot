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


def test_count_mismatch_recovers_via_tabber_block():
    """数量不一致且两侧各有一个 tabber 块时，整块同步 en 的 tabber。"""
    zh = (
        "{{Init}}\n{{To do}}\n<center><tabber>\n动画=\n<gallery>old.png</gallery>\n"
        "</tabber></center>\n[[en:X/Image Gallery]]\n[[Category:X]]"
    )
    en = (
        "{{Parent Tab}}\n<center><tabber>\nAnime=\n<gallery>new1.png</gallery>\n"
        "{{!}}-{{!}}\nSeason 2=\n<gallery>new2.png</gallery>\n"
        "</tabber></center>\n[[Category:Y]]"
    )
    res = g.merge_galleries(zh, en)
    assert res.text is not None and res.is_tabber
    assert "<gallery>new1.png</gallery>" in res.text
    assert "<gallery>new2.png</gallery>" in res.text
    # 块外内容原样保留：zh 页首模板、跨语言链接、分类；en 页首模板不混入
    assert "{{Init}}" in res.text and "{{To do}}" in res.text
    assert "{{Parent Tab" not in res.text
    assert "[[en:X/Image Gallery]]" in res.text
    assert "[[Category:X]]" in res.text


def test_tabber_sync_preserves_preamble_templates_any_order():
    """回归：页首模板无论顺序都不被 tabber 同步吞掉。

    2026-05-26 角色:夏乌拉/图库事故：页首为 {{To do}}+{{Init}} 顺序时，
    旧 PAGE_REGEX 从第一个 }} 起替换整段，把 {{Init}} 静默删掉。
    """
    zh = (
        "{{To do}}\n{{Init}}\n<center><tabber>\n<gallery>old.png</gallery>\n"
        "</tabber></center>\n[[en:X/Image Gallery]]"
    )
    en = (
        "{{Parent Tab}}\n<center><tabber>\n<gallery>new1.png</gallery>\n"
        "<gallery>new2.png</gallery>\n</tabber></center>\n[[Category:Y]]"
    )
    res = g.merge_galleries(zh, en)
    assert res.text is not None and res.is_tabber
    assert res.text.startswith("{{To do}}\n{{Init}}\n")


def test_count_mismatch_bad_format_returns_none():
    """tabber 块数不为 1（无 tabber 结构）时无法整块同步，报错返回 None。"""
    zh = "<gallery>old.png</gallery>"
    en = "<gallery>new1.png</gallery>\n<gallery>new2.png</gallery>"
    res = g.merge_galleries(zh, en)
    assert res.text is None and not res.is_tabber
    assert "incorrect tabber format" in res.message


def test_count_mismatch_tabber_still_mismatch_returns_none():
    """整块同步后数量仍不一致（en 块外还有画廊），报错返回 None。"""
    zh = "{{Tab}}\n<tabber>\n<gallery>old.png</gallery>\n</tabber>\n[[Category:X]]"
    en = (
        "{{Tab}}\n<tabber>\n<gallery>new1.png</gallery>\n<gallery>new2.png</gallery>\n"
        "</tabber>\n[[Category:Y]]\n<gallery>new3.png</gallery>"
    )
    res = g.merge_galleries(zh, en)
    assert res.text is None and res.is_tabber
    assert "still mismatch" in res.message


# region find_en_title
def test_find_en_title_basic():
    assert (
        g.find_en_title("正文\n[[en:Rem/Image Gallery]]\n[[de:...]]")
        == "Rem/Image Gallery"
    )


def test_find_en_title_with_pipe_and_section():
    assert g.find_en_title("[[en:Rem#sec|label]]") == "Rem"


def test_find_en_title_none_when_absent():
    assert g.find_en_title("[[es:Rem]]") is None


def test_find_en_title_ignores_inline_colon_link():
    """[[:en:X]] 是内联跨站链接，不是语言链接。"""
    assert g.find_en_title("参见[[:en:Rem]]") is None


def test_find_en_title_ignores_empty_target():
    """首页的 [[en:]] 空目标特例不匹配。"""
    assert g.find_en_title("[[en:]]") is None


def test_find_en_title_takes_first():
    assert g.find_en_title("[[en:A]]\n[[en:B]]") == "A"


# endregion
