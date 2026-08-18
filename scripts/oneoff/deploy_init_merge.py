"""部署 AutoTab → Init 合并（用户已批准）：

1. Module:Init 换新版（tab 逻辑内联 + Module:Tab 拼接，废弃 lcp/lcs 与大精灵帕克特判）
2. 删除 Module:AutoTab 与 Module:AutoTab/doc
3. 同步 Template:Init/doc 描述与 Template:Tab/Tab 导航链接
4. 部署前后 parse 对比渲染等价（含子页面样本）

幂等：内容相同则跳过保存。
"""

import os
import re

os.environ.pop("PYTHONPATH", None)

import pywikibot
from pywikibot.data import api

site = pywikibot.Site("zh", "re0")

SAMPLE_PAGES = [
    "角色:菜月·昴",  # 主页 + 5 子页（含猫语/语录共享后缀）
    "角色:菜月·昴/猫语",  # 子页面上的 Init（兄弟页导航）
    "角色:爱蜜莉雅",  # 同构样本
    "角色:罗兹瓦尔",  # 含短篇子页
    "小说:1卷",  # 小说前缀样本
]


def parse_html(page):
    req = api.Request(
        site=site,
        parameters={"action": "parse", "page": page, "prop": "text"},
    )
    html = req.submit()["parse"]["text"]["*"]
    html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
    # PortableInfobox tab id 带每次 parse 随机的哈希后缀
    return re.sub(r"pi-tab(panel)?-[0-9a-f]+-", r"pi-tab\1-", html)


print("采集编辑前渲染快照...")
before = {p: parse_html(p) for p in SAMPLE_PAGES}
print(f"快照 {len(before)} 页\n")

site.login()
assert site.user() == "IchiSanNi"

# ── 1. Module:Init ────────────────────────────────────────
with open("logs/modules/new/Init.lua", encoding="utf-8") as f:
    new_init = f.read()
p = pywikibot.Page(site, "Module:Init")
if p.text.strip() != new_init.strip():
    p.text = new_init
    p.save(
        summary="AutoTab 并入：tab 探测逻辑内联，拼接改调 Module:Tab，废弃 lcp/lcs 与大精灵帕克特判"
    )
    print("已保存 Module:Init")
else:
    print("跳过 Module:Init（已是最新）")

# ── 2. 删除 AutoTab ───────────────────────────────────────
for t in ["Module:AutoTab", "Module:AutoTab/doc"]:
    p = pywikibot.Page(site, t)
    if p.exists():
        p.delete(reason="逻辑已并入 Module:Init（唯一消费者），模块删除", prompt=False)
        print(f"已删除 {t}")
    else:
        print(f"跳过 {t}（不存在）")

# ── 3. 文档同步 ───────────────────────────────────────────
doc = pywikibot.Page(site, "Template:Init/doc")
OLD = "# 经 [[Module:AutoTab]] 生成页面顶部分页导航（当前页 + 各已存在的子页面）。"
NEW = "# 生成页面顶部分页导航（当前页 + 各已存在的子页面，经 [[Module:Tab]] 拼接）。"
if OLD in doc.text:
    doc.text = doc.text.replace(OLD, NEW)
    doc.save(summary="AutoTab 已并入 Module:Init，更新描述")
    print("已更新 Template:Init/doc")
else:
    print("跳过 Template:Init/doc（原文不匹配或已更新）")

tabtab = pywikibot.Page(site, "Template:Tab/Tab")
if "[[Module:AutoTab]]|" in tabtab.text:
    tabtab.text = tabtab.text.replace("|[[Module:AutoTab]]", "")
    tabtab.save(summary="Module:AutoTab 已删除，摘除导航链接")
    print("已更新 Template:Tab/Tab")
else:
    print("跳过 Template:Tab/Tab（原文不匹配或已更新）")

# ── 4. 部署后对比 ─────────────────────────────────────────
print("\n部署后渲染对比：")
fails = 0
for page in SAMPLE_PAGES:
    after = parse_html(page)
    err = "scribunto-error" in after or "Lua错误" in after
    same = after == before[page]
    fails += err or not same
    print(
        f"{'OK ' if (same and not err) else 'FAIL'} {page}: 渲染{'等价' if same else '有差异'}{'，有 Lua 错误！' if err else ''}"
    )

print(f"\n{'ALL CHECKS PASSED' if fails == 0 else f'{fails} 项异常'}")
