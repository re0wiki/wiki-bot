"""写速率边界探测：沙盒连续小编辑逐级加快直到触发 429。

用户已确认：bot 未运行，触发限速可接受。编辑仅限 zh 站沙盒，可整页回退。
"""

import sys
import time

import requests

from pywikibot.login import BotPassword

API = "https://rezero.fandom.com/zh/api.php"
SANDBOX = "User:IchiSanNi/沙盒"

# (间隔秒, 编辑数)：0 = 全速
LEVELS = [(0.5, 20), (0.25, 20), (0.0, 20)]

entries = []
with open("user-password.py", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line.startswith("("):
            entries.append(eval(line, {"BotPassword": BotPassword}))
username, bp = entries[0]

s = requests.Session()
s.headers["User-Agent"] = "Pywikibot/write-boundary-probe (re0wiki wiki-bot research)"


def api_post(data):
    r = s.post(API, data={**data, "format": "json"}, timeout=30)
    if r.status_code == 429:
        ra = r.headers.get("Retry-After", "?")
        print(f"[TRIGGERED] 429 on POST {data.get('action')}, Retry-After={ra}")
        sys.exit(2)
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

total = 0
t_all = time.time()
for interval, n in LEVELS:
    t0 = time.time()
    for i in range(n):
        res = api_post(
            {
                "action": "edit",
                "title": SANDBOX,
                "appendtext": f"\nwrite-boundary probe interval={interval}s #{i + 1} "
                f"{time.strftime('%H:%M:%S')}\n",
                "summary": f"写速率边界探测 interval={interval}s（可回退）",
                "token": csrf,
                "bot": "1",
            }
        )
        assert "edit" in res and res["edit"]["result"] == "Success", res
        total += 1
        if interval:
            elapsed = time.time() - t0
            target = (i + 1) * interval
            if target > elapsed:
                time.sleep(target - elapsed)
    dt = time.time() - t0
    print(f"[OK] interval={interval}s: {n} edits in {dt:.0f}s ({n / dt:.2f} edit/s)")

print(f"DONE: {total} edits, zero 429, total {time.time() - t_all:.0f}s")
