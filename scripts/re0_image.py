import logging
from os import path
from tempfile import TemporaryDirectory

import pywikibot
from pywikibot import exceptions
from tqdm import tqdm


def transfer_file(
    *,
    target_site: pywikibot.Site,
    source_site: pywikibot.Site,
    source_page: pywikibot.FilePage,
):
    """搬运一张图片。"""
    if not target_site.logged_in():
        target_site.login()

    title = source_page.title(as_filename=True, with_ns=False)
    if title.startswith("Site-"):
        return
    target_page: pywikibot.FilePage = pywikibot.FilePage(target_site, title)

    if source_page is None:
        logging.warning("source_page is None. title=%s", title)
        return

    if (
        target_page.exists()
        and target_page.latest_file_info.sha1 == source_page.latest_file_info.sha1
    ):
        return

    text = "\n".join([x.astext() for x in source_page.iterlanglinks()])
    if text != "":
        text += "\n"
    text += f"[[{source_site.code}:{source_page.title(with_ns=True)}]]"

    logging.info("upload %s", title)
    with TemporaryDirectory() as tmp_dir:
        filename = path.join(tmp_dir, title)
        source_page.download(filename)
        target_page.upload(
            filename,
            comment=text,
            text=text,
            report_success=False,
            ignore_warnings=True,
        )


def transfer(*, source, target):
    """搬运图片。"""
    logging.info("source=%s, target=%s", source, target)

    for page in tqdm(list(source.allimages())):
        assert isinstance(page, pywikibot.FilePage)
        try:
            transfer_file(target_site=target, source_site=source, source_page=page)
        except (exceptions.PageRelatedError, exceptions.APIError, ValueError) as e:
            logging.warning(e)
            continue


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    transfer(source=pywikibot.Site("en", "re0"), target=pywikibot.Site("zh", "re0"))
