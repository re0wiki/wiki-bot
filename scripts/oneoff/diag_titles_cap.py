# 一次性探测：titles= 多标题查询的实际上限（bot 账号会话）
import sys

sys.path = [
    p
    for p in sys.path
    if p and not p.replace("\\", "/").rstrip("/").endswith("GitHub/wiki-bot")
]
import pywikibot

site = pywikibot.Site("zh", "re0")
site.login()
print("user:", site.user())

titles = "|".join(f"角色:菜月·昴{i}" for i in range(60))
r = site.simple_request(action="query", prop="info", titles=titles, formatversion="2", format="json").submit()
print("60 titles ->", len(r["query"]["pages"]), "pages returned")

titles = "|".join(f"角色:菜月·昴{i}" for i in range(500))
r = site.simple_request(action="query", prop="info", titles=titles, formatversion="2", format="json").submit()
print("500 titles ->", len(r["query"]["pages"]), "pages returned")
