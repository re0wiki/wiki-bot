from .jobs_ import CmdJob, add_job

add_job(CmdJob(["redirect", "do"]))
add_job(CmdJob(["redirect", "br", "-delete"]))
