"""B/C 组文档同步：seiyu/staff/anime 的 /doc 整页重写（新参数名 + 旧名兼容说明），
event/music 的 /doc 摘除已过期的「信息框内标签为 X」备注。"""

import os

os.environ.pop("PYTHONPATH", None)

import pywikibot

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi", site.user()

SEIYU_DOC = """; 说明
声优信息框。

; 语法
<pre>
{{Infobox seiyu
| image = 
| Caption = 
| name = 
| name_en = 
| name_ja_kanji = 
| name_ja_romaji = 
| birth = 
| death = 
| role = 
}}
</pre>

* 旧参数名 <code>image1</code>/<code>caption1</code>/<code>title1</code>/<code>nombre</code>/<code>rōmaji</code>/<code>nacimiento</code>/<code>personaje</code>（es 站搬运遗留）仍兼容，新搬运页无需立即改写；2026-08-02 起全站调用已统一为新名。

; 示例
<pre>
{{Infobox seiyu
| image = Aimi Tanaka.png
| name = 田中爱美
| name_en = Aimi Tanaka
| name_ja_kanji = 田中 あいみ
| name_ja_romaji = Tanaka Aimi
| birth = 1992-04-28
| role = [[角色:普拉姆|普拉姆·里施]]
}}
</pre>

<templatedata>
{
\t"format": "block",
\t"params": {
\t\t"image": {
\t\t\t"label": "图片",
\t\t\t"description": "图片（文件名）"
\t\t},
\t\t"Caption": {
\t\t\t"label": "图片说明",
\t\t\t"description": ""
\t\t},
\t\t"name": {
\t\t\t"label": "名称",
\t\t\t"description": "信息框标题，一般为姓名"
\t\t},
\t\t"name_en": {
\t\t\t"label": "英译名",
\t\t\t"description": ""
\t\t},
\t\t"name_ja_kanji": {
\t\t\t"label": "日文名",
\t\t\t"description": ""
\t\t},
\t\t"name_ja_romaji": {
\t\t\t"label": "罗马字",
\t\t\t"description": ""
\t\t},
\t\t"birth": {
\t\t\t"label": "出生日期",
\t\t\t"description": ""
\t\t},
\t\t"death": {
\t\t\t"label": "逝世日期",
\t\t\t"description": ""
\t\t},
\t\t"role": {
\t\t\t"label": "配音角色",
\t\t\t"description": ""
\t\t}
\t},
\t"paramOrder": [
\t\t"image",
\t\t"Caption",
\t\t"name",
\t\t"name_en",
\t\t"name_ja_kanji",
\t\t"name_ja_romaji",
\t\t"birth",
\t\t"death",
\t\t"role"
\t]
}
</templatedata>
"""

STAFF_DOC = """; 说明
制作人员信息框。

; 语法
<pre>
{{Infobox staff
| image = 
| Caption = 
| name = 
| name_en = 
| name_ja_kanji = 
| name_ja_romaji = 
| birth = 
| director = 
| script = 
| design = 
| composer = 
}}
</pre>

* 旧参数名 <code>image1</code>/<code>caption1</code>/<code>title1</code>/<code>nombre</code>/<code>rōmaji</code>/<code>nacimiento</code>/<code>guión</code>/<code>diseño</code>/<code>compositor</code>（es 站搬运遗留）仍兼容，新搬运页无需立即改写；2026-08-02 起全站调用已统一为新名。

; 示例
<pre>
{{Infobox staff
| name = 末广健一郎
| image = Kenichiro Suehiro.png
| name_en = Kenichirō Suehiro
| name_ja_kanji = 末廣健一郎
| name_ja_romaji = Suehiro Kenichirō
| birth = 1980-12-27
| composer = [[动画:TV|TV 动画]]<br>[[动画:Re:从零开始的休息时间|迷你动画]]
}}
</pre>

<templatedata>
{
\t"format": "block",
\t"params": {
\t\t"image": {
\t\t\t"label": "图片",
\t\t\t"description": "图片（文件名）"
\t\t},
\t\t"Caption": {
\t\t\t"label": "图片说明",
\t\t\t"description": ""
\t\t},
\t\t"name": {
\t\t\t"label": "名称",
\t\t\t"description": "信息框标题，一般为姓名"
\t\t},
\t\t"name_en": {
\t\t\t"label": "英译名",
\t\t\t"description": ""
\t\t},
\t\t"name_ja_kanji": {
\t\t\t"label": "日文名",
\t\t\t"description": ""
\t\t},
\t\t"name_ja_romaji": {
\t\t\t"label": "罗马字",
\t\t\t"description": ""
\t\t},
\t\t"birth": {
\t\t\t"label": "出生日期",
\t\t\t"description": ""
\t\t},
\t\t"director": {
\t\t\t"label": "监督",
\t\t\t"description": ""
\t\t},
\t\t"script": {
\t\t\t"label": "剧本",
\t\t\t"description": ""
\t\t},
\t\t"design": {
\t\t\t"label": "设计",
\t\t\t"description": ""
\t\t},
\t\t"composer": {
\t\t\t"label": "作曲",
\t\t\t"description": ""
\t\t}
\t},
\t"paramOrder": [
\t\t"image",
\t\t"Caption",
\t\t"name",
\t\t"name_en",
\t\t"name_ja_kanji",
\t\t"name_ja_romaji",
\t\t"birth",
\t\t"director",
\t\t"script",
\t\t"design",
\t\t"composer"
\t]
}
</templatedata>
"""

