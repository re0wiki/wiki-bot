from .jobs_ import CmdJob, add_job

base = ["redirect", "-always", "-randomredirect", "-limit:128"]

add_job(CmdJob(base + ["do"]))
add_job(CmdJob(base + ["br"]))
