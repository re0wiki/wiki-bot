"""标题归一移动（留重定向）。


三类规则，依次尝试：
1. 整题模式规则 TITLE_PATTERNS：en 站模式化标题（卷/话/子页后缀）→ zh 命名，
   模式本身即前缀映射，不受「伪命名空间前缀变化」守卫限制；
2. translation 规则：标题命中译名表的页面移到简体标准名（留重定向）。
   与 replace -fix:translation 共用 user-fixes.py 的同一张译名表，译名表更新时
   无需两边同步。正文替换与标题均一律归一到简体（标题惯例只认简体，前缀同理，
   见 AGENTS.md）：含繁体字的标题做纯繁简移动（否则 fixing-redirects 解析到
   繁体存储标题，与 fix:translation 来回拉锯）；
3. 角色前缀归位：主空间无伪前缀、非子页、含 {{Infobox character}} 的非重定向页
   → 加 角色: 前缀（入 分类:角色 后 heading_char 等按分类限定的 fix 才够得着）。

跳过：重定向页、本轮已移动标题及其子页（移动遗留的重定向——预加载缓存的
isRedirectPage 是移动前的旧值，识别不了它，见 is_leftover）、产出模板调用的
规则（{{...}}）、伪命名空间前缀会变化的（规则 1 除外）、新标题含非法字符的、
目标已存在且不是指回当前页的重定向的（需人工合并）、File 空间无有效扩展名的
标题（Fandom 外部视频，见 is_external_video）。

子页后缀移动（/Image Gallery|Synopsis|Relationships → /图库|梗概|关系）的父页
解析：父标题在 zh 已是指向中文名的重定向时，落到最终目标名下（目标冲突照常跳过）。
page.move 默认 movesubpages=True，父页移动时其子页随之联动到半归一标题
（后缀未归一），全归一由后续（同轮枚举推进到或下轮）对半归一标题的内容页
执行。本轮若误移动联动遗留的旧子页重定向，全归一标题会被抢占成重定向，
内容页反被钉在半归一标题（抢占重定向带移动 null revision，非
single-rev-redirect，覆盖移动必吃 articleexists，无法自愈）。
"""

from collections.abc import Callable, Iterable

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
    [(re.compile(o, re.IGNORECASE), n) for o, n in translation_pairs if "{{" not in n]
    + [(re.compile(p2st(pat), re.IGNORECASE), n) for pat, n in translation_name_rules]
    + [
        (re.compile(o, re.IGNORECASE), n)
        for o, n in translation_manual
        if "{{" not in n  # 产出模板调用的规则不能用于标题
    ]
    + [(re.compile(o, re.IGNORECASE), n) for o, n in translation_pairs if "{{" not in n]
)
ILLEGAL_TITLE_CHARS = re.compile(r"[#<>\[\]{}|]")

_SUFFIX_MAP = {"image gallery": "图库", "synopsis": "梗概", "relationships": "关系"}


def _manga_chapter(m: re.Match) -> str:
    """Manga Arc X Chapter Y（可选 Part N）→ 漫画:第X章第Y话（Part 1→前篇 2→后篇）。"""
    part = m.group(3)
    suffix = {"1": "前篇", "2": "后篇"}.get(part or "", "")
    if part and not suffix:
        return m.group(0)  # Part 3+ 无 zh 先例，留人工
    return f"漫画:第{m.group(1)}章第{m.group(2)}话{suffix}"


def _suffix(m: re.Match) -> str:
    return "/" + _SUFFIX_MAP[m.group(1).lower()]


# 整题模式规则（有序，先头部系列题名后子页后缀，两者组合生效）。
# 命中即视为整题归位，不再套译名别名规则，也不受前缀守卫限制。
TITLE_PATTERNS: list[tuple[re.Pattern, str | Callable[[re.Match], str]]] = [
    (re.compile(r"^Re:Zero Light Novel Volume (\d+)", re.IGNORECASE), r"小说:\1卷"),
    (
        re.compile(r"^Re:Zero Tanpenshuu Volume (\d+)", re.IGNORECASE),
        r"小说:短篇集第\1卷",
    ),
    (re.compile(r"^Manga Arc (\d+) Volume (\d+)", re.IGNORECASE), r"漫画:第\1章第\2卷"),
    (
        re.compile(r"^Manga Arc (\d+) Chapter (\d+)(?: Part (\d+))?", re.IGNORECASE),
        _manga_chapter,
    ),
    (
        re.compile(r"/(Image Gallery|Synopsis|Relationships)$", re.IGNORECASE),
        _suffix,
    ),
]


def is_leftover(title: str, moved_sources: Iterable[str]) -> bool:
    """title 是本轮已移动的源标题或其子页 = 移动后遗留的重定向。

    movesubpages 联动在移动前预加载（PreloadingGenerator）的页面对象上不可见：
    其缓存的 isRedirectPage 仍是移动前的 False，treat_page 的重定向检查拦不住，
    必须靠本轮移动记录显式排除。
    """
    return any(title == s or title.startswith(f"{s}/") for s in moved_sources)


