import logging
import mimetypes
import pathlib
from os import path
from pprint import pformat
from tempfile import TemporaryDirectory

import pywikibot
from pywikibot import exceptions


def get_stem(filename: str):
    """Return the stem of a filename."""
    return pathlib.Path(filename).stem


def get_ext(filename: str):
    """Return the extension of a filename."""
    return pathlib.Path(filename).suffix


def upload_file(target: pywikibot.Site, source: pywikibot.FilePage, summary, text):
    """File uploading behavior. See **pywikibot.page.FilePage** for more details.

    :param target: target site
    :param source: path or url of the image to be uploaded
    :param summary: Summary object which records some statistics while running
    :param text: Initial page text
    """
    # 生成你站文件名。注意有时候英文站的标题为xxx.jpg的图可能实际是个png图 所以优先使用mime来推断类型
    if hasattr(source.latest_file_info, "mime"):
        ext = mimetypes.guess_extension(source.latest_file_info.mime)
    else:
        source_file_name = source.title(as_filename=True, with_ns=False)
        ext = get_ext(source_file_name)
    stem = get_stem(source.title(as_filename=True, with_ns=False))
    target: pywikibot.FilePage = pywikibot.FilePage(target, stem + ext)

    # 真正的上传
    logging.info(f"UPLOAD file to page '{target.title()}' with '{source}'\n")
    logging.debug("saving page:\n" + target.title() + text)
    with TemporaryDirectory() as tmp_dir:
        filename = path.join(tmp_dir, target.title(as_filename=True, with_ns=False))
        source.download(filename)
        target.upload(filename, comment=text, text=text)
    summary["uploaded"] += 1


def get_final_redirect_target(page: pywikibot.Page):
    """Continuously get redirect target until a non-redirect page encountered."""
    try:
        while page.isRedirectPage():
            page = page.getRedirectTarget()
    except exceptions.CircularRedirectError as e:
        logging.warning(str(e))
    else:
        return page


def main():
    """搬运图片。"""
    source = pywikibot.Site("en", "re0")
    target = pywikibot.Site("zh", "re0")
    target.login()
    if target.logged_in():
        logging.info(f"Logged in to {target}")

    summary = {
        "scanned_files": 0,
        "uploaded": 0,
        "skipped": 0,
        "matched files": [],
    }

    logging.info(f"Generating image list for all images on {source} ...")
    images_source = list(source.allimages())

    # 这一部分就是把你站有的图片都存到两个dict里面 一个把sha1 map到FilePage对象 一个把不带后缀的文件名map到FilePage对象 后面会用到
    logging.info(f"Generating the set for all images on {target} ...")
    images_target_sha1 = {}
    images_target_stem = {}
    for fp in target.allpages(
        namespace="File"
    ):  # use all pages to include redirect pages
        fp: pywikibot.Page
        images_target_stem[get_stem(fp.title(with_ns=False)).replace(" ", "_")] = fp
        if fp.isRedirectPage():
            final_target = get_final_redirect_target(fp)
            if not isinstance(final_target, pywikibot.FilePage):
                logging.warning(
                    f"Found a pages in File name which redirect "
                    f"to a non-file page: '{fp.create_short_link()}'"
                )
                continue
        elif isinstance(fp, pywikibot.FilePage):
            try:
                images_target_sha1[fp.latest_file_info.sha1] = fp
            except exceptions.PageRelatedError as e:
                logging.warning(str(e))
        else:
            logging.warning(
                f"Found a non-file page in File name space: '{fp.create_short_link()}'"
            )
            continue

    # 这边就是en上的一张一张图片循环过去
    summary["scanned_files"] = len(images_source)
    for i, im_source in enumerate(images_source):
        if i % 100 == 0:
            logging.info(f"Scanned files: {i} / {summary['scanned_files']}")

        # 如果当前的FilePage是重定向 那就找到它最终的目标再进行下面的操作
        im_source = get_final_redirect_target(im_source)
        if im_source is None:
            summary["skipped"] += 1
            continue

        same_sh1 = im_source.latest_file_info.sha1 in images_target_sha1
        same_name = (
            get_stem(im_source.title(with_ns=False)).replace(" ", "_")
            in images_target_stem
        )

        # 如果当前的FilePage的sha1和文件名都没有和你站图片匹配的 那就进行更新操作
        if not same_sh1 and not same_name:
            im_source = pywikibot.FilePage(source, im_source.title())

            # 忽略youtube视频
            if (
                hasattr(im_source.latest_file_info, "mime")
                and im_source.latest_file_info.mime == "video/youtube"
            ):
                summary["skipped"] += 1
                continue

            text = "\n".join([x.astext() for x in im_source.iterlanglinks()])
            if text != "":
                text += "\n"
            text += f"[[{source.code}:{im_source.title(with_ns=True)}]]"
            upload_file(target, im_source, summary, text=text)

        # 如果它和你站图片有match到 那就往最后的report/summary中加入对应的条目
        else:
            if same_sh1:
                im_target = images_target_sha1[im_source.latest_file_info.sha1]
            else:
                im_target = images_target_stem[
                    get_stem(im_source.title(with_ns=False)).replace(" ", "_")
                ]
            summary["matched files"].append(
                {
                    "match_sha1": same_sh1,
                    "match_name": same_name,
                    f"{source}_title": im_source.title(),
                    f"{source}_url": im_source.full_url(),
                    f"{target}_title": im_target.title(),
                    f"{target}_url": im_target.full_url(),
                }
            )
            summary["skipped"] += 1

    logging.info(pformat(summary))
    return summary


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    main()
