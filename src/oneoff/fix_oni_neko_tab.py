"""Tab/The Oni Sisters of the Hidden Village/Neko 补 ~女僕們的夜曲~ 条目（对齐母 tab 末位）。"""

import pywikibot

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

p = pywikibot.Page(site, "Template:Tab/The Oni Sisters of the Hidden Village/Neko")
OLD = "|[[小说:隐世村的鬼姐妹 ~祈祷的千纸鹤篇~/猫语|~祈祷的千纸鹤篇~]]\n}}"
NEW = (
    "|[[小说:隐世村的鬼姐妹 ~祈祷的千纸鹤篇~/猫语|~祈祷的千纸鹤篇~]]\n"
    "|[[小说:隐世村的鬼姐妹 ~女僕們的夜曲~/猫语|~女僕們的夜曲~]]\n}}"
)
assert OLD in p.text
p.text = p.text.replace(OLD, NEW)
p.save(
    summary="补 ~女僕們的夜曲~ 条目（该 /猫语 页已挂本 tab，对齐母 tab 顺序）", bot=True
)
print("updated")
