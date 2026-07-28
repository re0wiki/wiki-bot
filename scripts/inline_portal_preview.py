"""生成首页组件模板内联后的 wikitext（只读+本地文件，不编辑 wiki）。

内联范围：Portal 链 10 模板（Portal、Portal Left/Right、Slider、Welcome、
Announcements、Latest Volume、Latest Volume/LN、Latest Volume/Manga、Social Media）。
均确认无参数调用（单点），内联 = 剥 <noinclude> 后文本替换。
保留不动：Init、To do、Clear、Blur、Project:入站指引、w:animangafooter、magic words。
验证：action=parse 对比内联前后渲染 HTML 是否一致。
"""

import re

from pywikibot.data import api

import pywikibot

INLINE = [
    "Portal Left",
    "Portal Right",
    "Slider",
    "Welcome",
    "Announcements",
    "Social Media",
    "Portal",
]
# Latest Volume 链（Latest Volume、/LN、/Manga）刻意不内联：
# 外层 <tabber> 的内容里嵌套内层 <tabber>，依赖 transclusion 先展开模板再解析标签；
# 字面内联会导致内层 tabber 被转义（实测渲染 diff 证实）。

site = pywikibot.Site("zh", "re0")
MAIN = "Re:从零开始的异世界生活 Wiki"


def transclude_body(text):
    """模拟 transclusion 语义：去 noinclude，解 includeonly/onlyinclude。"""
    text = re.sub(r"<noinclude>.*?</noinclude>", "", text, flags=re.DOTALL)
    if "<onlyinclude>" in text:
        parts = re.findall(r"<onlyinclude>(.*?)</onlyinclude>", text, flags=re.DOTALL)
        return "".join(parts)
    text = re.sub(r"</?includeonly>", "", text)
    return text


main_text = pywikibot.Page(site, MAIN).text

bodies = {}
for name in INLINE:
    bodies[name] = transclude_body(pywikibot.Page(site, f"Template:{name}").text)

inlined = main_text
while True:  # 迭代到不动点：父模板内联会引入子模板调用
    before = inlined
    for name in INLINE:  # 长名在前，避免 Portal 先于 Portal Left 误匹配
        pat = re.compile(
            r"\{\{\s*" + re.escape(name).replace("\\ ", r"[ _]") + r"\s*\}\}"
        )
        calls = re.findall(
            r"\{\{[^{}]*" + re.escape(name.split("/")[0]) + r"[^{}]*\}\}", inlined
        )
        for c in calls:
            assert "|" not in c, f"带参数调用，需人工处理: {c}"
        inlined = pat.sub(lambda m, n=name: bodies[n], inlined)
    if inlined == before:
        break

rest = sorted(set(re.findall(r"\{\{([^{}|]+?)(?:\|[^{}]*)?\}\}", inlined)))
print("内联后仍保留的模板调用:", rest)

with open("logs/mainpage_inlined_2026-07-28.wiki", "w", encoding="utf-8") as f:
    f.write(inlined)
print(f"原 {len(main_text)} 字符 -> 内联后 {len(inlined)} 字符")


# ---- 渲染等价验证 ----
def render(wikitext=None, page=None):
    params = {"action": "parse", "prop": "text", "format": "json"}
    if page:
        params["page"] = page
    else:
        params["text"] = wikitext
        params["title"] = MAIN
        params["contentmodel"] = "wikitext"
    return api.Request(site=site, parameters=params).submit()["parse"]["text"]["*"]


html_orig = render(page=MAIN)
html_inlined = render(wikitext=inlined)
print("渲染一致:", html_orig == html_inlined)
if html_orig != html_inlined:
    import difflib

    # twitter widget-id 每次 parse 重新生成，归一化后再比
    norm = lambda h: re.sub(r'data-widget-id="[0-9a-f]+"', 'data-widget-id="X"', h)
    print("归一化 widget-id 后一致:", norm(html_orig) == norm(html_inlined))
    diff = list(
        difflib.unified_diff(
            norm(html_orig).splitlines(), norm(html_inlined).splitlines(), lineterm=""
        )
    )
    print(f"归一化后 diff 行数: {len(diff)}")
    print("\n".join(diff[:40]))
