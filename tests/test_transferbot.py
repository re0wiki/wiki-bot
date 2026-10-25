"""src/scripts/re0_transferbot.py 的纯函数测试（不触碰 wiki）。"""

import runpy

from repo_loader import load_module

import pywikibot as pwb
import pywikibot.config
import pywikibot.pagegenerators

tb = load_module("re0_transferbot", "src/scripts/re0_transferbot.py")


def test_normalize():
    assert tb.normalize("_foo bar_ ") == "Foo bar"


def test_build_text_matches_fork_patch():
    text = tb.build_text("正文", "Rem")
    assert text.startswith("{{Init}}\n{{To do}}\n正文")
    assert text.endswith("[[en:Rem]]\n[[Category:新搬运待整理]]")


def test_build_summary_matches_fork_i18n():
    assert tb.build_summary("Rem") == "自[[en:Rem]]搬运页面"


def test_build_text_strips_en_categories():
    """en 源码的分类行在搬运时剥除（en 分类在 zh 必为红链）。"""
    text = tb.build_text("正文\n[[Category:Foo]]\n[[Category:Bar| ]]\n", "Rem")
    assert "Category:Foo" not in text
    assert "Category:Bar" not in text
    assert text.endswith("[[en:Rem]]\n[[Category:新搬运待整理]]")


def test_strip_en_categories_keeps_content():
    assert tb.strip_en_categories("a\nb\n") == "a\nb\n"


class FakeTitlePage:
    def __init__(self, title, text=""):
        self._title = title
        self.text = text

    def title(self):
        return self._title


class FakeRequest:
    def __init__(self, site, params):
        self.site = site
        self.params = params

    def submit(self):
        if self.site.kind == "zh":
            return {
                "query": {
                    "pages": [
                        {"title": title, "missing": True}
                        for title in self.params["titles"].split("|")
                    ]
                }
            }
        return {
            "query": {
                "pages": [
                    {
                        "title": "Copy",
                        "revisions": [
                            {"slots": {"main": {"content": "正文"}}},
                        ],
                    }
                ]
            }
        }


class FakeSite:
    def __init__(self, kind):
        self.kind = kind

    def allpages(self, **kwargs):
        if self.kind == "en":
            return [FakeTitlePage("Covered"), FakeTitlePage("Copy")]
        return []

    def simple_request(self, **params):
        return FakeRequest(self, params)


def run_transfer(monkeypatch, conflict=None):
    en, zh = FakeSite("en"), FakeSite("zh")
    calls = []

    class FakePage(FakeTitlePage):
        def save(self, **kwargs):
            calls.append((self._title, self.text, kwargs))
            if self._title == conflict:
                raise pwb.exceptions.PageCreatedConflictError(0)

    monkeypatch.setattr(pwb, "handle_args", lambda *args: None)
    monkeypatch.setattr(pwb.config, "simulate", False)
    monkeypatch.setattr(
        pwb, "Site", lambda lang="zh", family=None: en if lang == "en" else zh
    )
    monkeypatch.setattr(pwb, "Page", lambda site, title: FakePage(title))
    monkeypatch.setattr(
        pwb.pagegenerators,
        "PreloadingGenerator",
        lambda gen, groupsize: [FakeTitlePage("角色:已有", "[[en:Covered]]")],
    )
    monkeypatch.setattr(pwb, "info", lambda *args: None)
    monkeypatch.setattr(pwb, "warning", lambda *args: None)
    runpy.run_path(tb.__file__, run_name="__main__")
    return calls


def test_new_pages_use_createonly(monkeypatch):
    calls = run_transfer(monkeypatch)
    assert [title for title, _, _ in calls] == ["Covered", "Copy"]
    assert all(kwargs["createonly"] is True for _, _, kwargs in calls)


def test_created_conflict_does_not_stop_later_pages(monkeypatch):
    calls = run_transfer(monkeypatch, conflict="Covered")
    assert [title for title, _, _ in calls] == ["Covered", "Copy"]
