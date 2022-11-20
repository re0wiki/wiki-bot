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
    source_page: pywikibot.Page,
):
    """搬运一张图片。"""
    if not target_site.logged_in():
        target_site.login()

    title = source_page.title(as_filename=True, with_ns=False)
    target_page: pywikibot.FilePage = pywikibot.FilePage(target_site, title)

    source_page: pywikibot.FilePage = get_final_redirect_target(source_page)
    if source_page is None:
        logging.warning(f"source_page is None. {title=}")
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

    logging.info(f"upload {title}")
    with TemporaryDirectory() as tmp_dir:
        filename = path.join(tmp_dir, title)
        source_page.download(filename)
        try:
            target_page.upload(
                filename,
                comment=text,
                text=text,
                report_success=False,
                ignore_warnings=True,
            )
        except (exceptions.APIError, ValueError) as e:
            logging.warning(e)


def get_final_redirect_target(page: pywikibot.Page) -> pywikibot.FilePage | None:
    """Continuously get redirect target until a non-redirect page encountered."""
    try:
        while page.isRedirectPage():
            page = page.getRedirectTarget()
    except exceptions.CircularRedirectError as e:
        logging.warning(str(e))
        return None
    else:
        if not isinstance(page, pywikibot.FilePage):
            logging.warning(f"{page.title()} is not a FilePage.")
            return None
        return page


def transfer(*, source, target):
    """搬运图片。"""
    logging.info(f"{source=}")
    logging.info(f"{target=}")

    # use allpages to include redirect pages
    for page in tqdm(source.allpages(namespace="File")):
        transfer_file(target_site=target, source_site=source, source_page=page)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.ERROR,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    pywikibot.output("Transfer files")
    pywiki_logger = logging.getLogger("pywiki")
    pywiki_logger.setLevel(logging.ERROR)

    transfer(source=pywikibot.Site("en", "re0"), target=pywikibot.Site("zh", "re0"))
