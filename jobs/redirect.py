from ._helper import CmdJob, add_job

base = [
    'redirect',
    'do',
    '-always',
]

add_job(CmdJob(base + [
    '-moves',
    '-limit:128',
]))
add_job(CmdJob(base + [
    '-recentchanges:128',
]))
