from typing import NamedTuple

import regex as re
from pywikibot.cosmetic_changes import CosmeticChangesToolkit
from pywikibot.pagegenerators import GeneratorFactory

import pywikibot as pwb

# 改编自 pywikibot textlib.NESTED_TEMPLATE_REGEX：去掉命名捕获组（findall 要
# 取整体匹配串做模板备份/还原）与 unhandled_depth 分支。不换成 textlib 原版
# （findall 会返回分组元组）或 mwparserfromhell（历史决策，见其下注释的
# 原始理由；现已有 tests/test_gallery.py 离线回归）。
NESTED_TEMPLATE_REGEX = re.compile(
    r"""
{{\s*(?:msg:\s*)?
  (?:[^{\|#0-9][^{\|#]*?)\s*
  (?:\|(?:[^{]*?
          (?:(?:{{{[^{}]+?}}}
            |{{[^{}]+?}}
            |{[^{}]*?}
          ) [^{]*?
        )*?
    )?
  )?
}}
""",
    re.VERBOSE | re.DOTALL,
)
GALLERY_REGEX = re.compile(r"<gallery[^>]*>.*?</gallery>", re.DOTALL)
# 只匹配字面 <tabber> 块（内层嵌套走 {{#tag:tabber}} 解析函数，不会误截）。
TABBER_REGEX = re.compile(r"<tabber>.*?</tabber>", re.DOTALL)


class MergeResult(NamedTuple):
    text: str | None  # None = 本页无法处理（message 为原因）
    is_tabber: bool  # 是否走了 tabber 整段同步
    message: str  # 失败原因或过程信息


def merge_galleries(zh_raw_text: str, en_raw_text: str) -> MergeResult:
    """把 zh 页面的 <gallery> 内容替换为 en 对应内容（纯函数，可离线测试）。

    zh 侧模板先备份为 \\0 占位符、替换画廊后再还原，避免 en 模板混入。
    两侧画廊数量不一致时，用 TABBER_REGEX 把 zh 的 tabber 块整块替换为 en 的
    （只动 tabber 块，zh 页首模板与页尾链接/分类原样保留），再复核数量；
    仍不一致或块数不为 1 则返回 text=None。
    """
    # Ignore en templates.
    en_text = NESTED_TEMPLATE_REGEX.sub("", en_raw_text)

    # Backup zh templates.
    zh_templates = NESTED_TEMPLATE_REGEX.findall(zh_raw_text)
    zh_text = NESTED_TEMPLATE_REGEX.sub("\0", zh_raw_text)

    # Check galleries counts.
    zh_galleries: list[str] = GALLERY_REGEX.findall(zh_text)
    en_galleries: list[str] = GALLERY_REGEX.findall(en_text)
    is_sync_tabber = False
    if len(en_galleries) != len(zh_galleries):
        # Try to sync the tabber block.
        en_tabbers: list[str] = TABBER_REGEX.findall(en_raw_text)
        zh_tabbers: list[str] = TABBER_REGEX.findall(zh_raw_text)
        if len(en_tabbers) != 1 or len(zh_tabbers) != 1:
            return MergeResult(
                None,
                False,
                f"incorrect tabber format: en tabbers={len(en_tabbers)}, "
                f"zh tabbers={len(zh_tabbers)}",
            )

        is_sync_tabber = True
        # lambda 替换避免 en 内容里的反斜杠被当作转义。
        zh_text = TABBER_REGEX.sub(lambda _: en_tabbers[0], zh_raw_text, count=1)

        # Check galleries counts again.
        zh_galleries = GALLERY_REGEX.findall(zh_text)
        en_galleries = GALLERY_REGEX.findall(en_text)
        if len(en_galleries) != len(zh_galleries):
            return MergeResult(
                None,
                True,
                f"gallery count still mismatch: en={len(en_galleries)}, "
                f"zh={len(zh_galleries)}",
            )

    # Replace galleries.
    it = iter(en_galleries)
    zh_text = GALLERY_REGEX.sub(lambda _: next(it), zh_text)

    # Restore templates.
    it = iter(zh_templates)
    zh_text = re.sub("\0", lambda _: next(it), zh_text)

    return MergeResult(zh_text, is_sync_tabber, "")


class GalleryBot(pwb.bot.SingleSiteBot, pwb.bot.ExistingPageBot):
    """Replace zh galleries with en galleries."""

    def treat_page(self) -> None:
        zh_raw_text = self.current_page.text

        # Get en text.
        for link in self.current_page.iterlanglinks():
            if link.site.code == "en":
                en_raw_text = pwb.Page(link).text
                break
        else:
            return pwb.logging.info("No en page for %s.", self.current_page.title())

        result = merge_galleries(zh_raw_text, en_raw_text)
        if result.is_tabber:
            pwb.logging.info(
                "Gallery count mismatch for %s; synced whole tabber section.",
                self.current_page.title(),
            )
        if result.text is None:
            return pwb.logging.error(
                "%s: %s", self.current_page.title(), result.message
            )

        # Cosmetic changes.
        zh_text = CosmeticChangesToolkit(self.current_page).change(result.text)
        if isinstance(zh_text, bool):
            return pwb.logging.error(
                "Cosmetic failed for %s.", self.current_page.title()
            )

        # Check if text changed.
        if zh_text == self.current_page.text:
            return pwb.logging.info("No change for %s.", self.current_page.title())

        self.put_current(
            zh_text,
            summary=f"Sync {'tabber' if result.is_tabber else 'galleries'} with {link}.",
        )

        return None


def main() -> None:
    factory = GeneratorFactory()
    args = factory.handle_args(pwb.handle_args())

    options = {}
    for arg in args:
        options[arg.removeprefix("-")] = True

    GalleryBot(generator=factory.getCombinedGenerator(preload=True), **options).run()


if __name__ == "__main__":
    main()
