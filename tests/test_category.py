"""src/scripts/re0_category.py 的纯函数测试（不触碰 wiki）。"""

from repo_loader import load_module

rc = load_module("re0_category", "src/scripts/re0_category.py")

MAPPING = {"Deceased": "已故角色", "Characters": "角色", "Emilia Camp": "爱蜜莉雅阵营"}
MANAGED = set(MAPPING) | set(MAPPING.values())
INIT_CATS = rc.parse_init_cats(
    "local prefixes = { '角色', '术语' }\nlocal suffixes = { '图库' }",
    "if x then\n  c = a\nelse\n  c = '杂项'\nend",
)


def sync(
    text,
    registered=frozenset(),
    en_cats=(),
    mapping=MAPPING,
    managed=MANAGED,
    excluded=frozenset(),
    init_cats=INIT_CATS,
):
    return rc.compute_sync(
        text, set(registered), list(en_cats), mapping, managed, excluded, init_cats
    )


# region CAT_LINE_RE
def test_cat_line_basic():
    assert [m.group(1) for m in rc.CAT_LINE_RE.finditer("[[Category:角色]]\n")] == [
        "角色"
    ]


def test_cat_line_localized_and_sortkey():
    text = "[[分类:角色]]\n[[分類:術語|*]]\n[[Category:X|排序键]]\n"
    names = [m.group(1) for m in rc.CAT_LINE_RE.finditer(text)]
    assert names == ["角色", "術語", "X"]


def test_cat_line_colon_inline_not_matched():
    """[[:Category:X]] 是内联链接不是归类。"""
    assert rc.CAT_LINE_RE.search("[[:Category:角色]]\n") is None


def test_cat_line_indented_not_matched():
    """行前空格是 preformatted 文本，不构成归类。"""
    assert rc.CAT_LINE_RE.search(" [[Category:角色]]\n") is None


def test_cat_line_mid_text_not_matched():
    assert rc.CAT_LINE_RE.search("正文[[Category:角色]]\n") is None


# endregion
# region parse_en_link
def test_parse_en_link_first():
    assert (
        rc.parse_en_link("正文\n[[en:Natsuki Subaru]]\n[[en:Other]]")
        == "Natsuki Subaru"
    )


def test_parse_en_link_normalizes():
    assert rc.parse_en_link("[[en:natsuki_subaru#Life|昴]]") == "Natsuki subaru"


def test_parse_en_link_none():
    assert rc.parse_en_link("没有链接") is None
    assert rc.parse_en_link("[[en:]]") is None  # 首页空目标特例


# endregion
# region build_mapping
def test_build_mapping_basic():
    mapping, conflicts, hints = rc.build_mapping({"角色": "[[en:Category:Characters]]"})
    assert mapping == {"Characters": "角色"}
    assert conflicts == []
    assert any("Characters 待建" in h for h in hints)


def test_build_mapping_redirect_crosscheck_ok():
    mapping, conflicts, _ = rc.build_mapping(
        {
            "角色": "[[en:Category:Characters]]",
            "Characters": "{{Category redirect|角色}}",
        }
    )
    assert mapping == {"Characters": "角色"}
    assert conflicts == []


def test_build_mapping_conflict():
    _, conflicts, _ = rc.build_mapping(
        {
            "漫画分类": "[[en:Category:Re:Zero Manga]]",
            "Re:Zero Manga": "{{Category redirect|单行本漫画}}",
        }
    )
    assert len(conflicts) == 1
    assert "Re:Zero Manga" in conflicts[0]


def test_build_mapping_duplicate_claim():
    _, conflicts, _ = rc.build_mapping(
        {
            "角色": "[[en:Category:Characters]]",
            "角色2": "[[en:Category:Characters]]",
        }
    )
    assert any("多个分类声称" in c for c in conflicts)


def test_build_mapping_multiple_en_links():
    _, conflicts, _ = rc.build_mapping({"X": "[[en:Category:A]]\n[[en:Category:B]]"})
    assert any("多个 en 链接" in c for c in conflicts)


def test_build_mapping_redirect_without_interwiki_hint():
    _, _, hints = rc.build_mapping({"Old Name": "{{Category redirect|新名}}"})
    assert any("无 interwiki 映射对应" in h for h in hints)


