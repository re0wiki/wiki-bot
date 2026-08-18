"""扫描主命名空间所有 `前缀:词干` 形式的页面，按前缀分组统计。

登记前缀清单取自 user-fixes.py 的 PSEUDO_PREFIXES（唯一权威，经
pywikibot.fixes 导出——import pywikibot.fixes 时 user-fixes.py 被 exec 进其
globals，静态检查不可见）。
"""

from collections import defaultdict

import pywikibot
from pywikibot.fixes import PSEUDO_PREFIXES  # ty: ignore[unresolved-import]

site = pywikibot.Site("zh", "re0")

by_prefix: dict[str, list[str]] = defaultdict(list)
for page in site.allpages(namespace=0):
    title = page.title()
    if ":" in title:
        by_prefix[title.split(":", 1)[0]].append(title)

for prefix, titles in sorted(by_prefix.items()):
    print(f"{prefix} ({len(titles)})")
    if prefix not in PSEUDO_PREFIXES:
        for t in titles:
            print(f"    {t}")
