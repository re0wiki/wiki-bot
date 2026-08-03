"""摘除 Infobox character/doc templatedata 里全部陈旧 aliases（08-02 废弃旧名）。

精确匹配单元素 aliases 块 → 删除 → JSON 校验 → 保存（bot=False）→ parse 验证。
"""

import json
import re

from pywikibot.data import api

import pywikibot

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

doc = pywikibot.Page(site, "Template:Infobox character/doc")
text = doc.text

pat = re.compile(r'\t\t\t"aliases": \[\n\t\t\t\t"[^"]*"\n\t\t\t\],\n')
new_text, n = pat.subn("", text)
assert n == 30, f"命中 {n} 个 aliases 块，预期 30"

# JSON 校验
m = re.search(
    r"<templatedata>(.*?)</templatedata>", new_text, re.DOTALL | re.IGNORECASE
)
td = json.loads(m.group(1))
assert not any("aliases" in v for v in td["params"].values()), "aliases 未摘净"
assert len(td["params"]) == 42, f"参数数 {len(td['params'])}，预期 42（41+name_zh_tw）"

doc.text = new_text
doc.save(
    summary="templatedata 摘除 30 个陈旧 aliases（08-02 已废弃的旧参数名，模板体不再识别）"
)
print(f"saved，摘除 {n} 个 aliases 块，JSON 校验通过（{len(td['params'])} 参数）")

# parse 验证文档盒在模板页正常渲染
r = api.Request(
    site=site,
    parameters={
        "action": "parse",
        "format": "json",
        "page": "Template:Infobox character",
        "prop": "text",
        "disablelimitreport": "1",
    },
).submit()
html = r["parse"]["text"]["*"]
assert "name_zh_tw" in html and "台版译名" in html, "文档渲染异常"
print("parse 验证通过：文档盒含 name_zh_tw/台版译名")
