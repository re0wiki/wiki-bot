import logging

import regex as re
from pywikibot import Page
from pywikibot.pagegenerators import AllpagesPageGenerator
from tqdm import tqdm

pattern = re.compile(r"<gallery[^>]*>.*?</gallery>", re.DOTALL)


def sync_galleries():
    """Replace zh galleries with en galleries."""
    for zh_page in tqdm(AllpagesPageGenerator(includeredirects=False)):
        zh_page: Page

        for link in zh_page.iterlanglinks():
            if link.site.code == "en":
                en_text: str = Page(link).text
                break
        else:
            logging.info("no en page for %s", zh_page.title())
            continue

        zh_galleries: list[str] = pattern.findall(zh_page.text)
        en_galleries: list[str] = pattern.findall(en_text)
        if len(en_galleries) != len(zh_galleries):
            logging.info("gallery count mismatch for %s", zh_page.title())
            continue

        it = iter(en_galleries)
        zh_page.text, cnt = pattern.subn(lambda _: next(it), zh_page.text)

        if not cnt:
            logging.debug("same galleries for %s", zh_page.title())
            continue

        zh_page.save(summary=f"Sync galleries with en. {cnt} replacements.")


if __name__ == "__main__":
    sync_galleries()
