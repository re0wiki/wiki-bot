import argparse
import itertools
import logging
import sys
from subprocess import CalledProcessError

from jobs.jobs import Job, jobs
from jobs.run_job import run_job

# region logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
# endregion


# region parser
def gen_help(cmd: list[str]) -> str:
    return f"python pywikibot/pwb.py {' '.join(f'"{s}"' for s in cmd)}"


parser = argparse.ArgumentParser(
    description="执行自动化规则。",
    epilog="\n\n".join(
        f"{i} {job.name}\n{gen_help(job.cmd)}" for i, job in enumerate(jobs)
    ),
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument(
    "job",
    help="任务名字或编号，231代表循环所有任务",
)
parser.add_argument(
    "-s",
    "--simulate",
    help="不对服务器内容做任何实际更改，只显示将更改的内容",
    action="store_true",
)
# endregion


def resolve(job_arg: str) -> Job | None:
    """把命令行参数解析为任务。返回 None 表示 231（循环所有任务）。"""
    if job_arg == "231":
        return None
    # 编号会随插入平移，名字才是稳定引用
    if job_arg.isdigit() and 0 <= int(job_arg) < len(jobs):
        return jobs[int(job_arg)]
    for job in jobs:
        if job.name == job_arg:
            return job
    parser.error(f"未知任务: {job_arg}（可用名字见下方任务列表）")


if __name__ == "__main__":
    args = parser.parse_args()
    try:
        if (job := resolve(args.job)) is None:
            for j in itertools.cycle(jobs):
                run_job(j.cmd, args.simulate)
        else:
            run_job(job.cmd, args.simulate)
    except CalledProcessError as e:
        # 任务失败不继续：退出等待人工修复，避免 231 循环故障期空转锤站
        logger.error("任务失败（exit %s），退出等待人工修复: %s", e.returncode, e.cmd)
        sys.exit(e.returncode or 1)
    except KeyboardInterrupt:
        sys.exit(130)
