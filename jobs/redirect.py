from .jobs_ import CmdJob, add_job

base = ["redirect", "-always", "-randomredirect:128"]

add_job(CmdJob(base + ["do"]))
add_job(CmdJob(base + ["br", "delete"]))
