"""完善索引页 ReZero Wiki:模板 + 模板分类统一（2026-07-29，用户确认）。

1. 7 个模板页改分类：
   - Infobox anime/music/bd/game：内容模板 -> 信息框模板
   - Kana2Romaji：字词转换模板 -> 注音模板（音译属注音工作流，非字词转换）
   - Bot：消息框模板 -> 维护模板（bot 声明属站务维护）
   - Category redirect：摘 消息框模板（保留 重定向模板，功能即重定向维护）
2. 删除清空的 Category:内容模板、Category:消息框模板
3. 索引页：清已删模板条目（Quote/big、Quote/small、AV）、补 BV、
   信息框 4 条目移入信息框节、Copy/Sandbox 移入格式与工具节、
   Category redirect 移入重定向节、重定向节例子补新接管旧名
存档 logs/index_page_fix_2026-07-29.json
"""

import json

import pywikibot

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

archive: dict = {"templates": {}, "index_before": None, "index_after": None}

# --- 1. 模板页分类修改 ---
RECAT = {
    "Infobox anime": ("内容模板", "信息框模板"),
    "Infobox music": ("内容模板", "信息框模板"),
    "Infobox bd": ("内容模板", "信息框模板"),
    "Infobox game": ("内容模板", "信息框模板"),
    "Kana2Romaji": ("字词转换模板", "注音模板"),
    "Bot": ("消息框模板", "维护模板"),
}
for name, (old_cat, new_cat) in RECAT.items():
    p = pywikibot.Page(site, f"Template:{name}")
    archive["templates"][name] = p.text
    old_line = f"[[Category:{old_cat}]]"
    assert old_line in p.text, f"{name} 找不到 {old_line}"
    p.text = p.text.replace(old_line, f"[[Category:{new_cat}]]")
    p.save(summary=f"模板分类调整：{old_cat} -> {new_cat}（分类与功能对齐）", bot=True)
    print(f"{name}: {old_cat} -> {new_cat}")

# Category redirect：摘除 消息框模板
p = pywikibot.Page(site, "Template:Category redirect")
archive["templates"]["Category redirect"] = p.text
assert "\n[[Category:消息框模板]]" in p.text
p.text = p.text.replace("\n[[Category:消息框模板]]", "")
p.save(summary="模板分类调整：摘除 消息框模板（功能归 重定向模板）", bot=True)
print("Category redirect: 摘除 消息框模板")

# --- 2. 删除空分类 ---
for cn in ["内容模板", "消息框模板"]:
    cat = pywikibot.Category(site, f"Category:{cn}")
    members = list(cat.members())
    if members:
        print(f"!! Category:{cn} 非空，跳过删除: {[m.title() for m in members]}")
        continue
    pywikibot.Page(site, f"Category:{cn}").delete(
        reason="空分类：成员已归入功能匹配的分类（见 ReZero Wiki:模板 索引）",
        prompt=False,
    )
    print(f"已删除空分类 Category:{cn}")

# --- 3. 索引页 ---
idx = pywikibot.Page(site, "ReZero Wiki:模板")
archive["index_before"] = idx.text
text = idx.text


def rep(old: str, new: str) -> None:
    global text
    assert text.count(old) == 1, (
        f"定位串不唯一或缺失: {old[:60]!r} (count={text.count(old)})"
    )
    text = text.replace(old, new)


# 3a. 信息框节补 4 个条目
rep(
    "* {{t|Infobox staff}} — 制作人员\n",
    "* {{t|Infobox staff}} — 制作人员\n"
    "* {{t|Infobox anime}} — 动画剧集条目（引用页归入 [[:Category:剧集]]）\n"
    "* {{t|Infobox music}} — 音乐条目\n"
    "* {{t|Infobox bd}} — BD 圆盘（引用页归入 [[:Category:圆盘]]）\n"
    "* {{t|Infobox game}} — 游戏\n",
)

