"""删除重定向 Template:Infobox Events（2026-07-28，用户确认）。

en 站有同名模板（4 引用），已加入 jobs 模板替换（Infobox Events -> Infobox event）。
先把 zh 现存 2 处调用改成规范名，再删重定向；索引页同步。存档 logs/。
"""

import json
import re

import pywikibot

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

# 1. 现存调用改名（避免删重定向后页面破渲染；jobs 之后处理搬运页）
pat = re.compile(r"\{\{\s*Infobox[ _]Events\s*", re.IGNORECASE)
for title in ["术语:王室疫病", "术语:王族誘拐案"]:
    p = pywikibot.Page(site, title)
    new = pat.sub("{{Infobox event ", p.text)
    assert new != p.text, title
    p.text = new
    p.save(summary="模板改名：Infobox Events -> Infobox event（规范名）", bot=True)
    print(f"renamed usage in {title}")

# 2. 存档 + 删除重定向
rd = pywikibot.Page(site, "Template:Infobox Events")
assert rd.exists() and rd.isRedirectPage()
with open(
    "logs/deleted_redirect_infobox_events_2026-07-28.json", "w", encoding="utf-8"
) as f:
    json.dump({rd.title(): rd.text}, f, ensure_ascii=False, indent=1)
rd.delete(
    reason="英文站搬运名重定向：用量已由 jobs 模板替换任务接管（-> Infobox event）",
    prompt=False,
)
print("deleted Template:Infobox Events")

# 3. 索引页
idx = pywikibot.Page(site, "ReZero Wiki:模板")
text = idx.text
OLD = "以下模板名是重定向，指向现行模板（多为英文旧名），见到可顺手替换：Infobox Events、Infobox battles、Re:Zero Manga Volumes。"
NEW = "以下模板名是重定向，指向现行模板（多为英文旧名），见到可顺手替换：Infobox battles、Re:Zero Manga Volumes。"
assert OLD in text
idx.text = text.replace(OLD, NEW)
idx.save(summary="更新重定向节：Infobox Events 已删，由 bot 批量替换接管", bot=True)
print("updated ReZero Wiki:模板")
print("DONE")
