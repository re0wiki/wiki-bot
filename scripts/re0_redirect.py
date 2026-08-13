"""给 `前缀:词干` 页创建裸词干重定向（批量存在性检查版）。

旧实现逐页 Page(词干).exists() 单独查询（`Re:...` 等带冒号标题也大量误中
词干正则），实测 ~2000 请求/轮、16-18 分钟（2026-08-13，见 docs/todo.md）。
现改为：生成器只取标题（不预载内容），词干收集后 prop=info 50/批批量查
存在性（~50 请求），仅对不存在的词干建重定向。行为差异：同词干多前缀页
时保留排序最前者为创建目标（与旧逐页处理顺序等效）。
"""

import regex as re
from pywikibot.pagegenerators import GeneratorFactory
from pywikibot.tools import first_upper

import pywikibot as pwb
from pywikibot import config

REGEX = re.compile(r".+?:(.+)")


def normalize(title: str) -> str:
    """归一到 MediaWiki 规范标题（下划线转空格、首字母大写）。"""
    return first_upper(title.replace("_", " ").strip())


def collect_stems(titles) -> dict[str, str]:
    """词干（规范化） -> 前缀页标题。同词干保留排序最前的。"""
    out: dict[str, str] = {}
    for title in titles:
        if (m := REGEX.fullmatch(title)) and (stem := m.group(1)):
            out.setdefault(normalize(stem), title)
    return out


def find_missing(site, stems: list[str]) -> list[str]:
    """批量存在性检查（50/批），返回不存在的（规范化）词干标题。"""
    missing = []
    for i in range(0, len(stems), 50):
        data = site.simple_request(
            action="query",
            prop="info",
            titles="|".join(stems[i : i + 50]),
            formatversion="2",
            format="json",
        ).submit()
        missing.extend(p["title"] for p in data["query"]["pages"] if p.get("missing"))
    return missing


if __name__ == "__main__":
    factory = GeneratorFactory()
    factory.handle_args(pwb.handle_args())  # -always 无需处理：不询问，-s 走下方分支
    site = pwb.Site()
    gen = factory.getCombinedGenerator()  # 只要标题，不预载内容
    assert gen is not None  # -start: 系列参数必定给出生成器
    stem_to_prefixed = collect_stems(page.title() for page in gen)
    missing = find_missing(site, list(stem_to_prefixed))
    created = 0
    for stem in missing:
        prefixed = stem_to_prefixed.get(stem)
        if prefixed is None:
            pwb.warning(f"API 规范化标题 {stem} 与本地不一致，跳过")
            continue
        if config.simulate:
            pwb.info(f"将创建 {stem} -> {prefixed}")
        else:
            pwb.Page(site, stem).set_redirect_target(
                pwb.Page(site, prefixed),
                create=True,
                summary=f"{stem} -> {prefixed}",
            )
        created += 1
    pwb.info(
        f"词干 {len(stem_to_prefixed)} 个，缺失 {len(missing)} 个，创建 {created} 个重定向"
    )
