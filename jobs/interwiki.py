from ._jobs import CmdJob, add_job
from ._starts import starts_more

add_job(
    CmdJob([
        'interwiki',
        '-quiet',
        '-async',
        '-auto',
        '-force',
        '-localonly',
    ] + starts_more))
