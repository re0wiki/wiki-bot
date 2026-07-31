"""删除重定向 Infobox battles 与 Re:Zero Manga Volumes（2026-07-28，用户确认）。

两者均为 en 站搬运名（en 各有 31/44 引用），已加入 jobs 模板替换。
先改 zh 现存调用，再删重定向；索引页重定向节清空改写。存档 logs/。
"""

import json
import re

import pywikibot

RENAMES = {
    "Infobox battles": (
        "Infobox battle",
        ["术语:卢克尼卡颠覆阴谋", "术语:米洛德邸事件"],
    ),
    "Re:Zero Manga Volumes": ("Infobox book", ["漫画:第4章第13卷"]),
}

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

for old, (new, pages) in RENAMES.items():
    pat = re.compile(
        r"\{\{\s*" + re.escape(old).replace(r"\ ", r"[ _]") + r"\s*", re.IGNORECASE
    )
    for title in pages:
        p = pywikibot.Page(site, title)
        newtext = pat.sub("{{" + new + " ", p.text)
        assert newtext != p.text, title
        p.text = newtext
        p.save(summary=f"模板改名：{old} -> {new}（规范名）", bot=True)
        print(f"renamed usage in {title}")

archive = {}
for old in RENAMES:
    rd = pywikibot.Page(site, f"Template:{old}")
    assert rd.exists() and rd.isRedirectPage(), old
    archive[rd.title()] = rd.text
with open("logs/deleted_redirects_round3_2026-07-28.json", "w", encoding="utf-8") as f:
    json.dump(archive, f, ensure_ascii=False, indent=1)
for title in archive:
    p = pywikibot.Page(site, title)
    p.delete(reason="英文站搬运名重定向：用量已由 jobs 模板替换任务接管", prompt=False)
    print(f"deleted {title}")

idx = pywikibot.Page(site, "ReZero Wiki:模板")
text = idx.text
OLD = "以下模板名是重定向，指向现行模板（多为英文旧名），见到可顺手替换：Infobox battles、Re:Zero Manga Volumes。en 站在用的其他英文旧名（Re:Zero Light Novel Volumes、Re:Zero Arc 4/5 Manga 等）由 bot 定期批量替换为 Infobox book，zh 站不再保留同名重定向。"
NEW = "英文站搬运页里的旧模板名（Re:Zero Light Novel Volumes、Re:Zero Arc 4/5 Manga、Re:Zero Manga Volumes、Infobox Events、Infobox battles 等）由 bot 定期批量替换为规范名（Infobox book、Infobox event、Infobox battle 等），zh 站不保留同名重定向。"
assert OLD in text
idx.text = text.replace(OLD, NEW)
idx.save(summary="重定向节清空：英文旧名全部由 bot 批量替换接管", bot=True)
print("updated ReZero Wiki:模板")
print("DONE")
