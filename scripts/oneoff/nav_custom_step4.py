"""nav Custom- 迁移 阶段0-4：为缺 key 标签生成英文拟名，并在 en 站验证页面存在性。

产出 .cache/nav_custom/key_proposals.json（含 en 验证结果）。
"""

import json
from pathlib import Path

from pywikibot.data import api

import pywikibot

OUT = Path(".cache/nav_custom")
m = json.loads((OUT / "map.json").read_text(encoding="utf-8"))

# label -> 拟名（None = 无把握，留空给用户）
PROPOSALS = {
    # 年份
    **{f"{y}年": str(y) for y in range(2014, 2025)},
    # 书店（特典SS 分区）
    "a店": "Animate",
    **{
        f"t店 {r}": f"Toranoana {r}"
        for r in ("2014-2016", "2017-2019", "2020-2024", "2025-")
    },
    **{
        f"g店 {r}": f"Gamers {r}"
        for r in ("2014-2018", "2019-2021", "2022-2024", "2025-")
    },
    **{
        f"m店 {r}": f"Melonbooks {r}"
        for r in ("2014-2015", "2016-2018", "2019-2021", "2022-2024", "2025-")
    },
    # 卷数（多目标共享）
    **{f"第{n}卷": f"Volume {n}" for n in range(1, 15)},
    # 已有 Custom- 裸标签
    "Custom-メイド&執事": "Maid & Butler",
    "Custom-大罪司教": "Sin Archbishops",
    "Custom-魔女教徒": "Witch Cultists",
    "Custom-ウォルフ": "Wolf",
    "Custom-シオン(Lost in Memories)": "Shion (Lost in Memories)",
    "Custom-ヘレナ·カルステン": "Helena Karsten",
    # 势力/组织节标题
    "官方势力": "Official Factions",
    "民间势力": "Civilian Factions",
    "其他势力": "Other Factions",
    "王选阵营": "Royal Selection Camps",
    "家族": "Families",
    "暗杀组织": None,  # 另有同名术语标签，见下
    "神龍教會": None,  # en 用名待验
    "史泰德勢力": "Stride's Faction",
    "屍兵": None,
    "欧米伽旅行團": None,
    "摯愛之子": None,
    "六枚舌": None,
    # 家族
    "菜月家": None,
    "梅札斯家": None,
    "米洛德家": None,
    "卡尔斯腾家": None,
    "阿盖尔家": None,
    "跋利耶尔家": None,
    "阿斯特雷亚家": None,
    "尤克歷烏斯家": None,
    "蘇文家": None,
    "里施家": None,
    "湯普森家": None,
    "費瑟蘭家": None,
    # 地域
    "卢克尼卡王国": "Kingdom of Lugunica",
    "佛拉基亚帝国": "Vollachia Empire",
    "佛拉基亞皇室": None,
    "卡拉拉基城邦": "Kararagi City-States",
    "艾利歐爾大森林": "Elior Forest",
    "鬼村": None,
    "王都": None,
    "水門都市": "Water Gate City",
    "聘可塔特": "Pictat",
    "弗兰德斯": "Flanders",
    "柯司兹尔&吉內布": None,
    "梅札斯領地": "Mathers Domain",
    "跋利耶爾領地": "Barielle Domain",
    "阿斯特雷亞領地": "Astrea Domain",
    "希爾芙亞": None,
    "靈布斯": None,
    "歐爾克斯领": None,
    "萊亞諾特": None,
    "魔都": None,
    "剑奴": None,
    "修德拉格之民": None,
    # 群体/传说
    "傳說": "Legends",
    "三英傑": None,
    "其餘傳說": "Other Legends",
    "四大精靈": "Four Great Spirits",
    "三大魔獸": None,
    "衍生游戏·IF线": "Spin-off Games & IF Routes",
    "IF线": "IF Routes",
    "其他(未分類)": "Others (Uncategorized)",
    "其他": "Others",
    # 职业/阶层
    "王國文官": "Kingdom Civil Officials",
    "贤人会": None,
    "近衛騎士團": "Royal Guard",
    "地方领主·贵族": "Lords & Nobles",
    "商人": "Merchants",
    "其餘将领": "Other Generals",
    "士兵": "Soldiers",
    "城市官員": "City Officials",
    "帝国官員": "Imperial Officials",
    "帝国貴族": "Imperial Nobles",
    "帝国九神将": "Nine Divine Generals",
    "皇族子嗣": "Imperial Offspring",
    "王族": "Royal Family",
    "貴族": "Nobles",
    "神殿騎士": "Temple Knights",
    "傳教士": "Missionaries",
    "平民": "Civilians",
    # 术语区（无 en 链接的术语目标）
    "亚人": None,
    "人工精灵": None,
    "伽那库斯": None,
    "时刻": None,
    "贤人": "Sages",
    "文字": "Writing",
    "魔女": "Witches",
    "魔女因子": "Witch Factors",
    # 设定区节标题
    "群体·种族": "Groups & Races",
    "超自然力量": "Supernatural Powers",
    "战役": "Battles",
    "事件": "Events",
    "其他设定": "Other Lore",
    # 作品区
    "文库正传": "Light Novel Main Story",
    "文库外传": "Light Novel Side Stories",
    "短篇集": "Tanpenshuu",
    "特典SS": "Bonus SS",
    "特典SS一覽": "Bonus SS List",
    "月刊CA短篇": "Monthly CA Short Stories",
    "月刊CA短篇一覽": "Monthly CA Short Stories List",
    "动画特典": "Anime Bonus",
    "漫画特典": "Manga Bonus",
    "爱蜜莉雅生日特典": "Emilia Birthday Bonus",
    "拉姆&雷姆生日特典": "Ram & Rem Birthday Bonus",
    "S4 全卷 Re:從零開始溺水的異世界生活": None,
    "动画": "Anime",
    "动画第一季": "Anime Season 1",
    "动画第二季": "Anime Season 2",
    "动画第三季": "Anime Season 3",
    "动画第四季": "Anime Season 4",
    "漫画": "Manga",
    "APP连载漫画": "APP Manga",
    "单行本漫画": "Tankobon Manga",
    "杂志版漫画": "Magazine Manga",
    "游戏": "Games",
    "音乐": "Music",
    "专辑": "Albums",
    "圆盘": "Discs",
    "设定集、画集": "Artbooks",
    "嘟哇哇 戀愛年齡差": None,
    "鼠色猫语录": None,
    # Wiki 站务
    "Wiki指引·站务": "Wiki Guides & Administration",
    "指引": "Guides",
    "入站指引": "Newcomer Guide",
    "攻略指南": "Walkthrough Guide",
    "译名表": "Translation Table",
    "常见问题及解决方法": "FAQ",
    "组织条目": "Organizations",
    "导航": "Navigation",
    "所有頁面": "All Pages",
    "模板索引": "Template Index",
    "简繁转换表": "Conversion Table",
    "新搬运待整理": "Newly Transferred",
    "功能": "Features",
    "最近更改": "Recent Changes",
    "高级文件检索": "Advanced File Search",
    "小工具": "Gadgets",
    "沙盒": "Sandbox",
    "个人沙盒": "Personal Sandbox",
    "帮助中心": "Help",
    "贴吧精品区": "Tieba Highlights",
    "资源汇总": "Resource Collection",
}

