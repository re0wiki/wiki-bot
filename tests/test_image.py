"""src/scripts/re0_image.py 的纯函数测试（不触碰 wiki）。"""

import hashlib
from types import SimpleNamespace

import pytest
from repo_loader import load_module

img = load_module("re0_image", "src/scripts/re0_image.py")

PNG = {"ts": "2026-01-01T00:00:00Z", "mime": "image/png"}
PNG_OLD = {"ts": "2025-01-01T00:00:00Z", "mime": "image/png"}
PNG_NEW = {"ts": "2026-08-01T00:00:00Z", "mime": "image/png"}
YT = {"ts": "2026-01-01T00:00:00Z", "mime": "video/youtube"}
YT_NEW = {"ts": "2026-08-01T00:00:00Z", "mime": "video/youtube"}


# region calc_diff（键为无命名空间前缀的图片名；返回 (普通文件, 视频)）
def test_missing_is_diff():
    assert img.calc_diff({"A.png": PNG}, {}) == (["A.png"], [])


def test_older_zh_is_diff():
    assert img.calc_diff({"A.png": PNG}, {"A.png": PNG_OLD}) == (["A.png"], [])


def test_up_to_date_not_diff():
    assert img.calc_diff({"A.png": PNG}, {"A.png": PNG}) == ([], [])


def test_newer_zh_not_diff():
    """zh 更新（理论上不该发生）也不算差量——不会回退。"""
    assert img.calc_diff({"A.png": PNG_OLD}, {"A.png": PNG_NEW}) == ([], [])


def test_en_deleted_ignored():
    """只增不删：zh 多出的图片不在差量里。"""
    assert img.calc_diff({}, {"B.png": PNG}) == ([], [])


def test_timestamp_lexicographic_order():
    """ISO 时间戳字典序即时间序（跨年/跨月边界）。"""
    assert img.calc_diff({"A.png": PNG}, {"A.png": PNG_OLD}) == (["A.png"], [])


def test_video_missing_is_video_diff():
    """video/youtube 走视频差量，不进普通文件差量。"""
    assert img.calc_diff({"PV": YT}, {}) == ([], ["PV"])


def test_video_existing_not_diff():
    """视频只补缺失：zh 已有同名即不同步（导入端点不能更新已有视频）。"""
    assert img.calc_diff({"PV": YT}, {"PV": YT}) == ([], [])
    assert img.calc_diff({"PV": YT_NEW}, {"PV": YT}) == ([], [])


def test_video_zh_extra_ignored():
    """只增不删：zh 独有的视频（如 zh 原创）不在差量里。"""
    assert img.calc_diff({}, {"PV": YT}) == ([], [])


# endregion


class FakeDownloadImage:
    latest_file_info: SimpleNamespace
    site: SimpleNamespace

    def __init__(self, name: str, ok: bool):
        self.name = name
        self.ok = ok

    def title(self, with_ns=True, as_filename=False):
        return self.name if not with_ns else f"File:{self.name}"


def test_download_one_uses_images_alias_and_verifies_original(monkeypatch, tmp_path):
    content = b"complete image"
    source_url = "https://static.wikia.nocookie.net/rezero/images/a/ab/good.png"
    image = FakeDownloadImage("good.png", True)
    image.latest_file_info = SimpleNamespace(
        url=source_url, sha1=hashlib.sha1(content, usedforsecurity=False).hexdigest()
    )

    class FakeThrottle:
        delay = 0.25

        def __init__(self):
            self.calls = []

        def set_delays(self, delay=None):
            self.calls.append(delay)

        def __call__(self):
            self.calls.append("wait")

    throttle = FakeThrottle()
    image.site = SimpleNamespace(throttle=throttle)
    calls = []

    class FakeResponse:
        status_code = 200
        closed = False

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.closed = True

        def iter_content(self, chunk_size):
            assert chunk_size == 100 * 1024
            yield content[:4]
            yield content[4:]

    response = FakeResponse()

    def fake_fetch(url, **kwargs):
        calls.append((url, kwargs))
        return response

    monkeypatch.setattr(img.http, "fetch", fake_fetch)
    assert img.download_one(image, str(tmp_path)) is True
    assert (tmp_path / "good.png").read_bytes() == content
    url, kwargs = calls[0]
    assert (
        url
        == source_url.replace("static.wikia.nocookie.net", "images.wikia.com")
        + "?format=original"
    )
    assert kwargs == {"stream": True}
    assert response.closed is True
    assert throttle.calls == [6.25, "wait", None]


