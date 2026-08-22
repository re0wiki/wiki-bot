"""para fix 的 previous/next 参数删除规则测试（离线，不触 wiki）。"""

import importlib
import re
from typing import Any

fx = importlib.import_module("pywikibot.fixes")

# user_fixes 定义在 user-fixes.py，由 pwb/pywikibot/fixes.py 末尾 exec 进自己的
# globals，静态检查不可见，故经 __dict__ 取（同 test_translation.py 模式）。
user_fixes: dict[str, Any] = fx.__dict__["user_fixes"]


def apply_para(text: str) -> str:
    """模拟 replace.py 引擎：顺序应用全部 replacements（regex + nocase）。"""
    for pat, repl in user_fixes["para"]["replacements"]:
        text = re.sub(pat, repl, text, flags=re.IGNORECASE)
    return text


def test_plain_line_removed():
    src = "{{Infobox anime\n| name = X\n| previous = [[动画:第79集|Episode 79]]\n| next = [[动画:第81集|Episode 81]]}}\n"
    out = apply_para(src)
    assert out == "{{Infobox anime\n| name = X\n}}\n"


def test_closing_braces_preserved():
    src = "{{Infobox anime\n| name = X\n| next = [[动画:第81集|Episode 81]]}}\n"
    assert apply_para(src) == "{{Infobox anime\n| name = X\n}}\n"


def test_empty_value_attached_braces():
    # 形态：空值且与模板闭合同行（| next =}}）
    src = "{{Infobox bd\n| name = X\n| next =}}\n"
    assert apply_para(src) == "{{Infobox bd\n| name = X\n}}\n"


def test_empty_value_then_next_param_not_swallowed():
    # 空值独占一行时不得吞掉下一行参数
    src = "{{Infobox book\n| next = \n| cover = X\n}}\n"
    assert apply_para(src) == "{{Infobox book\n| cover = X\n}}\n"


def test_no_space_variant():
    src = "{{Infobox anime\n| name=X\n|previous=[[动画:第79集]]\n}}\n"
    # 既有的 Name→name 归一规则顺带把 | name=X 改成 | name =X，属预期行为
    assert apply_para(src) == "{{Infobox anime\n| name =X\n}}\n"


def test_similar_param_names_untouched():
    # Infobox character 的合法字段，不得误伤
    src = "{{Infobox character\n| previous_affiliation = [[术语:王国]]\n| next_episode = x\n}}\n"
    assert apply_para(src) == src


# ------------------------------------------------------------ 多语言堆积参数拆分


def test_cram_basic_split():
    # en 搬运真实形态（小说:1卷）：Pages/Release Date 多语言堆积单行
    src = (
        "{{Infobox book\n| name = X\n"
        "| pages_ja = 292 (Japanese)<br>312 (Korean)<br>280 (Traditional Chinese)\n"
        "| date_ja = January 24, 2014 (Japanese)<br>March 2018 (Russian)"
        "<br>April 1, 2018 (Spanish)\n}}\n"
    )
    assert apply_para(src) == (
        "{{Infobox book\n| name = X\n"
        "| pages_ja = 292\n| pages_ko = 312\n| pages_zh_hant = 280\n"
        "| date_ja = 2014-01-24\n| date_ru = 2018-03\n| date_es = 2018-04-01\n}}\n"
    )


def test_cram_unnormalized_param_names():
    # en 原名参数先归一；en 原名模板本轮不拆（template 任务先归一名，下轮收敛）
    src = (
        "{{Re:Zero Light Novel Volumes| name = X\n"
        "|Pages = 292 (Japanese)<br>312 (Korean)\n}}\n"
    )
    assert apply_para(src) == (
        "{{Re:Zero Light Novel Volumes| name = X\n"
        "| pages_ja = 292 (Japanese)<br>312 (Korean)\n}}\n"
    )


def test_cram_glued_closing_braces():
    # 模板闭合 }} 与末行参数同行
    src = (
        "{{Infobox book\n| date_ja = 2014-01-24 (Japanese)<br>2016-07-19 (English)}}\n"
    )
    assert apply_para(src) == (
        "{{Infobox book\n| date_ja = 2014-01-24\n| date_en = 2016-07-19}}\n"
    )


def test_cram_duplicate_language_skipped():
    # 同语言多段（分册形态，真实案例 小说:從零開始的無職轉生）→ 整参数留人工
    src = (
        "{{Infobox book\n"
        "| pages_ja = 15 (Part 1) (Japanese)<br>17 (Part 2) (Japanese)\n}}\n"
    )
    assert apply_para(src) == src


