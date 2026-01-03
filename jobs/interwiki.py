from .jobs_ import Job, add_job
from .starts_ import starts_more

add_job(
    Job(
        [
            "interwiki",
            "-quiet",
            "-async",
            "-auto",
            "-force",
            "-localonly",
        ]
        + starts_more
    )
)
