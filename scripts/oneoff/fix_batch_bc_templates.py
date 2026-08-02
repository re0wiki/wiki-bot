"""B/C 组模板体编辑（2026-08-02 全站模板复查待办）。

- B5+C10：Infobox staff 参数名归一 + label 中文化（整页重写，旧参数 fallback）
- C10：Infobox seiyu 参数名归一（整页重写，旧参数 fallback）
- C12：Infobox anime 参数名归一（Volume/Air Date/Opening/Ending → 小写下划线，旧名 fallback）
- B6：Infobox event label 中文化
- B7：Infobox bd / Infobox music label 中文化
- B8：著作权六件套显示文本中文化 + id 去重
- B9：Bot / Category redirect / Disambiguation 源码统一简体
- C11：Quote/main templatedata 迁入 Quote/doc
"""

import os

os.environ.pop("PYTHONPATH", None)

import re

import pywikibot

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi", site.user()


def edit(title, transforms, summary):
    """transforms: [(old, new)] 精确替换，每对必须命中恰好一次。"""
    p = pywikibot.Page(site, title)
    text = p.text
    for old, new in transforms:
        assert text.count(old) == 1, f"{title}: 命中 {text.count(old)} 次: {old[:60]!r}"
        text = text.replace(old, new)
    p.text = text
    p.save(summary=summary, bot=False)
    print(f"saved {title}")


def rewrite(title, new_text, summary, must_contain):
    p = pywikibot.Page(site, title)
    old = p.text
    for frag in must_contain:
        assert frag in old, f"{title}: 现状不含预期片段 {frag[:50]!r}"
    p.text = new_text
    p.save(summary=summary, bot=False)
    print(f"rewrote {title}")


# ── B5+C10: Infobox staff ──────────────────────────────────
rewrite(
    "Template:Infobox staff",
    """<onlyinclude><infobox>
  <image source="image">
    <default>{{{image1|}}}</default>
    <caption source="Caption"><default>{{{caption1|}}}</default></caption>
  </image>
  <title source="name"><default>{{{title1|}}}</default></title>
  <data source="name_en"><label>英译</label><default>{{{nombre|}}}</default></data>
  <data source="name_ja_kanji"><label>日文</label></data>
  <data source="name_ja_romaji"><label>罗马字</label><default>{{{rōmaji|}}}</default></data>
  <data source="birth"><label>出生</label><default>{{{nacimiento|}}}</default></data>
  <data source="director"><label>监督</label></data>
  <data source="script"><label>剧本</label><default>{{{guión|}}}</default></data>
  <data source="design"><label>设计</label><default>{{{diseño|}}}</default></data>
  <data source="composer"><label>作曲</label><default>{{{compositor|}}}</default></data>
</infobox></onlyinclude><noinclude>{{Documentation}}</noinclude>

[[es:Plantilla:Staff]]

[[Category:信息框模板]]
""",
    "参数名归一（image/Caption/name/name_en/name_ja_romaji/birth/script/design/composer，旧西语名经 default 兼容）+ label 中文化",
    ['source="nombre"', 'source="guión"', "<label>Nombre</label>"],
)

# ── C10: Infobox seiyu ─────────────────────────────────────
rewrite(
    "Template:Infobox seiyu",
    """<onlyinclude><infobox>
  <image source="image">
    <default>{{{image1|}}}</default>
    <caption source="Caption"><default>{{{caption1|}}}</default></caption>
  </image>
  <title source="name"><default>{{{title1|}}}</default></title>
  <data source="name_en"><label>英译</label><default>{{{nombre|}}}</default></data>
  <data source="name_ja_kanji"><label>日文</label></data>
  <data source="name_ja_romaji"><label>罗马字</label><default>{{{rōmaji|}}}</default></data>
  <data source="birth"><label>出生</label><default>{{{nacimiento|}}}</default></data>
  <data source="death"><label>逝世</label></data>
  <data source="role"><label>配音角色</label><default>{{{personaje|}}}</default></data>
</infobox></onlyinclude><noinclude>{{Documentation}}</noinclude>

[[es:Plantilla:Seiyu]]

[[Category:信息框模板]]
""",
    "参数名归一（image/Caption/name/name_en/name_ja_romaji/birth/role，旧西语名经 default 兼容）",
    ['source="nombre"', 'source="personaje"', "<label>英译</label>"],
)

