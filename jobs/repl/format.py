from .base import base
from .._jobs import CmdJob, add_job
from .._starts import starts_more

nbsp = '\xa0'

mid_dots_code = [
    721, 903, 1468, 5867, 8226, 8231, 8728, 8729, 8901, 9210, 9679, 9702, 9899,
    10625, 11824, 11825, 11827, 12539, 42895, 65381, 65793
]
mid_dots = '[' + ''.join(chr(i) for i in mid_dots_code) + ']'
mid_dot = '\xb7'

pairs = [
    (nbsp, ' '),
    (mid_dots, mid_dot),
    ('－－', '——'),
    ('<br */?>', '<br>'),
    (r'<!---->|￼', ''),
    ('“', '「'),
    ('”', '」'),
    ('【', '『'),
    ('】', '』'),
    (r'(?<!==)\s*\n==', r'\n\n=='),
    (r'==\n\s*', r'==\n'),
    (r'\n{3,}', r'\n\n'),
    ('stickytable', 'floatheader'),
]

repl = base.copy()

for o, n in pairs:
    repl += [o, n]

add_job(CmdJob(repl + starts_more))
