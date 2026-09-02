"""nav Custom- 迁移 阶段1：批量创建 MediaWiki:Custom-*/zh-hans 消息页。

用法：--limit N 试点；无参全量。幂等：内容一致则跳过。失败计数非零退出。
"""

import json
import sys
from pathlib import Path

import pywikibot

OUT = Path(".cache/nav_custom")
plan = json.loads((OUT / "write_plan.json").read_text(encoding="utf-8"))

limit = None
if "--limit" in sys.argv:
    limit = int(sys.argv[sys.argv.index("--limit") + 1])

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

items = sorted(plan.items())
if limit:
    items = items[:limit]

created = skipped = failed = 0
for i, (key, rec) in enumerate(items):
    title = f"MediaWiki:{key}/zh-hans"
    try:
        p = pywikibot.Page(site, title)
        if p.exists() and p.text == rec["hans"]:
            skipped += 1
            continue
        p.text = rec["hans"]
        p.save(summary="导航简繁转换：创建 zh-hans 消息（Custom- key 迁移）", bot=True)
        created += 1
    except Exception as e:  # noqa: BLE001 批处理脚本：单页失败不中断，计数后非零退出
        failed += 1
        print(f"FAIL {title}: {e}")
    if (i + 1) % 100 == 0:
        print(
            f"progress {i + 1}/{len(items)} created={created} skipped={skipped} failed={failed}"
        )

print(f"DONE created={created} skipped={skipped} failed={failed} total={len(items)}")
sys.exit(1 if failed else 0)
