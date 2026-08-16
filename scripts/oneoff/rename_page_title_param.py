"""page-title → page_title：Disambiguation 体 + /doc（零真实调用，无需 fallback）。"""

import json
import re

from pywikibot.data import api

import pywikibot

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

for title in ("Template:Disambiguation", "Template:Disambiguation/doc"):
    page = pywikibot.Page(site, title)
    n = page.text.count("page-title")
    assert n >= 1, f"{title} 未命中"
    page.text = page.text.replace("page-title", "page_title")
    page.save(summary="参数名归一：page-title → page_title（零真实调用，直接改）")
    print(f"saved {title}（{n} 处）")

# JSON 校验 + parse 验证
doc = pywikibot.Page(site, "Template:Disambiguation/doc").text
m = re.search(r"<templatedata>(.*?)</templatedata>", doc, re.DOTALL)
assert m, "未找到 templatedata 块"
td = json.loads(m.group(1))
print(f"templatedata 键: {list(td.get('params', {}).keys())}")

r = api.Request(
    site=site,
    parameters={
        "action": "parse",
        "format": "json",
        "page": "琉兹 (消歧义)",
        "prop": "text",
        "disablelimitreport": "1",
    },
).submit()
html = r["parse"]["text"]["*"]
assert (
    "内部链接" in html
    and "Whatlinkshere" in html
    or "Special:Whatlinkshere" in html
    or "whatlinkshere" in html.lower()
)
print("parse 验证通过（消歧义页正常渲染）")
