"""llm_translate 的 en→zh 机械转换层测试（离线，不触 wiki）。"""

from repo_loader import load_module

lt = load_module("llm_translate", "scripts/tools/llm_translate.py")


# ------------------------------------------------------------ 模板名 / 内链


def test_convert_template_names():
    src = "{{Character\n|Name = X\n}}\n{{Re:Zero Light Novel Volumes| name = Y}}\n{{Quote|z}}\n"
    out = lt.convert_template_names(src)
    assert "{{Infobox character\n" in out
    assert "{{Infobox book| name = Y}}" in out
    assert "{{Quote|z}}" in out  # 映射表外的模板不动


def test_convert_links():
    mapping = {"Natsuki Subaru": "角色:菜月·昴", "Emilia": "角色:爱蜜莉雅"}
    src = "[[Natsuki Subaru]] said [[Emilia|her]]... [[Unknown Page]] [[File:X.png]]"
    out = lt.convert_links(src, mapping)
    assert "[[角色:菜月·昴|Natsuki Subaru]]" in out  # 裸链补 en 显示文字，留 agent 翻译
    assert "[[角色:爱蜜莉雅|her]]" in out  # 已有显示文字保留
    assert "[[Unknown Page]]" in out  # 未解析原样
    assert "[[File:X.png]]" in out  # 文件链不在映射内，原样


# ------------------------------------------------------------ 信息框合并


def test_merge_infobox_cjk_curation_wins():
    conv = "{{Infobox character\n| name = Natsuki Subaru\n| birthday = April 1\n}}\n"
    zh = (
        "{{Infobox character\n| name = 菜月·昴\n"
        "| birthday = 4月1日<ref>考据</ref>\n| voice_zh_cn = \n}}\n"
    )
    out = lt.merge_infobox(conv, zh)
    assert "| name = 菜月·昴" in out  # zh 策展值保留
    assert "4月1日<ref>考据</ref>" in out
    assert "April 1" not in out
    assert "| voice_zh_cn = " in out  # zh 独有参数保留（空值也留，模板渲染需要）


def test_merge_infobox_residue_uses_en():
    conv = "{{Infobox book\n| date_ja = 2014-01-24\n| isbn_ja = 978-4-04-066208-4\n}}\n"
    zh = "{{Infobox book\n| date_ja = January 24, 2014\n| isbn_ko = 979-x\n}}\n"
    out = lt.merge_infobox(conv, zh)
    assert "| date_ja = 2014-01-24" in out  # 英文残留跟 en 转换值
    assert "January" not in out
    assert "| isbn_ja = 978-4-04-066208-4" in out
    assert "| isbn_ko = 979-x" in out  # zh 独有行块尾保留


def test_merge_infobox_image_guard():
    conv = "{{Infobox character\n| image = <gallery>\nEp1.png|Anime\n</gallery>\n}}\n"
    zh = "{{Infobox character\n| image_a = <gallery>\n菜月·昴 动画.png|TV\n</gallery>\n| image = \n}}\n"
    out = lt.merge_infobox(conv, zh)
    assert "Ep1.png" not in out  # zh 有分媒介图库时 en 的单 image 丢弃
    assert "菜月·昴 动画.png|TV" in out  # 多行 gallery 值完整保留


def test_merge_infobox_drop_rules():
    conv = "{{Infobox character\n| name = X\n}}\n"
    zh = (
        "{{Infobox character\n| name = 菜月·昴\n| previous = [[动画:第1集]]\n"
        "| name_ja_romaji = 手写值\n}}\n"
    )
    out = lt.merge_infobox(conv, zh)
    assert "previous" not in out  # fix:para 删除对象不复活
    assert "name_ja_romaji" not in out  # character 的废弃字段不复活


def test_merge_structure_zh_only_infobox_kept():
    conv = "正文段。\n"
    zh = "{{Infobox event\n| name = 原创事件\n}}\n\n正文。\n"
    out = lt.merge_structure(conv, zh)
    assert out.startswith("{{Infobox event\n| name = 原创事件\n}}\n正文段。")


def test_merge_structure_no_infobox():
    assert lt.merge_structure("纯 prose。\n", "zh prose。\n") == "纯 prose。\n"


def test_split_en_body_strips_navigation():
    # 页尾 ==Navigation== + navbox 群剥离（navbox 全在 template-remove 清单）
    body = lt.split_en_body(
        "{{Parent Tab |tab1 = Information}}\n"
        "正文。\n\n"
        "==Navigation==\n"
        "{{Royal Selection Navbox}}\n"
        "{{Lugunica Navbox}}\n"
        "[[Category:Terminology]]\n"
        "[[de:X]]\n"
    )
    assert body == "正文。\n"


def test_split_en_body_trailing_navbox_without_heading():
    body = lt.split_en_body("正文。\n\n{{LN Navigation}}\n")
    assert body == "正文。\n"


# ------------------------------------------------------------ 端到端（真实 fix 表规则）


def test_convert_en_body_end_to_end():
    body = (
        "{{Re:Zero Light Novel Volumes\n"
        "|Name = Re:Zero Light Novel Volume 1\n"
        "|Pages = 292 (Japanese)<br>312 (Korean)\n"
        "|Release Date = January 24, 2014 (Japanese)<br>July 19, 2016 (English)\n"
        "|Cover = [[Emilia]]<br>[[Puck]]\n"
        "| previous = none\n"
        "}}\n"
        "==Synopsis==\n"
        "[[Natsuki Subaru]] is summoned.\n"
    )
    zh_text = "{{Init}}\n{{Infobox book\n| painter = [[wikipedia:zh:大塚真一郎|大塚真一郎]]\n}}\n\n旧文。\n\n[[en:Re:Zero Light Novel Volume 1]]\n"
    mapping = {
        "Emilia": "角色:爱蜜莉雅",
        "Puck": "角色:帕克",
        "Natsuki Subaru": "角色:菜月·昴",
    }
    out = lt.convert_en_body(body, zh_text, mapping, "小说:1卷")
    assert "{{Infobox book" in out  # 模板名归一
    assert "| name = Re:Zero Light Novel Volume 1" in out  # 参数名归一
    assert "| pages_ja = 292\n| pages_ko = 312" in out  # 堆积拆分
    assert "| date_ja = 2014-01-24" in out and "| date_en = 2016-07-19" in out  # 日期
    assert "previous" not in out  # 删行规则
    assert "[[角色:爱蜜莉雅|Emilia]]" in out  # 内链目标替换
    assert "== 梗概 ==" in out  # 标题归一
    assert "[[角色:菜月·昴|Natsuki Subaru]] is summoned." in out
    assert "大塚真一郎" in out  # zh 独有字段合并保留
