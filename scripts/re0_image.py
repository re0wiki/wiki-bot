from os import path
from tempfile import TemporaryDirectory

from tqdm import tqdm

import pywikibot as pwb


def all_images(code: str) -> dict[str, pwb.FilePage]:
    """返回所有图片的从页面名到页面的映射。"""
    site = pwb.Site(code, "re0")
    site.login()
    return {
        image.title(): image
        for image in tqdm(site.allimages(), f"Collecting {code} images")
    }


def calc_diff(
    en_images: dict[str, pwb.FilePage], zh_images: dict[str, pwb.FilePage]
) -> list[pwb.FilePage]:
    """返回 en 的图片中，zh 缺失或过时的部分。"""
    return [
        image
        for title, image in en_images.items()
        if (
            title not in zh_images
            or zh_images[title].latest_file_info.timestamp
            < image.latest_file_info.timestamp
        )
    ]


def download_one(image: pwb.FilePage, tmp_dir: str) -> None:
    """从 en 下载一张图片文件到临时目录。"""
    filename = path.join(tmp_dir, image.title(with_ns=False, as_filename=True))
    try:
        image.download(filename)
    except Exception as e:
        pwb.logging.error(e)


def upload_one(image: pwb.FilePage, tmp_dir: str) -> None:
    """从临时目录上传一张图片文件到 zh。"""
    filename = path.join(tmp_dir, image.title(with_ns=False, as_filename=True))
    title = image.title()
    text = f"[[en:{title}]]"

    try:
        pwb.FilePage(pwb.Site("zh", "re0"), title).upload(
            filename,
            comment=text,
            text=text,
            report_success=False,
            ignore_warnings=True,
        )
    except Exception as e:
        pwb.logging.error(e)


def download_all(images: list[pwb.FilePage], tmp_dir: str):
    """从 en 下载所有图片文件到临时目录。"""
    pwb.Site("en", "re0").login()
    for image in tqdm(images, "Downloading images"):
        download_one(image, tmp_dir)


def upload_all(images: list[pwb.FilePage], tmp_dir: str):
    """从临时目录上传所有图片文件到 zh。"""
    pwb.Site("zh", "re0").login()
    for image in tqdm(images, "Uploading images"):
        upload_one(image, tmp_dir)


def main() -> None:
    en_images = all_images("en")
    zh_images = all_images("zh")
    diff = calc_diff(en_images, zh_images)
    with TemporaryDirectory() as tmp_dir:
        download_all(diff, tmp_dir)
        upload_all(diff, tmp_dir)


if __name__ == "__main__":
    main()
