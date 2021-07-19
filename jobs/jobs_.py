import logging
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from importlib import import_module
from pathlib import Path
from subprocess import run
from time import sleep


class Job(ABC):
    @abstractmethod
    def run(self, simulate: bool):
        pass


class CmdJob(Job):
    def __init__(self, cmd: list[str], skip_no_bot=True):
        cmd = ["python", "pywikibot/pwb.py"] + cmd
        if skip_no_bot:
            cmd.append("-titleregexnot:no bot/")

        self.cmd = " ".join('"' + c.replace('"', r"\"") + '"' for c in cmd)

    def run(self, simulate=False, capture_output=False):
        cmd = self.cmd
        if simulate:
            cmd += " -simulate"

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
        finally:
            logging.info(cmd)
            logging.info("=" * 16 + "end" + "=" * 16)

        return res.stdout

    def __str__(self):
        return self.cmd


class FuncJob(Job):
    def __init__(self, func: Callable[[], Job]):
        self.func = func

    def run(self, simulate):
        self.func().run(simulate)

    def __str__(self):
        return self.func.__name__


class IterableJob(Job):
    def __init__(self, iterable: Iterable[Job]):
        self.iterable = iterable

    def run(self, simulate):
        for j in self.iterable:
            try:
                j.run(simulate)
            except KeyboardInterrupt:
                logging.info("KeyboardInterrupt: 3s后自动进行下一项任务，3s内按 Ctrl+C 以退出。")
                sleep(3)


class Jobs:
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
