"""模板第一轮编辑：bd/music/game/event/battle 参数名归一——新名 source + 旧名 fallback。

与 2026-08-02 12:48 批（seiyu/staff/anime）同一模式：先让模板同时认新旧名，
待 fix:para 把页面全部替换为新名后再摘除 fallback。
每个替换带断言，失败即停。
"""

import os

os.environ.pop("PYTHONPATH", None)

import pywikibot

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"


def fb(old: str) -> str:
    return f"<default>{{{{{{{old}|}}}}}}</default>"


EDITS = {
    "Template:Infobox bd": [
        (
            '<data source="Number">\n        <label>编号</label>\n    </data>',
            f'<data source="number">\n        <label>编号</label>\n        {fb("Number")}\n    </data>',
        ),
        (
            '<data source="Previous">\n            <label>前一卷</label>\n        </data>',
            f'<data source="previous">\n            <label>前一卷</label>\n            {fb("Previous")}\n        </data>',
        ),
        (
            '<data source="Next">\n            <label>后一卷</label>\n        </data>',
            f'<data source="next">\n            <label>后一卷</label>\n            {fb("Next")}\n        </data>',
        ),
    ],
    "Template:Infobox music": [
        (
            '<data source="Singer">\n        <label>歌手</label>\n    </data>',
            f'<data source="singer">\n        <label>歌手</label>\n        {fb("Singer")}\n    </data>',
        ),
        (
            '<data source="Composition">\n        <label>作曲</label>\n    </data>',
            f'<data source="composition">\n        <label>作曲</label>\n        {fb("Composition")}\n    </data>',
        ),
        (
            '<data source="Arrangement">\n        <label>编曲</label>\n    </data>',
            f'<data source="arrangement">\n        <label>编曲</label>\n        {fb("Arrangement")}\n    </data>',
        ),
        (
            '<data source="Lyric">\n        <label>作词</label>\n    </data>',
            f'<data source="lyric">\n        <label>作词</label>\n        {fb("Lyric")}\n    </data>',
        ),
        (
            '<data source="Length">\n        <label>时长</label>\n    </data>',
            f'<data source="length">\n        <label>时长</label>\n        {fb("Length")}\n    </data>',
        ),
    ],
    "Template:Infobox game": [
        (
            '<data source="Developers">\n        <label>开发</label>\n    </data>',
            f'<data source="developers">\n        <label>开发</label>\n        {fb("Developers")}\n    </data>',
        ),
        (
            '<data source="Publishers">\n        <label>发行</label>\n    </data>',
            f'<data source="publishers">\n        <label>发行</label>\n        {fb("Publishers")}\n    </data>',
        ),
        (
            '<data source="Platform">\n        <label>平台</label>\n    </data>',
            f'<data source="platform">\n        <label>平台</label>\n        {fb("Platform")}\n    </data>',
        ),
        (
            '<data source="Genre">\n        <label>类型</label>\n    </data>',
            f'<data source="genre">\n        <label>类型</label>\n        {fb("Genre")}\n    </data>',
        ),
        (
            '<data source="Modes">\n        <label>模式</label>\n    </data>',
            f'<data source="modes">\n        <label>模式</label>\n        {fb("Modes")}\n    </data>',
        ),
    ],
    "Template:Infobox event": [
        (
            '<data source="Rōmaji">\n        <label>罗马字</label>\n    </data>',
            f'<data source="name_ja_romaji">\n        <label>罗马字</label>\n        {fb("Rōmaji")}\n    </data>',
        ),
        (
            '<data source="Date">\n        <label>时间</label>\n    </data>',
            f'<data source="date">\n        <label>时间</label>\n        {fb("Date")}\n    </data>',
        ),
        (
            '<data source="Place">\n        <label>地点</label>\n    </data>',
            f'<data source="place">\n        <label>地点</label>\n        {fb("Place")}\n    </data>',
        ),
        (
            '<data source="Result">\n        <label>结果</label>\n    </data>',
            f'<data source="result">\n        <label>结果</label>\n        {fb("Result")}\n    </data>',
        ),
        (
            '<data source="Also known as">\n        <label>别名</label>\n    </data>',
            f'<data source="also_known_as">\n        <label>别名</label>\n        {fb("Also known as")}\n    </data>',
        ),
    ],
    "Template:Infobox battle": [
        (
            '<data source="rōmaji"><label>罗马字</label></data>',
            f'<data source="name_ja_romaji"><label>罗马字</label>{fb("rōmaji")}</data>',
        ),
        (
            '<data source="also known as"><label>别名</label></data>',
            f'<data source="also_known_as"><label>别名</label>{fb("also known as")}</data>',
        ),
    ],
}

SUMMARY = "参数名归一：旧名经 default fallback 兼容（待 fix:para 全站替换后摘除）"

for title, pairs in EDITS.items():
    page = pywikibot.Page(site, title)
    text = page.text
    for old, new in pairs:
        assert old in text, f"{title}: 未找到预期片段 {old[:50]!r}"
        text = text.replace(old, new, 1)
    page.text = text
    page.save(summary=SUMMARY)
    print(f"saved {title} ({len(pairs)} 处)")
print("ALL DONE")
