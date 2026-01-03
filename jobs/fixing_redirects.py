from .jobs_ import Job, add_job
from .starts_ import starts_more

add_job(
    Job(
        [
            "fixing_redirects",
            "-always",
        ]
        + starts_more
    )
)
