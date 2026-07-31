"""删除 12 个零引用重定向（2026-07-28，用户确认）。

en 站有同名的 9 个已加入 jobs/jobs.py 模板替换任务（bot 会把搬运页里的旧名替换成 Infobox book）；
en 站无同名的 3 个（Infobox novel、Bond of Ice、Ex Manga）直接删。
删除前存档 logs/deleted_redirects_2026-07-28.json，同步更新索引页。
"""

import json

import pywikibot

REDIRECTS = [
    "Infobox novel",
    "Re:Zero Light Novel Volumes",
    "Re:Zero Arc 4 Manga",
    "Re:Zero Arc 5 Manga",
    "Re:Zero Bond of Ice Manga",
    "Re:Zero Bonds of Ice Manga",
    "Re:Zero Daigoshou Manga",
    "Re:Zero Daiisshou Manga",
    "Re:Zero Dainishou Manga",
    "Re:Zero Daisanshou Manga",
    "Re:Zero Daiyonshou Manga",
    "Re:Zero Ex Manga",
]
REASON = "零引用重定向清理：en 同名模板用量已由 jobs 模板替换任务接管（或 en 无同名）"

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

archive = {}
for t in REDIRECTS:
    p = pywikibot.Page(site, f"Template:{t}")
    assert p.exists() and p.isRedirectPage(), t
    archive[p.title()] = p.text
with open("logs/deleted_redirects_2026-07-28.json", "w", encoding="utf-8") as f:
    json.dump(archive, f, ensure_ascii=False, indent=1)
print(f"archived {len(archive)}")

for title in archive:
    p = pywikibot.Page(site, title)
    p.delete(reason=REASON, prompt=False)
    print(f"deleted {title}")

# 索引页「重定向」节更新
idx = pywikibot.Page(site, "ReZero Wiki:模板")
text = idx.text
OLD = "以下模板名是重定向，指向现行模板（多为英文旧名），见到可顺手替换：Infobox Events、Infobox battles、Infobox novel、Re:Zero Light Novel Volumes、Re:Zero Manga Volumes、Re:Zero Arc 4/5 Manga、Re:Zero Bonds of Ice Manga、Re:Zero Daiisshou~Daiyonshou Manga、Re:Zero Daigoshou Manga、Re:Zero Ex Manga。"
NEW = "以下模板名是重定向，指向现行模板（多为英文旧名），见到可顺手替换：Infobox Events、Infobox battles、Re:Zero Manga Volumes。en 站在用的其他英文旧名（Re:Zero Light Novel Volumes、Re:Zero Arc 4/5 Manga 等）由 bot 定期批量替换为 Infobox book，zh 站不再保留同名重定向。"
assert OLD in text
idx.text = text.replace(OLD, NEW)
idx.save(summary="更新重定向节：英文旧名重定向已删，由 bot 批量替换接管", bot=True)
print("updated ReZero Wiki:模板")
print("DONE")