# 3b. 引文节：Quote 行去掉已删的 big/small
rep(
    "* {{t|Quote}} — 引文基底模板（{{t|Quote/main}}、{{t|Quote/big}}、{{t|Quote/small}}，"
    "见 [[:Category:引文模板]]）",
    "* {{t|Quote}} — 引文基底模板（共用实现 {{t|Quote/main}}，见 [[:Category:引文模板]]）",
)

# 3c. 页首与维护节：移除 Category redirect（移入重定向节）
rep("* {{t|Category redirect}} — 分类重定向\n", "")

# 3d. 外部链接节：补 BV
rep(
    "* {{t|Twitter}} — 社交媒体\n",
    "* {{t|Twitter}} — 社交媒体\n* {{t|BV}} — B 站视频\n",
)

# 3e. 内容与作品节：去掉信息框 4 条目、已删 AV、空分类指引；指向字词转换模板
rep(
    """== 内容与作品 ==
全系列见 [[:Category:内容模板]]。

* {{t|Infobox anime}} — 动画剧集条目（引用页归入 [[:Category:剧集]]）
* {{t|Infobox music}} — 音乐条目
* {{t|AV}} — 动画/音声关联
* {{t|Infobox bd}} — BD 圆盘（引用页归入 [[:Category:圆盘]]）
* {{t|Infobox game}} — 游戏
* {{t|加护}} — 加护
* {{t|Seirei}} / {{t|Yousei}} / {{t|Elf}} — 易混种族相关模板""",
    """== 内容与作品 ==
作品设定相关的字词转换模板，全系列见 [[:Category:字词转换模板]]。

* {{t|加护}} — 加护
* {{t|Seirei}} / {{t|Yousei}} / {{t|Elf}} — 易混种族相关模板""",
)

# 3f. 元模板节：移除 Copy、Sandbox（先于 3g，保证定位串唯一）
rep(
    "* {{t|T category}} — 模板分类辅助\n* {{t|Copy}} — 复制内容\n* {{t|Sandbox}} — 测试用\n",
    "* {{t|T category}} — 模板分类辅助\n",
)

# 3g. 格式与工具节：补 Copy、Sandbox（自元模板节迁入）
rep(
    "* {{t|NoteTA}} — 字词转换\n",
    "* {{t|NoteTA}} — 字词转换\n* {{t|Copy}} — 复制内容\n* {{t|Sandbox}} — 测试用\n",
)

# 3h. 重定向节：补 Category redirect 条目 + 例子补新接管旧名
rep(
    "== 重定向 ==\n"
    "英文站搬运页里的旧模板名（Re:Zero Light Novel Volumes、Re:Zero Arc 4/5 Manga、"
    "Re:Zero Manga Volumes、Infobox Events、Infobox battles 等）由 bot 定期批量替换为规范名"
    "（Infobox book、Infobox event、Infobox battle 等），zh 站不保留同名重定向。",
    "== 重定向 ==\n"
    "* {{t|Category redirect}} — 分类重定向（引用页归入 [[:Category:已重定向的分类]]）\n"
    "\n"
    "英文站搬运页里的旧模板名（Re:Zero Light Novel Volumes、Re:Zero Arc 4/5 Manga、"
    "Re:Zero Manga Volumes、Infobox Events、Infobox battles、Anime、Music、Re:Zero BD、"
    "Re:Zero Game 等）由 bot 定期批量替换为规范名（Infobox book、Infobox event、"
    "Infobox battle、Infobox anime、Infobox music、Infobox bd、Infobox game 等），"
    "zh 站不保留同名重定向。",
)

idx.text = text
idx.save(summary="索引完善：清已删模板条目、补 BV、信息框归类与分节对齐", bot=True)
archive["index_after"] = text
print("索引页已更新")

with open("logs/index_page_fix_2026-07-29.json", "w", encoding="utf-8") as f:
    json.dump(archive, f, ensure_ascii=False, indent=2)
print("存档完成")
