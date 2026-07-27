# -*- coding: utf-8 -*-
"""读速率边界探测：逐级加快直到触发 429，记录触发点与 Retry-After。

用户已确认：bot 未运行，触发限速可接受。
"""

import sys
import time

import requests

API = "https://rezero.fandom.com/zh/api.php"
UA = "Pywikibot/rate-probe (re0wiki wiki-bot research)"

s = requests.Session()
s.headers["User-Agent"] = UA

# (间隔秒, 请求数)：0 = 全速
LEVELS = [(0.15, 400), (0.10, 400), (0.05, 600), (0.02, 600), (0.0, 1000)]

apfrom = ""
total_req = 0
t_all = time.time()
for interval, n in LEVELS:
    ok = 0
    t0 = time.time()
    for i in range(n):
        params = {
            "action": "query",
            "list": "allpages",
            "aplimit": "500",
            "apfrom": apfrom,
            "format": "json",
        }
        r = s.get(API, params=params, timeout=30)
        total_req += 1
        if r.status_code == 429:
            ra = r.headers.get("Retry-After", "?")
            dt = time.time() - t0
            print(
                f"[TRIGGERED] interval={interval}s: 429 after {ok} ok reqs "
                f"in {dt:.0f}s ({ok / max(dt, 0.01):.2f} req/s), "
                f"Retry-After={ra}, total_req={total_req}, "
                f"total_time={time.time() - t_all:.0f}s"
            )
            sys.exit(2)
        r.raise_for_status()
        data = r.json()
        pages = data["query"]["allpages"]
        if pages:
            apfrom = pages[-1]["title"]
        ok += 1
        if interval:
            elapsed = time.time() - t0
            target = ok * interval
            if target > elapsed:
                time.sleep(target - elapsed)
    dt = time.time() - t0
    print(f"[OK] interval={interval}s: {ok} reqs in {dt:.0f}s ({ok / dt:.2f} req/s)")

print(f"DONE: {total_req} requests, zero 429, total {time.time() - t_all:.0f}s")
