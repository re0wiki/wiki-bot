"""标题命中 translation 规则的页面，自动移动到简体标准名（留重定向）。

与 replace -fix:translation 共用 user-fixes.py 的同一张译名表，译名表更新时
无需两边同步。正文替换与标题均一律归一到简体（标题惯例只认简体，前缀同理，见 AGENTS.md）。

跳过：重定向页、产出模板调用的规则（{{...}}）、伪命名空间前缀会变化的、
新标题含非法字符的、目标已存在且不是指回当前页的重定向的（需人工合并）。
"""

import regex as re

import pywikibot as pwb
import pywikibot.config
from pywikibot.exceptions import Error as PwbError

# translation_* / p2st 定义在 user-fixes.py，由 pwb/pywikibot/fixes.py 末尾
# exec 进自己的 globals，静态检查不可见但运行时可用。
from pywikibot.fixes import (
    p2st,  # ty: ignore[unresolved-import]
    t2s,  # ty: ignore[unresolved-import]
    translation_manual,  # ty: ignore[unresolved-import]
    translation_name_rules,  # ty: ignore[unresolved-import]
    translation_pairs,  # ty: ignore[unresolved-import]
)
from pywikibot.pagegenerators import GeneratorFactory

RULES = (
    [(re.compile(o, re.IGNORECASE), n) for o, n in translation_pairs]
    + [(re.compile(p2st(pat), re.IGNORECASE), n) for pat, n in translation_name_rules]
    + [
        (re.compile(o, re.IGNORECASE), n)
        for o, n in translation_manual
        if "{{" not in n  # 产出模板调用的规则不能用于标题
    ]
    + [(re.compile(o, re.IGNORECASE), n) for o, n in translation_pairs]
)
ILLEGAL_TITLE_CHARS = re.compile(r"[#<>\[\]{}|]")


def resolve_move(
    old: str, rules: list[tuple[re.Pattern, str]] = RULES
) -> tuple[str | None, str | None]:
    """计算标题归一结果（纯函数，可离线测试）。

    返回 (新标题, 跳过原因)：
    - (None, None)：标题无需移动
    - (新标题, None)：可以移动
    - (新标题, 原因)：需跳过（伪命名空间前缀变化 / 新标题含非法字符）。
      其余跳过条件（目标已存在）依赖 wiki，留在 MoveBot 里判断。
    """
    new = t2s(
        old
    )  # 标题先归一简体再套规则：正文的繁体保留语义不适用于标题（标题惯例只认简体），且繁体标题可能是与日文原名同字的写法
    for pattern, name in rules:
        new = pattern.sub(lambda _, n=name: n, new)
    if new == t2s(old):  # 规则未命中：不做纯繁简移动
        return None, None
    if ":" in old and old.split(":", 1)[0] != new.split(":", 1)[0]:
        return new, "伪命名空间前缀变化"
    if ILLEGAL_TITLE_CHARS.search(new):
        return new, "新标题含非法字符"
    return new, None


class MoveBot(pwb.bot.SingleSiteBot, pwb.bot.ExistingPageBot):
    """Move pages with non-standard translated titles to standard names."""

    def treat_page(self) -> None:
        page = self.current_page
        if page.isRedirectPage():
            return
        old = page.title()
        new, skip = resolve_move(old)
        if new is None:
            return
        if skip:
            pwb.warning(f"SKIP（{skip}）: {old} -> {new}")
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
