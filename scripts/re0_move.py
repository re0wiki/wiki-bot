"""标题命中 translation 规则的页面，自动移动到简体标准名（留重定向）。

与 replace -fix:translation 共用 user-fixes.py 的同一张译名表，译名表更新时
无需两边同步。与正文替换的差异：正文对繁体标准名原样保留（get_repl_func），
标题则一律归一到简体（wiki 标题惯例只认简体，前缀同理，见 AGENTS.md）。

跳过：重定向页、产出模板调用的规则（{{...}}）、伪命名空间前缀会变化的、
新标题含非法字符的、目标已存在且不是指回当前页的重定向的（需人工合并）。
"""

import re

import pywikibot.config
from pywikibot.exceptions import Error as PwbError

# translation_* / p2o / p2n 定义在 user-fixes.py，由 pywikibot/fixes.py 末尾
# exec 进自己的 globals，静态检查不可见但运行时可用。
from pywikibot.fixes import (
    p2n,  # ty: ignore[unresolved-import]
    p2o,  # ty: ignore[unresolved-import]
    translation_manual,  # ty: ignore[unresolved-import]
    translation_names,  # ty: ignore[unresolved-import]
)
from pywikibot.pagegenerators import GeneratorFactory

import pywikibot as pwb

RULES = [(re.compile(p2o(p), re.IGNORECASE), p2n(p)) for p in translation_names] + [
    (re.compile(o, re.IGNORECASE), n)
    for o, n in translation_manual
    if "{{" not in n  # 产出模板调用的规则不能用于标题
]
ILLEGAL_TITLE_CHARS = re.compile(r"[#<>\[\]{}|]")


class MoveBot(pwb.bot.SingleSiteBot, pwb.bot.ExistingPageBot):
    """Move pages with non-standard translated titles to standard names."""

    def treat_page(self) -> None:
        page = self.current_page
        if page.isRedirectPage():
            return
        old = page.title()
        new = old
        for pattern, name in RULES:
            new = pattern.sub(lambda _, n=name: n, new)
        if new == old:
            return
        if ":" in old and old.split(":", 1)[0] != new.split(":", 1)[0]:
            pwb.warning(f"SKIP（伪命名空间前缀变化）: {old} -> {new}")
            return
        if ILLEGAL_TITLE_CHARS.search(new):
            pwb.warning(f"SKIP（新标题含非法字符）: {old} -> {new}")
            return
        target = pwb.Page(self.site, new)
        if target.exists() and not (
            # 标准名只是指回当前页的重定向：直接移动覆盖，消除循环
            target.isRedirectPage() and target.getRedirectTarget() == page
        ):
            pwb.warning(f"SKIP（目标已存在，需人工合并）: {old} -> {new}")
            return
        if pwb.config.simulate:
            pwb.info(f"[SIMULATE] {old} -> {new}")
            return
        try:
            page.move(new, reason=f"译名归一: {old} -> {new}", noredirect=False)
        except PwbError as e:
            pwb.error(f"FAILED: {old} -> {new}: {e}")


if __name__ == "__main__":
    factory = GeneratorFactory()
    factory.handle_args(pwb.handle_args())
    MoveBot(generator=factory.getCombinedGenerator(preload=True)).run()
