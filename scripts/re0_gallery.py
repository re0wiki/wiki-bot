import regex as re
from pywikibot.cosmetic_changes import CosmeticChangesToolkit
from pywikibot.pagegenerators import GeneratorFactory

import pywikibot as pwb

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
PAGE_REGEX = re.compile(r"(?<=}}).*?(?=\[\[)", re.DOTALL)


class GalleryBot(pwb.bot.SingleSiteBot, pwb.bot.ExistingPageBot):
    """Replace zh galleries with en galleries."""

    def treat_page(self) -> None:
        # Get zh text.
        zh_raw_text = zh_text = self.current_page.text

        # Get en text.
        for link in self.current_page.iterlanglinks():
            if link.site.code == "en":
                en_raw_text = en_text = pwb.Page(link).text
                break
        else:
            return pwb.logging.info("No en page for %s.", self.current_page.title())

        # Ignore en templates.
        en_text = NESTED_TEMPLATE_REGEX.sub("", en_text)

        # Backup zh templates.
        zh_templates = NESTED_TEMPLATE_REGEX.findall(zh_text)
        zh_text = NESTED_TEMPLATE_REGEX.sub("\0", zh_text)

        # Check galleries counts.
        zh_galleries: list[str] = GALLERY_REGEX.findall(zh_text)
        en_galleries: list[str] = GALLERY_REGEX.findall(en_text)
        is_sync_tabber = False
        if len(en_galleries) != len(zh_galleries):
            pwb.logging.info(
                "Gallery count mismatch for %s. en: %d, zh: %d.",
                self.current_page.title(),
                len(en_galleries),
                len(zh_galleries),
            )

            # Try to sync the page.
            en_pages: list[str] = PAGE_REGEX.findall(en_raw_text)
            zh_pages: list[str] = PAGE_REGEX.findall(zh_raw_text)
            if len(en_pages) != 1 or len(zh_pages) != 1:
                return pwb.logging.error(
                    "Incorrect page format for %s. en: %d, zh: %d.",
                    self.current_page.title(),
                    len(en_pages),
                    len(zh_pages),
                )

            is_sync_tabber = True
            zh_text = PAGE_REGEX.sub(en_pages[0], zh_raw_text)

            # Check galleries counts again.
            zh_galleries: list[str] = GALLERY_REGEX.findall(zh_text)
            en_galleries: list[str] = GALLERY_REGEX.findall(en_text)
            if len(en_galleries) != len(zh_galleries):
                return pwb.logging.error(
                    "Gallery count still mismatch for %s. en: %d, zh: %d.",
                    self.current_page.title(),
                    len(en_galleries),
                    len(zh_galleries),
                )

        # Replace galleries.
        it = iter(en_galleries)
        zh_text = GALLERY_REGEX.sub(lambda _: next(it), zh_text)

        # Restore templates.
        it = iter(zh_templates)
        zh_text = re.sub("\0", lambda _: next(it), zh_text)

        # Cosmetic changes.
        zh_text = CosmeticChangesToolkit(self.current_page).change(zh_text)
        if isinstance(zh_text, bool):
            return pwb.logging.error(
                "Cosmetic failed for %s.", self.current_page.title()
            )

        # Check if text changed.
        if zh_text == self.current_page.text:
            return pwb.logging.info("No change for %s.", self.current_page.title())

        self.put_current(
            zh_text,
            summary=f"Sync {'tabber' if is_sync_tabber else 'galleries'} with {link}.",
        )

        return None


def main() -> None:
    factory = GeneratorFactory()
    args = factory.handle_args(pwb.handle_args())

    options = {}
    for arg in args:
        options[arg] = True

    GalleryBot(generator=factory.getCombinedGenerator(preload=True), **options).run()


if __name__ == "__main__":
    main()