# ── C12: Infobox anime ─────────────────────────────────────
edit(
    "Template:Infobox anime",
    [
        (
            """    <data source="Volume">
        <label>文库</label>
    </data>""",
            """    <data source="volume">
        <label>文库</label>
        <default>{{{Volume|}}}</default>
    </data>""",
        ),
        (
            """    <data source="Air Date">
        <label>上映时间</label>
    </data>""",
            """    <data source="air_date">
        <label>上映时间</label>
        <default>{{{Air Date|}}}</default>
    </data>""",
        ),
        (
            """        <data source="Opening">
            <label>OP</label>
        </data>""",
            """        <data source="opening">
            <label>OP</label>
            <default>{{{Opening|}}}</default>
        </data>""",
        ),
        (
            """        <data source="Ending">
            <label>ED</label>
        </data>""",
            """        <data source="ending">
            <label>ED</label>
            <default>{{{Ending|}}}</default>
        </data>""",
        ),
    ],
    "参数名归一：Volume/Air Date/Opening/Ending → volume/air_date/opening/ending（旧名经 default 兼容）",
)

# ── B6: Infobox event label 中文化 ─────────────────────────
edit(
    "Template:Infobox event",
    [
        (
            '<data source="name_ja_kanji">\n        <label>Kanji</label>',
            '<data source="name_ja_kanji">\n        <label>日文</label>',
        ),
        (
            '<data source="Rōmaji">\n        <label>Rōmaji</label>',
            '<data source="Rōmaji">\n        <label>罗马字</label>',
        ),
        (
            '<data source="Date">\n        <label>Date</label>',
            '<data source="Date">\n        <label>时间</label>',
        ),
        (
            '<data source="Place">\n        <label>Place</label>',
            '<data source="Place">\n        <label>地点</label>',
        ),
        (
            '<data source="Result">\n        <label>Outcome</label>',
            '<data source="Result">\n        <label>结果</label>',
        ),
        (
            '<data source="Also known as">\n        <label>Also known as</label>',
            '<data source="Also known as">\n        <label>别名</label>',
        ),
    ],
    "label 中文化（Kanji/Rōmaji/Date/Place/Outcome/Also known as → 日文/罗马字/时间/地点/结果/别名）",
)

# ── B7: Infobox bd / music label 中文化 ────────────────────
edit(
    "Template:Infobox bd",
    [
        ("<header>Volume Chronology</header>", "<header>圆盘序列</header>"),
        (
            '<data source="Previous">\n            <label>Previous</label>',
            '<data source="Previous">\n            <label>前一卷</label>',
        ),
        (
            '<data source="Next">\n            <label>Next</label>',
            '<data source="Next">\n            <label>后一卷</label>',
        ),
    ],
    "label 中文化（Volume Chronology/Previous/Next → 圆盘序列/前一卷/后一卷）",
)
edit(
    "Template:Infobox music",
    [
        ("<label>Kanji</label>", "<label>日文</label>"),
        ("<label>Romaji</label>", "<label>罗马字</label>"),
    ],
    "label 中文化（Kanji/Romaji → 日文/罗马字）",
)

