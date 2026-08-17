"""漫画卷 Tab 双层化重构（2026-08-17，已执行完毕，幂等可重跑）。

`Tab/Manga_Volume`（单块扁平列表，缺第4章 9~13 卷与整个第5章）拆为
`Tab/Manga Arc 1~5 Volume` 五个 per-arc 双块模板，结构仿 `Tab/Manga Arc N Chapter`：
块 0 = 章导航（本章粗体，其余链到该章第1卷），块 1 = 本章各卷（当前卷靠自链接自动粗体）。

步骤：创建 5 个模板 → 34 个卷页换装（26 页替换旧调用）/补挂（8 页在 {{To do}} 后插入）。
"""

import re

import pywikibot

VOLUMES = {1: 2, 2: 5, 3: 11, 4: 13, 5: 3}
TAB_RE = re.compile(r"\{\{[Tt]ab/Manga[ _]Volume\}\}")


def template_text(arc: int) -> str:
    row1 = [
        f"|'''第{a}章'''" if a == arc else f"|[[漫画:第{a}章第1卷|第{a}章]]"
        for a in VOLUMES
    ]
    row2 = [f"|[[漫画:第{arc}章第{v}卷|{v}]]" for v in range(1, VOLUMES[arc] + 1)]
    return (
        "{{Tab\n" + "\n".join(row1) + "\n}}"
        "{{Tab\n" + "\n".join(row2) + "\n}}"
        "<noinclude>[[Category:分页模板]]</noinclude>"
    )


def main() -> None:
    site = pywikibot.Site("zh", "re0")
    site.login()
    assert site.user() == "IchiSanNi"

    for arc in VOLUMES:
        p = pywikibot.Page(site, f"Template:Tab/Manga Arc {arc} Volume")
        if not p.exists():
            p.text = template_text(arc)
            p.save(
                summary="创建漫画卷双层 Tab 模板（仿 Tab/Manga Arc N Chapter）",
                bot=True,
            )

    for arc, count in VOLUMES.items():
        new_tpl = f"{{{{Tab/Manga Arc {arc} Volume}}}}"
        for vol in range(1, count + 1):
            p = pywikibot.Page(site, f"漫画:第{arc}章第{vol}卷")
            if TAB_RE.search(p.text):
                p.text = TAB_RE.sub(new_tpl, p.text)
                summary = f"换装双层 Tab：Tab/Manga Volume → Tab/Manga Arc {arc} Volume"
            elif new_tpl in p.text:
                continue
            else:
                lines = p.text.split("\n")
                assert lines[0] == "{{Init}}" and lines[1] == "{{To do}}"
                lines.insert(2, new_tpl)
                p.text = "\n".join(lines)
                summary = f"补充双层 Tab：Tab/Manga Arc {arc} Volume"
            p.save(summary=summary, bot=True)


if __name__ == "__main__":
    main()
