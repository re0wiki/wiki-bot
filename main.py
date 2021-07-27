import argparse
import logging
from contextlib import suppress

from jobs import jobs, run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

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

if __name__ == "__main__":
    args = parser.parse_args()
    with suppress(KeyboardInterrupt):
        run(index=args.index, simulate=args.simulate)
