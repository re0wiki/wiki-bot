from ._jobs import CmdJob, add_job
from ._starts import starts_more

add_job(CmdJob([
    'fixing_redirects',
] + starts_more))