ANIME_DOC = """; 说明
动画剧集信息框。

; 语法
<pre>
{{Infobox anime
| name = 
| image = 
| Caption = 
| name_ja_kanji = 
| name_ja_romaji = 
| volume = 
| air_date = 
| opening = 
| ending = 
}}
</pre>

* <code>name</code> 留空时默认取页面名。
* 在主命名空间（文章页）使用时，自动给页面加入 [[:Category:剧集]]。
* 旧参数名 <code>Volume</code>/<code>Air Date</code>/<code>Opening</code>/<code>Ending</code>（en 站搬运遗留）仍兼容，新搬运页无需立即改写；2026-08-02 起全站调用已统一为新名。

; 示例
<pre>
{{Infobox anime
| name = 初始的终结与结束的开始
| image = Episode 1 Title.png
| name_ja_kanji = 始まりの終わりと終わりの始まり
| name_ja_romaji = Hajimari no Owari to Owari no Hajimari
| volume = [[小说:1卷|文库正传第1卷]]第一章 - 第三章
| air_date = 2016-04-03（旧版）<br>2020-01-01（新编集版）
| opening = [[音乐:Redo|Redo]]
| ending = [[音乐:STYX HELIX|STYX HELIX]]
}}
</pre>

<templatedata>
{
\t"format": "block",
\t"params": {
\t\t"name": {
\t\t\t"label": "名称",
\t\t\t"description": "留空时默认取页面名",
\t\t\t"default": "{{PAGENAME}}"
\t\t},
\t\t"image": {
\t\t\t"label": "图片",
\t\t\t"description": "图片（文件名）"
\t\t},
\t\t"Caption": {
\t\t\t"label": "图片说明",
\t\t\t"description": ""
\t\t},
\t\t"name_ja_kanji": {
\t\t\t"label": "日文名",
\t\t\t"description": ""
\t\t},
\t\t"name_ja_romaji": {
\t\t\t"label": "罗马字",
\t\t\t"description": ""
\t\t},
\t\t"volume": {
\t\t\t"label": "文库",
\t\t\t"description": "改编出处（文库版卷、章）"
\t\t},
\t\t"air_date": {
\t\t\t"label": "上映时间",
\t\t\t"description": ""
\t\t},
\t\t"opening": {
\t\t\t"label": "OP",
\t\t\t"description": "片头曲"
\t\t},
\t\t"ending": {
\t\t\t"label": "ED",
\t\t\t"description": "片尾曲"
\t\t}
\t},
\t"paramOrder": [
\t\t"name",
\t\t"image",
\t\t"Caption",
\t\t"name_ja_kanji",
\t\t"name_ja_romaji",
\t\t"volume",
\t\t"air_date",
\t\t"opening",
\t\t"ending"
\t]
}
</templatedata>
"""

for title, doc in [
    ("Template:Infobox seiyu/doc", SEIYU_DOC),
    ("Template:Infobox staff/doc", STAFF_DOC),
    ("Template:Infobox anime/doc", ANIME_DOC),
]:
    p = pywikibot.Page(site, title)
    assert p.exists(), title
    p.text = doc
    p.save(
        summary="参数名归一同步：语法/示例/templatedata 改用新名，旧名兼容说明",
        bot=False,
    )
    print(f"rewrote {title}")

for title, notes in [
    ("Template:Infobox event/doc", ["Kanji", "Rōmaji", "Date", "Place", "Outcome"]),
    ("Template:Infobox music/doc", ["Kanji", "Romaji"]),
]:
    p = pywikibot.Page(site, title)
    text = p.text
    for note in notes:
        old = f'"description": "信息框内标签为 {note}"'
        assert text.count(old) == 1, f"{title}: {old} 命中 {text.count(old)} 次"
        text = text.replace(old, '"description": ""')
    p.text = text
    p.save(summary="摘除过期备注：信息框 label 已中文化", bot=False)
    print(f"saved {title}")

print("\nDOCS DONE")
