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
        ("其[他它她]", "其他"),  # 用字归一（非译名，不属 translation fix）
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
t2s = OpenCC("t2s.json").convert

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


def p2st(pattern: str):
    """别名的简繁展开：正则中每个字面字符展开为 [简繁] 字符类。

    与 p2o（相似组宽展开，用于标准名）分工：别名只做简繁展开（窄），防止
    f('梅') 含 美 这类相似组把普通词卷进来。手写 [...] 字符类与转义原样保留
    （利格鲁 的宽组、梅莉 的选择性展开靠手写类表达）。
    """
    out = []
    in_class = False
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "\\" and i + 1 < len(pattern):
            out.append(pattern[i : i + 2])
            i += 2
            continue
        if c == "[":
            in_class = True
        elif c == "]":
            in_class = False
        if in_class or c in "[]":
            out.append(c)
        else:
            t = s2t(c)
            out.append(f"[{c}{t}]" if t != c else c)
        i += 1
    return "".join(out)


translation_names = [
    e.pattern or e.name for e in translations.ENTRIES if e.fuzzy
]  # 数据在 translations.py
# 长匹配优先：短名规则排在长名规则后，防止短名吃掉长名内部（菈姆 命中 [[普菈姆|..]] 类）
translation_names.sort(key=lambda p: -len(p2n(p)))

translation_manual = [  # 手动添加的替换组（模板替换；译名规则全部在 translations.py）
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
]


# 别名机制：精确对由 Entry.aliases 生成，繁体写法一并归一（fuzzy=False 条目的别名也
# 生成：名字本身不归一，别名归一到它）。带 pattern 的别名生成 guard 对（p2st 简繁展开，
# 手写字符类原样保留），别名位于更长他名内部时防子串误伤。
def _variant(v):
    return v if isinstance(v, translations.Variant) else None


translation_pairs = [
    (a2, e.name)
    for e in translations.ENTRIES
    for a in e.aliases
    if not ((v := _variant(a)) and v.pattern)
    for a0 in [a.text if isinstance(a, translations.Variant) else a]
    for a2 in dict.fromkeys((a0, s2t(a0)))
] + [
    (p2st(v.pattern), e.name)
    for e in translations.ENTRIES
    for a in e.aliases
    if (v := _variant(a)) and v.pattern
]
# 精确对/guard 对在首尾各跑一遍：先行使别名不被模糊规则截胡成中间态；收尾兜底繁简混合文本
# （名字规则把别名周围繁体字归一简体后，简体精确对才有机会命中）

user_fixes["translation"] = base | {
    "generator": generator_more,
    # 一律归一到官方简中标准名
    "exceptions": base["exceptions"]
    | {
        "inside": [
            # NekoQuote 月表的日文原文字段（Lua 字符串）不归一；replace.py 自行编译，这里只给字符串
            r'(?m)^\s*(?:jq|jt)\s*=\s*"(?:[^"\\]|\\.)*"',
            # 信息框日文原名字段不归一
            r"(?m)^\s*\|\s*name_ja\s*=[^\n]*$",
        ],
    },
    "replacements": list(translation_pairs)
    + [(p2o(p), p2n(p)) for p in translation_names]
    + list(translation_manual)
    + list(translation_pairs),
}
# endregion

fixes: dict
# noinspection PyUnboundLocalVariable
fixes.update(user_fixes)  # ty: ignore[unresolved-reference]  # fixes 由 pwb/pywikibot/fixes.py exec 本文件时注入
