import argparse
import logging
import re

import sentry_sdk

from jobs.jobs_ import CmdJob
from jobs.starts_ import ns2start, ns_more, starts_more

# region sentry
sentry_sdk.init(
    "https://b9865f81742941e1b658462ed983cfe7@o996799.ingest.sentry.io/5975280",
    traces_sample_rate=1.0,
)
sentry_sdk.set_user({"ip_address": "{{auto}}"})
# endregion

# region logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
# endregion

# region parser
parser = argparse.ArgumentParser(description="移动页面 & 替换文本")
parser.add_argument("old")
parser.add_argument("new")


# endregion


def rename(old, new):
    """Move pages and replace text."""
    o_pages = []
    for ns in ns_more + ["file"]:
        pages = (
            CmdJob(["listpages", "-format:3", f"-titleregex:{old}", ns2start(ns)])
            .run(simulate=True, capture_output=True)
            .split("\n")
        )
        for page in pages:
            if page:
                o_pages.append(ns + ":" + page)

    for o_page in o_pages:
        n_page = re.sub(old, new, o_page, flags=re.I)
        CmdJob(
            [
                "movepages",
                "-always",
                f"-from:{o_page}",
                f"-to:{n_page}",
            ]
        ).run()

    CmdJob(
        [
            "replace",
            "-automaticsummary",
            "-always",
            "-nocase",
            "-regex",
            r"-exceptinside:\[\[:?(zh|de|en|es|fr|it|nl|pl|pt-br|ru|uk|wp|wikipedia)\s?:[^\]]*\]\]",
            old,
            new,
        ]
        + starts_more
    ).run()


if __name__ == "__main__":
    args = parser.parse_args()
    rename(args.old, args.new)
