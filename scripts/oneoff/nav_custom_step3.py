"""nav Custom- 迁移 阶段0-3：组装映射表与裁决清单。

hans 取值：Custom- 标签 = 目标条目信息框 | name =（无则词干）；CJK 标签 = 标签文本（繁化简）。
key 命名：en 链接标题；无 en/裸标签/多目标 → 进裁决清单（附拟名建议为空，由 LLM/用户填）。

产出 .cache/nav_custom/map.json 与 adjudicate.json。
"""

import json
import re
from pathlib import Path

from pywikibot.data import api

import pywikibot

OUT = Path(".cache/nav_custom")
candidates = json.loads((OUT / "candidates.json").read_text(encoding="utf-8"))
labels = json.loads((OUT / "labels.json").read_text(encoding="utf-8"))

site = pywikibot.Site("zh", "re0")

# ---- 1. 拉 Custom- 标签目标条目的信息框 name / name_zh_tw ----
custom_targets = sorted(
    {
        labels[label]["targets"][0].split("#", 1)[0]
        for label, rec in candidates.items()
        if rec["kind"] == "custom" and len(labels[label]["targets"]) == 1
    }
)
print("Custom- 标签单目标数:", len(custom_targets))
NAME_RE = re.compile(r"^\|\s*name\s*=\s*(.*)$", re.MULTILINE)
NAME_TW_RE = re.compile(r"^\|\s*name_zh_tw\s*=\s*(.*)$", re.MULTILINE)
AS_IS_RE = re.compile(r'<div class="as-is">(.*?)</div>', re.DOTALL)


def clean(v: str) -> str:
    v = AS_IS_RE.sub(r"\1", v).strip()
    return v


info = {}
for i in range(0, len(custom_targets), 50):
    batch = custom_targets[i : i + 50]
    req = api.Request(
        site=site,
        parameters={
            "action": "query",
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "titles": "|".join(batch),
            "redirects": 1,
        },
    )
    data = req.submit()
    redirects = {r["from"]: r["to"] for r in data["query"].get("redirects", [])}
    for page in data["query"]["pages"].values():
        if "revisions" not in page:
            continue
        text = page["revisions"][0]["slots"]["main"]["*"]
        m = NAME_RE.search(text)
        mtw = NAME_TW_RE.search(text)
        info[page["title"]] = {
            "name": clean(m.group(1)) if m else None,
            "name_zh_tw": clean(mtw.group(1)) if mtw else None,
            "raw_name": m.group(1) if m else None,
        }
    # 记录重定向来源
    for frm, to in redirects.items():
        if to in info:
            info[frm] = info[to]
print("拉到条目内容:", len(info))

# ---- 2. 组装映射表 ----
mapping = {}
adjudicate = []

used_keys = {}  # key -> label（冲突检测）

for label, rec in candidates.items():
    key_en = rec.get("key_hint_en")
    hans = rec.get("hans_candidate")
    flags = list(rec["flags"])

    if rec["kind"] == "custom":
        targets = labels[label]["targets"]
        if len(targets) == 1:
            t = targets[0]
            if "#" in t:
                # 锚点目标（次要角色#X）：hans 直接用锚点文本，不取条目 infobox
                hans = t.split("#", 1)[1]
                flags.append("锚点目标，hans 取锚点文本")
            else:
                stem = t.split(":", 1)[1] if ":" in t else t
                article = info.get(t, {})
                name = article.get("name")
                if name:
                    hans = name
                    if name != stem:
                        flags.append(f"全名升级: 词干「{stem}」-> 「{name}」")
                else:
                    hans = stem
                    flags.append("条目无 infobox name，用词干")
                # 一致性：name_zh_tw vs 现有 hant 消息
                ntw = article.get("name_zh_tw")
                if ntw and rec.get("hant") and ntw != rec["hant"]:
                    flags.append(
                        f"name_zh_tw「{ntw}」!= 现有 hant「{rec['hant']}」（沿用现有 hant）"
                    )
                # name 里带模板/链接等复杂标记的进裁决
                if name and re.search(r"[{}\[\]|]", article.get("raw_name") or ""):
                    flags.append(f"infobox name 含复杂标记: {article['raw_name']!r}")
        else:
            hans = rec.get("hans_candidate")  # 裸标签：hant 简体化（step2 已算）
            if hans is None:
                flags.append("Custom- 裸/多目标，hans 未定")
    else:
        # CJK 标签：hans=转换值（step2 已算），原样
        pass

    # key 合法性
    if key_en:
        if "/" in key_en:
            flags.append(f"en 名含 /: {key_en!r}——需改名")
        if re.search(r"[#\[\]{}|]", key_en):
            flags.append(f"en 名含非法字符: {key_en!r}")

    mapping[label] = {
        "kind": rec["kind"],
        "key_en": key_en,
        "hans": hans,
        "hant": rec.get("hant"),
        "targets": labels[label]["targets"],
        "flags": flags,
    }
    if key_en:
        key = "Custom-" + key_en
        if key in used_keys and used_keys[key] != label:
            mapping[label]["flags"].append(
                f"key 冲突: {key} 已被标签 {used_keys[key]!r} 占用"
            )
            mapping[used_keys[key]]["flags"].append(
                f"key 冲突: {key} 与 {label!r} 共享"
            )
        else:
            used_keys[key] = label

    if (
        not key_en
        or not hans
        or any(
            "冲突" in f
            or "需改名" in f
            or "非法字符" in f
            or "裸" in f
            or "多目标" in f
            for f in flags
        )
    ):
        adjudicate.append(label)

(OUT / "map.json").write_text(
    json.dumps(mapping, ensure_ascii=False, indent=1), encoding="utf-8"
)
(OUT / "adjudicate.json").write_text(
    json.dumps({k: mapping[k] for k in adjudicate}, ensure_ascii=False, indent=1),
    encoding="utf-8",
)
print("映射表:", len(mapping), "| 待裁决:", len(adjudicate))
need_key = [k for k, v in mapping.items() if not v["key_en"]]
print("缺 key 拟名:", len(need_key))
full_upgrades = [
    k for k, v in mapping.items() if any("全名升级" in f for f in v["flags"])
]
print("全名升级:", len(full_upgrades))
tw_mismatch = [
    k for k, v in mapping.items() if any("name_zh_tw" in f for f in v["flags"])
]
print("name_zh_tw 与现有 hant 不一致:", len(tw_mismatch))
complex_name = [
    k for k, v in mapping.items() if any("复杂标记" in f for f in v["flags"])
]
print("infobox name 含复杂标记:", len(complex_name))
