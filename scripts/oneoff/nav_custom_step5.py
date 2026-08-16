"""nav Custom- 迁移 阶段0-5：应用拟名，产出最终映射表与裁决报告。

产出：
  .cache/nav_custom/final_map.json  —— label -> {key, hans, hant, targets}
  .cache/nav_custom/report.md       —— 给用户过目的裁决报告
"""

import json
import re
from pathlib import Path

OUT = Path(".cache/nav_custom")
m = json.loads((OUT / "map.json").read_text(encoding="utf-8"))
proposals = json.loads((OUT / "key_proposals.json").read_text(encoding="utf-8"))

# en 验证后的修正与补充（verified=True 表示 en 站有对应页）
FIXES = {
    "暗杀组织": ("Assassin Organization", False),
    "暗殺組織": ("Assassin Organization", False),  # 与「暗杀组织」共享 key
    "神龍教會": ("Divine Dragon Church", True),
    "屍兵": ("Corpse Soldiers", True),
    "欧米伽旅行團": ("Omega Party", True),
    "摯愛之子": ("Beloved Children", True),
    "六枚舌": ("Six Tongues", True),
    "三英傑": ("Three Heroes", False),
    "三大魔獸": ("Three Great Mabeasts", False),
    "佛拉基亞皇室": ("Vollachia Imperial Family", False),
    "鬼村": ("Oni Village", False),
    "王都": ("Royal Capital", True),
    "柯司兹尔&吉內布": ("Costuul & Guineb", False),
    "希爾芙亞": ("Sylphoa", False),
    "靈布斯": ("Lembus", False),
    "歐爾克斯领": ("Orcus Domain", False),
    "萊亞諾特": ("Leanote", False),
    "魔都": ("Demon City", True),
    "剑奴": ("Sword Slaves", False),
    "修德拉格之民": ("People of Shudrak", False),
    "亚人": ("Demi-Humans", False),
    "人工精灵": ("Artificial Spirits", False),
    "伽那库斯": ("Ganacks", False),
    "时刻": ("Time", False),
    "贤人会": ("Sage Council", False),
    "菜月家": ("House Natsuki", False),
    "梅札斯家": ("House Mathers", True),
    "米洛德家": ("House Miload", False),
    "卡尔斯腾家": ("House Karsten", True),
    "阿盖尔家": ("House Argyle", False),
    "跋利耶尔家": ("House Barielle", False),
    "阿斯特雷亚家": ("House Astrea", True),
    "尤克歷烏斯家": ("House Juukulius", False),
    "蘇文家": ("House Suwen", False),
    "里施家": ("House Risch", False),
    "湯普森家": ("House Thompson", False),
    "費瑟蘭家": (None, False),  # en 拼写无把握
    "S4 全卷 Re:從零開始溺水的異世界生活": ("Re:Zero Drowning in Another World", False),
    "嘟哇哇 戀愛年齡差": (None, False),
    "鼠色猫语录": ("Nezumi-iro Neko Quotes", False),
    "簡繁轉換表": ("Conversion Table", False),
}

final = {}
report_unverified = []
report_nokey = []

for label, rec in m.items():
    key = rec["key_en"]
    verified = True
    if not key:
        prop = proposals.get(label, {}).get("key")
        fix = FIXES.get(label)
        if fix and fix[0]:
            key, verified = fix
        elif prop:
            key, verified = prop, bool(proposals[label].get("en_page_exists"))
        # 结构性标签（年份/书店/卷数/wiki 站务等）无需 en 验证
        structural = bool(
            proposals.get(label, {}).get("key")
            and not proposals[label].get("en_page_exists")
            and label not in FIXES
        )
        if key and not verified and not structural:
            report_unverified.append((label, key))
        if key and structural:
            verified = True  # 结构性拟名，不标未验证
    if not key:
        report_nokey.append((label, rec["hans"], rec["targets"]))
    final[label] = {
        "key": "Custom-" + key if key else None,
        "hans": rec["hans"],
        "hant": rec["hant"],
        "targets": rec["targets"],
        "key_verified": verified,
        "flags": rec["flags"],
    }

# key 冲突终检：同 key 必须同 hans/hant 值，否则报错
from collections import defaultdict

# 人工消歧：同 en 名但语义/显示不同的标签
KEY_OVERRIDES = {
    "Custom-プリスカ·ベネディクト": "Prisca Benedict",  # 皇族子嗣形态，非 Priscilla Barielle
    "梅札斯家": "Mathers House",  # 节标题；术语标签 梅札斯家族 占 House Mathers
    "卡尔斯腾家": "Karsten House",
    "阿斯特雷亚家": "Astrea House",
    "卢克尼卡亲龙王国": "Dragon Kingdom of Lugunica",  # 规范全称
    "艾利歐爾大森林": "Elior Forest (section)",  # 节标题；且与术语 艾力欧尔大森林 源文用字不同
    "王族": "Gusteko Royal Family",  # 古斯提科节标题；术语 卢克尼卡王室 占 Royal Family
    "神圣佛拉基亚帝国": "Sacred Vollachia Empire",  # 规范全称；节标题占 Vollachia Empire
}


def story_part_key(label: str, key: str) -> str | None:
    """月刊CA 前后篇标签：key 按标签语义拆 Part N。"""
    m = re.search(r"（(前|中|后)篇）", label)
    if not m:
        return None
    n = {"前": 1, "中": 2, "后": 3}[m.group(1)]
    base = re.sub(r" Part \d+$", "", key)
    return f"{base} Part {n}"