# ── B8: 著作权六件套 ───────────────────────────────────────
LICENSE_TEXT = {
    "Template:CC-BY-SA": (
        'id="cc-by-sa"',
        "'''''This file is licensed under the [http://creativecommons.org/licenses/by-sa/3.0/ Creative Commons Attribution-Share Alike License].'''''",
        'id="c-cc-by-sa"',
        "'''''本文件以[https://creativecommons.org/licenses/by-sa/3.0/deed.zh 知识共享署名-相同方式共享 3.0 许可协议]授权。'''''",
    ),
    "Template:Fairuse": (
        'id="c-fairuse"',
        "'''''This file is copyrighted. It will be used in a way that qualifies as fair use under US copyright law.'''''",
        'id="c-fairuse"',
        "'''''本文件受著作权保护，本站依据美国著作权法的合理使用条款使用。'''''",
    ),
    "Template:From Wikimedia": (
        'id="c-fairuse"',
        "'''''This file was originally uploaded on Wikipedia or another Wikimedia project.'''''",
        'id="c-from-wikimedia"',
        "'''''本文件最初上传于维基百科或其他维基媒体计划。'''''",
    ),
    "Template:Other free": (
        'id="c-fairuse"',
        "'''''This file is licensed under a free license.'''''",
        'id="c-other-free"',
        "'''''本文件以自由许可协议授权。'''''",
    ),
    "Template:PD": (
        'id="c-fairuse"',
        "'''''This file is in the public domain'''''",
        'id="c-pd"',
        "'''''本文件属于公有领域。'''''",
    ),
    "Template:Self": (
        'id="c-fairuse"',
        "'''''This file was uploaded by the photographer or author.'''''",
        'id="c-self"',
        "'''''本文件由拍摄者或作者本人上传。'''''",
    ),
}
for title, (old_id, old_text, new_id, new_text) in LICENSE_TEXT.items():
    edit(
        title,
        [(old_id, new_id), (old_text, new_text)],
        "显示文本中文化；id 按模板名区分（原 5 个模板共用 c-fairuse）",
    )

# ── B9: Bot 简体化（整页重写；switch 的繁体 key 保留兼容） ─
rewrite(
    "Template:Bot",
    """{| class="plainlinks ombox ombox-notice" role="presentation" style="margin: 4px 10%; border-collapse: collapse; border: 1px solid #a2a9b1; "
|-
| class="mbox-image" style="border: none; padding: 2px 0 2px 0.9em; text-align: center;" | [[File:{{#switch:{{lc:{{{status}}}}}|approved|已批准|active=Crystal Clear accepted bot.png|inactive=Crystal Clear inactive bot.png|申請中|申请中=Crystal Clear inactive bot2.png|unapproved|未批准=Crystal Clear denied bot.png|#default=Crystal Clear action run.png}}|75px|此为机器人账号|link=]]
| class="mbox-text" style="border: none; padding: 0.25em 0.9em; width: 100%;" | '''{{#if:{{{operator|}}}|此[[w:c:zh.community:Help:Bot|机器人账号]]由[[User:{{{operator}}}|{{{operator}}}]]操作|此为[[w:c:zh.community:Help:Bot|机器人账号]]}}'''{{#switch:{{lc:{{{awb}}}}}|yes|是=，使用{{#switch:{{{codebase|}}}|N/A|無=|#default={{{codebase}}}与|}}[[Wikipedia:zh:Wikipedia:AWB|自动维基浏览器]]|no|否|#default={{#switch:{{{codebase|}}}|N/A|無=|=|#default=，使用{{{codebase}}}}}}}{{#switch:{{lc:{{{status}}}}}|approved|已批准|active|inactive=，属[[w:c:zh.community:Project:機器人申請|已通过申请的机器人账号]]|申請中|申请中=，属[[w:c:zh.community:Project:機器人申請|正在申请的机器人账号]]|unapproved|未批准=，属[[w:c:zh.community:Project:機器人申請|未通过申请的机器人账号]]|未申請|#default=，属[[w:c:zh.community:Project:機器人申請|尚未申请的机器人账号]]}}{{#if:{{{usage|}}}|，用于{{{usage}}}，并|，}}{{#switch:{{lc:{{{auto}}}}}|no|否=以手动方式进行编辑|yes|是|#default=以半自动或全自动方式协助用户处理繁琐而重复的工作}}。{{{more|}}}<br><small>'''致管理员：如果此机器人{{#switch:{{lc:{{{awb}}}}}|yes|是=在收到提醒或警告信息后继续作出有问题的编辑|no|否|#default=失灵或作出有问题的编辑}}，请[{{fullurl:Special:Block|wpTarget={{PAGENAMEE}}&wpExpiry=infinite&wpHardBlock=1&wpAutoBlock=0&wpCreateAccount=0&wpReason=other&wpReason-other=机器人发生故障并必须紧急停止}} 封禁此账号]。'''</small>
|}<noinclude>
{{Documentation}}
[[Category:维护模板]]
</noinclude>
""",
    "源码统一简体（switch 的繁体 key 保留以兼容旧调用；外站链接目标不变）",
    ["此為機器人帳號", "自動維基瀏覽器", "致管理員"],
)

