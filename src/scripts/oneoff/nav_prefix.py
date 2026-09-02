"""nav Custom- key 加 nav- 前缀：copy / update / delete 三阶段。

  copy   ：MediaWiki:Custom-<key>/{zh-hans,zh-hant} 逐字节复制到 Custom-nav-<key>/*（--limit 试点）
  update ：Project:Wiki-navigation 的 Custom- 引用换 nav- 前缀（--simulate 干跑）
  delete ：删除旧 key 页面

幂等，可重跑。阶段间按 copy -> update -> delete 顺序人工推进。
"""

import json
import sys
from pathlib import Path

import pywikibot
from pywikibot.data import api

OUT = Path(".cache/nav_custom")
plan = json.loads((OUT / "write_plan.json").read_text(encoding="utf-8"))
OLD_KEYS = sorted(plan)  # 975 个旧 key（Custom- 开头）

mode = sys.argv[1] if len(sys.argv) > 1 else None
limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None

site = pywikibot.Site("zh", "re0")


def old_pages() -> dict[str, str]:
    """旧 key -> 变体列表（hans 全有，hant 部分有）。"""
    return {k: ["zh-hans"] + (["zh-hant"] if plan[k]["hant"] else []) for k in OLD_KEYS}


if mode == "copy":
    keys = OLD_KEYS[:limit] if limit else OLD_KEYS
    # 批量读旧页内容
    old_titles = [f"MediaWiki:{k}/{v}" for k in keys for v in old_pages()[k]]
    contents = {}
    for i in range(0, len(old_titles), 50):
        batch = old_titles[i : i + 50]
        req = api.Request(
            site=site,
            parameters={
                "action": "query",
                "prop": "revisions",
                "rvprop": "content",
                "rvslots": "main",
                "titles": "|".join(batch),
            },
        )
        for page in req.submit()["query"]["pages"].values():
            if "revisions" in page:
                contents[page["title"]] = page["revisions"][0]["slots"]["main"]["*"]
    missing = [t for t in old_titles if t not in contents]
    assert not missing, f"旧页缺失: {missing}"
    print(f"读取旧页 {len(contents)}，开始复制")

    site.login()
    assert site.user() == "IchiSanNi"
    created = skipped = failed = 0
    for i, (title, text) in enumerate(contents.items()):
        new_title = title.replace("MediaWiki:Custom-", "MediaWiki:Custom-nav-", 1)
        try:
            p = pywikibot.Page(site, new_title)
            if p.exists() and p.text == text:
                skipped += 1
                continue
            p.text = text
            p.save(summary="导航简繁转换：Custom- key 加 nav- 前缀（复制）", bot=True)
            created += 1
        except Exception as e:  # noqa: BLE001 批处理脚本：单页失败不中断，计数后非零退出
            failed += 1
            print(f"FAIL {new_title}: {e}")
        if (i + 1) % 200 == 0:
            print(
                f"progress {i + 1}/{len(contents)} created={created} skipped={skipped} failed={failed}"
            )
    print(
        f"DONE created={created} skipped={skipped} failed={failed} total={len(contents)}"
    )
    sys.exit(1 if failed else 0)

elif mode == "update":
    proj = pywikibot.Page(site, "Project:Wiki-navigation")
    src = proj.text
    # 按 key 长度降序替换，避免前缀子串互吃；key 边界为 ]] 或行尾
    new_src = src
    n = 0
    import re

    for key in sorted(OLD_KEYS, key=len, reverse=True):
        new_src, cnt = re.subn(
            re.escape(key) + r"(?=\]\]|\s*$)",
            "Custom-nav-" + key.removeprefix("Custom-"),
            new_src,
            flags=re.MULTILINE,
        )
        n += cnt
    changed = sum(
        1 for a, b in zip(src.splitlines(), new_src.splitlines(), strict=True) if a != b
    )
    print(f"替换引用 {n} 处，变化行 {changed}")
    assert "Custom-" not in new_src or all(
        "Custom-nav-" in line or "Custom-" not in line
        for line in new_src.splitlines()
        if line.startswith("*")
    )
    leftover = [
        line
        for line in new_src.splitlines()
        if "Custom-" in line and "Custom-nav-" not in line
    ]
    print("未加前缀的 Custom- 残留:", leftover)
    if "--simulate" in sys.argv:
        print("SIMULATE, not saving")
        sys.exit(0)
    site.login()
    assert site.user() == "IchiSanNi"
    proj.text = new_src
    proj.save(summary="导航简繁转换：Custom- key 加 nav- 前缀", bot=False, minor=False)
    print("saved")

elif mode == "delete":
    keys = OLD_KEYS[:limit] if limit else OLD_KEYS
    site.login()
    assert site.user() == "IchiSanNi"
    deleted = skipped = failed = 0
    titles = [f"MediaWiki:{k}/{v}" for k in keys for v in old_pages()[k]]
    for i, title in enumerate(titles):
        try:
            p = pywikibot.Page(site, title)
            if not p.exists():
                skipped += 1
                continue
            p.delete(
                reason="导航简繁转换：Custom- key 已加 nav- 前缀，旧 key 删除",
                prompt=False,
            )
            deleted += 1
        except Exception as e:  # noqa: BLE001 批处理脚本：单页失败不中断，计数后非零退出
            failed += 1
            print(f"FAIL {title}: {e}")
        if (i + 1) % 200 == 0:
            print(
                f"progress {i + 1}/{len(titles)} deleted={deleted} skipped={skipped} failed={failed}"
            )
    print(
        f"DONE deleted={deleted} skipped={skipped} failed={failed} total={len(titles)}"
    )
    sys.exit(1 if failed else 0)

else:
    print(__doc__)
    sys.exit(2)
