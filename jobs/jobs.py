"""任务列表。

每个任务有稳定名字：main.py 可按名字或编号调用（编号随插入平移，名字不变）。
fix 类任务的名字与 -fix: 参数一致，方便对照（如 `python main.py fix:translation -s`）。
wiki 上的状态页 User:IchiSanNi/jobs 与本表对应。
"""

from typing import NamedTuple

from .starts import starts_base, starts_more


class Job(NamedTuple):
    name: str
    cmd: list[str]


# pwb.py template 的参数是扁平的旧新交替序列，直接写扁平列表插错位会静默
# 错配，故结构化成 (旧模板, 新模板) 元组再展开。
_template_replacements = [
    ("Character", "Infobox character"),
    ("Re:Zero Light Novel Volumes", "Infobox book"),
    ("Re:Zero Arc 4 Manga", "Infobox book"),
    ("Re:Zero Arc 5 Manga", "Infobox book"),
    ("Re:Zero Bonds of Ice Manga", "Infobox book"),
    ("Re:Zero Daigoshou Manga", "Infobox book"),
    ("Re:Zero Daiisshou Manga", "Infobox book"),
    ("Re:Zero Dainishou Manga", "Infobox book"),
    ("Re:Zero Daisanshou Manga", "Infobox book"),
    ("Re:Zero Daiyonshou Manga", "Infobox book"),
    ("Infobox Events", "Infobox event"),
    ("Infobox battles", "Infobox battle"),
    ("Re:Zero Manga Volumes", "Infobox book"),
    ("Anime", "Infobox anime"),
    ("Music", "Infobox music"),
    ("Re:Zero BD", "Infobox bd"),
    ("Re:Zero Game", "Infobox game"),
    ("AV", "BV"),
]

jobs: list[Job] = [
    # 跨站同步
    Job("transferbot", ["transferbot", "-lang:en", "-tolang:zh", "-start"]),
    Job("gallery", ["re0_gallery", "-catr:图库"]),
    Job("image", ["re0_image"]),
    Job("interwiki", ["interwiki", "-quiet", "-async", "-localonly", *starts_more]),
    # 整理新搬运页面
    Job("fix:date", ["replace", "-automaticsummary", "-fix:date"]),
    Job("fix:gallery", ["replace", "-automaticsummary", "-fix:gallery"]),
    Job("fix:heading", ["replace", "-automaticsummary", "-fix:heading"]),
    Job(
        "cat-image-gallery", ["category", "remove", "-nodelete", "-from:Image Gallery"]
    ),
    Job(
        "cat-relationships", ["category", "remove", "-nodelete", "-from:Relationships"]
    ),
    # 模板维护
    Job(
        "template",
        ["template", *[x for pair in _template_replacements for x in pair]],
    ),
    Job(
        "template-remove",
        [
            "template",
            "-remove",
            # Navbox
            "Gusteko Navbox",
            "Lugunica Navbox",
            "Royal Election Navbox",
            "Royal Selection Navbox",
            "Terminology Navbox",
            "Vollachia Navbox",
            # Navigation
            "Anime Navigation",
            "LN Navigation",
            "Manga Navigation",
            "Music Navigation",
            "Re:Zero Manga Navigation",
            # Other
            "Construction",
            "Parent Tab",
            "References",
        ],
    ),
    Job("fix:para", ["replace", "-automaticsummary", "-fix:para"]),
    # 重定向维护
    Job("redirect", ["re0_redirect", "-start:!"]),
    Job("fixing-redirects", ["fixing_redirects", *starts_more]),
    Job("redirect-do", ["redirect", "do"]),
    Job("redirect-br", ["redirect", "br", "-delete"]),
    # 语法规范化
    Job("cosmetic", ["cosmetic_changes", "-async", "-ignore:method", *starts_base]),
    Job("fix:HTML", ["replace", "-automaticsummary", "-fix:HTML", *starts_base]),
    Job("fix:anti-ve", ["replace", "-automaticsummary", "-fix:anti-ve"]),
    Job("fix:syntax", ["replace", "-automaticsummary", "-fix:syntax", *starts_base]),
    # 内容规范化
    Job("move", ["re0_move", "-start:!"]),
    Job("fix:translation", ["replace", "-automaticsummary", "-fix:translation"]),
    Job("fix:isbn", ["replace", "-automaticsummary", "-fix:isbn"]),
    Job(
        "fix:specialpages",
        ["replace", "-automaticsummary", "-fix:specialpages", *starts_base],
    ),
    Job("noreferences", ["noreferences", "-quiet", *starts_base]),
    Job("fix:misc", ["replace", "-automaticsummary", "-fix:misc"]),
    # 杂项
    Job("nav", ["re0_nav", "-page:MediaWiki:Wiki-navigation"]),
    Job("touch", ["touch", "-random:128"]),
]
