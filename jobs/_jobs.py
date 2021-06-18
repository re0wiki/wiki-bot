import logging
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from importlib import import_module
from pathlib import Path
from shlex import join
from subprocess import run
from time import sleep


class Job(ABC):
    @abstractmethod
    def run(self, simulate: bool):
        pass


class CmdJob(Job):
    def __init__(self, cmd: list[str]):
        # noinspection SpellCheckingInspection
        self.cmd = ['python', 'pywikibot/pwb.py'
                    ] + cmd + ['-titleregexnot:"no bot/"']

    def run(self, simulate):
        cmd = self.cmd
        if simulate:
            cmd.append('-simulate')
        logging.info(join(cmd))
        run(cmd)
        sleep(1)

    def __str__(self):
        return join(self.cmd)


class FuncJob(Job):
    def __init__(self, func: Callable[[], Job]):
        self.func = func

    def run(self, simulate):
        self.func().run(simulate)


class IterableJob(Job):
    def __init__(self, iterable: Iterable[Job]):
        self.iterable = iterable

    def run(self, simulate):
        for j in self.iterable:
            j.run(simulate)


jobs: list[Job] = list()


def add_job(job: Job):
    jobs.append(job)


def load_jobs():
    """遍历初始化所有子模块/子包，'_'开头的除外"""
    for j in Path('jobs').iterdir():
        if not j.name.startswith('_'):
            import_module('jobs.' + j.stem)


def get_jobs():
    return jobs
