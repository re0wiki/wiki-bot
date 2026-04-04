import argparse
import logging

from jobs.run_job import run_job
from jobs.starts import ns2start, ns_base, starts_more

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def rename(old, new):
    """Move pages and replace text."""
    o_pages: list[str] = []
    for ns in ns_base + ["file"]:
        pages = run_job(
            ["listpages", "-format:3", f"-titleregex:{old}", ns2start(ns)],
            simulate=True,
            capture_output=True,
        )
        if not pages:
            continue
        for page in pages.split("\n"):
            if page:
                o_pages.append(ns + ":" + page)

    move_cmd = ["python", "pywikibot/pwb.py", "movepages"]
    for o_page in o_pages:
        n_page = o_page.replace(old, new)
        move_cmd += [f"-from:'{o_page}'", f"-to:'{n_page}'"]
    print(" ".join(move_cmd))

    replace_cmd = [
        "python",
        "pywikibot/pwb.py",
        "replace",
        "-automaticsummary",
        r"-exceptinside:'\[\[:?(zh|de|en|es|fr|it|nl|pl|pt-br|ru|uk|wp|wikipedia)\s?:[^\]]*\]\]'",
        *starts_more,
        f"'{old}'",
        f"'{new}'",
    ]
    print(" ".join(replace_cmd))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="移动页面 & 替换文本")
    parser.add_argument("old")
    parser.add_argument("new")

    args = parser.parse_args()
    rename(args.old, args.new)
