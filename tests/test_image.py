"""scripts/re0_image.py 的纯函数测试（不触碰 wiki）。"""

from repo_loader import load_module

img = load_module("re0_image", "scripts/re0_image.py")


# region calc_diff（键为无命名空间前缀的图片名）
def test_missing_is_diff():
    assert img.calc_diff({"A.png": "2026-01-01T00:00:00Z"}, {}) == ["A.png"]


def test_older_zh_is_diff():
    en = {"A.png": "2026-08-01T00:00:00Z"}
    zh = {"A.png": "2026-01-01T00:00:00Z"}
    assert img.calc_diff(en, zh) == ["A.png"]


def test_up_to_date_not_diff():
    en = {"A.png": "2026-01-01T00:00:00Z"}
    zh = {"A.png": "2026-01-01T00:00:00Z"}
    assert img.calc_diff(en, zh) == []


def test_newer_zh_not_diff():
    """zh 更新（理论上不该发生）也不算差量——不会回退。"""
    en = {"A.png": "2026-01-01T00:00:00Z"}
    zh = {"A.png": "2026-08-01T00:00:00Z"}
    assert img.calc_diff(en, zh) == []


def test_en_deleted_ignored():
    """只增不删：zh 多出的图片不在差量里。"""
    assert img.calc_diff({}, {"B.png": "2026-01-01T00:00:00Z"}) == []


def test_timestamp_lexicographic_order():
    """ISO 时间戳字典序即时间序（跨年/跨月边界）。"""
    en = {"A.png": "2026-01-01T00:00:00Z"}
    zh = {"A.png": "2025-12-31T23:59:59Z"}
    assert img.calc_diff(en, zh) == ["A.png"]


# endregion
