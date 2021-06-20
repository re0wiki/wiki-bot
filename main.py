import argparse
import logging

from jobs import jobs, run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

parser = argparse.ArgumentParser(
    description="将自动化规则应用到全站条目，循环执行。",
    epilog=jobs.info,
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument(
    "start",
    help="从第几个任务开始执行 (default: 0)",
    type=int,
    nargs="?",
    default=0,
    choices=range(jobs.num),
)
parser.add_argument(
    "-s",
    "--simulate",
    help="不对服务器内容做任何实际更改，只显示将更改的内容 (default: False)",
    action="store_true",
)

if __name__ == "__main__":
    args = parser.parse_args()
    run(start=args.start, simulate=args.simulate)
