"""信息框模板命名统一：6 个模板改名为 Infobox X 格式（2026-07-29，用户确认）。

Anime -> Infobox anime、Seiyu -> Infobox seiyu、Music -> Infobox music、
Re:Zero BD -> Infobox bd、Staff -> Infobox staff、Re:Zero Game -> Infobox game。

步骤：收集引用页 -> 移动（不留重定向）-> 批量替换调用名 -> 更新索引页。
en 有同名的 4 个旧名由 jobs/jobs.py 模板替换任务接管（本次提交同步改）。
存档 logs/renamed_infobox_templates_2026-07-29.json。
"""

import json
import re

import pywikibot
from pywikibot import pagegenerators

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

RENAMES = {
    "Anime": "Infobox anime",
    "Seiyu": "Infobox seiyu",
    "Music": "Infobox music",
    "Re:Zero BD": "Infobox bd",
    "Staff": "Infobox staff",
    "Re:Zero Game": "Infobox game",
}

SUMMARY = "信息框模板命名统一：{} -> {}（Infobox X 格式）"
archive: dict = {"renames": RENAMES, "pages": {}, "stray_mentions": []}


def call_pat(old: str) -> re.Pattern:
    # {{old|...}} / {{old}} / {{old |...}}，空格可写成下划线，首字母大小写不敏感
    body = re.escape(old).replace(r"\ ", "[ _]")
    return re.compile(r"\{\{\s*" + body + r"\s*([|}])", re.IGNORECASE)


for old, new in RENAMES.items():
    tpl = pywikibot.Page(site, f"Template:{old}")
    assert tpl.exists() and not tpl.isRedirectPage(), f"Template:{old} 状态异常"
    archive["pages"][old] = {"wikitext": tpl.text, "callers": {}}

    callers = list(tpl.embeddedin())
    print(f"\n=== {old} -> {new}（{len(callers)} 个引用页）===")

    tpl.move(
        f"Template:{new}",
        reason=SUMMARY.format(old, new),
        movetalk=True,
        noredirect=True,
    )
    print(f"已移动 Template:{old} -> Template:{new}")

    pat = call_pat(old)
    for caller in pagegenerators.PreloadingGenerator(callers, groupsize=50):
        if not caller.exists():
            continue
        text = caller.text
        new_text, n = pat.subn("{{" + new + r" \1", text)
        # 顺带检查是否有 [[Template:old]] 纯链接形式的提及
        for m in re.finditer(r"\[\[\s*[Tt]emplate\s*:\s*" + re.escape(old), text):
            archive["stray_mentions"].append(caller.title())
        if n:
            caller.text = new_text
            caller.save(summary=SUMMARY.format(old, new), bot=True)
            archive["pages"][old]["callers"][caller.title()] = n
            print(f"  {caller.title()}（{n} 处）")

# 索引页更新：{{t|旧名}} 与「尚无用法文档」行里的平列举
idx = pywikibot.Page(site, "ReZero Wiki:模板")
archive["index_before"] = idx.text
lines = idx.text.splitlines()
for i, line in enumerate(lines):
    for old, new in RENAMES.items():
        line = re.sub(
            r"(\{\{t\|)" + re.escape(old) + r"(\}\})", r"\1" + new + r"\2", line
        )
        # 平举清单里的「、旧名、」形式（行首/行尾边界也要处理）
        line = re.sub(
            r"(?<=[、：])" + re.escape(old) + r"(?=[、。，])",
            new,
            line,
        )
    lines[i] = line
idx.text = "\n".join(lines)
idx.save(summary="信息框模板改名同步：6 个信息框统一为 Infobox X 命名", bot=True)
print("\n索引页已更新")

with open("logs/renamed_infobox_templates_2026-07-29.json", "w", encoding="utf-8") as f:
    json.dump(archive, f, ensure_ascii=False, indent=2)

total = sum(len(v["callers"]) for v in archive["pages"].values())
print(f"\n完成：6 个模板改名，{total} 个引用页替换，存档已写入")
if archive["stray_mentions"]:
    print("注意：以下页面有 [[Template:旧名]] 链接形式提及，需人工核查：")
    for t in sorted(set(archive["stray_mentions"])):
        print(f"  {t}")
