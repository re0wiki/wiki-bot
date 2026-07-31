import argparse
import itertools
import logging
import sys
from subprocess import CalledProcessError

from jobs.jobs import jobs
from jobs.run_job import run_job

# region logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
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
    except CalledProcessError as e:
        # 任务失败不继续：退出等待人工修复，避免 231 循环故障期空转锤站
        logger.error("任务失败（exit %s），退出等待人工修复: %s", e.returncode, e.cmd)
        sys.exit(e.returncode or 1)
    except KeyboardInterrupt:
        sys.exit(130)
