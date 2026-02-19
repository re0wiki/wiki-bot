import argparse
import itertools
import logging
import sys

from jobs.jobs import jobs
from jobs.run_job import run_job

# region logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
# endregion


# region parser
def gen_help(job: list[str]) -> str:
    return f"python pywikibot/pwb.py {' '.join(f'"{s}"' for s in job)}"


parser = argparse.ArgumentParser(
    description="执行自动化规则。",
    epilog="\n\n".join(f"{i}\n{gen_help(job)}" for i, job in enumerate(jobs)),
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument(
    "index",
    help="任务编号，231代表循环所有任务",
    type=int,
    choices=list(range(len(jobs))) + [231],
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
        if args.index == 231:
            for job in itertools.cycle(jobs):
                run_job(job, args.simulate)
        else:
            run_job(jobs[args.index], args.simulate)
    except KeyboardInterrupt:
        sys.exit(130)
