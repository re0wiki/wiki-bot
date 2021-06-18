from .jobs_ import CmdJob, add_job
from .starts_ import starts_more

add_job(CmdJob([
    'noreferences',
    '-always',
    '-quiet',
] + starts_more))
