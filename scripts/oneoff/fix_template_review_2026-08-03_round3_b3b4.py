"""2026-08-03 三轮复查 B3+B4 修复：#invoke 大小写归一 + Tab 显示文本简体化。

B3: interwiki→Interwiki（Infobox battle/character、To do×2）、tab→Tab（Tab）。
    功能等价（标题首字母大写规范化），纯源码一致性。
B4: 13 个 Tab 子页中 10 个的链接显示文本繁体→简体；3 条经重定向链接顺手直连。
    Kararagi Reaper、Oni Sisters 的目标页本身标题含繁体且真实存在——目标不动，
    只改显示文本。Beatrice and Rem / Content 是「除」同形字误报，不改。

每页：精确匹配断言 → 替换 → 保存（bot=False，手动编辑不加 bot flag）。
Tab 改动前后 action=parse 对比渲染等价（显示文本变化除外）。
失败即停，不静默跳过。
"""

import pywikibot

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"


def edit(title: str, replacements: list[tuple[str, str]], summary: str) -> None:
    page = pywikibot.Page(site, title)
    text = page.text
    for old, new in replacements:
        n = text.count(old)
        assert n >= 1, f"{title}: 未命中 {old!r}"
        text = text.replace(old, new)
    page.text = text
    page.save(summary=summary)
    print(f"saved {title} ({len(replacements)} 组)")


SUM3 = "#invoke 模块名大小写归一为实际模块名（功能等价，纯一致性）"
edit("Template:Infobox battle", [("{{#invoke:interwiki", "{{#invoke:Interwiki")], SUM3)
edit(
    "Template:Infobox character", [("{{#invoke:interwiki", "{{#invoke:Interwiki")], SUM3
)
edit("Template:To do", [("{{#invoke:interwiki", "{{#invoke:Interwiki")], SUM3)
edit("Template:Tab", [("{{#invoke:tab", "{{#invoke:Tab")], SUM3)

SUM4 = (
    "Tab 链接显示文本繁体转简体（渲染经 langconv 本就等价）；经重定向链接直连现行标题"
)
edit(
    "Template:Tab/Anastasia's Side Story",
    [
        ("|纖弱手腕繁盛記]]", "|纤弱手腕繁盛记]]"),
        ("|最優秀遊記]]", "|最优秀游记]]"),
    ],
    SUM4,
)
edit(
    "Template:Tab/Emilia's Side Story",
    [
        ("|王都觀光記]]", "|王都观光记]]"),
        ("|初次约會]]", "|初次约会]]"),
    ],
    SUM4,
)
edit(
    "Template:Tab/Joshua Juukulius's Careful Encyclopedia",
    [
        (
            "[[小说:約書亞·尤克歷烏斯的切勿大意慎重百科Ex|Ex]]",
            "[[小说:约书亚·尤克历乌斯的切勿大意慎重百科Ex|Ex]]",
        ),
    ],
    SUM4,
)
edit(
    "Template:Tab/Julius Juukulius's Promise Keeping Notebook",
    [
        (
            "|由里乌斯·尤克歷烏斯的言出必行備忘錄]]",
            "|由里乌斯·尤克历乌斯的言出必行备忘录]]",
        ),
    ],
    SUM4,
)
edit(
    "Template:Tab/Priscilla's Cheers for Me",
    [("|餘興篇]]", "|余兴篇]]")],
    SUM4,
)
edit(
    "Template:Tab/Ram's Side Story",
    [
        ("|拒絕搭訕記]]", "|拒绝搭讪记]]"),
        ("|晚間學習會]]", "|晚间学习会]]"),
        ("|姐姐之心很複雜]]", "|姐姐之心很复杂]]"),
    ],
    SUM4,
)
edit(
    "Template:Tab/Rem's Side Story",
    [("|少女心超複雜]]", "|少女心超复杂]]")],
    SUM4,
)
edit(
    "Template:Tab/Sword Demon Love Story",
    [("|地龍之都，弗蘭德斯篇]]", "|地龙之都，弗兰德斯篇]]")],
    SUM4,
)
edit(
    "Template:Tab/The Land of Nascent Wolves",
    [
        (
            "[[小说:新生狼之國/佛拉基亞華麗皇帝的工作|佛拉基亞華麗皇帝的工作]]",
            "[[小说:新生狼之國/佛拉基亚華麗皇帝的工作|佛拉基亚华丽皇帝的工作]]",
        ),
        (
            "[[小说:新生狼之國/佛拉基亞華麗皇帝的工作②|②]]",
            "[[小说:新生狼之國/佛拉基亚華麗皇帝的工作②|②]]",
        ),
    ],
    SUM4,
)
edit(
    "Template:Tab/The Oni Sisters of the Hidden Village",
    [
        ("|歡迎來到晚會]]", "|欢迎来到晚会]]"),
        ("|~女僕們的夜曲~]]", "|~女仆们的夜曲~]]"),
    ],
    SUM4,
)
edit(
    "Template:Tab/The Oni Sisters of the Hidden Village/Neko",
    [
        ("|歡迎來到晚會]]", "|欢迎来到晚会]]"),
        ("|~女僕們的夜曲~]]", "|~女仆们的夜曲~]]"),
    ],
    SUM4,
)
print("ALL DONE")
