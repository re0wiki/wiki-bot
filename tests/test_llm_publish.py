"""llm_translate 的 publish 子命令测试（离线，api/工作目录打桩，不触 wiki）。"""

import hashlib
import json
import sys
from types import SimpleNamespace

import pytest
from repo_loader import load_module

from pywikibot.exceptions import EditConflictError

lt = load_module("llm_translate", "src/tools/llm_translate.py")

META = {
    "title": "角色:测试",
    "en_title": "Test",
    "en_revid": 100,
    "zh_revid": 90,
    "cold": "2020-01-01T00:00:00+00:00",
    "head": ["{{Init}}"],
    "tail": [],
    "zh_body_len": 3,
    "link_map": {},
    "unresolved_links": [],
}
SLUG = "角色_测试"


def make_work(tmp_path, monkeypatch, zh_text="{{Init}}\n\n旧文。\n"):
    work = tmp_path / "work"
    work.mkdir()
    (work / f"{SLUG}.meta.json").write_text(
        json.dumps(META, ensure_ascii=False), encoding="utf-8"
    )
    (work / f"{SLUG}.zh.txt").write_text(zh_text, encoding="utf-8")
    monkeypatch.setattr(lt, "WORK", work)
    return work


def stub_live(monkeypatch, content):
    """打桩 get_page 用的 api()：返回指定最新源码。"""
    rev = {
        "revid": 95,
        "timestamp": "2026-01-01T00:00:00Z",
        "slots": {"main": {"content": content}},
    }
    monkeypatch.setattr(
        lt, "api", lambda *a, **k: {"query": {"pages": [{"revisions": [rev]}]}}
    )


class FakeWiki:
    """可写入的离线 wiki 状态；Page.save 只推进这个对象，不触网络。"""

    def __init__(
        self,
        monkeypatch,
        content="{{Init}}\n\n旧文。\n",
        revid=90,
        strict_base=False,
    ):
        self.content = content
        self.revid = revid
        self.saved = []
        self.comment = ""
        self.strict_base = strict_base
        self.before_save = None
        monkeypatch.setattr(lt, "get_page", self.get_page)
        monkeypatch.setattr(lt, "api", self.api)
        monkeypatch.setattr(lt, "std_summary", lambda *args: "测试摘要")
        monkeypatch.setitem(
            sys.modules,
            "pywikibot",
            SimpleNamespace(Site=self.make_site, Page=self.make_page),
        )

    def get_page(self, base, title):
        return self.content, self.revid, "2026-01-01T00:00:00Z"

    def api(self, base, **params):
        assert params["prop"] == "revisions"
        rev = {
            "revid": self.revid,
            "user": lt.BOT,
            "comment": self.comment,
            "timestamp": "2026-01-01T00:00:00Z",
            "slots": {"main": {"content": self.content}},
        }
        return {"query": {"pages": [{"revisions": [rev]}]}}

    def make_site(self, *args):
        wiki = self

        class FakeSite:
            def login(self):
                pass

            def user(self):
                return lt.BOT

        class FakePage:
            def __init__(self, site, title):
                self.text = None
                self.latest_revision_id = None

            def save(self, **kwargs):
                wiki.saved.append(kwargs)
                if wiki.before_save:
                    wiki.before_save()
                if wiki.strict_base and kwargs.get("baserevid") != wiki.revid:
                    raise EditConflictError(0)
                wiki.revid += 1
                wiki.content = self.text
                wiki.comment = kwargs["summary"]
                self.latest_revision_id = wiki.revid

        self.page_class = FakePage
        return FakeSite()

    def make_page(self, site, title):
        return self.page_class(site, title)


# ------------------------------------------------------------ ensure_proofread_cat


def test_proofread_cat_appended_before_langlink():
    out = lt.ensure_proofread_cat("正文。\n\n[[en:X]]\n")
    assert out == "正文。\n\n[[Category:机翻待校对]]\n\n[[en:X]]\n"


def test_proofread_cat_merges_into_existing_section():
    out = lt.ensure_proofread_cat("正文。\n\n[[Category:新搬运待整理]]\n\n[[en:X]]\n")
    assert "[[Category:新搬运待整理]]\n[[Category:机翻待校对]]" in out


def test_proofread_cat_already_present_noop():
    src = "正文。\n\n[[category:机翻待校对]]\n"  # 大小写不敏感
    assert lt.ensure_proofread_cat(src) == src


