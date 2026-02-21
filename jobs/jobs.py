from .starts import starts_base, starts_more

jobs: list[list[str]] = [
    # 跨站同步
    ["transferbot", "-lang:en", "-tolang:zh", "-start"],
    ["re0_gallery", "-catr:图库"],
    ["re0_image"],
    [
        "transferbot",
        "-family:w",
        "-lang:zh",
        "-tofamily:re0",
        "-tolang:zh",
        "-start:mediawiki:!",
        "-titleregex:Gadget.*css",
        "-overwrite",
    ],
    ["interwiki", "-quiet", "-async", "-localonly"] + starts_more,
    # 整理新搬运页面
    ["replace", "-automaticsummary", "-fix:date"],
    ["replace", "-automaticsummary", "-fix:gallery"],
    ["replace", "-automaticsummary", "-fix:heading"],
    ["category", "remove", "-nodelete", "-from:Image Gallery"],
    # 模板维护
    [
        "template",
        "Character",
        "Infobox character",
        "Re:Zero Light Novel Volumes",
        "Infobox novel",
    ],
    [
        "template",
        "-remove",
        "Parent Tab",
        "Lugnica Navbox",
        "Vollachia Navbox",
        "Gusteko Navbox",
        "Royal Election Navbox",
        "Royal Selection Navbox",
        "Anime Navigation",
        "Manga Navigation",
        "Disambig",
        "LN Navigation",
        "Re:Zero Manga Navigation",
        "Music Navigation",
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
    # 刷新
    ["touch", "-random:128"],
]
