import logging
import os
import sys
from subprocess import run

logger = logging.getLogger(__name__)

# 强制子进程 stdio 用 UTF-8：比 mbcs（系统 ANSI 代码页，仅在 zh-CN 机器上
# 恰好是 GBK）确定，不依赖区域设置。capture_output=False（循环模式）时子进程
# 继承控制台，走 WriteConsoleW 宽字符 API，不受此变量影响，显示行为不变。
CHILD_ENV = os.environ | {"PYTHONIOENCODING": "utf-8"}


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
    else:
        cmd.append("-always")
    return cmd


def run_job(job: list[str], simulate=False, capture_output=False) -> str | None:
    """跑一个任务。

    子进程非零退出时抛 CalledProcessError——不吞失败。吞掉的后果是循环模式
    在 wiki 故障/凭据过期时以子进程启动速度空转锤站（叠加 429 惩罚）；
    直接炸出来让人工介入修复。
    """
    cmd = build_cmd(job, simulate)

    # Run the job.
    # 不用 shell=True：它曾是裸 "python" 时代解释器解析错误的 workaround
    # （2026-01 ade2716），sys.executable 绝对路径后动机已消；去掉可消除
    # cmd.exe 二次解析引号的隐患。
    logger.info("=" * 16 + "start" + "=" * 16)
    logger.info(cmd)
    try:
        res = run(
            cmd,
            capture_output=capture_output,
            env=CHILD_ENV,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
    finally:
        logger.info(cmd)
        logger.info("=" * 16 + "end" + "=" * 16)
    return res.stdout
