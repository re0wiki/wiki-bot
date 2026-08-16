"""nav Custom- 迁移 阶段0-6：应用用户裁决，产出终版映射表。

裁决（2026-08-16 用户确认）：
- 費瑟蘭家 -> Custom-House Featherrun（en 有 Featherrun Sisters 条目）
- 嘟哇哇 戀愛年齡差 -> Custom-Doowawa : Koi no toshi no sa（en 曾用名）
- §2 未验证拟名暂用
- 琉兹对 hans 加 (本体)/(复制体)；普莉丝卡 hans=普莉丝卡·班奈狄克；エリドナ hans=围巾多娜
"""

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

OUT = Path(".cache/nav_custom")
final: dict[str, dict[str, Any]] = json.loads(
    (OUT / "final_map.json").read_text(encoding="utf-8")
)

final["費瑟蘭家"]["key"] = "Custom-House Featherrun"
final["嘟哇哇 戀愛年齡差"]["key"] = "Custom-Doowawa : Koi no toshi no sa"

final["Custom-リューズ·メイエル"]["hans"] = "琉兹·梅埃尔(本体)"
final["Custom-リューズ·メイエル(copy)"]["hans"] = "琉兹·梅埃尔(复制体)"
final["Custom-プリスカ·ベネディクト"]["hans"] = "普莉丝卡·班奈狄克"
final["Custom-エリドナ"]["hans"] = "围巾多娜"

# 终检：无 key / 无 hans 的条目应为零
no_key = [k for k, v in final.items() if not v["key"]]
no_hans = [k for k, v in final.items() if not v["hans"]]
print("无 key:", no_key)
print("无 hans:", no_hans)
assert not no_key and not no_hans


# key 合法性终检（/ 不允许，会变体子页化）
def sanitize(key: str) -> str:
    return key.replace(" / ", " - ").replace("/", "-")


n_sanitized = 0
for rec in final.values():
    if rec["key"] and "/" in rec["key"]:
        rec["key"] = sanitize(rec["key"])
        n_sanitized += 1
print("消毒含 / 的 key:", n_sanitized)
bad = [v["key"] for v in final.values() if "/" in v["key"]]
assert not bad

# 汇总写入计划：唯一 key -> hans/hant

by_key: dict[str, dict[str, Any]] = defaultdict(
    lambda: {"hans": set(), "hant": set(), "labels": []}
)
for label, rec in final.items():
    k = rec["key"]
    by_key[k]["hans"].add(rec["hans"])
    by_key[k]["labels"].append(label)
    if rec["hant"]:
        by_key[k]["hant"].add(rec["hant"])
conflicts = {
    k: v for k, v in by_key.items() if len(v["hans"]) > 1 or len(v["hant"]) > 1
}
print("key 内值冲突:", conflicts)
assert not conflicts

plan = {
    k: {
        "hans": next(iter(v["hans"])),
        "hant": next(iter(v["hant"])) if v["hant"] else None,
        "labels": v["labels"],
    }
    for k, v in by_key.items()
}
(OUT / "final_map.json").write_text(
    json.dumps(final, ensure_ascii=False, indent=1), encoding="utf-8"
)
(OUT / "write_plan.json").write_text(
    json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8"
)
n_hant_move = sum(1 for v in plan.values() if v["hant"])
print(
    f"写入计划: {len(plan)} 个 key，建 zh-hans {len(plan)} 页，移 zh-hant {n_hant_move} 页"
)
