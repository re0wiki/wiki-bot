from .jobs_ import CmdJob, add_job
from .starts_ import starts_more

add_job(
    CmdJob([
        "interwiki",
        "-quiet",
        "-async",
        "-auto",
        "-force",
        "-localonly",
    ] + starts_more))
