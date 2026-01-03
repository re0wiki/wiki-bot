from .jobs_ import Job, add_job
from .starts_ import starts_base

add_job(
    Job(
        [
            "cosmetic_changes",
            "-always",
            "-async",
            "-ignore:method",
        ]
        + starts_base
    )
)
