"""给 `前缀:词干` 页创建裸词干重定向（批量存在性检查版）。

旧实现逐页 Page(词干).exists() 单独查询（`Re:...` 等带冒号标题也大量误中
词干正则），实测 ~2000 请求/轮、16-18 分钟（2026-08-13，见 docs/todo.md）。
现改为：生成器只取标题（不预载内容）收集词干，zh 主空间标题集 500/批
拉取（~21 次，列表上限匿名即 500，不依赖登录）内存比对出缺失词干。
不用 prop=info 逐批查标题：Fandom 登录会话不稳定（跨语言流量互踢 +
pywikibot login() 有 cookie jar 即跳过重新认证），apihighlimits 的
500 titles/批会间歇 toomanyvalues（2026-08-13 实证，见 AGENTS.md 坑节）。
行为差异：同词干多前缀页时保留排序最前者为创建目标（与旧逐页处理顺序
等效）；词干含真实命名空间前缀的（如 小说:Category:X → Category:X）跳过
——跨命名空间存在性不在标题集覆盖范围，实践中不存在。
"""

import regex as re

import pywikibot as pwb
from pywikibot import config
from pywikibot.pagegenerators import GeneratorFactory
from pywikibot.tools import first_upper

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


def all_ns_prefixes(site) -> set[str]:
    """所有命名空间的名字（小写）：词干含这些前缀的属于其他命名空间，跳过。"""
    prefixes = set()
    for ns in site.namespaces.values():
        names = [ns.custom_name, ns.canonical_name, *ns.aliases]
        prefixes.update(n.lower() for n in names if n)
    return prefixes


if __name__ == "__main__":
    factory = GeneratorFactory()
    factory.handle_args(pwb.handle_args())  # -always 无需处理：不询问，-s 走下方分支
    site = pwb.Site()
    gen = factory.getCombinedGenerator()  # 只要标题，不预载内容
    assert gen is not None  # -start: 系列参数必定给出生成器
    stem_to_prefixed = collect_stems(page.title() for page in gen)
    zh_titles = {normalize(p.title()) for p in site.allpages(namespace=0)}
    missing = [s for s in stem_to_prefixed if s not in zh_titles]
    ns_prefixes = all_ns_prefixes(site)
    created = 0
    for stem in missing:
        prefix = stem.split(":", 1)[0].lower() if ":" in stem else None
        if prefix in ns_prefixes:
            pwb.warning(f"词干 {stem} 属其他命名空间，跳过")
            continue
        prefixed = stem_to_prefixed[stem]
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
