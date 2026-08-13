# 一次性诊断：48 处改写涉及的重定向创建时间 + 链接表是否含这些链接
import requests

h = {"User-Agent": "IchiSanNi/debug (https://rezero.fandom.com/wiki/User:IchiSanNi)"}
S = requests.Session()
API = "https://rezero.fandom.com/zh/api.php"


def q(**params):
    r = S.get(API, params={**params, "format": "json", "formatversion": "2"}, headers=h, timeout=15).json()
    if "query" not in r:
        raise SystemExit(f"API error: {r}")
    return r


# 1. 涉及重定向的创建时间（rvdir=newer 只支持单页，逐页查）
print("== 重定向创建时间 ==")
for title in ["Episode 78", "Puck", "菜月·昴", "Rem", "NOX LUX", "Manga Arc 4 Chapter 70 Part 2", "Re:IF Kasaneru", "Salum", "Break Time Episode 66"]:
    r = q(action="query", titles=title, prop="revisions", rvdir="newer", rvlimit="1", rvprop="timestamp")
    p = r["query"]["pages"][0]
    print(p["title"], p.get("revisions", [{}])[0].get("timestamp"))

# 2. 链接表（派生表）是否含这些链接：以 动画:第79集 为例
r = q(action="query", titles="动画:第79集", prop="links", pllimit="max")
links = [l["title"] for l in r["query"]["pages"][0].get("links", [])]
print("\n== 动画:第79集 链接表含 Episode 78/80:", "Episode 78" in links, "Episode 80" in links, f"(共 {len(links)} 条)")

# 3. 对照：该页源码里确实有 [[Episode 78]]
r = q(action="query", titles="动画:第79集", prop="revisions", rvprop="content", rvslots="main")
text = r["query"]["pages"][0]["revisions"][0]["slots"]["main"]["content"]
print("源码含 [[Episode 78]]:", "[[Episode 78]]" in text)
