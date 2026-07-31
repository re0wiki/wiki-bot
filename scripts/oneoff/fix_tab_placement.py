"""修复 Tab 系挂载缺失（2026-07-28 审计后）。

规则（与 anime 系既成惯例一致：每页只挂自己系列的 tab，跨章/跨季导航块不算）：
- Manga Arc X Chapter：块0=章导航（跳过），块1=本章各话 → 挂 {{Tab/Manga Arc X Chapter}}
- 单块 tab（Manga Volume、剑鬼恋歌 Chapter/Volume、Puck、Elsa、LN/Synopsis）→ 全部链接页
- 已带任何 Tab/ 调用的页跳过；红链跳过（不建页）
- 插入位置：{{To do}} 行之后（无 To do 则 {{Init}} 之后），与既成页面一致
另修两个模板本身：Battle Ballad Act 繁体红链 終幕->终幕；Tab/Ruby 移除已删的 R/ja。
"""

import re

import pywikibot

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
BLOCK_RE = re.compile(r"\{\{Tab.*?\}\}", flags=re.DOTALL)

PLAN = {  # tab 名 -> 取哪些块（None=全部块）
    "Tab/Manga Arc 1 Chapter": 1,
    "Tab/Manga Arc 2 Chapter": 1,
    "Tab/Manga Arc 3 Chapter": 1,
    "Tab/Manga Arc 4 Chapter": 1,
    "Tab/Manga Volume": None,
    "Tab/Sword Demon Love Song Chapter": None,
    "Tab/Sword Demon Love Song Volume": None,
    "Tab/The Great Spirit Puck": None,
    "Tab/Elsa and Meili, Assassin Sisters' Dark Diary": None,
    "Tab/LN/Synopsis": None,
}

fixed, skipped, redlinks = [], [], []
for tab, block_idx in PLAN.items():
    text = pywikibot.Page(site, f"Template:{tab}").text
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)  # 注释内链接不算
    blocks = BLOCK_RE.findall(text)
    targets = []
    for b in blocks[1:] if block_idx else blocks:
        targets += [m.group(1).strip() for m in LINK_RE.finditer(b)]
    for t in dict.fromkeys(targets):  # 保序去重
        if t.startswith(("Category:", "File:", "Template:", "Module:")):
            continue
        p = pywikibot.Page(site, t)
        if not p.exists():
            redlinks.append((tab, t))
            continue
        if "{{Tab/" in p.text:
            skipped.append((tab, t, "已带 tab"))
            continue
        call = "{{" + tab + "}}\n"
        if "{{To do}}\n" in p.text:
            p.text = p.text.replace("{{To do}}\n", "{{To do}}\n" + call, 1)
        elif "{{Init}}\n" in p.text:
            p.text = p.text.replace("{{Init}}\n", "{{Init}}\n" + call, 1)
        else:
            skipped.append((tab, t, "无 Init/To do 锚点"))
            continue
        p.save(summary=f"补挂 {tab}（Tab 挂载缺失修复）", bot=True)
        fixed.append((tab, t))
        print(f"OK {t} <- {tab}")

# ---- 模板自身小修 ----
p = pywikibot.Page(site, "Template:Tab/Sword Demon Battle Ballad Act")
assert "小说:剑鬼战歌——終幕|終" in p.text
p.text = p.text.replace("[[小说:剑鬼战歌——終幕|終]]", "[[小说:剑鬼战歌——终幕|终]]")
p.save(summary="链接目标改为简体现存页（終幕->终幕）", bot=True)
print("OK Template:Tab/Sword Demon Battle Ballad Act")

p = pywikibot.Page(site, "Template:Tab/Ruby")
assert "[[Template:R/ja]]" in p.text
p.text = p.text.replace("|[[Template:R/ja]]", "")
p.save(summary="移除已删除模板 R/ja 的导航项", bot=True)
print("OK Template:Tab/Ruby")

print(f"\n修复 {len(fixed)} 页 | 跳过 {len(skipped)} | 红链 {len(redlinks)}")
for tab, t, why in skipped:
    print(f"  跳过({why}): {t} <- {tab}")
for tab, t in redlinks:
    print(f"  红链: {t} <- {tab}")
