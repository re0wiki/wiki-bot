import argparse
import logging

from jobs.jobs_ import CmdJob
from jobs.repl.base import base
from jobs.starts_ import ns2start, ns_more, starts_more

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(description="移动页面 & 替换文本")
    parser.add_argument("old")
    parser.add_argument("new")
    args = parser.parse_args()

    old, new = args.old, args.new

    o_pages = []

    cmd = [
        "listpages",
        "-format:3",
        f"-titleregex:{old}",
    ]

    for ns in ns_more:
        pages = (
            CmdJob(cmd + [ns2start(ns)])
            .run(simulate=True, capture_output=True)
            .split("\n")
        )
        for page in pages:
            if page:
                o_pages.append(ns + ":" + page)

    for o_page in o_pages:
        n_page = o_page.replace(old, new)
        CmdJob(
            [
                "movepages",
                "-always",
                f"-from:{o_page}",
                f"-to:{n_page}",
            ]
        ).run()

    CmdJob(base + [old, new] + starts_more).run()
