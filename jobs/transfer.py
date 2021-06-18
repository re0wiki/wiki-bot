from ._jobs import CmdJob, add_job

add_job(CmdJob([
    'transferbot',
    '-lang:en',
    '-tolang:zh',
    '-start',
]))
