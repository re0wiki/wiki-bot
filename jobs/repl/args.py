from .base import base
from ..jobs_ import CmdJob, add_job
from ..starts_ import starts_more

pairs = [
    ("Image-Size", "请手动移除该参数"),
    ("Name", "name"),
    ("Image", "image"),
    ("Kanji", "name_ja_kanji"),
    ("Romaji", "name_ja_romaji"),
    ("Alias", "alias"),
    ("Nickname", "nickname"),
    ("Race", "race"),
    ("Gender", "gender"),
    ("Birthday", "birthday"),
    ("Age", "age"),
    ("Hair Color", "hair"),
    ("Eye Color", "eyes"),
    ("Height", "height"),
    ("Weight", "weight"),
    ("Affiliation", "affiliation"),
    ("Previous Affiliation", "previous_affiliation"),
    ("Occupation", "occupation"),
    ("Previous Occupation", "previous_occupation"),
    ("Status", "status"),
    ("Relatives", "relatives"),
    ("Magic", "magic"),
    ("Divine Protection", "divine_protection"),
    ("Authority", "authority"),
    ("Weapon", "weapon"),
    ("Equipment", "equipment"),
    ("Anime", "anime"),
    ("Light Novel", "novel"),
    ("Game", "game"),
    ("Manga", "comic"),
    ("Japanese Voice", "voice_ja"),
    ("English Voice", "voice_en"),
]

repl = base.copy()

for o, n in pairs:
    repl += [rf"\|\s*{o}\s*= *", f"| {n} = "]

add_job(CmdJob(repl + starts_more))