def test_proofread_cat_no_tail():
    assert lt.ensure_proofread_cat("正文。\n") == "正文。\n\n[[Category:机翻待校对]]\n"


# ------------------------------------------------------------ finalize_new_text


def test_finalize_stamps_marker_after_category_before_langlink():
    out = lt.finalize_new_text("正文。\n\n[[en:X]]\n", 100)
    assert out.count("<!-- LLM: revid 100;") == 1
    assert (
        out.index("[[Category:机翻待校对]]")  # 分类由 finalize 机械挂上
        < out.index("<!-- LLM: revid 100;")
        < out.index("[[en:X]]")
    )


def test_finalize_strips_agent_supplied_markers():
    src = "正文。\n<!-- K3: revid 90; 2020-01-01 -->\n<!-- LLM: revid 91; 2020-06-01 -->\n"
    out = lt.finalize_new_text(src, 100)
    assert "revid 90" not in out and "revid 91" not in out
    assert out.count("LLM: revid") == 1 and "revid 100" in out


# ------------------------------------------------------------ cmd_publish 前置校验


def test_publish_binds_baseline_and_records_publication(tmp_path, monkeypatch):
    work = make_work(tmp_path, monkeypatch)
    (work / f"{SLUG}.new.txt").write_text("{{Init}}\n\n新文。\n", encoding="utf-8")
    wiki = FakeWiki(monkeypatch, revid=95)
    lt.cmd_publish(SLUG)
    assert wiki.saved[0]["baserevid"] == 95
    meta = json.loads((work / f"{SLUG}.meta.json").read_text(encoding="utf-8"))
    assert meta["published"] == {
        "revid": 96,
        "sha256": hashlib.sha256(wiki.content.encode("utf-8")).hexdigest(),
    }


def test_publish_conflict_keeps_wip_and_publication_metadata(tmp_path, monkeypatch):
    work = make_work(tmp_path, monkeypatch)
    (work / f"{SLUG}.new.txt").write_text("{{Init}}\n\n新文。\n", encoding="utf-8")
    wiki = FakeWiki(monkeypatch, revid=95, strict_base=True)

    def concurrent_edit():
        wiki.revid = 96
        wiki.content += "\n他人编辑。\n"

    wiki.before_save = concurrent_edit
    with pytest.raises(EditConflictError):
        lt.cmd_publish(SLUG)
    meta = json.loads((work / f"{SLUG}.meta.json").read_text(encoding="utf-8"))
    assert "published" not in meta
    assert list(work.iterdir())
    assert "他人编辑" in wiki.content and "新文" not in wiki.content


@pytest.mark.parametrize(
    "template",
    ["{{Quote|一句引语}}", "{{Infobox character| name = 菜月·昴}}"],
)
def test_publish_accepts_content_templates_as_body(tmp_path, monkeypatch, template):
    work = make_work(tmp_path, monkeypatch)
    (work / f"{SLUG}.new.txt").write_text(
        f"{{{{Init}}}}\n{template}\n", encoding="utf-8"
    )
    wiki = FakeWiki(monkeypatch)
    lt.cmd_publish(SLUG)
    assert len(wiki.saved) == 1


def test_republish_recovers_failed_done(tmp_path, monkeypatch):
    old = "{{Init}}\n\n旧文。\n\n[[en:Test]]\n"
    work = make_work(tmp_path, monkeypatch, old)
    (work / f"{SLUG}.conv.txt").write_text("新文。\n", encoding="utf-8")
    new_file = work / f"{SLUG}.new.txt"
    new_file.write_text("{{Init}}\n\n新文。\n", encoding="utf-8")
    wiki = FakeWiki(monkeypatch, old)
    lt.cmd_publish(SLUG)
    with pytest.raises(SystemExit, match="语言链接"):
        lt.cmd_done(SLUG)

    new_file.write_text("{{Init}}\n\n修正文。\n\n[[en:Test]]\n", encoding="utf-8")
    lt.cmd_republish(SLUG)
    assert wiki.saved[1]["baserevid"] == 91
    meta = json.loads((work / f"{SLUG}.meta.json").read_text(encoding="utf-8"))
    assert meta["published"] == {
        "revid": 92,
        "sha256": hashlib.sha256(wiki.content.encode("utf-8")).hexdigest(),
    }
    lt.cmd_done(SLUG)
    assert not list(work.iterdir())


