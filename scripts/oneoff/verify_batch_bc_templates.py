"""验证：模板编辑后样本页 parse 与快照对比。

- seiyu/staff/anime 样本：fallback 应保证字节级一致
- event/music 样本：仅 label 文字应有差异（中文化）
"""

import json
import os
import re

os.environ.pop("PYTHONPATH", None)

import pywikibot
from pywikibot.data import api

site = pywikibot.Site("zh", "re0")

with open("logs/batch_bc_parse_snapshot.json", encoding="utf-8") as f:
    snap = json.load(f)


def normalize(html):
    """剥离全部 HTML 注释（缓存时间戳/展开耗时报告噪音）与 PI data-source 属性
    （参数名归一的有意元数据差异）。"""
    html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
    html = re.sub(r'\s?data-source="[^"]*"', "", html)
    return html


snap = {t: normalize(h) for t, h in snap.items()}


def parse(title):
    html = api.Request(
        site=site, parameters={"action": "parse", "page": title, "prop": "text"}
    ).submit()["parse"]["text"]["*"]
    return normalize(html)


IDENTICAL = [
    "声优:田中爱美",
    "声优:高桥李依",
    "动画:第1集",
    "动画:OVA1",
    "动画:迷你动画第1集",
    "音乐:Redo",
]
LABEL_DIFF = {
    "制作人员:末广健一郎": [
        "Nombre",
        "Kanji",
        "Rōmaji",
        "Nacimiento",
        "Director",
        "Guión",
        "Diseño",
        "Compositor",
    ],
    "术语:王室疫病": ["Kanji", "Rōmaji", "Date", "Place", "Outcome"],
}
# 注：音乐:Redo 不传 name_ja_kanji/name_ja_romaji，Kanji/Romaji 行本就不渲染，期望一致；
# music label 中文化由 verify_music_bd_labels.py 在传参页（音乐:小孩子的梦）上验证。

ok = True
for title in IDENTICAL:
    html = parse(title)
    same = html == snap[title]
    ok &= same
    print(f"{'OK ' if same else 'DIFF!'} {title}（期望一致）")
    if not same:
        # 找出第一处差异上下文
        for i, (a, b) in enumerate(zip(snap[title], html)):
            if a != b:
                print(f"  首个差异 @ {i}: 旧={snap[title][max(0, i - 60) : i + 60]!r}")
                print(f"               新={html[max(0, i - 60) : i + 60]!r}")
                break
        print(f"  长度: {len(snap[title])} -> {len(html)}")

for title in LABEL_DIFF:
    html = parse(title)
    if html == snap[title]:
        print(f"?? {title} 完全一致——label 改动没生效？")
        ok = False
        continue
    # 差异应只含 label 文字：把新旧 label 归一后应一致
    normed_new = html
    normed_old = snap[title]
    pairs = {
        "制作人员:末广健一郎": [
            ("Nombre", "英译"),
            ("Kanji", "日文"),
            ("Rōmaji", "罗马字"),
            ("Nacimiento", "出生"),
            ("Director", "监督"),
            ("Guión", "剧本"),
            ("Diseño", "设计"),
            ("Compositor", "作曲"),
        ],
        "术语:王室疫病": [
            ("Kanji", "日文"),
            ("Rōmaji", "罗马字"),
            (">Date<", ">时间<"),
            (">Place<", ">地点<"),
            ("Outcome", "结果"),
            ("Also known as", "别名"),
        ],
    }
    for old, new in pairs[title]:
        normed_old = normed_old.replace(old, new)
    same = normed_new == normed_old
    ok &= same
    print(f"{'OK ' if same else 'DIFF!'} {title}（期望仅 label 差异）")
    if not same:
        for i, (a, b) in enumerate(zip(normed_old, normed_new)):
            if a != b:
                print(
                    f"  归一后首个差异 @ {i}: 旧={normed_old[max(0, i - 60) : i + 60]!r}"
                )
                print(
                    f"                     新={normed_new[max(0, i - 60) : i + 60]!r}"
                )
                break
        print(f"  长度: {len(normed_old)} vs {len(normed_new)}")

print("\n" + ("ALL VERIFIED" if ok else "FAILURES — 见上"))