def is_external_video(title: str, extensions) -> bool:
    """File 标题无有效扩展名 = Fandom 从 YouTube 导入的外部视频。

    这类标题即外语原文名（YouTube 原标题）：译名归一会产生半简半日的
    四不像标题，且破坏 re0_image 的跨站同名比对（2026-09-06 手动带 File
    生成器参数误跑，一批视频被移成中文名后重新同步修复）。循环任务的
    生成器不含 File 空间，此防护针对手动带参误跑。
    """
    *_, ext = title.rpartition(".")
    return ext.lower() not in extensions


def resolve_move(
    old: str, rules: list[tuple[re.Pattern, str]] = RULES
) -> tuple[str | None, str | None]:
    """计算标题归一结果（纯函数，可离线测试）。

    返回 (新标题, 跳过原因)：
    - (None, None)：标题无需移动（已全简体且规则未命中）
    - (新标题, None)：可以移动（规则命中，或含繁体字做纯繁简移动）
    - (新标题, 原因)：需跳过（伪命名空间前缀变化 / 新标题含非法字符）。
      其余跳过条件（目标已存在）依赖 wiki，留在 MoveBot 里判断。

    整题模式规则（TITLE_PATTERNS）先于译名别名规则；命中即视为整题归位，
    不再套别名规则，也不受伪命名空间前缀守卫限制（模式本身即前缀映射）。
    """
    new = t2s(
        old
    )  # 标题先归一简体再套规则：正文的繁体保留语义不适用于标题（标题惯例只认简体），且繁体标题可能是与日文原名同字的写法
    pattern_hit = False
    for pattern, repl in TITLE_PATTERNS:
        substituted = pattern.sub(repl, new)
        if substituted != new:
            pattern_hit = True
            new = substituted
    if not pattern_hit:
        for pattern, name in rules:
            new = pattern.sub(lambda _, n=name: n, new)
    if new == old:  # 已全简体且规则未命中
        return None, None
    if (
        not pattern_hit
        and ":" in old
        and t2s(old).split(":", 1)[0] != new.split(":", 1)[0]
    ):
        # 规则把前缀改成另一个伪命名空间才跳过；t2s 本身的前缀归一照常移动
        return new, "伪命名空间前缀变化"
    if ILLEGAL_TITLE_CHARS.search(new):
        return new, "新标题含非法字符"
    return new, None


class MoveBot(pwb.bot.SingleSiteBot, pwb.bot.ExistingPageBot):
    """Move pages with non-standard translated titles to standard names."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.moved_sources: list[str] = []  # 本轮已移动的源标题（含模拟）

    def treat_page(self) -> None:
        page = self.current_page
        old = page.title()
        if is_leftover(old, self.moved_sources):
            return
        if page.isRedirectPage():
            return
        if page.namespace() == 6 and is_external_video(
            page.title(with_ns=False), page.site.file_extensions
        ):
            return
        reason = "译名归一"
        new, skip = resolve_move(old)
        if (
            new is None
            and ":" not in old
            and "/" not in old
            and "{{Infobox character" in page.text
        ):
            # 角色前缀归位：无伪前缀、非子页、含角色信息框的页 = 未归位角色页
            # （非主命名空间标题自带 Namespace: 前缀，已被 ":" 条件排除）
            new, reason = "角色:" + old, "角色前缀归位"
        if new is None:
            return
        if skip:
            pwb.warning(f"SKIP（{skip}）: {old} -> {new}")
            return
        # 子页后缀移动的父页解析：父标题在 zh 已是指向中文名的重定向时，
        # 落到最终目标名下（如 Melty Pristis/关系 -> 角色:梅尔蒂·布里司堤斯/关系）
        if re.search(r"/(?:Image Gallery|Synopsis|Relationships)$", old, re.IGNORECASE):
            parent = pwb.Page(self.site, old.rsplit("/", 1)[0])
            if parent.isRedirectPage():
                new = parent.getRedirectTarget().title() + "/" + new.rsplit("/", 1)[1]
        target = pwb.Page(self.site, new)
        if target.exists() and not (
            # 标准名只是指回当前页的重定向：直接移动覆盖，消除循环
            target.isRedirectPage() and target.getRedirectTarget() == page
        ):
            pwb.warning(f"SKIP（目标已存在，需人工合并）: {old} -> {new}")
            return
        if pwb.config.simulate:
            pwb.info(f"[SIMULATE] {old} -> {new}")
            self.moved_sources.append(old)
            return
        try:
            page.move(new, reason=f"{reason}: {old} -> {new}", noredirect=False)
            self.moved_sources.append(old)
        except PwbError as e:
            pwb.error(f"FAILED: {old} -> {new}: {e}")


if __name__ == "__main__":
    factory = GeneratorFactory()
    factory.handle_args(pwb.handle_args())
    MoveBot(generator=factory.getCombinedGenerator(preload=True)).run()
