import logging
import sys
from subprocess import run

logger = logging.getLogger(__name__)


def build_cmd(job: list[str], simulate: bool = False) -> list[str]:
    """拼 pwb.py 命令行。

    解释器用 sys.executable 而非裸 "python"：后者从 PATH 解析，在 venv 未
    激活的 shell 里可能是没有项目依赖（opencc 等）的其他 Python 版本。
    """
    cmd = [sys.executable, "pywikibot/pwb.py", *job]
    if simulate:
        cmd.append("-simulate")
    elif job[0] == "interwiki":
        cmd.append("-auto")
        cmd.append("-force")
    elif job[0] != "transferbot":
        cmd.append("-always")
    return cmd


def run_job(job: list[str], simulate=False, capture_output=False) -> str | None:
    """跑一个任务。

    子进程非零退出时抛 CalledProcessError——不吞失败。吞掉的后果是 231 循环
    在 wiki 故障/凭据过期时以子进程启动速度空转锤站（叠加 429 惩罚）；
    直接炸出来让人工介入修复。
    """
    cmd = build_cmd(job, simulate)

    # Run the job.
    logger.info("=" * 16 + "start" + "=" * 16)
    logger.info(cmd)
    try:
        res = run(
            cmd,
            capture_output=capture_output,
            encoding="mbcs",
            shell=True,
            check=True,
        )
    finally:
        logger.info(cmd)
        logger.info("=" * 16 + "end" + "=" * 16)
    return res.stdout
