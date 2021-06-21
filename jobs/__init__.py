from itertools import cycle

from jobs.jobs_ import IterableJob, Job, jobs

jobs.load()


def run(start: int, simulate: bool):
    j = cycle(jobs.jobs_)
    for _ in range(start):
        next(j)
    IterableJob(j).run(simulate=simulate)
