# -*- coding: utf-8 -*-
"""读速率探测：匿名 GET list=allpages，逐级加快间隔，遇 429 即停。

不触发 429 的间隔就是 minthrottle 的候选值。
"""

import sys
import time

import requests

API = "https://rezero.fandom.com/zh/api.php"
UA = "Pywikibot/rate-probe (re0wiki wiki-bot research)"

s = requests.Session()
s.headers["User-Agent"] = UA

# (间隔秒, 请求数)：从保守到激进；全部通过后再加更快的档
LEVELS = [(0.35, 300), (0.25, 300), (0.20, 300)]

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
            print(
                f"[ABORT] 429 at interval={interval}s after {ok}/{n} ok, "
                f"Retry-After={ra}, total_req={total_req}"
            )
            sys.exit(1)
        r.raise_for_status()
        data = r.json()
        pages = data["query"]["allpages"]
        if pages:
            apfrom = pages[-1]["title"]
        ok += 1
        # 精确控制请求起始间隔
        elapsed = time.time() - t0
        target = ok * interval
        if target > elapsed:
            time.sleep(target - elapsed)
    dt = time.time() - t0
    print(f"[OK] interval={interval}s: {ok} reqs in {dt:.0f}s ({ok / dt:.2f} req/s)")

print(f"DONE: {total_req} requests, zero 429, total {time.time() - t_all:.0f}s")
