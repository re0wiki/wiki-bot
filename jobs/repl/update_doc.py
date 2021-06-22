from .base import base
from ..jobs_ import CmdJob, FuncJob, add_job, jobs


def update_doc():
    return CmdJob(
        base
        + [
            "-dotall",
            r"(?<=<pre>\n).*(?=\n</pre>)",
            jobs.info,
            "-page:No bot/jobs",
        ],
        skip_no_bot=False,
    )


add_job(FuncJob(update_doc))