def test_republish_refuses_post_publish_drift(tmp_path, monkeypatch):
    work = make_work(tmp_path, monkeypatch)
    new_file = work / f"{SLUG}.new.txt"
    new_file.write_text("{{Init}}\n\n修正文。\n", encoding="utf-8")
    published = lt.finalize_new_text("{{Init}}\n\n已发布。\n", 100)
    meta_path = work / f"{SLUG}.meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["published"] = {
        "revid": 91,
        "sha256": hashlib.sha256(published.encode("utf-8")).hexdigest(),
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    for live, revid in ((published + "\n漂移。\n", 91), (published, 92)):
        wiki = FakeWiki(monkeypatch, live, revid)
        with pytest.raises(SystemExit, match="发布后.*漂移"):
            lt.cmd_republish(SLUG)
        assert not wiki.saved


def test_republish_legacy_wip_fails_closed_with_recovery(tmp_path, monkeypatch):
    work = make_work(tmp_path, monkeypatch)
    (work / f"{SLUG}.new.txt").write_text("{{Init}}\n\n修正文。\n", encoding="utf-8")
    wiki = FakeWiki(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        lt.cmd_republish(SLUG)
    assert "发布元数据" in str(exc.value)
    assert "done" in str(exc.value) and "prepare" in str(exc.value)
    assert not wiki.saved


@pytest.mark.parametrize(
    "empty_page",
    [
        (
            "{{Init}}\n[[Category:机翻待校对]]\n"
            "<!-- LLM: revid 100; 2026-01-01T00:00:00+00:00 -->\n"
        ),
        (
            "{{Init}}\n[[en:Test]]\n[[Category:机翻待校对]]\n"
            "<!-- LLM: revid 100; 2026-01-01T00:00:00+00:00 -->\n"
        ),
    ],
)
def test_done_rejects_empty_body_and_preserves_work(tmp_path, monkeypatch, empty_page):
    work = make_work(tmp_path, monkeypatch)
    (work / f"{SLUG}.conv.txt").write_text("新文。\n", encoding="utf-8")
    wiki = FakeWiki(monkeypatch, empty_page, revid=101)
    with pytest.raises(SystemExit, match="正文为空"):
        lt.cmd_done(SLUG)
    assert list(work.iterdir())
    assert wiki.revid == 101


@pytest.mark.parametrize(
    "content",
    [
        "",
        " \n\t\n",
        "{{Init}}\n",
        "<!-- LLM: revid 100; 2026-01-01T00:00:00+00:00 -->\n",
        "{{Init}}\n[[Category:机翻待校对]]\n[[en:Test]]\n",
        "{{Init}}\n[[en:Test]]\n[[Category:机翻待校对]]\n",
    ],
)
def test_publish_blank_draft_aborts_before_wiki(tmp_path, monkeypatch, content):
    work = make_work(tmp_path, monkeypatch)
    (work / f"{SLUG}.new.txt").write_text(content, encoding="utf-8")
    monkeypatch.setattr(
        lt,
        "get_page",
        lambda *args: pytest.fail("空白成稿不应查询 wiki"),
    )
    with pytest.raises(SystemExit, match="空白成稿"):
        lt.cmd_publish(SLUG)


def test_publish_missing_new_file_aborts(tmp_path, monkeypatch):
    make_work(tmp_path, monkeypatch)
    with pytest.raises(SystemExit, match="new.txt"):
        lt.cmd_publish(SLUG)


def test_publish_baseline_mismatch_aborts(tmp_path, monkeypatch):
    work = make_work(tmp_path, monkeypatch)
    (work / f"{SLUG}.new.txt").write_text("新文。\n", encoding="utf-8")
    stub_live(monkeypatch, "{{Init}}\n\n被别人改过的文。\n")
    with pytest.raises(SystemExit, match="基线不一致"):
        lt.cmd_publish(SLUG)


def test_publish_missing_page_aborts(tmp_path, monkeypatch):
    work = make_work(tmp_path, monkeypatch)
    (work / f"{SLUG}.new.txt").write_text("新文。\n", encoding="utf-8")
    monkeypatch.setattr(
        lt, "api", lambda *a, **k: {"query": {"pages": [{"missing": True}]}}
    )
    with pytest.raises(SystemExit, match="不存在"):
        lt.cmd_publish(SLUG)
