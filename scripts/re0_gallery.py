import logging

import regex as re
from pywikibot import Page
from pywikibot.cosmetic_changes import CosmeticChangesToolkit
from pywikibot.pagegenerators import AllpagesPageGenerator
from tqdm import tqdm

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

gallery_pattern = re.compile(r"<gallery[^>]*>.*?</gallery>", re.DOTALL)
page_pattern = re.compile(r"(?<=}}).*(?=\[\[)", re.DOTALL)


def sync_galleries():
    """Replace zh galleries with en galleries."""
    for zh_page in tqdm(list(AllpagesPageGenerator(includeredirects=False))):
        zh_page: Page

        # get zh text
        zh_raw_text = zh_text = zh_page.text

        # get en text
        for link in zh_page.iterlanglinks():
            if link.site.code == "en":
                en_raw_text = en_text = Page(link).text
                break
        else:
            logging.debug("no en page for %s", zh_page.title())
            continue

        # ignore en templates
        en_text = NESTED_TEMPLATE_REGEX.sub("", en_text)

        # backup zh templates
        zh_templates = NESTED_TEMPLATE_REGEX.findall(zh_text)
        zh_text = NESTED_TEMPLATE_REGEX.sub("\0", zh_text)

        # check galleries counts
        zh_galleries: list[str] = gallery_pattern.findall(zh_text)
        en_galleries: list[str] = gallery_pattern.findall(en_text)
        is_sync_tabber = False
        if len(en_galleries) != len(zh_galleries):
            logging.info(
                "gallery count mismatch for %s. en: %d, zh: %d",
                zh_page.title(),
                len(en_galleries),
                len(zh_galleries),
            )

            # try to sync the page for 图库
            if not zh_page.title().endswith("图库"):
                continue
            en_pages: list[str] = page_pattern.findall(en_raw_text)
            zh_pages: list[str] = page_pattern.findall(zh_raw_text)
            if len(en_pages) != 1:
                logging.warning("en page format mismatch for %s", zh_page.title())
                continue
            if len(zh_pages) != 1:
                logging.warning("zh page format mismatch for %s", zh_page.title())
                continue
            is_sync_tabber = True
            zh_text = page_pattern.sub(en_pages[0], zh_raw_text)

        # check galleries counts again
        zh_galleries: list[str] = gallery_pattern.findall(zh_text)
        en_galleries: list[str] = gallery_pattern.findall(en_text)
        if len(en_galleries) != len(zh_galleries):
            logging.warning(
                "gallery count still mismatch for %s. en: %d, zh: %d",
                zh_page.title(),
                len(en_galleries),
                len(zh_galleries),
            )
            continue

        # replace galleries
        it = iter(en_galleries)
        zh_text = gallery_pattern.sub(lambda _: next(it), zh_text)

        # restore templates
        it = iter(zh_templates)
        zh_text = re.sub("\0", lambda _: next(it), zh_text)

        # cosmetic changes
        zh_text = CosmeticChangesToolkit(zh_page).change(zh_text)

        # check if text changed
        if zh_text == zh_page.text:
            logging.debug("no change for %s", zh_page.title())
            continue

        zh_page.text = zh_text
        zh_page.save(
            summary=f"Sync {'tabber' if is_sync_tabber else 'galleries'} with {link}"
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sync_galleries()
