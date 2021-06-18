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
    def __init__(self, cmd: list[str]):
        # noinspection SpellCheckingInspection
        cmd = ['python', 'pywikibot/pwb.py'
               ] + cmd + ['-titleregexnot:"no bot/"']
        self.cmd = ' '.join('"' + c + '"' if ' ' in c and '"' not in c else c
                            for c in cmd)

    def run(self, simulate, capture_output=False):
        cmd = self.cmd
        if simulate:
            cmd += ' -simulate'
        logging.info(cmd)
        return run(cmd, capture_output=capture_output, encoding='utf8').stdout

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
            j.run(simulate)
            sleep(1)


jobs: list[Job] = list()


def add_job(job: Job):
    jobs.append(job)


def load_jobs():
    """遍历初始化所有子模块/子包，以'_'开头或结尾的除外"""
    for j in Path('jobs').iterdir():
        if not j.name.startswith('_') and not j.name.endswith('_'):
            import_module('jobs.' + j.stem)


def get_jobs():
    return jobs
