import logging
from importlib import import_module
from pathlib import Path
from subprocess import CalledProcessError, run


class Job:
    """执行一条命令行指令的任务。"""

    def __init__(self, cmd: list[str]):
        cmd = ["python", "pywikibot/pwb.py"] + cmd
        self.cmd = " ".join('"' + c.replace('"', r"\"") + '"' for c in cmd)

    def run(self, simulate=False, capture_output=False):
        cmd = self.cmd
        if simulate:
            cmd += " -simulate"
            cmd = cmd.replace('"-always"', "")

        logging.info("=" * 16 + "start" + "=" * 16)
        logging.info(cmd)
        try:
            res = run(
                cmd,
                capture_output=capture_output,
                encoding="utf8",
                shell=True,
                check=True,
            )
        except CalledProcessError as e:
            logging.error(e)
            return ""
        finally:
            logging.info(cmd)
            logging.info("=" * 16 + "end" + "=" * 16)

        return res.stdout

    def __str__(self):
        return self.cmd


class Jobs:
    """所有任务的集合，用于单例。"""

    def __init__(self):
        self.jobs_: list[Job] = []

    def add(self, job: Job):
        """由子模块/子包于初始化时调用。"""
        self.jobs_.append(job)

    @staticmethod
    def load():
        """遍历初始化所有子模块/子包，以'_'开头或结尾的除外。"""
        for j in sorted(Path("jobs").iterdir()):
            if not j.name.startswith("_") and not j.name.endswith("_"):
                import_module("jobs." + j.stem)

    @property
    def info(self):
        return "\n\n".join(f"{i}\n{job}" for i, job in enumerate(self.jobs_))

    @property
    def num(self):
        return len(self.jobs_)


# singleton
jobs = Jobs()

# for convenience
add_job = jobs.add
