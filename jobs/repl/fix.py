from ..jobs_ import CmdJob, add_job
from ..starts_ import starts_base

add_job(
    CmdJob(
        [
            "replace",
            "-automaticsummary",
            "-always",
            "-nocase",
            "-fix:HTML",
        ]
        + starts_base
    )
)
