from .jobs_ import CmdJob, add_job
from .starts_ import starts_base

add_job(
    CmdJob(
        [
            "noreferences",
            "-always",
            "-quiet",
        ]
        + starts_base
    )
)
