"""src/scripts/re0_fixing_redirects.py 的纯函数测试（不触碰 wiki）。"""

from typing import ClassVar

from repo_loader import load_module

fr = load_module("re0_fixing_redirects", "src/scripts/re0_fixing_redirects.py")


class FakeNamespaces:
    @staticmethod
    def lookup_name(name):
        return name in ("category", "分类", "file", "文件", "media") or None


class FakeFamily:
    langs: ClassVar[dict] = {"zh": None, "en": None, "de": None}


class FakeSite:
    """只提供 rewrite_links/is_interwiki 需要的属性，不触网。"""

    code = "zh"
    namespaces = FakeNamespaces()
    family = FakeFamily()
    siteinfo: ClassVar[dict] = {
        "interwikimap": [{"prefix": "wikipedia"}, {"prefix": "wp"}]
    }

    def __init__(self, trail=""):
        self._trail = trail

    def linktrail(self):
        return self._trail


SITE = FakeSite()
SKIP = {"category", "分类", "file", "文件", "media"}
RMAP = {"A": ("B", None)}


def rewrite(text, rmap=RMAP, site=SITE):
    return fr.rewrite_links(text, rmap, site, SKIP)


# region resolve_chains
def test_chain_plain():
    assert fr.resolve_chains({"A": ("B", None)}) == {"A": ("B", None)}


def test_chain_transitive():
    raw = {"A": ("B", None), "B": ("C", None)}
    assert fr.resolve_chains(raw) == {"A": ("C", None), "B": ("C", None)}


def test_chain_cycle_dropped():
    raw = {"A": ("B", None), "B": ("A", None)}
    assert fr.resolve_chains(raw) == {}


def test_chain_self_loop_dropped():
    assert fr.resolve_chains({"A": ("A", None)}) == {}


def test_chain_first_fragment_wins():
    raw = {"A": ("B", "f1"), "B": ("C", "f2")}
    assert fr.resolve_chains(raw)["A"] == ("C", "f1")


# endregion


# region normalize
def test_normalize():
    assert fr.normalize("_a_b_ ") == "A b"


# endregion


# region is_interwiki
def test_is_interwiki_foreign_language():
    assert fr.is_interwiki(SITE, "en:Foo") is True


def test_is_interwiki_same_language_is_local():
    assert fr.is_interwiki(SITE, "zh:Foo") is False


def test_is_interwiki_interwiki_map_prefix():
    assert fr.is_interwiki(SITE, "wikipedia:zh:Foo") is True
    assert fr.is_interwiki(SITE, "wp:Foo") is True


def test_is_interwiki_namespace_is_local():
    assert fr.is_interwiki(SITE, "分类:Foo") is False


def test_is_interwiki_pseudo_prefix_is_local():
    assert fr.is_interwiki(SITE, "角色:Foo") is False


def test_is_interwiki_plain_title():
    assert fr.is_interwiki(SITE, "Foo") is False


def test_is_interwiki_leading_colon():
    assert fr.is_interwiki(SITE, ":en:Foo") is True


# endregion


# region rewrite_links
def test_plain_link_gets_label():
    assert rewrite("[[A]]") == ("[[B|A]]", [("[[A]]", "[[B|A]]")])


def test_piped_label_preserved():
    assert rewrite("[[甲|显示]]", {"甲": ("乙", None)}) == (
        "[[乙|显示]]",
        [("[[甲|显示]]", "[[乙|显示]]")],
    )


def test_lowercase_label_lowercases_latin_target():
    """上游首字母规则：显示文本非大写开头时目标首字母小写（对中文无影响，
    拉丁目标依赖首字母大小写不敏感）。"""
    assert rewrite("[[A|显示]]") == ("[[b|显示]]", [("[[A|显示]]", "[[b|显示]]")])


def test_section_preserved():
    assert rewrite("[[A#节]]") == ("[[B#节|A]]", [("[[A#节]]", "[[B#节|A]]")])


def test_target_fragment_inherited():
    new, _ = rewrite("[[A]]", {"A": ("B", "锚")})
    assert new == "[[B#锚|A]]"


def test_double_section_skipped():
    assert rewrite("[[A#节]]", {"A": ("B", "锚")}) == ("[[A#节]]", [])


def test_identity_collapse():
    """链接文本与最终目标相同（大小写差异）时归并为裸链接。"""
    assert rewrite("[[a]]", {"A": ("A", None)})[0] == "[[a]]"


def test_interwiki_skipped():
    assert rewrite("[[en:A]]", {"En:A": ("B", None)}) == ("[[en:A]]", [])


def test_category_without_colon_skipped():
    assert rewrite("[[分类:A]]", {"分类:A": ("分类:B", None)}) == ("[[分类:A]]", [])


def test_category_with_colon_rewritten_and_colon_kept():
    new, _ = rewrite("[[:分类:A]]", {"分类:A": ("分类:B", None)})
    assert new == "[[:分类:B|分类:A]]"


def test_pseudo_namespace_treated_as_plain_link():
    """伪命名空间前缀（角色: 等）不是真实命名空间，照常规则改写。"""
    new, _ = rewrite("[[角色:A]]", {"角色:A": ("角色:B", None)})
    assert new == "[[角色:B|角色:A]]"


def test_disabled_area_untouched():
    assert rewrite("<nowiki>[[A]]</nowiki>") == ("<nowiki>[[A]]</nowiki>", [])
    assert rewrite("<!-- [[A]] -->") == ("<!-- [[A]] -->", [])


def test_surrounding_text_and_multiple_links():
    new, changes = rewrite("x[[子]]y[[子|丙]]z", {"子": ("终", None)})
    assert new == "x[[终|子]]y[[终|丙]]z"
    assert len(changes) == 2


def test_no_match_returns_original():
    assert rewrite("[[C]]") == ("[[C]]", [])


def test_linktrail_merge():
    """链接尾字符可并入时用裸链接形式（英文 trail 才可能有，中文 trail 为空）。"""
    site = FakeSite(trail="[a-z]*")
    new, _ = rewrite("[[Apple]]s", {"Apple": ("Apple juice", None)}, site)
    assert new == "[[Apple juice|Apples]]"  # 目标更长，只能管道形式


# endregion