@pytest.mark.parametrize(
    ("status_code", "content"), [(403, b"content"), (200, b"wrong")]
)
def test_download_one_rejects_invalid_downloads(
    monkeypatch, tmp_path, status_code, content
):
    image = FakeDownloadImage("bad.png", False)
    image.latest_file_info = SimpleNamespace(
        url="https://static.wikia.nocookie.net/rezero/images/a/ab/bad.png",
        sha1=hashlib.sha1(b"content", usedforsecurity=False).hexdigest(),
    )

    class FakeThrottle:
        delay = 0.25

        def set_delays(self, delay=None):
            pass

        def __call__(self):
            pass

    image.site = SimpleNamespace(throttle=FakeThrottle())

    class FakeResponse:
        status_code = 200

        def __init__(self):
            self.closed = False

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.closed = True

        def iter_content(self, chunk_size):
            yield content

    response = FakeResponse()
    response.status_code = status_code
    monkeypatch.setattr(img.http, "fetch", lambda url, **kwargs: response)
    assert img.download_one(image, str(tmp_path)) is False
    assert not (tmp_path / "bad.png").exists()
    assert response.closed is True


def test_download_all_filters_failed_files(monkeypatch, tmp_path):
    good = FakeDownloadImage("good.png", True)
    bad = FakeDownloadImage("bad.png", False)
    monkeypatch.setattr(img, "download_original", lambda image, filename: image.ok)
    assert img.download_all([good, bad], str(tmp_path)) == [good]
    assert not (tmp_path / "bad.png").exists()


def test_upload_all_counts_failures(monkeypatch):
    class FakeSite:
        def login(self):
            return None

    monkeypatch.setattr(img.pwb, "Site", lambda *args: FakeSite())
    monkeypatch.setattr(img, "upload_one", lambda image, tmp_dir: image != "bad")
    assert img.upload_all(["good", "bad"], "") == 1


def test_upload_one_honors_false_result(monkeypatch, tmp_path):
    (tmp_path / "bad.png").write_bytes(b"bad")

    class FakeUploader:
        def __init__(self, site, title):
            pass

        def upload(self, filename, **kwargs):
            return False

    monkeypatch.setattr(img.pwb, "Site", lambda *args: object())
    monkeypatch.setattr(img.pwb, "FilePage", FakeUploader)
    image = FakeDownloadImage("bad.png", True)
    assert img.upload_one(image, str(tmp_path)) is False


def test_main_uploads_only_downloaded_and_raises_on_failure(monkeypatch):
    monkeypatch.setattr(img.pwb, "handle_args", lambda *args: None)
    monkeypatch.setattr(img.pwb.config, "simulate", False)
    monkeypatch.setattr(img.pwb, "Site", lambda *args: object())
    # 两次 list_images 分别对应 en/zh。
    responses = iter([{"bad.png": PNG}, {}])
    monkeypatch.setattr(img, "list_images", lambda site: next(responses))
    monkeypatch.setattr(img.pwb, "FilePage", lambda site, title: title)
    monkeypatch.setattr(img, "download_all", lambda images, tmp_dir: [])
    uploaded = []
    monkeypatch.setattr(
        img, "upload_all", lambda images, tmp_dir: uploaded.append(images) or 0
    )
    with pytest.raises(RuntimeError, match="图片同步失败"):
        img.main()
    assert uploaded == [[]]
