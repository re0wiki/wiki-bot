from .jobs_ import CmdJob, add_job
from .starts_ import starts_base

add_job(
    CmdJob([
        "cosmetic_changes",
        "-always",
        "-async",
        "-ignore:method",
    ] + starts_base))
