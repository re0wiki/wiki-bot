import logging
from os import path
from tempfile import TemporaryDirectory

from tqdm import tqdm

import pywikibot
from pywikibot import exceptions


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
    target_page: pywikibot.FilePage = pywikibot.FilePage(target_site, title)

    source_page = get_final_redirect_target(source_page)
    if source_page is None:
        logging.warning(f"source_page is None. {title=}")
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


def get_final_redirect_target(page: pywikibot.Page):
    """Continuously get redirect target until a non-redirect page encountered."""
    try:
        while page.isRedirectPage():
            page = page.getRedirectTarget()
    except exceptions.CircularRedirectError as e:
        logging.warning(str(e))
    else:
        return page


def transfer(*, source, target):
    """搬运图片。"""
    logging.info(f"{source=}")
    logging.info(f"{target=}")

    # use all pages to include redirect pages
    source_titles = {
        page.title(with_ns=False)
        for page in tqdm(source.allpages(namespace="File"), f"Files on {source}")
    }
    target_titles = {
        page.title(with_ns=False)
        for page in tqdm(target.allpages(namespace="File"), f"Files on {target}")
    }

    for title in tqdm(source_titles - target_titles):
        page = pywikibot.FilePage(source, "File:" + title)

        # 忽略youtube视频
        if (
            hasattr(page.latest_file_info, "mime")
            and page.latest_file_info.mime == "video/youtube"
        ):
            logging.warning(f"youtube视频: {title}")
            continue

        transfer_file(target_site=target, source_site=source, source_page=page)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    transfer(source=pywikibot.Site("en", "re0"), target=pywikibot.Site("zh", "re0"))