for label, rec in final.items():
    if rec["key"] and rec["key"] in (
        "Custom-The Valkyrie of the Karsten Duchy Part 1",
        "Custom-Kararagi Girl Meets Cats Part 1",
        "Custom-Red Snowfall on the Orcos Domain Part 1",
        "Custom-The Three Idiots Set Out! Earth Spider Episode Part 1",
        "Custom-Pride and Prejudice and Zombies Part 1",
        "Custom-Once Upon a Time in Lugunica Part 1",
    ):
        new_key = story_part_key(label, rec["key"])
        if new_key and new_key != rec["key"]:
            rec["key"] = "Custom-" + new_key.removeprefix("Custom-")
            rec["flags"].append("前后篇按标签语义拆 Part N")
for label, key in KEY_OVERRIDES.items():
    if label in final:
        final[label]["key"] = "Custom-" + key
        final[label]["flags"].append(f"人工消歧 key: {key}")

# hans 值繁体归一 + 用字差异/显示冲突检测（OpenCC t2s）
import subprocess

_t2s_map_json = OUT / "_t2s_input.json"
_t2s_map_json.write_text(
    json.dumps(
        {k: v["hans"] for k, v in final.items() if v["hans"]}, ensure_ascii=False
    ),
    encoding="utf-8",
)
r = subprocess.run(
    [
        "uv",
        "run",
        "--no-project",
        "--with",
        "opencc-python-reimplemented",
        "python",
        "-c",
        (
            "import json,sys; from opencc import OpenCC; d=json.load(open(sys.argv[1],encoding='utf-8')); "
            "c=OpenCC('t2s'); json.dump({k:c.convert(v) for k,v in d.items()}, open(sys.argv[2],'w',encoding='utf-8'), ensure_ascii=False)"
        ),
        str(_t2s_map_json),
        str(OUT / "_t2s_output.json"),
    ],
    check=True,
    capture_output=True,
)
t2s_map = json.loads((OUT / "_t2s_output.json").read_text(encoding="utf-8"))
for label, rec in final.items():
    if rec["hans"] and t2s_map.get(label) and t2s_map[label] != rec["hans"]:
        rec["flags"].append(f"hans 含繁体字，归一: {rec['hans']} -> {t2s_map[label]}")
        rec["hans"] = t2s_map[label]

# 同 hans 显示但 hant 不同（如琉兹本体/复制体）——导航简体下无法区分
from collections import defaultdict as dd

by_hans = dd(list)
for label, rec in final.items():
    by_hans[rec["hans"]].append(label)
for hans, labs in by_hans.items():
    hants = {final[x]["hant"] for x in labs}
    if len(labs) > 1 and len(hants) > 1:
        for x in labs:
            final[x]["flags"].append(f"!! 同 hans 显示「{hans}」但 hant 不同: {labs}")

by_key = defaultdict(list)
for label, rec in final.items():
    if rec["key"]:
        by_key[rec["key"]].append(label)
bad = {
    k: v
    for k, v in by_key.items()
    if len({(final[x]["hans"], final[x]["hant"]) for x in v}) > 1
}
shared_ok = {k: v for k, v in by_key.items() if len(v) > 1 and k not in bad}
print("最终映射:", len(final), "| 唯一 key:", len(by_key))
print("共享 key（同显示值）:", {k: v for k, v in shared_ok.items()})
print("!! 值冲突 key:", bad)

(OUT / "final_map.json").write_text(
    json.dumps(final, ensure_ascii=False, indent=1), encoding="utf-8"
)

# 报告
lines = ["# nav Custom- 迁移映射表 — 裁决报告\n"]
lines.append(f"总标签 {len(final)}，唯一 key {len(by_key)}。\n")
lines.append(f"## 1. 未能拟名的 key（{len(report_nokey)}）——需要你给英文名\n")
for label, hans, targets in report_nokey:
    lines.append(f"- `{label}`（hans={hans}，targets={targets}）")
lines.append(f"\n## 2. 拟名未经 en 站验证（{len(report_unverified)}）——请过目\n")
for label, key in report_unverified:
    lines.append(f"- `{label}` → `Custom-{key}`")
upgrades = [
    (k, v["hans"]) for k, v in final.items() if any("全名升级" in f for f in v["flags"])
]
lines.append(
    f"\n## 3. hans 全名升级清单（{len(upgrades)}，取自条目 infobox name，自动采用）\n"
)
for label, hans in upgrades:
    lines.append(f"- `{label}` → {hans}")
tw = [(k, f) for k, v in final.items() for f in v["flags"] if "name_zh_tw" in f]
lines.append(
    f"\n## 4. name_zh_tw 与现有 hant 不一致（{len(tw)}，沿用现有 hant，仅供参考）\n"
)
for label, f in tw:
    lines.append(f"- `{label}`: {f}")
norm = [(k, f) for k, v in final.items() for f in v["flags"] if "hans 含繁体字" in f]
lines.append(
    f"\n## 5. infobox name 含繁体字，hans 已 t2s 归一（{len(norm)}）——条目本体疑似未归一，建议另行检查\n"
)
for label, f in norm:
    lines.append(f"- `{label}`: {f}")
dup = [(k, f) for k, v in final.items() for f in v["flags"] if "同 hans 显示" in f]
lines.append(
    f"\n## 6. 同 hans 显示但 hant 有区分（{len(dup)}）——简体导航下两条目同名人，需裁决是否加限定词\n"
)
for label, f in dup:
    lines.append(f"- `{label}`: {f}")
(OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")
print("report:", OUT / "report.md")
print("繁体归一:", len(norm), "| 同 hans 冲突:", len(dup))
