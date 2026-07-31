"""写速率探测：裸 API 登录后在沙盒连续小编辑，逐级加快间隔，遇 429 即停。

编辑目标仅限 zh 站沙盒；每次编辑追加一行时间戳，可整页回退。
"""

import sys
import time

import requests
from pywikibot.login import BotPassword

API = "https://rezero.fandom.com/zh/api.php"
SANDBOX = "User:IchiSanNi/沙盒"

# (间隔秒, 编辑数)：从保守到激进
LEVELS = [(2.0, 10), (1.0, 10)]

# --- login (BotPassword) ---
entries = []
with open("user-password.py", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line.startswith("("):
            entries.append(eval(line, {"BotPassword": BotPassword}))
username, bp = entries[0]

s = requests.Session()
s.headers["User-Agent"] = "Pywikibot/write-rate-probe (re0wiki wiki-bot research)"


def api_post(data):
    r = s.post(API, data={**data, "format": "json"}, timeout=30)
    if r.status_code == 429:
        ra = r.headers.get("Retry-After", "?")
        print(f"[ABORT] 429 on POST {data.get('action')}, Retry-After={ra}")
        sys.exit(1)
    r.raise_for_status()
    return r.json()


tok = s.get(
    API,
    params={"action": "query", "meta": "tokens", "type": "login", "format": "json"},
    timeout=30,
).json()["query"]["tokens"]["logintoken"]
login_res = api_post(
    {
        "action": "login",
        "lgname": bp.login_name(username),
        "lgpassword": bp.password,
        "lgtoken": tok,
    }
)
assert login_res["login"]["result"] == "Success", login_res
csrf = api_post({"action": "query", "meta": "tokens", "type": "csrf"})["query"][
    "tokens"
]["csrftoken"]
print("logged in")

# --- probe ---
total = 0
for interval, n in LEVELS:
    t0 = time.time()
    for i in range(n):
        res = api_post(
            {
                "action": "edit",
                "title": SANDBOX,
                "appendtext": f"\nwrite-rate probe interval={interval}s #{i + 1} "
                f"{time.strftime('%H:%M:%S')}\n",
                "summary": f"写速率探测 interval={interval}s（可回退）",
                "token": csrf,
                "bot": "1",
            }
        )
        assert "edit" in res and res["edit"]["result"] == "Success", res
        total += 1
        elapsed = time.time() - t0
        target = total_this_level = (i + 1) * interval
        if target > elapsed:
            time.sleep(target - elapsed)
    dt = time.time() - t0
    print(f"[OK] interval={interval}s: {n} edits in {dt:.0f}s")

print(f"DONE: {total} edits, zero 429")
