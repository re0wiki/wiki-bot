"""voice 系归一步骤②③：Infobox character 加 voice_zh_* fallback + 菜月·昴快照。"""

import json
import os

from pywikibot.data import api

import pywikibot

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

tpl = pywikibot.Page(site, "Template:Infobox character")
REPL = [
    (
        '    <data source="voice_zh-cn">\n      <label>普通话（中国大陆）</label>\n    </data>',
        '    <data source="voice_zh_cn">\n      <label>普通话（中国大陆）</label>\n      <default>{{{voice_zh-cn|}}}</default>\n    </data>',
    ),
    (
        '    <data source="voice_zh-tw">\n      <label>國語（臺灣）</label>\n    </data>',
        '    <data source="voice_zh_tw">\n      <label>國語（臺灣）</label>\n      <default>{{{voice_zh-tw|}}}</default>\n    </data>',
    ),
    (
        '    <data source="voice_zh-hk">\n      <label>华语（香港）</label>\n    </data>',
        '    <data source="voice_zh_hk">\n      <label>华语（香港）</label>\n      <default>{{{voice_zh-hk|}}}</default>\n    </data>',
    ),
]
text = tpl.text
for old, new in REPL:
    assert text.count(old) == 1, f"匹配失败: {old[:60]}"
    text = text.replace(old, new)
tpl.text = text
tpl.save(
    summary="参数名归一：voice_zh-cn/tw/hk → 下划线写法（先加 fallback，fix:para 归一后摘除）"
)
print("模板 fallback 已加")

# ③ 快照（唯一用这三个参数的正文页）
r = api.Request(
    site=site,
    parameters={
        "action": "parse",
        "format": "json",
        "page": "角色:菜月·昴",
        "prop": "text",
        "disablelimitreport": "1",
    },
).submit()
html = r["parse"]["text"]["*"]
assert (
    "普通话（中国大陆）" in html and "國語（臺灣）" in html and "华语（香港）" in html
)
os.makedirs("logs", exist_ok=True)
with open("logs/voice_snapshot_before.json", "w", encoding="utf-8") as f:
    json.dump({"角色:菜月·昴": html}, f, ensure_ascii=False)
print("快照已存（三个配音栏均渲染）")
