"""nav Custom- 迁移 阶段3：把 355 个旧日文 key 的 zh-hant 消息移动到新英文 key（不留重定向）。

旧 key -> 新 key 的映射从 final_map.json 的 labels 反查（旧 Custom- 标签 -> 新 key）。
幂等：旧页不存在且新页已存在则跳过。
"""

import json
import sys
from pathlib import Path

import pywikibot

OUT = Path(".cache/nav_custom")
final = json.loads((OUT / "final_map.json").read_text(encoding="utf-8"))

moves = {}
for label, rec in final.items():
    if label.startswith("Custom-") and rec["hant"] is not None:
        if label == rec["key"]:
            continue  # 英文 key 未改名（Custom-Camp related 等）
        moves[label] = rec["key"]
print("待移动:", len(moves))

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

moved = skipped = failed = 0
for i, (old, new) in enumerate(sorted(moves.items())):
    old_title = f"MediaWiki:{old}/zh-hant"
    new_title = f"MediaWiki:{new}/zh-hant"
    try:
        p = pywikibot.Page(site, old_title)
        if not p.exists():
            assert pywikibot.Page(site, new_title).exists(), f"新旧页均不存在: {old}"
            skipped += 1
            continue
        p.move(
            new_title,
            reason="导航简繁转换：Custom- key 统一为英文",
            movetalk=False,
            noredirect=True,
        )
        moved += 1
    except Exception as e:  # noqa: BLE001 批处理脚本：单页失败不中断，计数后非零退出
        failed += 1
        print(f"FAIL {old_title}: {e}")
    if (i + 1) % 50 == 0:
        print(
            f"progress {i + 1}/{len(moves)} moved={moved} skipped={skipped} failed={failed}"
        )

print(f"DONE moved={moved} skipped={skipped} failed={failed}")
sys.exit(1 if failed else 0)
