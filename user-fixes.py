import inspect
import itertools
import re
import sys
from collections import defaultdict
from functools import partial
from pathlib import Path

from opencc import OpenCC

# 本文件由 pwb/pywikibot/fixes.py exec 加载（无 __file__、仓库根不在 sys.path），
# 用编译时的 co_filename 自锚定后 import 同目录的数据模块。
_HERE = Path(inspect.currentframe().f_code.co_filename).resolve().parent  # ty: ignore[unresolved-attribute]
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import translations

# 伪命名空间登记前缀（唯一权威清单）：主空间文章页靠标题前缀分类，
# Module:Init 按这些简体前缀自动分类（繁体前缀不入分类）。
# AGENTS.md「伪命名空间」节的清单以此为准；审计工具经 pywikibot.fixes 取本常量。
PSEUDO_PREFIXES = [
    "角色",
    "术语",
    "小说",
    "漫画",
    "动画",
    "游戏",
    "音乐",
    "设定集、画集",
]

# generator_base/generator_more 是 jobs/starts.py 中 ns_base/ns_more 的副本：
# 本文件由 pwb/pywikibot/fixes.py exec（无法 import 仓库包），两处事实源需手工同步。
generator_base = [
    "-start::!",
    "-start:project:!",
    "-start:template:!",
    "-start:category:!",
]
generator_more = generator_base + ["-start:module:!", "-start:mediawiki:!"]

base: dict[str, bool | dict] = {
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
        # 依据 GB/T 7714-2025：引文标注置于句号之前。
        # 连续多个引文一并前移，以终结编辑者在此细节上的反复争执。
        (r"。((?:<ref\b[^>]*?/>|<ref\b[^>]*?>[\s\S]*?</ref>)+)", r"\1。"),
    ],
}

# endregion


# region date
MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
MONTH_NUM = {m.lower(): i + 1 for i, m in enumerate(MONTHS)}


def match_to_yyyymmdd(month: int, match: re.Match) -> str:
    return f"{match.group(2)}-{str(month).zfill(2)}-{match.group(1).zfill(2)}"


def normalize_date_value(value: str) -> str:
    """单个日期值归一：Month D, YYYY → YYYY-MM-DD；Month YYYY → YYYY-MM；其余原样。"""
    m = re.fullmatch(
        rf"({'|'.join(MONTHS)})\s*(\d+)\s*[，,]\s*(\d+)", value, re.IGNORECASE
    )
    if m:
        return f"{m.group(3)}-{MONTH_NUM[m.group(1).lower()]:02d}-{int(m.group(2)):02d}"
    m = re.fullmatch(
        rf"({'|'.join(MONTHS)})\s*[，,]?\s*(\d{{4}})", value, re.IGNORECASE
    )
    if m:
        return f"{m.group(2)}-{MONTH_NUM[m.group(1).lower()]:02d}"
    return value


