"""跨语言链接审计 v3（用户指定的正确方式，全程只读）。

模型：transferbot 把 en 主空间每页搬到 zh 并保持原名，随后人工移动到中文名并留重定向。
- en→zh 映射：遍历 en 主空间每个非重定向页面 E → zh 同名页（通常是重定向）→ 最终重定向目标 Z。
- zh→en 映射：zh 主空间所有页面**源码**里的 [[en:...]]（不读 langlinks 派生表——今日实证其可与源码不一致）。
- 比对输出：
  match                 E→Z 且 Z 源码含 [[en:E]]
  missing_link          E→Z 但 Z 源码无 en 链接
  divergent             E→Z 但 Z 源码链接的是别的 en 页
  untransferred         en 页在 zh 无同名页（新创建未搬运，预期存在）
  dead_link             zh 页链接的 en 页不存在
  link_via_en_redirect  zh 页链接指向 en 的重定向（应指最终目标）
  link_no_counterpart   zh 页链接的 en 页存在，但该 en 页在 zh 无同名页（未经搬运链）
  redirect_with_link    zh 重定向页自身携带 en 链接（链接应在最终目标页上）
"""

import json
import os
import re
import time

import requests

os.makedirs("logs", exist_ok=True)

ZH = "https://rezero.fandom.com/zh/api.php"
EN = "https://rezero.fandom.com/api.php"
S = requests.Session()

EN_LINK_RE = re.compile(
    r"\[\[en:([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]"
)  # 剥 #片段与 |显示文本


def api(base, **params):
    params.update(format="json", formatversion="2")
    for attempt in range(5):
        try:
            r = S.post(base, data=params, timeout=60)
            if r.status_code == 200:
                return r.json()
        except requests.RequestException:
            pass
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"API failed: {base}")


def cont_params(d):
    return {k: v for k, v in d.get("continue", {}).items() if k != "continue"}


def batched(seq, n=50):
    seq = list(seq)
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


# ---------- A. en 主空间全页 + 重定向标记 ----------
en_pages, en_redirects = [], {}
cont = {}
while True:
    d = api(
        EN,
        action="query",
        generator="allpages",
        gapnamespace="0",
        gaplimit="max",
        prop="info",
        **cont,
    )
    for p in d["query"]["pages"]:
        if "redirect" in p:
            en_redirects[p["title"]] = True
        else:
            en_pages.append(p["title"])
    if "continue" not in d:
        break
    cont = cont_params(d)
print(f"en 主空间: {len(en_pages)} 正文页 + {len(en_redirects)} 重定向")

# en 重定向目标（用于 link_via_en_redirect 判定；批量 redirects=1 顺带拿）
en_redir_target = {}
for chunk in batched(sorted(en_redirects)):
    d = api(EN, action="query", titles="|".join(chunk), redirects="1", prop="info")
    for r in d["query"].get("redirects", []):
        en_redir_target[r["from"]] = r["to"]
    time.sleep(0.2)


def resolve(t, norm, redir):
    t = norm.get(t, t)
    seen = set()
    while t in redir and t not in seen:
        seen.add(t)
        t = redir[t]
    return t


# ---------- B. en→zh：同名页 → zh 最终重定向目标 ----------
en_to_zh = {}  # en title -> zh final title
untransferred = []
for chunk in batched(en_pages):
    d = api(ZH, action="query", titles="|".join(chunk), redirects="1", prop="info")
    norm = {x["from"]: x["to"] for x in d["query"].get("normalized", [])}
    redir = {x["from"]: x["to"] for x in d["query"].get("redirects", [])}
    pages = {p["title"]: p for p in d["query"]["pages"]}

    for e in chunk:
        z = resolve(e, norm, redir)
        p = pages.get(z)
        if p is None or "missing" in p:
            untransferred.append(e)
        else:
            en_to_zh[e] = z
    time.sleep(0.2)
print(f"en→zh 映射: {len(en_to_zh)}，zh 无同名页（未搬运）: {len(untransferred)}")

# ---------- C. zh→en：全页源码扫 [[en:...]] ----------
zh_link = {}  # zh title -> en link target（正文页）
redirect_with_link = {}  # zh redirect title -> en link target
zh_all = []
cont = {}
while True:
    d = api(
        ZH,
        action="query",
        generator="allpages",
        gapnamespace="0",
        gaplimit="50",
        prop="info|revisions",
        rvprop="content",
        rvslots="main",
        **cont,
    )
    for p in d["query"]["pages"]:
        t = p["title"]
        zh_all.append(t)
        text = p["revisions"][0]["slots"]["main"]["content"] if "revisions" in p else ""
        m = EN_LINK_RE.search(text)
        if m:
            if "redirect" in p:
                redirect_with_link[t] = m.group(1)
            else:
                zh_link[t] = m.group(1)
    if "continue" not in d:
        break
    cont = cont_params(d)
    time.sleep(0.2)
print(
    f"zh 主空间: {len(zh_all)}，源码含 en 链接: {len(zh_link)}（另 {len(redirect_with_link)} 个重定向页带链接）"
)

# ---------- D. 比对 ----------
zh_to_en = dict(zh_link)
en_set = set(en_pages)

match, missing_link, divergent = [], [], []
for e, z in sorted(en_to_zh.items()):
    linked = zh_to_en.get(z)
    if linked is None:
        missing_link.append((e, z))
    elif linked == e:
        match.append((e, z))
    else:
        divergent.append((e, z, linked))

dead_link, link_via_en_redirect, link_no_counterpart = [], [], []
for z, e in sorted(zh_to_en.items()):
    if e in en_set:
        if en_to_zh.get(e) == z:
            continue  # match，已统计
        link_no_counterpart.append((z, e, en_to_zh.get(e)))
    elif e in en_redir_target:
        link_via_en_redirect.append((z, e, en_redir_target[e]))
    else:
        dead_link.append((z, e))

result = {
    "match": match,
    "missing_link": missing_link,
    "divergent": divergent,
    "untransferred": untransferred,
    "dead_link": dead_link,
    "link_via_en_redirect": link_via_en_redirect,
    "link_no_counterpart": link_no_counterpart,
    "redirect_with_link": sorted(redirect_with_link.items()),
}
with open("logs/langlink_audit_v3.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=1)

print(f"""
===== 比对结果 =====
match（一致）:            {len(match)}
missing_link（缺链接）:   {len(missing_link)}
divergent（链接到别处）:  {len(divergent)}
untransferred（未搬运）:  {len(untransferred)}
dead_link（en 页不存在）: {len(dead_link)}
link_via_en_redirect:     {len(link_via_en_redirect)}
link_no_counterpart:      {len(link_no_counterpart)}
redirect_with_link:       {len(redirect_with_link)}
""")
for name in (
    "missing_link",
    "divergent",
    "dead_link",
    "link_via_en_redirect",
    "link_no_counterpart",
    "redirect_with_link",
):
    rows = result[name]
    if not rows:
        continue
    print(f"--- {name} ---")
    for r in rows[:60]:
        print("  " + " | ".join(str(x) for x in r))
    if len(rows) > 60:
        print(f"  ... 共 {len(rows)} 条，详见 logs/langlink_audit_v3.json")
print("--- untransferred 抽样 ---")
for e in untransferred[:20]:
    print("  " + e)
if len(untransferred) > 20:
    print(f"  ... 共 {len(untransferred)} 条")