def test_cram_comma_month_year():
    src = "{{Infobox book\n| date_ja = 2015-12-22 (Japanese)<br>August, 2020 (Portuguese)\n}}\n"
    assert apply_para(src) == (
        "{{Infobox book\n| date_ja = 2015-12-22\n| date_pt = 2020-08\n}}\n"
    )


def test_cram_non_book_template_untouched():
    # game/bd/music 无 per-语言参数家族，纯语言括注堆积也不拆（拆了是死参数）
    src = (
        "{{Infobox game\n"
        "| date_ja = September 9, 2020 (Japanese)<br>May 12, 2023 (English)\n}}\n"
    )
    assert apply_para(src) == src


def test_cram_isbn_family():
    src = (
        "{{Infobox book\n"
        "| isbn_ja = 978-4-04-066208-4 (Japanese)<br>979-11-319-0098-7 (Korean)\n}}\n"
    )
    assert apply_para(src) == (
        "{{Infobox book\n"
        "| isbn_ja = 978-4-04-066208-4\n| isbn_ko = 979-11-319-0098-7\n}}\n"
    )


def test_cram_single_annotated_segment():
    # 单段带语言括注（无 <br>）：摘括注顺带归一日期
    src = "{{Infobox book\n| date_ja = April 28, 2021 (Japanese)\n}}\n"
    assert apply_para(src) == "{{Infobox book\n| date_ja = 2021-04-28\n}}\n"


def test_cram_idempotent():
    # 已拆分形态（zh 现行）不再匹配
    src = (
        "{{Infobox book\n| pages_ja = 292\n| pages_ko = 312\n"
        "| date_ja = 2014-01-24\n| date_ru = 2018-03\n}}\n"
    )
    assert apply_para(src) == src


def test_cram_unknown_language_skipped():
    # 语言表外的标注（区域/形态标注如 PAL）→ 整参数保守跳过
    src = (
        "{{Infobox book\n"
        "| date_ja = January 24, 2014 (Japanese)<br>August 2024 (PAL)\n}}\n"
    )
    assert apply_para(src) == src


def test_cram_language_aliases():
    # Indonesian 与简写/笔误别名（JP/Japenese/Potuguese/Portuguese-BR 均 en 实测）
    src = (
        "{{Infobox book\n"
        "| date_ja = 2014-01-24 (JP)<br>2021-05-05 (Indonesian)"
        "<br>2018-04-01 (Spanish)\n"
        "| pages_ja = 292 (Japenese)<br>280 (Potuguese)<br>300 (Portuguese-BR)\n}}\n"
    )
    assert apply_para(src) == (
        "{{Infobox book\n"
        "| date_ja = 2014-01-24\n| date_id = 2021-05-05\n| date_es = 2018-04-01\n"
        "| pages_ja = 292\n| pages_pt = 280\n| pages_pt_br = 300\n}}\n"
    )


def test_cram_non_language_annotations_untouched():
    # 同形异义：(Termination)/(BD)/(TV size) 不是语言括注
    for src in (
        "{{Infobox game\n| date_ja = September 9, 2020<br>May 12, 2023 (Termination)\n}}\n",
        "{{Infobox bd\n| number = ZMXZ-10651 (BD)<br>ZMBZ-10661 (DVD)\n}}\n",
        "{{Infobox music\n| length = 1:30 (TV size)<br>4:18 (Full version)\n}}\n",
    ):
        assert apply_para(src) == src


def test_cram_existing_param_preserved():
    # 人工已拆的 date_ko 保留人工值，拆分跳过该段
    src = (
        "{{Infobox book\n| date_ko = 2014-08-02（人工订正）\n"
        "| date_ja = January 24, 2014 (Japanese)<br>August 1, 2014 (Korean)\n}}\n"
    )
    assert apply_para(src) == (
        "{{Infobox book\n| date_ko = 2014-08-02（人工订正）\n"
        "| date_ja = 2014-01-24\n}}\n"
    )


def test_cram_nested_template_skipped():
    # 模板体内含嵌套模板 → 作用域正则不匹配，整体保守跳过
    src = (
        "{{Infobox book\n| name = {{R|X|Y}}\n"
        "| pages_ja = 292 (Japanese)<br>312 (Korean)\n}}\n"
    )
    assert apply_para(src) == src
