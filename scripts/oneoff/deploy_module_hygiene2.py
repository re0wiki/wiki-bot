"""批量部署 Module 卫生修复第二轮（用户已批准，docs/modules.md 2026-07-31 复审 1-5 项）：

- Init / Title / 鼠色猫语录 / NoteTA / Bili 5 个模块换源码（logs/modules/new/）
- 删除 Module:Utils 与其 /doc（lcp/lcs/split 无消费者，a_in_b 已内联进 Title）
- 部署前后 parse 对比渲染等价（noteTA id 序号化属预期变化，归一化后比较）

只写 zh 站，手动编辑（无 bot flag）。幂等：内容相同则跳过保存。
"""

import os
import re

os.environ.pop("PYTHONPATH", None)

import pywikibot
from pywikibot.data import api

site = pywikibot.Site("zh", "re0")

MODULES = ["Init", "Title", "鼠色猫语录", "NoteTA", "Bili"]

SUMMARIES = {
    "Init": "卫生修复：display_title/category/tab 全局函数 local 化",
    "Title": "a_in_b 内联（Module:Utils 已无其他消费者，随本次删除）",
    "鼠色猫语录": "卫生修复：函数 local 化、删恒真死 assert 与噪声注释",
    "NoteTA": "indicator id 改用调用序号（code:len() 等长会碰撞）；溢出分类名与悬浮文本繁转简",
    "Bili": "可读性：ustring.sub(id, 0, 0) → sub(id, 1, 1)（行为等价）",
}


def parse_html(**params):
    req = api.Request(
        site=site, parameters={"action": "parse", "prop": "text", **params}
    )
    html = req.submit()["parse"]["text"]["*"]
    html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
    # PortableInfobox 的 tab id 带每次 parse 随机的哈希后缀，归一化后再比较
    html = re.sub(r"pi-tab(panel)?-[0-9a-f]+-", r"pi-tab\1-", html)
    # 裸写 http://rezero.fandom.com 的外链会被规范化成 https，两次 parse 间可能翻转
    html = html.replace("http://rezero.fandom.com", "https://rezero.fandom.com")
    # NoteTA 的 id 从 code 字节数改为调用序号，属预期变化
    return re.sub(r"noteTA-\d+", "noteTA-N", html)


def snapshot(pages):
    return {t: parse_html(page=t) for t in pages}


def check(snaps):
    fails = 0
    for title, before in snaps.items():
        after = parse_html(page=title)
        err = "scribunto-error" in after or "Lua错误" in after
        same = after == before
        fails += err or not same
        print(
            f"{'OK ' if (same and not err) else 'FAIL'} {title}: "
            f"渲染{'等价' if same else '有差异'}{'，有 Lua 错误！' if err else ''}"
        )
    return fails


# ── 前置断言 ──────────────────────────────────────────────
# Utils 的 lcp/lcs/split 在模块快照中无消费者（消费者排查只能靠本地快照 grep——
# 本站 CirrusSearch insource 对源码一律返回空）
for fn in ["lcp", "lcs", "split", "a_in_b"]:
    users = []
    for f in os.listdir("logs/modules"):
        if f.endswith(".lua") and f != "Utils.lua":
            with open(f"logs/modules/{f}", encoding="utf-8") as fp:
                src = fp.read()
            if re.search(rf"\b{fn}\b", src):
                users.append(f)
    expect = ["Title.lua"] if fn == "a_in_b" else []
    assert users == expect, f"Utils.{fn} 出现新消费者: {users}"

for m in MODULES:
    assert os.path.exists(f"logs/modules/new/{m}.lua"), f"缺新源码 {m}.lua"

# 对照页清单：Init/Title 链、Infobox book、鼠色猫语录、Bili、NoteTA 全部引用页
PAGES = [
    "角色:菜月·昴",
    "角色:菜月·昴/关系",
    "小说:1卷",
    "动画:第12集/猫语",
    "鼠色猫语录/all",
    "术语:异世界文字",
]
tpl = pywikibot.Page(site, "Template:NoteTA")
PAGES += [p.title() for p in tpl.embeddedin(total=10)]

print("采集编辑前渲染快照...")
snaps = snapshot(PAGES)
print(f"快照 {len(snaps)} 项: {list(snaps)}\n")

# ── 应用编辑 ──────────────────────────────────────────────
site.login()
assert site.user() == "IchiSanNi"

for m in MODULES:
    with open(f"logs/modules/new/{m}.lua", encoding="utf-8") as f:
        new_src = f.read()
    p = pywikibot.Page(site, "Module:" + m)
    if p.text.strip() == new_src.strip():
        print(f"跳过 Module:{m}（已是最新）")
        continue
    p.text = new_src
    p.save(summary=SUMMARIES[m])
    print(f"已保存 Module:{m}")

# Title 已不再 require Utils，可安全删除（顺序不能反）
for t in ["Module:Utils", "Module:Utils/doc"]:
    p = pywikibot.Page(site, t)
    if p.exists():
        p.delete(
            reason="孤儿模块：lcp/lcs/split 无消费者，a_in_b 已内联进 Module:Title",
            prompt=False,
        )
        print(f"已删除 {t}")
    else:
        print(f"跳过 {t}（不存在）")

# ── 编辑后对比（先 purge 强制重新解析，避免拿到旧缓存的虚假等价）────────────
print("\npurge 对照页...")
for title in PAGES:
    pywikibot.Page(site, title).purge()

print("部署后渲染对比：")
fails = check(snaps)
print(f"\n{'ALL CHECKS PASSED' if fails == 0 else f'{fails} 项异常'}")
