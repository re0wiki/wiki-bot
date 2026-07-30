"""拉取 zh 站全部 Module 源码到 logs/modules/（只读 wiki，写本地文件）。"""

import os

os.environ.pop("PYTHONPATH", None)

from pywikibot.data import api

import pywikibot

site = pywikibot.Site("zh", "re0")

gen = api.QueryGenerator(
    site=site,
    action="query",
    generator="allpages",
    gapnamespace=828,
    gaplimit="max",
    prop="revisions",
    rvprop="content",
    rvslots="main",
)

outdir = "logs/modules"
os.makedirs(outdir, exist_ok=True)

n = 0
for info in gen:
    title = info["title"].split(":", 1)[1]
    if title.endswith("/doc"):  # 文档子页跳过
        continue
    revs = info.get("revisions")
    text = revs[0]["slots"]["main"]["*"] if revs else ""
    fname = title.replace("/", "__") + ".lua"
    with open(os.path.join(outdir, fname), "w", encoding="utf-8") as f:
        f.write(text)
    n += 1
    print(f"{title:<40} {len(text):>6} chars")

print(f"\n共 {n} 个模块")
