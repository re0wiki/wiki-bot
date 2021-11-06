import itertools
import re
from collections import defaultdict

from opencc import OpenCC

generator_base = [
    "-start::!",
    "-start:project:!",
    "-start:template:!",
    "-start:category:!",
]
generator_more = generator_base + ["-start:module:! ", "-start:mediawiki:!"]

base: dict[str] = {
    "regex": True,
    "nocase": True,
    "exceptions": {
        "inside-tags": ["keep", "interwiki"],
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
        ("</br>", "<br>"),
        (r"'''(\{\{R\|.*?\}\})'''", r"\1"),
    ],
}
# endregion

# region anti-ve
user_fixes["anti-ve"] = {
    "regex": True,
    "nocase": True,
    "exceptions": {
        "inside-tags": ["keep", "interwiki", "template", "table"],
    },
    "generator": generator_base,
    "replacements": [
        ("<br>", r"\n\n"),
    ],
}
# endregion

# region para
user_fixes["para"] = base | {
    "generator": generator_more,
    "replacements": [
        (rf"\|\s*{o}\s*=", f"| {n} =")
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
        (o + r"\s*(?==)", n)
        for o, n in [
            ("Anime", "动画"),
            ("Season 1", "第一季"),
            ("Season 2", "第二季"),
            ("Light Novels?", "小说"),
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

# region heading
user_fixes["heading"] = base | {
    "generator": generator_more,
    "replacements": [
        ("(?<== )" + o + "(?= =)", n)
        for o, n in [
            ("Relationships", "关系"),
            ("Synopsis", "梗概"),
            ("Summary", "梗概"),
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

# region translation
flatten = itertools.chain.from_iterable
s2t = OpenCC("s2t.json").convert

similar_chars = (
    "珥尔耳鲁露卢勒拉菈利莉丽里吕李",
    "书舒修休杰珠裘鸠吉基其姬奇齐",
    "库克古谷格铬科赫黑海哈空柯寇",
    "托图多朵特提狄缇德蒂黛",
    "肯卡嘉加伽茄贾",
    "丝斯司兹茨",
    "娅亚雅阿安",
    "菲福飞弗芙伏佛沃",
    "莎沙纱萨",
    "西希席叙",
    "腾滕登坦",
    "娜纳那",
    "艾爱埃",
    "贝培佩",
    "赛瑟札",
    "塞泽佐",
    "乌厄",
    "因茵",
    "奥欧",
    "威维",
    "尤由",
    "昴昂",
    "梅麦",
    "汀丁",
    "碧比",
    "米蜜",
    "蕾雷菜莱",
    "文温",
    "霍荷",
    "谜迷",
    "琉流",
    ".·",
)


class SimilarCharsMap(defaultdict):
    """字符到相似字符的映射。"""

    def __missing__(self, key):
        """一个字符总是与它本身相似。"""
        self[key] = key
        return key


sc_map = SimilarCharsMap()  # singleton
sc_map |= {c: sc for sc in similar_chars for c in sc}


def f(chars: str):
    """
    返回匹配相似字符的正则表达式。

    短命名以方便大量使用。

    :param chars: 任意个字符
    :return: "[similar_chars]"
    """
    return (
        "["
        + "".join(sorted(set(flatten(sc_map[c] + s2t(sc_map[c]) for c in chars))))
        + "]"
    )


def p2o(pattern: str):
    """返回传入的正则表达式对应的所有可能译名对应的正则表达式。"""
    return "".join(c if c in "?!()=<" else f(c) for c in pattern)


def p2n(pattern: str):
    """返回传入的正则表达式对应的标准译名。"""
    return re.sub(r"\(.*?\)|\?", "", pattern)


def get_repl_func(name: str):
    """返回name对应的替换函数。"""

    def func(match: re.Match) -> str:
        """若为标准译名对应的繁体名则原样返回，否则返回标准译名。"""
        cur = match.group()
        if cur == s2t(name):
            return cur
        return name

    return func


user_fixes["translation"] = base | {
    "generator": generator_more,
    "replacements": [
        (p2o(p), get_repl_func(p2n(p)))
        for p in [  # 普通的
            "丝碧卡",
            "亚拉基亚",
            "亨克尔",
            "伽那库斯",
            "佛拉基亚",
            "佛格",
            "克林德",
            "利布雷",
            "卡佩拉",
            "卡吉雷斯",
            "卡尔兰",
            "卡尔斯腾",
            "卡德蒙",
            "卡拉拉基",
            "卡斯图鲁平原",
            "卡萝",
            "卡蜜拉",
            "古斯提科",
            "史泰德",
            "裘斯",
            "塞西尔斯",
            "夏乌拉",
            "夏库纳尔",
            "多鲁特洛",
            "奇力塔卡",
            "娅艾",
            "安妮罗泽",
            "密涅瓦",
            "尤里乌斯",
            "希尔菲",
            "希斯尼娅",
            "帕克",
            "帕特拉修",
            "库乌德",
            "库奥克",
            "库珥修",
            "库鲁刚",
            "弗琉盖尔",
            "弗莱巴尔",
            "戴因",
            "拉塞尔",
            "提姆兹",
            "文森特",
            "斯芬克丝",
            "普拉姆",
            "普莉希拉",
            "普莉斯卡",
            "李凯尔特",
            "查普",
            "格拉姆达特",
            "格拉希丝",
            "格蕾丝",
            "梅卡德",
            "梅娜",
            "梅拉奎拉",
            "欧尔尼娅",
            "欧米伽",
            "比恩",
            "汉娜",
            "波尔多",
            "波尔肯尼卡",
            "泰玛艾",
            "潘多拉",
            "特蕾西亚",
            "玛洛妮",
            "琉兹",
            "琉加",
            "璞可",
            "皮波特",
            "盖因",
            "碧翠丝",
            "福斯特",
            "米尔多",
            "米捷尔",
            "米路德",
            "约书亚",
            "缇丰",
            "缇莉艾娜",
            "罗伊",
            "梅札斯",
            "罗姆爷",
            "艾佐",
            "加德纳",
            "艾力欧尔大森林",
            "艾奇多娜",
            "艾米",
            "艾米莉娅",
            "艾西亚湿地",
            "芙蕾德莉卡",
            "荒地的合辛",
            "莉可莉丝",
            "莉莉安娜",
            "莎克拉",
            "莎缇拉",
            "莱伊",
            "莱普",
            "菜月菜穗子",
            "菜月贤一",
            "菲莉丝",
            "萨尔姆",
            "葛利奇",
            "蒂亚斯",
            "蕾姆",
            "蜜蜜",
            "席里乌斯",
            "谢尔盖",
            "贾雷克",
            "赛赫麦特",
            "赫克托尔",
            "赫罗西欧",
            "赫鲁贝尔",
            "达德利",
            "达芙妮",
            "迈尔斯",
            "邱登",
            "里卡多",
            "铁之牙",
            "阿尼茉尼",
            "阿拉姆村",
            "阿汉",
            "阿珍",
            "阿顿",
            "雷古勒斯",
            "雷诺",
            "露伊",
            "露格尼卡",
            "马可仕",
            "麦克罗托夫",
            "黑塔罗",
            "基尔提拉乌",
            "巴登凯托斯",
            "塞坦塔",
            "特里亚斯",
            "欧德古勒斯",
            "埃尔纱幕",
            "汀泽尔",
            "贝阿托莉丝",
            "奥斯洛",
            "雷金",
            "柯司兹尔",
            "福尔图娜",
            "汤普森",
            "莉西亚",
            "苏文",
            "佳莉华",
            "伊莉雅",
            "塞蕾丝缇雅",
            "禁书与谜之精灵",
            "弗洛普",
            "米迪娅姆",
            "罗安",
            "贾马尔",
            "瓜拉尔",
            "巴多海姆",
            "托斯卡",
            "拉米亚",
            "弗兰德斯",
            "米泽尔妲",
            "塔丽塔",
            "乌塔卡塔",
        ]
        + [  # 多字少字的
            "菜月·?昴",
            "安娜斯?塔西娅",
            "培提尔其乌?斯",
            "威尔海(鲁)?姆",
            "莱茵哈鲁?特",
            "罗兹瓦尔?",
        ]
        + [  # 需要特判的
            "加菲尔(?!丝)(?!特)(?!艾)",
            "拉菲尔(?!丝)(?!特)(?!艾)",
            "(?<!加)(?<!拉)菲鲁特(?!娜)",
            "利格鲁(?!卡)(?!姆)",
            "佩特拉(?!其乌斯)(?!姆)",
            "格林(?!德)",
            "(?<!艾米)莉亚拉",
            "(?<!萨)(?<!伽)拉姆(?!莉鲁)",
            "(?<!帕)贝尔托",
            "(?<!帕)提修雅",
            "凯缇(?!尔)(?!斯)",
            "(?<!莱茵哈鲁)缇碧(?!翠)",
            "艾尔莎(?!幕)",
            "(?<!多萝西)(?<!艾米莉)(?<!贝)(?<!约书)亚齐",
            "(?<!艾尔)萨德(?!拉)(?!兰)",
            "梅尔蒂(?!典)",
            "弗雷德(?!莉卡)",
            "(?<!丢)芙拉姆",
            "(?<!加)弗利艾",
            "(?<!帕)(?<!夏)(?<!拉)(?<!札)(?<!悟)库娜",
            "荷莉(?!蒙)",
            "(?<!攻)(?<!利)柯蕾特",
        ]
    ]
    + [
        (o, get_repl_func(n))
        for o, n in [  # 手动添加的替换组
            (f"{f('凛萍苹')}{f('果')}", "凛果"),
            (f"{f('贝')}{f('阿')}{f('托')}{f('莉')}{f('丝')}", "碧翠丝"),
            (f"{f('欧')}德", "欧德"),
            (f"{f('奥')}托", "奥托"),
            (f"{f('修')}{f('尔')}特", "修尔特"),
            (f"{f('基')}{f('尔')}提", "基尔提"),
            (f"阿{f('尔')}(?!{f('姆')})(?!{f('伯')})(?!{f('基')}{f('亚')})", "阿尔"),
            (f"{f('阿')}{f('斯')}{f('特')}{f('雷利')}{f('亚')}", "阿斯特雷亚"),
            (f"欧德(?!{f('古')}{f('勒')}{f('斯')})|{f('魂')}{f('力')}", "{{Od}}"),
            (f"{f('拉')}{f('格')}{f('纳')}|{f('源')}{f('池')}", "{{Laguna}}"),
            (f"{f('空')}{f('斯')}{f('图')}{f('卢')}", "柯司兹尔"),
            (f"{f('若')}{f('果')}", "如果"),
            (r"\{\{Od\}\}\{\{Laguna\}\}", "{{Od}}·{{Laguna}}"),
            (
                "(?<!禁书与谜之)(?<!人工|自然|契约)(?<!大|邪|微|准)" f"{f('精')}{f('灵')}" "(?!术)",
                "{{Spirit or Elf}}",
            ),
            (f"{f('妖')}{f('精')}", "{{Yousei or Elf}}"),
            (r"(?<=半)\{\{(Spirit|Yousei) or Elf\}\}", "{{Elf}}"),
        ]
    ],
}
_ = [  # 特判太麻烦的，不处理
    "梅丽(?!乌)(?!奎拉)(?!蒂)",
    "(?<!格)(?<!芙)(?<!·)雷德",
    "(?<!格拉姆)达兹(?!利)",
    "(?<!莉)卢安娜",
    "(?<!文森)狄加",
    "沃尔夫",
    "弗鲁夫",
]
# endregion

fixes: dict
# noinspection PyUnboundLocalVariable
fixes.update(user_fixes)
