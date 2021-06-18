from .base import base
from ..jobs_ import CmdJob, add_job

# noinspection SpellCheckingInspection
pairs = [
    ('Anime', '动画'),
    ('Season 1', '第一季'),
    ('Season 2', '第二季'),
    ('Light Novel', '小说'),
    ('Main Series', '正传'),
    ('Tanpenshuu', '月刊CA短篇'),
    ('Side Content', '特典SS'),
    ('Side Stories', '特典SS'),
    ('Manga', '漫画'),
    ('Daisshou', '第1章'),
    ('Dainishou', '第2章'),
    ('Daisanshou', '第3章'),
    ('Daiyonshou', '第4章'),
    ('Anthology', '官方同人精选集'),
    ('Games', '游戏'),
    ('Death or Kiss', '死或吻'),
    ('-Infinity', 'INFINITY'),
    ('The Prophecy of the Throne', '虚假的王选候补'),
    (r'Misc\.?', '其他'),
]

repl = base + ['-catr:图库']

for o, n in pairs:
    repl += [o + '(?==)', n]

add_job(CmdJob(repl))
