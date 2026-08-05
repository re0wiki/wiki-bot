"""voice 系归一⑤⑥⑦：复扫 → 摘 fallback + doc 同步 + 沙盒手动改 → 快照对比。"""

import json
import re

from pywikibot.data import api

import pywikibot

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

# ── ⑤ 全命名空间复扫旧名 ──────────────────────────────────
pats = {
    k: re.compile(rf"\|\s*voice_zh-{k}\s*=", re.IGNORECASE) for k in ("cn", "hk", "tw")
}
residual = []
for ns in (0, 2, 4, 6, 8, 10, 14, 828):
    params = {
        "action": "query",
        "format": "json",
        "generator": "allpages",
        "gapnamespace": str(ns),
        "gaplimit": "50",
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
    }
    data = api.Request(site=site, parameters=params).submit()
    while True:
        for pg in data.get("query", {}).get("pages", {}).values():
            text = (
                pg.get("revisions", [{}])[0]
                .get("slots", {})
                .get("main", {})
                .get("*", "")
            )
            for k, p in pats.items():
                if p.search(text):
                    residual.append((pg["title"], k))
        if "continue" in data:
            params.update(data["continue"])
            data = api.Request(site=site, parameters=params).submit()
        else:
            break
    print(f"ns {ns} rescanned", flush=True)
print(f"残留: {residual}")
# 预期只剩 ns2 沙盒（任务生成器不含 ns2）与 ns10 的 /doc（pre 保护）
expected = {t for t, _ in residual}
assert expected <= {"User:Wuxian3635/沙盒", "Template:Infobox character/doc"}, residual

# ── 沙盒手动改（bot 任务不含 ns2）─────────────────────────
sb = pywikibot.Page(site, "User:Wuxian3635/沙盒")
t = sb.text
for k in ("cn", "tw", "hk"):
    t, n = re.subn(rf"\|\s*voice_zh-{k}\s*=", f"| voice_zh_{k} =", t)
    print(f"沙盒 voice_zh-{k}: {n} 处")
sb.text = t
sb.save(
    summary="参数名归一：voice_zh-cn/tw/hk → 下划线写法（模板已改用新名）", bot=False
)
print("沙盒已改")

# ── ⑥ 摘 fallback ─────────────────────────────────────────
tpl = pywikibot.Page(site, "Template:Infobox character")
text = tpl.text
for old, new in [
    ("      <default>{{{voice_zh-cn|}}}</default>\n", ""),
    ("      <default>{{{voice_zh-tw|}}}</default>\n", ""),
    ("      <default>{{{voice_zh-hk|}}}</default>\n", ""),
]:
    assert text.count(old) == 1, f"fallback 匹配失败: {old[:50]}"
    text = text.replace(old, new)
tpl.text = text
tpl.save(summary="参数名归一收尾：摘除 voice_zh-cn/tw/hk fallback（全站已零残留）")
print("⑥ fallback 已摘")

# ── ⑥ doc 同步（语法示例 + templatedata 键 + paramOrder）──
doc = pywikibot.Page(site, "Template:Infobox character/doc")
text = doc.text
n = text.count("voice_zh-")
text = (
    text.replace("voice_zh-cn", "voice_zh_cn")
    .replace("voice_zh-tw", "voice_zh_tw")
    .replace("voice_zh-hk", "voice_zh_hk")
)
assert n == 9, f"doc 命中 {n} 处，预期 9（示例 3 + templatedata 键 3 + paramOrder 3）"
m = re.search(r"<templatedata>(.*?)</templatedata>", text, re.DOTALL)
td = json.loads(m.group(1))
assert "voice_zh_cn" in td["params"] and "voice_zh-cn" not in td["params"]
doc.text = text
doc.save(
    summary="参数名归一同步：voice_zh-cn/tw/hk → 下划线写法（语法示例 + templatedata）"
)
print(f"⑥ doc 已同步（{n} 处）")

# ── ⑦ 快照对比 ────────────────────────────────────────────
with open("logs/voice_snapshot_before.json", encoding="utf-8") as f:
    before = json.load(f)


def norm(html: str) -> str:
    html = re.sub(r'data-source="[^"]*"', "", html)
    html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
    html = re.sub(r"pi-tab(panel)?-[0-9a-f]+", r"pi-tab\1", html)
    return html


r = api.Request(
    site=site,
    parameters={
        "action": "parse",
        "format": "json",
        "page": "角色:菜月·昴",
        "prop": "text",
        "disablelimitreport": "1",
    },
).submit()
new_html = r["parse"]["text"]["*"]
same = norm(before["角色:菜月·昴"]) == norm(new_html)
ok = "國語（臺灣）" in new_html and "华语（香港）" in new_html
print(f"⑦ 渲染等价={same} 配音栏渲染={ok}")
assert same and ok
print("ALL DONE")
