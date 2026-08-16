# 一次性探测：config.simulate=True 下 login 后的会话是否真有 apihighlimits
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
site.login()
print("user:", site.user())
print("logged_in:", site.logged_in())
print("rights has apihighlimits:", site.has_right("apihighlimits"))

titles = "|".join(f"角色:菜月·昴{i}" for i in range(500))
try:
    r = site.simple_request(
        action="query", prop="info", titles=titles, formatversion="2", format="json"
    ).submit()
    print("500 titles ->", len(r["query"]["pages"]))
except Exception as e:  # noqa: BLE001 诊断脚本：成功/失败都是有价值输出
    print("500 titles 失败:", str(e)[:80])
