"""修复 Module:Kana2Romaji：双字片假名外来音（ウィ/ウェ/ウォ/トゥ/ドゥ）从单音拍表挪到双字音拍表。

单音拍查找只按单字符进行，双字符键不可达，导致 ウェ 拆成 ウ(u)+ェ(漏)。
"""

import pywikibot

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

page = pywikibot.Page(site, "Module:Kana2Romaji")
text = page.text

# 1) MONO_LIST：双字片假名条目下线，ゐ/ゑ 保留（单字符平假名仍走单音拍表）
old_mono = """	{ 'vu', 'ゔ', 'ヴ' },
	{ 'wi', 'ゐ', 'ウィ' }, { 'we', 'ゑ', 'ウェ' }, { 'wo', nil, 'ウォ' },
	{ 'tu', nil, 'トゥ' }, { 'du', nil, 'ドゥ' },
"""
new_mono = """	{ 'vu', 'ゔ', 'ヴ' },
	{ 'wi', 'ゐ', nil }, { 'we', 'ゑ', nil },
"""
assert text.count(old_mono) == 1, "MONO_LIST 锚点不唯一"
text = text.replace(old_mono, new_mono)

# 2) DI_LIST：补入五条双字片假名外来音
old_di = "\t{ 'va', nil, 'ヴァ' },"
new_di = """	{ 'wi', nil, 'ウィ' }, { 'we', nil, 'ウェ' }, { 'wo', nil, 'ウォ' },
	{ 'tu', nil, 'トゥ' }, { 'du', nil, 'ドゥ' },
	{ 'va', nil, 'ヴァ' },"""
assert text.count(old_di) == 1, "DI_LIST 锚点不唯一"
text = text.replace(old_di, new_di)

page.text = text
page.save(
    summary="fix: ウィ/ウェ/ウォ/トゥ/ドゥ 挪入双字音拍表（单音拍表按单字符查找，双字键不可达，ウェ 漏成 uェ）",
    bot=False,
)
print("saved:", page.full_url())
