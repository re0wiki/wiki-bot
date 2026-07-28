"""单点模板内联 + 删除（2026-07-28，用户确认全做）。

- Web Novel Chapter List -> 内联进 小说:Web（无参数，单层 tabber）
- USERNAME -> 攻略指南（展开为 mediaWikiData span），连带 MW 变零引用
- Facebook/Instagram -> 两个声优页（参数 # 替换；西语文本保留，用户另行专项清理）
- DISPLAYTITLE -> 纱提拉是重定向页（-> 角色:莎缇拉），调用无意义，直接摘除
- Example -> 空模板，直接删（他人沙盒不动）
每页编辑前后 parse 对比验证渲染等价；删除前存档 logs/。
"""

import json
import re

from pywikibot.data import api

import pywikibot

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"


def transclude_body(text):
    text = re.sub(r"<noinclude>.*?</noinclude>", "", text, flags=re.DOTALL)
    if "<onlyinclude>" in text:
        return "".join(
            re.findall(r"<onlyinclude>(.*?)</onlyinclude>", text, flags=re.DOTALL)
        )
    return re.sub(r"</?includeonly>", "", text)


def render(title):
    return api.Request(
        site=site,
        parameters={"action": "parse", "page": title, "prop": "text", "format": "json"},
    ).submit()["parse"]["text"]["*"]


def norm(h):
    h = re.sub(r'data-widget-id="[0-9a-f]+"', 'data-widget-id="X"', h)
    h = re.sub(r"<!--.*?-->", "", h, flags=re.DOTALL)
    return re.sub(r">\s+<", "><", h)


tpl = lambda n: pywikibot.Page(site, f"Template:{n}")

# ---- 1. Web Novel Chapter List -> 小说:Web ----
title = "小说:Web"
p = pywikibot.Page(site, title)
if "{{Web Novel Chapter List}}" in p.text:
    before = norm(render(title))
    body = transclude_body(tpl("Web Novel Chapter List").text)
    p.text = p.text.replace("{{Web Novel Chapter List}}", body)
    p.save(summary="内联 Template:Web Novel Chapter List（唯一使用页）")
    assert norm(render(title)) == before, f"{title} 渲染不一致"
    print(f"OK {title}")
else:
    print(f"SKIP {title}（已内联）")

# ---- 2. USERNAME -> 攻略指南（首轮已写入，此处清理 span 尾部换行）----
title = "ReZero Wiki:攻略指南"
p = pywikibot.Page(site, title)
if re.search(r"\{\{USERNAME\|", p.text):
    before = norm(render(title))
    mw_body = transclude_body(tpl("MW").text).rstrip("\n")
    m = re.search(r"\{\{USERNAME\|([^{}]*)\}\}", p.text)
    span = mw_body.replace("{{{1}}}", "wgUserName").replace("{{{2}}}", m.group(1))
    p.text = p.text.replace(m.group(0), span)
    p.save(summary="内联 Template:USERNAME/MW（唯一使用页）")
    assert norm(render(title)) == before, f"{title} 渲染不一致"
    print(f"OK {title}")
elif '<span class="mediaWikiData" data-var="wgUserName">人类</span>\n]]' in p.text:
    p.text = p.text.replace(
        '<span class="mediaWikiData" data-var="wgUserName">人类</span>\n]]',
        '<span class="mediaWikiData" data-var="wgUserName">人类</span>]]',
    )
    p.save(summary="清理内联 span 尾部换行")
    print(f"OK {title}（清理换行）")
else:
    print(f"SKIP {title}")

# ---- 3. Facebook / Instagram -> 声优页（保留西语文本，专项清理另行处理）----
for name, title in [("Facebook", "声优:水濑祈"), ("Instagram", "声优:堀江由衣")]:
    before = norm(render(title))
    body = transclude_body(tpl(name).text)
    p = pywikibot.Page(site, title)
    m = re.search(r"\{\{" + name + r"\|#=([^{}]*)\}\}", p.text)
    assert m, title
    p.text = p.text.replace(m.group(0), body.replace("{{{#|}}}", m.group(1)))
    p.save(summary=f"内联 Template:{name}（唯一使用页）")
    assert norm(render(title)) == before, f"{title} 渲染不一致"
    print(f"OK {title}")

# ---- 4. DISPLAYTITLE：纱提拉是重定向页，调用无意义，摘除 ----
p = pywikibot.Page(site, "纱提拉")
assert p.isRedirectPage()
assert "{{DISPLAYTITLE|莎缇拉}}" in p.text
p.text = p.text.replace("{{DISPLAYTITLE|莎缇拉}}\n", "").replace(
    "{{DISPLAYTITLE|莎缇拉}}", ""
)
p.save(summary="重定向页无需 DISPLAYTITLE，摘除（模板将删）")
print("OK 纱提拉")

# ---- 5. 删除模板（存档）----
PAGES = [
    "Template:Web Novel Chapter List",
    "Template:USERNAME",
    "Template:MW",
    "Template:Facebook",
    "Template:Instagram",
    "Template:DISPLAYTITLE",
    "Template:DISPLAYTITLE/doc",
    "Template:Example",
]
archive = {}
for t in PAGES:
    page = pywikibot.Page(site, t)
    assert page.exists(), t
    archive[t] = page.text
with open("logs/deleted_single_use_inline_2026-07-28.json", "w", encoding="utf-8") as f:
    json.dump(archive, f, ensure_ascii=False, indent=1)
for t in PAGES:
    pywikibot.Page(site, t).delete(
        reason="唯一使用页已内联/调用无意义（单点模板清理）", prompt=False
    )
    print(f"deleted {t}")
print("DONE")
