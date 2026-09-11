"""src/scripts/re0_image.py 的纯函数测试（不触碰 wiki）。"""

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