missing = {k for k, v in m.items() if not v["key_en"]}
not_proposed = missing - set(PROPOSALS)
extra = set(PROPOSALS) - missing
print(
    "缺 key:",
    len(missing),
    "| 已拟名:",
    len(missing & set(PROPOSALS)),
    "| 未拟:",
    len(not_proposed),
)
for k in sorted(not_proposed):
    print("  未拟:", k)
if extra:
    print("拟名表多余项:", sorted(extra))

# 在 en 站验证非 None 拟名（作为页面/重定向目标存在即为可信信号）
en = pywikibot.Site("en", "re0")
props = sorted({v for v in PROPOSALS.values() if v})
exists = {}
for i in range(0, len(props), 50):
    batch = props[i : i + 50]
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

result = {}
for label, key in PROPOSALS.items():
    result[label] = {"key": key, "en_page_exists": exists.get(key) if key else None}

ok = sum(1 for v in result.values() if v["en_page_exists"])
noen = [k for k, v in result.items() if v["key"] and not v["en_page_exists"]]
print(f"en 站有对应页: {ok} | 无对应页（结构性标签属预期）: {len(noen)}")
for k in noen:
    print("  无 en 页:", k, "->", result[k]["key"])

(OUT / "key_proposals.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8"
)
print("saved", OUT / "key_proposals.json")
