"""部署 Kana2Romaji 重写到 wiki 并用 parse API 跑回归测试矩阵。

用法：PYTHONPATH= .venv/Scripts/python.exe scripts/deploy_kana2romaji.py
"""

import os
import re
import sys

SUMMARY = (
    sys.argv[1]
    if len(sys.argv) > 1
    else "重写：完整平文式表（补ヴ系/外来拗音）、ん同化、促音 tch、长音 macron 化"
)

os.environ.pop("PYTHONPATH", None)

from pywikibot.data import api

import pywikibot

site = pywikibot.Site("zh", "re0")

with open("logs/modules/Kana2Romaji_new.lua", encoding="utf-8") as f:
    new_src = f.read()

site.login()
assert site.user() == "IchiSanNi"

p = pywikibot.Page(site, "Module:Kana2Romaji")
if p.text.strip() != new_src.strip():
    p.text = new_src
    p.save(summary=SUMMARY)
    print("已保存 Module:Kana2Romaji")
else:
    print("Module:Kana2Romaji 已是最新，跳过保存")

# ── 回归测试矩阵 ──────────────────────────────────────────
CASES = {
    # 旧行为保持
    "ナツキ": "Natsuki",
    "ナツキ·スバル": "Natsuki Subaru",
    "パック": "Pakku",
    "オットー": "Ottō",
    "エリオール": "Eriōru",
    "メイリィ": "Meiri",
    "ロズワール": "Rozuwāru",
    "ガーフィール": "Gāfīru",
    "ベアトリス": "Beatorisu",
    "菜月·昴": "菜月 昴",  # 汉字原样 + 间隔号→空格
    # 修复点
    "ヴィルヘルム": "Viruherumu",  # 旧：ヴィruherumu（假名漏出）
    "ヴァルグレン": "Varuguren",  # 旧：varuguren（首字母小写）
    # 新能力
    "シンバル": "Shimbaru",  # ん→m 同化
    "けんやく": "Ken'yaku",  # n'ya
    "マッチ": "Matchi",  # tch
    "アース": "Āsu",  # 长音符开头也大写
    "フェリックス": "Ferikkusu",  # フェ + ッ
    # 契约：无假名 → 空串
    "Subaru": "",
    "菜月昴": "",
}

fails = 0
for kana, expect in CASES.items():
    req = api.Request(
        site=site,
        parameters={
            "action": "parse",
            "text": "{{#invoke:Kana2Romaji|Kana2Romaji|kana=" + kana + "}}",
            "contentmodel": "wikitext",
            "prop": "text",
        },
    )
    html = req.submit()["parse"]["text"]["*"]
    m = re.search(r"<p>(.*?)</p>", html, re.DOTALL)
    got = (m.group(1).strip() if m else "").strip()
    ok = got == expect
    fails += not ok
    print(
        f"{'OK ' if ok else 'FAIL'} {kana:<12} -> {got!r}"
        + ("" if ok else f"（期望 {expect!r}）")
    )

print(f"\n{len(CASES) - fails}/{len(CASES)} 通过")
