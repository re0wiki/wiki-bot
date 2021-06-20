from .jobs_ import CmdJob, add_job
from .starts_ import starts_more

add_job(
    CmdJob(
        [
            "fixing_redirects",
        ]
        + starts_more
    )
)