# ── B9: Category redirect / Disambiguation 简体化 ──────────
edit(
    "Template:Category redirect",
    [
        (
            "'''本分類已-{zh:重新導向;zh-hans:重定向;zh-hant:重新導向}-{{#if:{{{1|}}}|至「[[:Category:{{{1}}}]]」|至其他分類}}。'''",
            "'''本分类已-{zh:重新導向;zh-hans:重定向;zh-hant:重新導向}-{{#if:{{{1|}}}|至「[[:Category:{{{1}}}]]」|至其他分类}}。'''",
        ),
        (
            ":: 請注意，本分類不應該包括任何页面，所有页面都應該重新被分類{{#if:{{{1|}}}|至「[[:Category:{{{1}}}]]」|}}。歡迎您協助重新分類，但請不要因為分類中沒有內容而刪除本分類，以防止同名分類不斷被建立。",
            ":: 请注意，本分类不应该包括任何页面，所有页面都应该重新分类{{#if:{{{1|}}}|至「[[:Category:{{{1}}}]]」|}}。欢迎您协助重新分类，但请不要因为分类中没有内容而删除本分类，以防止同名分类不断被建立。",
        ),
    ],
    "源码统一简体（语言转换标记保留）",
)
edit(
    "Template:Disambiguation",
    [
        (
            "这是一个[[Wikipedia:消歧义|消歧义]]页，羅列了与",
            "这是一个[[Wikipedia:消歧义|消歧义]]页，罗列了与",
        ),
        ("某條目的[", "某条目的["),
        (
            "希望您能協助修正该處的内部链接，將它指向以下条目之一：",
            "希望您能协助修正该处的内部链接，将它指向以下条目之一：",
        ),
    ],
    "源码统一简体（语言转换标记保留）",
)

# ── C11: Quote/main templatedata → Quote/doc ───────────────
p = pywikibot.Page(site, "Template:Quote/main")
text = p.text
m = re.search(r"\n<templatedata>.*?</templatedata>\n", text, re.DOTALL)
assert m, "Quote/main templatedata 未找到"
td_block = m.group(0)
new = text.replace(td_block, "\n")
assert new.count("<templatedata>") == 0
p.text = new
p.save(summary="templatedata 迁入 Quote/doc（约定：templatedata 放 /doc）", bot=False)
print("saved Template:Quote/main（摘除 templatedata）")

p = pywikibot.Page(site, "Template:Quote/doc")
text = p.text
assert "<templatedata>" not in text
assert text.endswith("\n")
p.text = text + td_block.strip("\n") + "\n"
p.save(
    summary="接收自 Quote/main 迁入的 templatedata（QUOTE/Quote/Quote/main 三页共享）",
    bot=False,
)
print("saved Template:Quote/doc（接收 templatedata）")

print("\nALL TEMPLATE EDITS DONE")
