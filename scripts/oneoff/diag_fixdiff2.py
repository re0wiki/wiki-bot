# 一次性诊断 2：链接表缺失的普遍性 + 页面最后编辑时间
import requests

h = {"User-Agent": "IchiSanNi/debug (https://rezero.fandom.com/wiki/User:IchiSanNi)"}
S = requests.Session()
API = "https://rezero.fandom.com/zh/api.php"


def q(**params):
    r = S.get(API, params={**params, "format": "json", "formatversion": "2"}, headers=h, timeout=15).json()
    if "query" not in r:
        raise SystemExit(f"API error: {r}")
    return r


# (页面, 源码里指向重定向的链接)
cases = [
    ("动画:第79集", "Episode 78"),
    ("动画:第二季", "Puck"),
    ("游戏:虚假的王选候补", "菜月·昴"),
    ("音乐:Ender Ember", "NOX LUX"),
]
for title, link in cases:
    r = q(action="query", titles=title, prop="links|revisions", pllimit="max", rvprop="timestamp", rvlimit="1")
    p = r["query"]["pages"][0]
    links = [l["title"] for l in p.get("links", [])]
    last_edit = p.get("revisions", [{}])[0].get("timestamp")
    print(f"{title}: 链接表含 {link}: {link in links} (共{len(links)}条), 最后编辑 {last_edit}")
