from .starts import starts_base, starts_more

jobs: list[list[str]] = [
    # 跨站同步
    ["transferbot", "-lang:en", "-tolang:zh", "-start"],
    ["re0_gallery", "-catr:图库"],
    ["re0_image"],
    ["interwiki", "-quiet", "-async", "-localonly"] + starts_more,
    # 整理新搬运页面
    ["replace", "-automaticsummary", "-fix:date"],
    ["replace", "-automaticsummary", "-fix:gallery"],
    ["replace", "-automaticsummary", "-fix:heading"],
    ["category", "remove", "-nodelete", "-from:Image Gallery"],
    ["category", "remove", "-nodelete", "-from:Relationships"],
    # 模板维护
    [
        "template",
        "Character",
        "Infobox character",
        "Re:Zero Light Novel Volumes",
        "Infobox book",
        "Re:Zero Arc 4 Manga",
        "Infobox book",
        "Re:Zero Arc 5 Manga",
        "Infobox book",
    ],
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
    ["replace", "-automaticsummary", "-fix:para"],
    # 重定向维护
    ["re0_redirect", "-start:!"],
    ["fixing_redirects"] + starts_more,
    ["redirect", "do"],
    ["redirect", "br", "-delete"],
    # 语法规范化
    ["cosmetic_changes", "-async", "-ignore:method"] + starts_base,
    ["replace", "-automaticsummary", "-fix:HTML"],
    ["replace", "-automaticsummary", "-fix:anti-ve"],
    ["replace", "-automaticsummary", "-fix:syntax"],
    # 内容规范化
    ["replace", "-automaticsummary", "-fix:translation"],
    ["replace", "-automaticsummary", "-fix:isbn"],
    ["replace", "-automaticsummary", "-fix:specialpages"],
    ["noreferences", "-quiet"] + starts_base,
    ["replace", "-automaticsummary", "-fix:misc"],
    # 杂项
    ["re0_nav", "-page:MediaWiki:Wiki-navigation"],
    ["touch", "-random:128"],
]
