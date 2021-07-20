generator_base = (
    " -start::! -start:project:! -start:template:! -start:category:! -start:file:!"
)
generator_more = generator_base + " -start:module:! " "-start:mediawiki:!"

base: dict[str] = {
    "regex": True,
    "nocase": True,
    "exceptions": {
        "inside-tags": ["keep"],
    },
}

user_fixes = {}

# region misc
nbsp = "\xa0"

mid_dots_code = [
    721,
    903,
    1468,
    5867,
    8226,
    8231,
    8728,
    8729,
    8901,
    9210,
    9679,
    9702,
    9899,
    10625,
    11824,
    11825,
    11827,
    12539,
    42895,
    65381,
    65793,
]
mid_dots = "[" + "".join(chr(i) for i in mid_dots_code) + "]"
mid_dot = "\xb7"

user_fixes["misc"] = base | {
    "generator": generator_base,
    "replacements": [
        (nbsp, " "),
        (mid_dots, mid_dot),
        ("－－", "——"),
        (r"<!---->|￼", ""),
        ("“", "「"),
        ("”", "」"),
        ("【", "『"),
        ("】", "』"),
        (r"(?<!==)\s*\n==", r"\n\n=="),
        (r"==\n\s*", r"==\n"),
        (r"\n{3,}", r"\n\n"),
        ("stickytable", "floatheader"),
    ],
}
# endregion

# region args
user_fixes["args"] = base | {
    "generator": generator_more,
    "replacements": [
        (rf"\|\s*{o}\s*= *", f"| {n} = ")
        for o, n in [
            ("Image-Size", "请手动移除该参数"),
            ("Name", "name"),
            ("Image", "image"),
            ("Kanji", "name_ja_kanji"),
            ("Romaji", "name_ja_romaji"),
            ("Alias", "alias"),
            ("Nickname", "nickname"),
            ("Race", "race"),
            ("Gender", "gender"),
            ("Birthday", "birthday"),
            ("Age", "age"),
            ("Hair Color", "hair"),
            ("Eye Color", "eyes"),
            ("Height", "height"),
            ("Weight", "weight"),
            ("Affiliation", "affiliation"),
            ("Previous Affiliation", "previous_affiliation"),
            ("Occupation", "occupation"),
            ("Previous Occupation", "previous_occupation"),
            ("Status", "status"),
            ("Relatives", "relatives"),
            ("Magic", "magic"),
            ("Divine Protection", "divine_protection"),
            ("Authority", "authority"),
            ("Weapon", "weapon"),
            ("Equipment", "equipment"),
            ("Anime", "anime"),
            ("Light Novel", "novel"),
            ("Game", "game"),
            ("Manga", "comic"),
            ("Japanese Voice", "voice_ja"),
            ("English Voice", "voice_en"),
        ]
    ],
}
# endregion

# region gallery
user_fixes["gallery"] = base | {
    "generator": "-catr:图库",
    "replacements": [
        (o + "(?==)", n)
        for o, n in [
            ("Anime", "动画"),
            ("Season 1", "第一季"),
            ("Season 2", "第二季"),
            ("Light Novel", "小说"),
            ("Main Series", "正传"),
            ("Tanpenshuu", "月刊CA短篇"),
            ("Side Content", "特典SS"),
            ("Side Stories", "特典SS"),
            ("Manga", "漫画"),
            ("Daisshou", "第1章"),
            ("Dainishou", "第2章"),
            ("Daisanshou", "第3章"),
            ("Daiyonshou", "第4章"),
            ("Anthology", "官方同人精选集"),
            ("Games", "游戏"),
            ("Death or Kiss", "死或吻"),
            ("-Infinity", "INFINITY"),
            ("The Prophecy of the Throne", "虚假的王选候补"),
            (r"Misc\.?", "其他"),
        ]
    ],
}
# endregion

# region head
user_fixes["head"] = base | {
    "generator": generator_more,
    "replacements": [
        ("(?<== )" + o + "(?= =)", n)
        for o, n in [
            ("Information", "简介"),
            ("Summary", "简介"),
            ("Relationships", "关系"),
            ("Synopsis", "梗概"),
            ("Gallery", "图库"),
            ("Image Gallery", "图库"),
            ("Appearance", "外貌"),
            ("Personality", "性格"),
            ("Abilities", "能力"),
            ("Trivia", "你知道吗"),
            ("Lyrics?", "歌词"),
            ("References?", "注释与外部链接"),
        ]
    ],
}
# endregion

fixes: dict
# noinspection PyUnboundLocalVariable
fixes.update(user_fixes)
