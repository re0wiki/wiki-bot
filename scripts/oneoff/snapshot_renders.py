"""只读：快照 8 个样本页的 parse HTML 到 logs/render_snapshots/，供各阶段对比。"""

import json
import os
import sys

os.environ.pop("PYTHONPATH", None)

import pywikibot
from pywikibot.data import api

SAMPLES = [
    "动画:第一季圆盘1卷",  # bd: Number/Previous/Next
    "音乐:Redo",  # music: Singer/Composition/...
    "游戏:虚假的王选候补",  # game: Developers/...
    "术语:王室疫病",  # event: Rōmaji/Date/Place/Result
    "术语:亚人战争",  # battle: rōmaji/also known as
    "声优:中村悠一",  # seiyu
    "动画:第1集",  # anime
    "角色:菜月·昴",  # character
]

stage = sys.argv[1] if len(sys.argv) > 1 else "0_before"
site = pywikibot.Site("zh", "re0")
out = {}
for t in SAMPLES:
    req = api.Request(site=site, action="parse", page=t, prop="text")
    out[t] = req.submit()["parse"]["text"]["*"]

os.makedirs("logs/render_snapshots", exist_ok=True)
path = f"logs/render_snapshots/{stage}.json"
with open(path, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False)
print(f"saved {path} ({len(out)} pages)")

# 与上一阶段对比
if stage != "0_before":
    prev = sorted(os.listdir("logs/render_snapshots"))[-2]
    with open(f"logs/render_snapshots/{prev}", encoding="utf-8") as f:
        before = json.load(f)
    diffs = [t for t in SAMPLES if before.get(t) != out[t]]
    if diffs:
        print(f"⚠️ 与 {prev} 有差异: {diffs}")
    else:
        print(f"✓ 与 {prev} 全部渲染等价")
