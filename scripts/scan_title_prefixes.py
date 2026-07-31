"""扫描主命名空间所有 `前缀:词干` 形式的页面，按前缀分组统计。"""

from collections import defaultdict

import pywikibot

site = pywikibot.Site("zh", "re0")

by_prefix: dict[str, list[str]] = defaultdict(list)
for page in site.allpages(namespace=0):
    title = page.title()
    if ":" in title:
        by_prefix[title.split(":", 1)[0]].append(title)

for prefix, titles in sorted(by_prefix.items()):
    print(f"{prefix} ({len(titles)})")
    if prefix not in [
        "角色",
        "术语",
        "小说",
        "漫画",
        "动画",
        "游戏",
        "音乐",
        "设定集、画集",
        "声优",
        "制作人员",
        "存档",
    ]:
        for t in titles:
            print(f"    {t}")
