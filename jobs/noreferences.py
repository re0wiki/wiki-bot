from ._jobs import CmdJob, add_job
from ._starts import starts_more

add_job(CmdJob([
    'noreferences',
    '-always',
    '-quiet',
] + starts_more))
