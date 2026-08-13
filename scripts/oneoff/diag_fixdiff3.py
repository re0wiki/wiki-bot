# 一次性诊断 3：缺失链接在源码中的上下文
import re

import requests

h = {"User-Agent": "IchiSanNi/debug (https://rezero.fandom.com/wiki/User:IchiSanNi)"}
S = requests.Session()
API = "https://rezero.fandom.com/zh/api.php"

for title, link in [("动画:第79集", "[[Episode 78]]"), ("游戏:虚假的王选候补", "[[菜月·昴]]"), ("音乐:Ender Ember", "[[NOX LUX]]")]:
    r = S.get(API, params={"action": "query", "titles": title, "prop": "revisions", "rvprop": "content", "rvslots": "main", "format": "json", "formatversion": "2"}, headers=h, timeout=15).json()
    text = r["query"]["pages"][0]["revisions"][0]["slots"]["main"]["content"]
    i = text.find(link)
    ctx = text[max(0, i - 120) : i + len(link) + 40].replace("\n", "\\n")
    print(f"== {title} ==\n...{ctx}...\n")
