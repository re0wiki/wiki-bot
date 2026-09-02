"""Auto ruby 并入 R（2026-07-28，用户指示：不留别名重定向）。

1. Template:R    ← Template:Auto ruby 的内容（R 由重定向变本体）
2. Template:R/ja ← Template:Auto ruby/ja 的内容（/ja 随迁，零引用但族内保留）
3. Template:Tab/Ruby 内的链接改为新名
4. 删除 Template:Auto ruby 与 Template:Auto ruby/ja（存档 logs/）
5. 索引页 ReZero Wiki:模板 同步
"""

import json

import pywikibot

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

src = pywikibot.Page(site, "Template:Auto ruby")
src_ja = pywikibot.Page(site, "Template:Auto ruby/ja")

# 存档
with open("logs/deleted_auto_ruby_2026-07-28.json", "w", encoding="utf-8") as f:
    json.dump(
        {"Template:Auto ruby": src.text, "Template:Auto ruby/ja": src_ja.text},
        f,
        ensure_ascii=False,
        indent=1,
    )

# 1+2. 写入 R 与 R/ja
r = pywikibot.Page(site, "Template:R")
r.text = src.text
r.save(summary="Auto ruby 并入 R：R 由重定向转为模板本体", bot=True)
print("updated Template:R")

r_ja = pywikibot.Page(site, "Template:R/ja")
r_ja.text = src_ja.text
r_ja.save(summary="Auto ruby/ja 随迁至 R/ja", bot=True)
print("created Template:R/ja")

# 3. Tab/Ruby 链接
tab = pywikibot.Page(site, "Template:Tab/Ruby")
text = tab.text
assert "[[Template:Auto ruby]]" in text and "[[Template:Auto ruby/ja]]" in text
text = text.replace("[[Template:Auto ruby/ja]]", "[[Template:R/ja]]")
text = text.replace("[[Template:Auto ruby]]", "[[Template:R]]")
tab.text = text
tab.save(summary="Auto ruby 并入 R：更新分页链接", bot=True)
print("updated Template:Tab/Ruby")

# 4. 删除旧名
for title in ["Template:Auto ruby", "Template:Auto ruby/ja"]:
    p = pywikibot.Page(site, title)
    p.delete(reason="已并入 Template:R（内容迁移完成，不留别名）", prompt=False)
    print(f"deleted {title}")

# 5. 索引页
idx = pywikibot.Page(site, "ReZero Wiki:模板")
text = idx.text
OLD_R = "* {{t|R}} — 注音简写\n* {{t|Auto ruby}} — 自动注音"
NEW_R = (
    "* {{t|R}} — 自动注音（中文、英文、日文、罗马音四合一；日文单注音用 {{t|R/ja}}）"
)
assert OLD_R in text
text = text.replace(OLD_R, NEW_R)
OLD_TODO = "Kana2Romaji、Anime、Auto ruby、R、Seirei"
NEW_TODO = "Kana2Romaji、Anime、R、Seirei"
assert OLD_TODO in text
text = text.replace(OLD_TODO, NEW_TODO)
idx.text = text
idx.save(summary="Auto ruby 并入 R，更新注音节与待补文档清单", bot=True)
print("updated ReZero Wiki:模板")
print("DONE")
