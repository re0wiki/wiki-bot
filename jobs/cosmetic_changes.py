from ._jobs import CmdJob, add_job
from ._starts import starts_base

add_job(
    CmdJob([
        'cosmetic_changes',
        '-always',
        '-async',
        '-ignore:method',
    ] + starts_base))
