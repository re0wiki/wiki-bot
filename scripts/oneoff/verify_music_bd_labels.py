"""只读：music label 中文化验证——含 name_ja_kanji 的页面应显示 日文/罗马字 而非 Kanji/Romaji。"""

import os

os.environ.pop("PYTHONPATH", None)

import pywikibot
from pywikibot.data import api

site = pywikibot.Site("zh", "re0")
import re

html = api.Request(
    site=site, parameters={"action": "parse", "page": "音乐:小孩子的梦", "prop": "text"}
).submit()["parse"]["text"]["*"]
labels = re.findall(r"pi-data-label[^>]*>([^<]+)</h3>", html)
print(f"音乐:小孩子的梦 label 列表: {labels}")
assert "日文" in labels, "缺 日文 label"
assert "Kanji" not in labels and "Romaji" not in labels, "仍有英文 label"
print("label 中文化 OK（罗马字行仅在传 name_ja_romaji 时渲染）")

# bd label 验证：找一个含 Previous/Next 的圆盘页
tpl = pywikibot.Page(site, "Template:Infobox bd")
target = None
for page in tpl.embeddedin(namespaces=0):
    if "Previous" in page.text:
        target = page.title()
        break
if target:
    html = api.Request(
        site=site, parameters={"action": "parse", "page": target, "prop": "text"}
    ).submit()["parse"]["text"]["*"]
    assert "前一卷" in html and "圆盘序列" in html, f"{target} 缺中文 label"
    assert "Volume Chronology" not in html and ">Previous<" not in html
    print(f"{target} — bd label 中文化 OK")
else:
    print("（无含 Previous 的圆盘页，跳过 bd 渲染验证）")
