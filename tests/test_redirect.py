"""scripts/re0_redirect.py 的纯函数测试（不触碰 wiki）。"""

from repo_loader import load_module

rd = load_module("re0_redirect", "scripts/re0_redirect.py")


# region collect_stems
def test_collect_basic():
    assert rd.collect_stems(["角色:菜月·昴"]) == {"菜月·昴": "角色:菜月·昴"}


def test_collect_skips_no_colon():
    assert rd.collect_stems(["菜月·昴"]) == {}


def test_collect_first_wins():
    """同词干多前缀页保留排序最前者。"""
    titles = ["角色:X", "术语:X"]
    assert rd.collect_stems(titles) == {"X": "角色:X"}


def test_collect_splits_at_first_colon():
    assert rd.collect_stems(["a:b:c"]) == {"B:c": "a:b:c"}


def test_collect_normalizes_stem():
    assert rd.collect_stems(["前缀:_foo_ "]) == {"Foo": "前缀:_foo_ "}


def test_collect_re_prefix_titles():
    """Re:... 标题也按词干处理（维持现状语义）。"""
    assert rd.collect_stems(["Re:从零开始"]) == {"从零开始": "Re:从零开始"}


# endregion


# region find_missing
class FakeReq:
    def __init__(self, data):
        self._d = data

    def submit(self):
        return self._d


class FakeSite:
    def __init__(self, existing):
        self.existing = existing
        self.batch_sizes = []

    def simple_request(self, **kw):
        titles = kw["titles"].split("|")
        self.batch_sizes.append(len(titles))
        pages = [
            {"title": t, **({} if t in self.existing else {"missing": True})} for t in titles
        ]
        return FakeReq({"query": {"pages": pages}})


def test_find_missing_chunks_by_50():
    site = FakeSite(existing=set())
    rd.find_missing(site, [f"S{i}" for i in range(120)])
    assert site.batch_sizes == [50, 50, 20]


def test_find_missing_only_missing_returned():
    site = FakeSite(existing={"B", "D"})
    assert rd.find_missing(site, ["A", "B", "C", "D"]) == ["A", "C"]


def test_find_missing_empty_input():
    site = FakeSite(existing=set())
    assert rd.find_missing(site, []) == []
    assert site.batch_sizes == []


# endregion
