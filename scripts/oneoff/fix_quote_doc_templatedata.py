"""C11 收尾：Quote/doc 追加 templatedata（从 Quote/main 摘除的那块）。"""

import os
import re

os.environ.pop("PYTHONPATH", None)

import pywikibot

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi", site.user()

# Quote/main 现状应已无 templatedata；从其历史版本取回原块太绕，
# 直接按摘除前的内容重建（与 fix_batch_bc_templates.py 中删除的一致）。
TD = """<templatedata>
{
\t"params": {
\t\t"1": {
\t\t\t"description": "引用内容",
\t\t\t"example": "人被杀，就会死。",
\t\t\t"type": "string",
\t\t\t"required": true
\t\t},
\t\t"2": {
\t\t\t"description": "出处",
\t\t\t"example": "卫宫士郎",
\t\t\t"type": "string",
\t\t\t"suggested": true
\t\t},
\t\t"3": {
\t\t\t"description": "称号（当出处为某人时）",
\t\t\t"example": "阿瓦隆持有者",
\t\t\t"type": "string"
\t\t},
\t\t"small": {
\t\t\t"description": "非空则使用较小字体，留空则使用较大字体",
\t\t\t"type": "string"
\t\t},
\t\t"voice": {
\t\t\t"description": "语音文件",
\t\t\t"type": "wiki-file-name",
\t\t\t"example": "IchiSanNi.ogg"
\t\t}
\t},
\t"description": "引用。"
}
</templatedata>
"""

p = pywikibot.Page(site, "Template:Quote/main")
assert "<templatedata>" not in p.text, "Quote/main 仍有 templatedata？"

p = pywikibot.Page(site, "Template:Quote/doc")
text = p.text
assert "<templatedata>" not in text, "Quote/doc 已有 templatedata"
p.text = text.rstrip("\n") + "\n" + TD
p.save(
    summary="接收自 Quote/main 迁入的 templatedata（QUOTE/Quote/Quote/main 三页共享）",
    bot=False,
)
print("saved Template:Quote/doc")

# 验证：三个模板页 parse 应各恰好 1 个 templatedata
from pywikibot.data import api

for t in ["Template:QUOTE", "Template:Quote", "Template:Quote/main"]:
    req = api.Request(
        site=site,
        parameters={"action": "parse", "page": t, "prop": "text"},
    )
    html = req.submit()["parse"]["text"]["*"]
    n = html.count("mw-templatedata-doc-wrap") + len(
        re.findall(r"<b>模板文件</b>", html)
    )
    print(f"{t}: 文档盒标记数 = {n}")
print("DONE")
