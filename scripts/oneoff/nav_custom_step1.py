"""nav Custom- 迁移 阶段0-1：抽取导航条目，拉取 en 链接与现有 zh-hant 值。

产出 .cache/nav_custom/entries.json：
  [{label, target, custom_key(若为Custom-标签), hant(若已有消息)}]
以及 labels.json：按 label 去重的汇总（含 target 冲突检查）。
"""

import json
import re
from collections import defaultdict
from pathlib import Path

import pywikibot
from pywikibot.data import api

OUT = Path(".cache/nav_custom")
OUT.mkdir(parents=True, exist_ok=True)

site = pywikibot.Site("zh", "re0")

# ---- 1. 解析导航源 ----
src = pywikibot.Page(site, "Project:Wiki-navigation").text
entries: list[dict[str, str]] = []
for line in src.splitlines():
    if not line.startswith("*") or " " not in line:
        continue
    stem = line.split(" ", 1)[1]
    m = re.match(r"\[\[([^\]|]+)\|([^\]]+)\]\]", stem)
    m2 = re.match(r"\[\[([^\]|]+)\]\]", stem)
    if m:
        target, label = m.group(1), m.group(2)
    elif m2:
        target = label = m2.group(1)
    elif "|" in stem:
        target, label = stem.split("|", 1)
        target = target or None
    else:
        target, label = None, stem
    entries.append({"line": line, "target": target or "", "label": label})

# 按 label 去重，检查 label->target 冲突
by_label = defaultdict(set)
for e in entries:
    by_label[e["label"]].add(e["target"])
conflicts = {k: v for k, v in by_label.items() if len(v) > 1}
print("标签总数:", len(by_label), "| 同标签多目标冲突:", len(conflicts))
for k, v in conflicts.items():
    print("  CONFLICT:", k, "->", sorted(v, key=str))

# ---- 2. 批量拉所有链接目标的 en 跨语言链接 ----
targets = sorted(
    {
        e["target"]
        for e in entries
        if e["target"] and not e["target"].startswith(("http", "Special:"))
    }
)
print("链接目标数:", len(targets))
langlinks = {}
for i in range(0, len(targets), 50):
    batch = targets[i : i + 50]
    req = api.Request(
        site=site,
        parameters={
            "action": "query",
            "prop": "langlinks",
            "lllimit": "max",
            "titles": "|".join(batch),
            "redirects": 1,
        },
    )
    data = req.submit()
    for page in data["query"]["pages"].values():
        ll = {x["lang"]: x["*"] for x in page.get("langlinks", [])}
        langlinks[page["title"]] = ll.get("en")
with_en = sum(1 for v in langlinks.values() if v)
print("拉到 en 链接:", with_en, "/", len(langlinks))
missing_en = [t for t, v in langlinks.items() if not v]
print("无 en 链接目标:", len(missing_en))
for t in missing_en:
    print("  ", t)

# ---- 3. 拉全部现有 Custom-*/zh-hant 内容 ----
custom_keys = sorted({e["label"] for e in entries if e["label"].startswith("Custom-")})
hant = {}
for i in range(0, len(custom_keys), 50):
    batch = custom_keys[i : i + 50]
    req = api.Request(
        site=site,
        parameters={
            "action": "query",
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "titles": "|".join(f"MediaWiki:{k}/zh-hant" for k in batch),
        },
    )
    data = req.submit()
    for page in data["query"]["pages"].values():
        if "revisions" in page:
            key = page["title"].removeprefix("MediaWiki:").removesuffix("/zh-hant")
            hant[key] = page["revisions"][0]["slots"]["main"]["*"]
print("zh-hant 消息拉到:", len(hant), "/", len(custom_keys))

# ---- 4. 汇总 ----
labels = {}
for label, tset in by_label.items():
    real_targets = sorted(t for t in tset if t)
    rec = {"targets": real_targets}
    if label.startswith("Custom-"):
        rec["custom_key"] = label
        rec["hant"] = hant.get(label)
    if len(real_targets) == 1:
        rec["en"] = langlinks.get(real_targets[0])
    labels[label] = rec

(OUT / "entries.json").write_text(
    json.dumps(entries, ensure_ascii=False, indent=1), encoding="utf-8"
)
(OUT / "labels.json").write_text(
    json.dumps(labels, ensure_ascii=False, indent=1), encoding="utf-8"
)
print("saved to", OUT)
