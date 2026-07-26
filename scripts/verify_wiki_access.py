"""Verify both wiki access paths are functional (read-only, no new edits).

Usage: PYTHONPATH= .venv/Scripts/python.exe scripts/verify_wiki_access.py
Working dir: wiki-bot repo root.
"""

import pywikibot
import requests
from pywikibot.login import BotPassword

API = "https://rezero.fandom.com/zh/api.php"
SANDBOX = "User:IchiSanNi/沙盒"

# --- 1. pywikibot library path ---
site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi", f"unexpected user: {site.user()}"
text = pywikibot.Page(site, SANDBOX).text
assert text, "sandbox returned empty text"
print(f"[1] pywikibot: logged in as {site.user()}, sandbox {len(text)} chars")

# --- 2. raw API path ---
entries = []
with open("user-password.py", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line.startswith("("):
            entries.append(eval(line, {"BotPassword": BotPassword}))  # noqa: S307
username, bp = entries[0]

s = requests.Session()
tok = s.get(
    API,
    params={"action": "query", "meta": "tokens", "type": "login", "format": "json"},
).json()["query"]["tokens"]["logintoken"]

login_res = s.post(
    API,
    data={
        "action": "login",
        "lgname": bp.login_name(username),
        "lgpassword": bp.password,
        "lgtoken": tok,
        "format": "json",
    },
).json()
assert login_res["login"]["result"] == "Success", login_res

r = s.get(
    API,
    params={
        "action": "query",
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "titles": SANDBOX,
        "format": "json",
        "formatversion": "2",
    },
).json()
content = r["query"]["pages"][0]["revisions"][0]["slots"]["main"]["content"]
assert content, "sandbox returned empty content via raw API"
print(f"[2] raw API: login {login_res['login']['result']}, sandbox {len(content)} chars")

print("ALL CHECKS PASSED")
