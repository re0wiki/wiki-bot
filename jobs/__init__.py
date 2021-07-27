from jobs.jobs_ import IterableJob, Job, jobs

jobs.load()


def run(index: int, simulate: bool):
    j = jobs.jobs_
    if index == 231:
        IterableJob(j).run(simulate=simulate)
    else:
        j[index].run(simulate=simulate)