def test_build_mapping_hints_nowiki_wrapped():
    """提示里的模板写法必须 nowiki 包裹——裸写会被报告页实际转置
    （报告页因此误入 已重定向的分类，2026-09-30 实证）。"""
    import re

    _, _, hints = rc.build_mapping({"角色": "[[en:Category:Characters]]"})
    assert hints
    for h in hints:
        stripped = re.sub(r"<nowiki>.*?</nowiki>", "", h, flags=re.DOTALL)
        assert "{{Category redirect" not in stripped


# endregion
# region resolve_en_cats
def _resp(pages, normalized=(), redirects=()):
    q = {"pages": pages}
    if normalized:
        q["normalized"] = [{"from": f, "to": t} for f, t in normalized]
    if redirects:
        q["redirects"] = [{"from": f, "to": t} for f, t in redirects]
    return {"query": q}


def test_resolve_en_cats_plain():
    data = _resp([{"title": "A", "categories": [{"title": "Category:X"}]}])
    assert rc.resolve_en_cats(data, ["A"]) == {"A": ["X"]}


def test_resolve_en_cats_normalized_and_redirect():
    data = _resp(
        [{"title": "B", "categories": [{"title": "Category:X"}]}],
        normalized=[("a", "A")],
        redirects=[("A", "B")],
    )
    assert rc.resolve_en_cats(data, ["a"]) == {"a": ["X"]}


def test_resolve_en_cats_missing():
    data = _resp([{"title": "A", "missing": True}])
    assert rc.resolve_en_cats(data, ["A"]) == {"A": None}


# endregion
# region parse_init_cats
def test_parse_init_cats_full():
    cats = rc.parse_init_cats(
        "local prefixes = { '角色', '术语' }\nlocal suffixes = { '关系', '图库' }",
        "else\n  c = '杂项'\n",
    )
    assert cats == {
        "角色",
        "术语",
        "杂项",
        "角色关系",
        "角色图库",
        "术语关系",
        "术语图库",
    }


def test_parse_init_cats_loud_on_format_change():
    import pytest

    with pytest.raises(AssertionError):
        rc.parse_init_cats("prefixes = {}", "else c = '杂项'")
    with pytest.raises(AssertionError):
        rc.parse_init_cats(
            "local prefixes = { '角色' }\nlocal suffixes = { '图库' }", ""
        )


# endregion
# region compute_sync
def test_sync_adds_before_langlinks():
    new, added, removed, _, _ = sync("正文\n[[en:A]]\n[[de:B]]\n", en_cats=["Deceased"])
    assert new == "正文\n[[Category:已故角色]]\n[[en:A]]\n[[de:B]]\n"
    assert added == {"已故角色"}
    assert removed == set()


def test_sync_init_cats_never_written_but_reported():
    """映射目标属 Init 覆盖集（角色/术语/…）：不写入，registered 缺失进报告。"""
    new, added, _, _, init_missing = sync("正文\n", en_cats=["Characters", "Deceased"])
    assert new == "正文\n[[Category:已故角色]]\n"
    assert added == {"已故角色"}
    assert init_missing == ["角色"]


def test_sync_init_cats_present_no_report():
    """registered 已含 Init 分类（标题前缀正确带入）时不报缺失。"""
    *_, init_missing = sync("正文\n", registered={"角色"}, en_cats=["Characters"])
    assert init_missing == []


def test_sync_template_provided_not_written():
    """模板带入的分类（registered 有、源码无，如 战役）不写源码行。"""
    new, added, _, _, _ = sync(
        "正文\n",
        registered={"战役"},
        en_cats=["Battles", "Deceased"],
        mapping={**MAPPING, "Battles": "战役"},
        managed=MANAGED | {"Battles", "战役"},
    )
    assert new == "正文\n[[Category:已故角色]]\n"
    assert added == {"已故角色"}


def test_sync_replaces_managed_residue():
    """en 名残留行被归一为中文名。"""
    new, _, removed, _, _ = sync("正文\n[[Category:Deceased]]\n", en_cats=["Deceased"])
    assert new == "正文\n[[Category:已故角色]]\n"
    assert removed == {"Deceased"}


def test_sync_keeps_unmanaged_lines():
    """不受管源码行（机翻待校对等）原样保留。"""
    new, _, _, _, _ = sync("正文\n[[Category:机翻待校对]]\n", en_cats=["Deceased"])
    assert "[[Category:机翻待校对]]" in new
    assert "[[Category:已故角色]]" in new


