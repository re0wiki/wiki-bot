from importlib import import_module
from itertools import cycle
from pathlib import Path

jobs = list()


def add_job(job):
    jobs.append(job)


def load_jobs():
    """遍历初始化所有子模块/子包，'_'开头的除外"""
    for j in Path('jobs').iterdir():
        if not j.name.startswith('_'):
            import_module('jobs.' + j.stem)


def get_jobs():
    return cycle(jobs)
