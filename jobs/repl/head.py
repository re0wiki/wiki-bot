from .base import base
from .._jobs import CmdJob, add_job
from .._starts import starts_more

pairs = [
    ('Information', '简介'),
    ('Summary', '简介'),
    ('Relationships', '关系'),
    ('Synopsis', '梗概'),
    ('Gallery', '图库'),
    ('Image Gallery', '图库'),
    ('Appearance', '外貌'),
    ('Personality', '性格'),
    ('Abilities', '能力'),
    ('Trivia', '你知道吗'),
    ('Lyrics?', '歌词'),
]

repl = base.copy()

for o, n in pairs:
    repl += ['(?<== )' + o + '(?= =)', n]

add_job(CmdJob(repl + starts_more))
