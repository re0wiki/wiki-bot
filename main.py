import argparse
import logging
import sys

import sentry_sdk

from jobs import jobs, run

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
parser = argparse.ArgumentParser(
    description="执行自动化规则。",
    epilog=jobs.info,
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument(
    "index",
    help="任务编号，231代表所有任务",
    type=int,
    choices=list(range(jobs.num)) + [231],
)
parser.add_argument(
    "-s",
    "--simulate",
    help="不对服务器内容做任何实际更改，只显示将更改的内容",
    action="store_true",
)
# endregion

if __name__ == "__main__":
    args = parser.parse_args()
    try:
        run(index=args.index, simulate=args.simulate)
    except KeyboardInterrupt:
        sys.exit(130)
