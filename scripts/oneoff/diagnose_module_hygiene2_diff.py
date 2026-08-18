"""诊断 deploy_module_hygiene2 的 5 项 FAIL：真值法取基线。

流程：恢复旧模块（含重建 Module:Utils）→ purge → 基线快照 → 打回新模块 →
purge → 对比快照 → 逐项 diff。结束时 wiki 状态 = 新模块 + Utils 已删。
"""

import difflib
import os
import re

os.environ.pop("PYTHONPATH", None)

import pywikibot
from pywikibot.data import api

site = pywikibot.Site("zh", "re0")

PAGES = [
    "角色:菜月·昴",
    "角色:菜月·昴/关系",
    "小说:1卷",
    "术语:异世界文字",
    "ReZero Wiki:攻略指南",
]

SWAP = ["Init", "Title", "NoteTA", "Bili"]  # 鼠色猫语录两项已 OK，不动


def parse_html(title):
    req = api.Request(
        site=site, parameters={"action": "parse", "prop": "text", "page": title}
    )
    html = req.submit()["parse"]["text"]["*"]
    html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
    html = re.sub(r"pi-tab(panel)?-[0-9a-f]+-", r"pi-tab\1-", html)
    html = html.replace("http://rezero.fandom.com", "https://rezero.fandom.com")
    return re.sub(r"noteTA-\d+", "noteTA-N", html)


def purge():
    for t in PAGES:
        pywikibot.Page(site, t).purge()


def snaps():
    return {t: parse_html(t) for t in PAGES}


def save(title, path, summary):
    p = pywikibot.Page(site, title)
    with open(path, encoding="utf-8") as f:
        src = f.read()
    if p.exists() and p.text.strip() == src.strip():
        print(f"跳过 {title}（已是目标内容）")
        return
    p.text = src
    p.save(summary=summary)
    print(f"已保存 {title}")


site.login()
assert site.user() == "IchiSanNi"

# ── 1. 恢复旧版取基线 ─────────────────────────────────────
# 旧 Title require Module:Utils，先重建
save(
    "Module:Utils",
    "logs/modules/Utils.lua",
    "临时重建：渲染对比基线用，对比后随新部署删除",
)
for m in SWAP:
    save(f"Module:{m}", f"logs/modules/{m}.lua", "临时恢复旧版：渲染对比基线")

purge()
before = snaps()
print("基线快照完成")

# ── 2. 打回新版 ───────────────────────────────────────────
SUMMARIES = {
    "Init": "卫生修复：display_title/category/tab 全局函数 local 化",
    "Title": "a_in_b 内联（Module:Utils 已无其他消费者，随本次删除）",
    "NoteTA": "indicator id 改用调用序号（code:len() 等长会碰撞）；溢出分类名与悬浮文本繁转简",
    "Bili": "可读性：ustring.sub(id, 0, 0) → sub(id, 1, 1)（行为等价）",
}
for m in SWAP:
    save(f"Module:{m}", f"logs/modules/new/{m}.lua", SUMMARIES[m])
u = pywikibot.Page(site, "Module:Utils")
if u.exists():
    u.delete(
        reason="孤儿模块：lcp/lcs/split 无消费者，a_in_b 已内联进 Module:Title",
        prompt=False,
    )
    print("已删除 Module:Utils")

purge()
after = snaps()

# ── 3. diff ───────────────────────────────────────────────
for t in PAGES:
    b, a = before[t], after[t]
    if a == b:
        print(f"\nOK  {t}: 渲染等价")
        continue
    d = list(difflib.unified_diff(b.splitlines(), a.splitlines(), lineterm="", n=1))
    print(f"\nFAIL {t}: {len(d)} 行 diff")
    for line in d[:40]:
        print("  " + line[:400])
