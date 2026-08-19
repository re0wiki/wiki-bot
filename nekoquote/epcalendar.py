"""拉 en 站 51-90 集首播日期 → logs/nekoquote/ep_calendar.json。"""

import json
import re
from pathlib import Path

import pywikibot

site = pywikibot.Site("en", "re0")

cal = {}
for n in range(51, 91):
    p = pywikibot.Page(site, f"Episode {n}")
    if not p.exists():
        print(f"第{n}集: 不存在（到顶）")
        break
    m = re.search(r"Air Date\s*=\s*(.*?)(?:\n\||\n\}\})", p.text, re.DOTALL)
    raw = m.group(1) if m else ""
    # Broadcast 日期优先（正式播出）；否则取第一个日期
    bm = re.search(r"(\w+ \d{1,2}, \d{4})\s*\(Broadcast\)", raw)
    fm = re.search(r"(\w+ \d{1,2}, \d{4})", raw)
    date = bm.group(1) if bm else (fm.group(1) if fm else None)
    cal[n] = date
    print(f"第{n}集: {date}")

Path("logs/nekoquote/ep_calendar.json").write_text(
    json.dumps(cal, ensure_ascii=False, indent=1), encoding="utf-8"
)
