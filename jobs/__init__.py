from itertools import cycle

from jobs.jobs_ import IterableJob, Job, get_jobs, load_jobs

load_jobs()
jobs = get_jobs()


def run(start: int, simulate: bool):
    global jobs
    jobs = cycle(jobs)
    for _ in range(start):
        next(jobs)
    IterableJob(jobs).run(simulate=simulate)