user_fixes["date"] = base | {
    "generator": generator_base,
    "replacements": [
        (
            rf"{month}\s*(\d+)\s*[，,]\s*(\d+)",
            # avoid late binding of i
            partial(match_to_yyyymmdd, i + 1),
        )
        for i, month in enumerate(MONTHS)
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
# 多语言堆积拆分的语言表：en 括注 → zh 参数后缀。
# 与 Module:Infobox book 的 languages 表同集（两个事实源，改动需同步）。
# 简写/笔写别名（JP/Japenese/Potuguese 均为 en 实测值）归并到对应语言；
# 集合外的标注（PAL/English/Physical/CN 等区域或形态标注）非语言，整参数保守跳过。
CRAM_LANGS = {
    "Japanese": "ja",
    "JP": "ja",
    "Japenese": "ja",  # en 拼写笔误实测值
    "Simplified Chinese": "zh_hans",
    "Traditional Chinese": "zh_hant",
    "English": "en",
    "Korean": "ko",
    "Polish": "pl",
    "Portuguese": "pt",
    "Potuguese": "pt",  # en 拼写笔误实测值
    "Portuguese-BR": "pt_br",
    "French": "fr",
    "Italian": "it",
    "Vietnamese": "vi",
    "Russian": "ru",
    "Spanish": "es",
    "Indonesian": "id",
}
CRAM_LINE = re.compile(
    r"^\|[ \t]*(pages|date|isbn)_ja[ \t]*=[ \t]*(\S[^\n]*?)[ \t]*$", re.IGNORECASE
)
CRAM_SEGMENT = re.compile(r"^(.*?)[ \t]*\(([^()]*)\)$")


def split_crammed_params(m: re.Match) -> str:
    """信息框多语言堆积参数拆分：`值 (语言)<br>值 (语言)…` → per-语言参数行。

    保守判据（不满足即原样返回，留人工）：
    - 每段都带已知语言括注（排除 (Termination)/(BD)/(TV size) 等同形异义）；
    - 含 Japanese 段（拆分后基底参数 pages_ja 等的值来源）；
    - 同语言不重复出现（分册等多段形态留人工）。
    目标参数在模板内已存在时跳过该段（保留人工值，防重复行）。
    含嵌套模板的模板体不被作用域正则匹配（保守跳过）。
    """
    head, body, tail_nl = m.group(1), m.group(2), m.group(3)
    # 只拆 Infobox book（唯一有多语言参数家族的模板，Module:Infobox book）；
    # game/bd/music 的同名参数无 per-语言渲染，拆了是死参数。
    # en 原名模板（新搬运页）本规则不匹配——template 任务先归一名，下轮收敛。
    if head[2:].split("|", 1)[0].strip().lower() != "infobox book":
        return m.group(0)
    lines = body.split("\n") if body else []
    existing = set()
    for line in lines:
        pm = re.match(r"^\|[ \t]*([a-z_]+)[ \t]*=", line, re.IGNORECASE)
        if pm:
            existing.add(pm.group(1).lower())
    out, changed = [], False
    for line in lines:
        pm = CRAM_LINE.match(line)
        parts = re.split(r"<br\s*/?>", pm.group(2)) if pm else []
        segs = [
            (m2.group(1).strip(), m2.group(2).strip())
            for s in parts
            if (m2 := CRAM_SEGMENT.match(s.strip()))
        ]
        if (
            not pm
            or not segs
            or len(segs) != len(parts)
            or any(lang not in CRAM_LANGS for _, lang in segs)
            # 基底参数的值来源（Japanese 及其别名）
            or "ja" not in {CRAM_LANGS[lang] for _, lang in segs}
            # 同语言多段（分册/别名混写）留人工——按归一后的后缀判重
            or len({CRAM_LANGS[lang] for _, lang in segs}) != len(segs)
        ):
            out.append(line)
            continue
        changed = True
        family = pm.group(1).lower()
        existing.discard(f"{family}_ja")  # 基底行被本拆分替换，不算重复
        for value, lang in segs:
            param = f"{family}_{CRAM_LANGS[lang]}"
            if param in existing:
                continue
            if family == "date":
                value = normalize_date_value(value)
            out.append(f"| {param} = {value}")
            existing.add(param)
    if not changed:
        return m.group(0)
    return head + ("\n" + "\n".join(out) if out else "") + tail_nl + "}}"


user_fixes["para"] = base | {
    "generator": generator_more,
    "replacements": [
        (rf"\|\s*{o}\s*=", f"| {n} =")
        for o, n in [
            ("Name", "name"),
            ("Image", "image"),
            # 2026-08-11 改名：字段实为日文名原文（en 把假名也填进 Kanji），
            # name_ja_kanji 名不副实 → name_ja；旧名自改名规则常驻
            # （transferbot 每次搬运重新带入 Kanji，loop 顺带收历史残留）。
            ("Kanji", "name_ja"),
            ("name_ja_kanji", "name_ja"),
            ("Romaji", "name_ja_romaji"),
            ("Alias", "alias"),
            ("Nickname", "nickname"),
            # 台版译名（全站唯一带空格的参数名，2026-08-03 归一）
            ("another translation", "name_zh_tw"),
            # 图片说明（en 搬运旧名，2026-08-03 取消大写例外）
            ("Caption", "caption"),
            # voice 系连字符 → 下划线（2026-08-03 归一）
            ("voice_zh-cn", "voice_zh_cn"),
            ("voice_zh-tw", "voice_zh_tw"),
            ("voice_zh-hk", "voice_zh_hk"),
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
            ("Affinity", "affinity"),  # en 后加的属性适性字段（zh 2026-08-22 同步）
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
            ("Pages", "pages_ja"),
            ("ISBN", "isbn_ja"),
            ("Release Date", "date_ja"),
            ("Painter", "painter"),
            ("Cover", "cover"),
            # 信息框参数名归一（2026-08-02）：en/es 搬运的旧名 → 全站统一小写蛇形。
            # 与上表同为长期条目——transferbot 每次搬运都会重新带入 en 侧旧名。
            # anime
            ("Volume", "volume"),
            ("Air Date", "air_date"),
            ("Opening", "opening"),
            ("Ending", "ending"),
            # bd
            ("Number", "number"),
            # music
            ("Singer", "singer"),
            ("Composition", "composition"),
            ("Arrangement", "arrangement"),
            ("Lyric", "lyric"),
            ("Length", "length"),
            # game
            ("Developers", "developers"),
            ("Publishers", "publishers"),
            ("Platform", "platform"),
            ("Genre", "genre"),
            ("Modes", "modes"),
            # battle + event（nocase 同时命中 Rōmaji/Also known as 大写写法）
            ("rōmaji", "name_ja_romaji"),
            ("also known as", "also_known_as"),
            ("Date", "date"),
            ("Place", "place"),
            ("Result", "result"),
            # seiyu/staff（es 搬运旧名，兜底保险）
            ("nombre", "name_en"),
            ("nacimiento", "birth"),
            ("personaje", "role"),
            ("guión", "script"),
            ("diseño", "design"),
            ("compositor", "composer"),
            ("image1", "image"),
            ("title1", "name"),
            ("caption1", "Caption"),
        ]
    ]
    + [
        # Infobox character 的 name_ja_romaji 已废弃（2026-08-11 起罗马字全部由
        # Kana2Romaji 自动生成）：删除该模板内的残留行（含上面刚由 Romaji 归一的行，
        # 即 transferbot 新搬运页带入的 en 手写值也会被清掉）。作用域用 (?!\{\{)
        # 限定在 character 信息框内（不跨 {{ 与 }}），不波及其他信息框合法的同名字段。
        (
            r"(?ms)(\{\{Infobox character(?:(?!\{\{|\}\}).)*?)^\| *name_ja_romaji *= *[^\n]*\n?",
            r"\1",
        ),
        # previous/next 参数删除：en 搬运残留，系列跳转由 Tab/* 承担，信息框一律
        # 不保留（见 docs/templates.md）；常驻以防 transferbot 复发（nocase 覆盖
        # Previous/Next 大小写变体）。
        # = 两侧用 [ \t]* 不用 \s*（\s 吃换行会把下一行吞成值）；
        # 值常以模板闭合 }} 结尾（该参数通常是信息框最后一行），须保留。
        (
            r"(?m)^[ \t]*\|[ \t]*(?:previous|next)[ \t]*=[^\n]*?(\}\})?[ \t]*\r?\n",
            lambda m: "}}\n" if m.group(1) else "",
        ),
        # 多语言堆积参数拆分（放列表最后，在上方参数名归一之后跑）：
        # en 把各语言塞在单行参数里（值 (语言)<br>值 (语言)…），
        # zh 用 per-语言参数家族（pages_*/date_*/isbn_*，Module:Infobox book）。
        (
            r"(?ms)^(\{\{[^\n{}]*?)\n((?:(?!\{\{|\}\}).)*?)(\n?)\}\}$",
            split_crammed_params,
        ),
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
            ("Games?", "游戏"),
            ("-Infinity", "INFINITY"),
            ("The Prophecy of the Throne", "虚假的王选候补"),
            ("Forbidden Book and the Mysterious Spirit", "禁书与谜之精灵"),
            (r"Misc(ellaneous|\.)?", "其他"),
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
            ("Characters", "登场人物"),
            ("References?", "注释与外部链接"),
        ]
    ],
}
# endregion

# region translation
flatten = itertools.chain.from_iterable
s2t = OpenCC("s2t.json").convert

similar_chars = translations.SIMILAR_CHARS  # 数据在 translations.py


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
    return "".join(c if c in "?!(|)=<" else f(c) for c in pattern)


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


translation_names = [
    e.pattern or e.name for e in translations.ENTRIES if e.main
]  # 数据在 translations.py

translation_manual = [  # 手动添加的替换组（结构规则：模板替换/防误伤 lookaround/选择性展开）
    (rf"{f('凛淋萍平苹')}{f('果')}", "{{Ringa}}"),
    (
        (
            "(?<!禁书与谜之)(?<!术语:)(?<!人工)(?<!自然)(?<!契约)(?<![大邪微准])"
            f"{f('精')}{f('灵')}"
            "(?!骑士|[术使])"
        ),
        "{{Seirei or Elf}}",
    ),
    (f"{f('妖')}{f('精')}", "{{Yousei or Elf}}"),
    (r"(?<=半)\{\{(Seirei|Yousei) or Elf\}\}", "{{Elf}}"),
    ("斯巴[鲁魯]", "昴"),  # 不用 f() 展开：茨(≈斯)巴 尔(≈鲁) 会误判「法茨巴尔穆」
    (f"梅{f('莉')}(?!{f('奥')})", "梅莉"),  # 防「梅里欧·阿嘎玛」误伤
    (r"(?<!莎)莉[娅婭]", "莉雅"),  # 莉娅→莉雅；前字 莎 时属 莎莉婭·费瑟兰
    (
        r"(?<!多萝西)(?<!艾米莉)(?<!约书)(?<!贝)(?<!卡秋)[亚亞][齐齊]|(?<!多萝西)(?<!艾米莉)(?<!约书)(?<!贝)(?<!卡秋)阿[奇齊]",
        "亚奇",
    ),  # 亚齐/阿奇→亚奇，guard 沿自记录
    (r"(?<!艾奇)(?<!福尔)提娜", "缇娜"),  # 提娜→缇娜，guard 沿自记录
    (r"(?<!加)弗利艾", "傅里叶"),  # 弗利艾→傅里叶，guard 沿自记录
    (r"[欧歐]德(?!古勒斯)", "奥多"),  # 欧德→奥多；欧德古勒斯 是另一存在
    (
        r"(?<!格拉姆)(?<!芙兰)达[兹茲](?!利)",
        "达茨",
    ),  # 达兹→达茨，guard 沿自记录（芙兰达兹 是 弗兰德斯 的别名）
    (
        r"(?<!加)(?<!卡)(?<!雷)德[纳納]",
        "多纳",
    ),  # 德纳→多纳；加德纳/卡德纳/雷德纳斯 是他名
    (
        r"(?<!佩)(?<!芙蕾)多尔肯(?!罗登|普里恩)",
        "多尔凯尔",
    ),  # 多尔肯→多尔凯尔，guard 沿自记录
    (r"卡[萝蘿](?!尔|爾)", "卡罗尔"),  # 卡萝尔 是同一人的完整变体，由别名精确对先行归一
    (f"其{f('他它她')}", "其他"),  # 用字归一（非译名）
]
# 有别名在更长的他名内部出现（子串误伤）的，不走精确对生成，在上面用 guard 规则处理
_GUARDED_ALIASES = {
    "莉娅",
    "亚齐",
    "阿奇",
    "提娜",
    "弗利艾",
    "欧德",
    "达兹",
    "德纳",
    "多尔肯",
    "卡萝",
}
# Entry.aliases 生成精确对，繁体写法一并归一
translation_manual += [
    (a2, e.name)
    for e in translations.ENTRIES
    for a in e.aliases
    if a not in _GUARDED_ALIASES
    for a2 in dict.fromkeys((a, s2t(a)))
]

user_fixes["translation"] = base | {
    "generator": generator_more,
    "replacements": [(p2o(p), get_repl_func(p2n(p))) for p in translation_names]
    + [(o, get_repl_func(n)) for o, n in translation_manual],
}
_ = [
    e.pattern or e.name for e in translations.RECORD_ONLY
]  # 特判太麻烦的，不处理；数据在 translations.py

# endregion

fixes: dict
# noinspection PyUnboundLocalVariable
fixes.update(user_fixes)  # ty: ignore[unresolved-reference]  # fixes 由 pwb/pywikibot/fixes.py exec 本文件时注入