def test_sync_noop():
    text = "正文\n[[Category:已故角色]]\n"
    assert sync(text, en_cats=["Deceased"])[0] is None


def test_sync_removes_when_en_dropped():
    new, _, removed, _, _ = sync("正文\n[[Category:已故角色]]\n", en_cats=[])
    assert new == "正文\n"
    assert removed == {"已故角色"}


def test_sync_removes_only_managed():
    new, _, _, _, _ = sync(
        "正文\n[[Category:已故角色]]\n[[Category:新搬运待整理]]\n", en_cats=[]
    )
    assert new == "正文\n[[Category:新搬运待整理]]\n"


def test_sync_appends_at_end_without_langlinks():
    new, _, _, _, _ = sync("正文\n", en_cats=["Deceased"])
    assert new == "正文\n[[Category:已故角色]]\n"


def test_sync_insert_position_stable():
    """改写发生在原受管行位置（不漂移到文末）。"""
    new, _, _, _, _ = sync(
        "正文\n[[Category:已故角色]]\n[[en:A]]\n", en_cats=["Emilia Camp"]
    )
    assert new == "正文\n[[Category:爱蜜莉雅阵营]]\n[[en:A]]\n"


def test_sync_unmapped_reported():
    *_, unmapped, _ = sync("正文\n", en_cats=["Deceased", "Unknown X"])
    assert unmapped == ["Unknown X"]


def test_sync_excluded_not_reported():
    *_, unmapped, _ = sync("正文\n", en_cats=["Browse"], excluded={"Browse"})
    assert unmapped == []


def test_sync_excluded_overrides_mapping_and_purges():
    """不同步优先于映射：不写 desired，且既有 en 名源码行被清空。"""
    new, added, removed, unmapped, _ = sync(
        "正文\n[[Category:Deceased]]\n[[Category:机翻待校对]]\n",
        en_cats=["Deceased"],
        excluded={"Deceased"},
    )
    assert new == "正文\n[[Category:机翻待校对]]\n"
    assert added == set()
    assert removed == {"Deceased"}
    assert unmapped == []


# endregion
# region find_autoempty
def test_find_autoempty():
    pages = {
        "Image Gallery": "[[Category:自动清空分类]]",
        "关系": "[[en:Category:Relationships]]",
    }
    assert rc.find_autoempty(pages) == {"Image Gallery"}


def test_find_autoempty_none():
    assert rc.find_autoempty({"角色": "[[en:Category:Characters]]"}) == set()


# endregion
# region build_report
def test_build_report_deterministic():
    from collections import Counter

    r1 = rc.build_report(Counter({"A": 2, "B": 1}), ["冲突X"], ["提示Y"], set(), {})
    r2 = rc.build_report(Counter({"B": 1, "A": 2}), ["冲突X"], ["提示Y"], set(), {})
    assert r1 == r2
    assert "<nowiki>[[en:Category:A]]</nowiki>（2 个 en 页面使用）" in r1
    assert "冲突X" in r1 and "提示Y" in r1


def test_build_report_empty():
    assert "（无）" in rc.build_report(
        __import__("collections").Counter(), [], [], set(), {}
    )


def test_build_report_lists_excluded():
    from collections import Counter

    r = rc.build_report(Counter(), [], [], {"Browse", "Synopses"}, {})
    assert "== 不同步 ==" in r
    assert "<nowiki>[[en:Category:Browse]]</nowiki>" in r
    assert "<nowiki>[[en:Category:Synopses]]</nowiki>" in r


def test_build_report_lists_init_missing():
    from collections import Counter

    r = rc.build_report(Counter(), [], [], set(), {"角色:某页": ["角色"]})
    assert "== Init 覆盖缺失 ==" in r
    assert "[[角色:某页]]（缺 角色）" in r


def test_build_report_no_stray_transclusion_or_assignment():
    """报告页自身不得引入模板转置或分类指派（2026-09-30 实证：
    <code> 不防 {{Category redirect}} 转置，[[Category:X]] 漏冒号会归类本页）。"""
    from collections import Counter

    r = rc.build_report(Counter({"A": 1}), ["c"], ["h"], {"Browse"}, {"p": ["角色"]})
    assert "{{Category redirect" not in r
    assert "[[Category:" not in r.replace("[[:Category:", "")


# endregion
