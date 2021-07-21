from .jobs_ import CmdJob, add_job

add_job(CmdJob(["touch", "-random:128"]))
