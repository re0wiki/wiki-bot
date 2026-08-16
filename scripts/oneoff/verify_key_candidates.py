"""一次性：为拿不准的拟名在 en 站测试多个候选，选有页面/重定向的。"""

from pywikibot.data import api

import pywikibot

CANDIDATES = {
    "聘可塔特": ["Picoutatte", "Pictat"],
    "暗杀组织": ["Assassin Association", "Assassin Organization", "Assassins"],
    "神龍教會": ["Church of the Divine Dragon", "Divine Dragon Church"],
    "屍兵": ["Corpse Soldier", "Corpse Soldiers", "Undead"],
    "欧米伽旅行團": ["Omega Party", "Omega's Party", "Omega Travelling Party"],
    "摯愛之子": ["Beloved Children", "Beloved Child", "The Beloved"],
    "六枚舌": ["Six Tongues", "The Six Tongues"],
    "三英傑": ["Three Heroes", "Three Great Heroes", "Three Heroes of the Dragon"],
    "三大魔獸": [
        "Three Great Mabeasts",
        "Three Great Witchbeasts",
        "Three Great Demon Beasts",
    ],
    "佛拉基亞皇室": [
        "Vollachia Imperial Family",
        "Imperial Family of Vollachia",
        "Vollachia Royalty",
    ],
    "鬼村": ["Oni Village", "Demon Village"],
    "王都": ["Royal Capital", "Lugunica Capital"],
    "柯司兹尔&吉內布": ["Costuul & Guineb", "Koszul & Guineb", "Costuul and Guineb"],
    "希爾芙亚": ["Sylphoa", "Silphia"],
    "希爾芙亞": ["Sylphoa", "Silphia"],
    "靈布斯": ["Lembus", "Rembus", "Limbus"],
    "歐爾克斯领": ["Orcus Domain", "Orcus Territory", "Olcos Domain"],
    "萊亞諾特": ["Leanote", "Laynote", "Leianote"],
    "魔都": ["Demon City", "Mado"],
    "剑奴": ["Sword Slave", "Sword Slaves"],
    "修德拉格之民": ["Shudrak People", "Shudrak", "People of Shudrak"],
    "亚人": ["Demi-Human", "Demi-Humans", "Demihuman"],
    "人工精灵": ["Artificial Spirit", "Artificial Spirits"],
    "伽那库斯": ["Ganacks", "Ganax"],
    "时刻": ["Time", "Timekeeping"],
    "贤人会": [
        "Council of Sages",
        "Sage Council",
        "Wise Men's Council",
        "Council of Wise Men",
    ],
    "菜月家": ["Natsuki Family", "House Natsuki"],
    "梅札斯家": ["House Mathers", "Mathers House", "Mathers Family"],
    "米洛德家": ["House Miload", "Miload House", "Miload Family"],
    "卡尔斯腾家": ["House Karsten", "Karsten House", "Karsten Family"],
    "阿盖尔家": ["House Argyle", "Argyle House", "Argyle Family"],
    "跋利耶尔家": ["House Barielle", "Barielle House", "Barielle Family"],
    "阿斯特雷亚家": ["House Astrea", "Astrea House", "Astrea Family"],
    "尤克歷烏斯家": ["House Juukulius", "Juukulius House", "Juukulius Family"],
    "蘇文家": ["House Suwen", "Suwen House", "Suwen Family"],
    "里施家": ["House Risch", "Risch House", "Risch Family"],
    "湯普森家": ["House Thompson", "Thompson House", "Thompson Family"],
    "費瑟蘭家": [
        "House Feserun",
        "Feserun House",
        "House Fezerrun",
        "Featherland House",
    ],
    "S4 全卷 Re:從零開始溺水的異世界生活": ["Re:Zero Drowning in Another World"],
    "嘟哇哇 戀愛年齡差": [],
    "鼠色猫语录": [],
}

en = pywikibot.Site("en", "re0")
all_titles = sorted({c for cs in CANDIDATES.values() for c in cs})
exists = {}
for i in range(0, len(all_titles), 50):
    batch = all_titles[i : i + 50]
    req = api.Request(
        site=en,
        parameters={"action": "query", "titles": "|".join(batch), "redirects": 1},
    )
    data = req.submit()
    normalized = {n["from"]: n["to"] for n in data["query"].get("normalized", [])}
    redirects = {r["from"]: r["to"] for r in data["query"].get("redirects", [])}
    for page in data["query"]["pages"].values():
        exists[page["title"]] = "missing" not in page
    for src, dst in {**normalized, **redirects}.items():
        exists[src] = exists.get(dst, False)

for label, cs in CANDIDATES.items():
    hits = [c for c in cs if exists.get(c)]
    print(f"{label}: {hits if hits else ('无命中 ' + str(cs) if cs else '待人工')}")
