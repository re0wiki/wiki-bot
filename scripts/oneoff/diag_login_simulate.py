# 一次性探测：simulate 模式下 login 是否被拦截 + 匿名 titles= 上限
import sys

sys.path = [
    p
    for p in sys.path
    if p and not p.replace("\\", "/").rstrip("/").endswith("GitHub/wiki-bot")
]
import pywikibot
from pywikibot import config

config.simulate = True
site = pywikibot.Site("zh", "re0")
try:
    site.login()
    print("simulate 下 login 成功, user =", site.user())
except Exception as e:
    print("simulate 下 login 失败:", type(e).__name__, str(e)[:120])

# 匿名（新会话）50+ titles
site2 = pywikibot.Site("zh", "re0")
titles = "|".join(f"角色:菜月·昴{i}" for i in range(60))
try:
    r = site2.simple_request(action="query", prop="info", titles=titles, formatversion="2", format="json").submit()
    print("匿名 60 titles ->", len(r["query"]["pages"]))
except Exception as e:
    print("匿名 60 titles 失败:", type(e).__name__, str(e)[:120])
