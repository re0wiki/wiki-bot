"""应用 B（假名同步 en Kanji）与 C（清除无汉字 override）计划。

输入 logs/bc_plan.json（plan_bc_edits.py 生成）。每页合并所有操作一次保存。
另处理蒂亚斯：假名含汉字「六世」，新增 name_ja_romaji override。
菜月贤一（全汉字名）归 D，本轮不动。
"""

import json
import re
import time

import pywikibot

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

with open("logs/bc_plan.json", encoding="utf-8") as f:
    plan = json.load(f)

# 每页操作列表
ops = {}  # title -> list of (kind, ...)
for e in plan["b_edits"]:
    ops.setdefault(e["title"], []).append(("set_kana", e["field"], e["old"], e["new"]))
for e in plan["c_removes"]:
    ops.setdefault(e["title"], []).append(("clear_override", e["override"]))
ops.setdefault("角色:蒂亚斯", []).append(
    ("set_override", "Diasu Repuntso Eremanso Opurēn Fattsubarumu Rokusei")
)

FIELD_RE = {
    k: re.compile(
        rf"^([ \t]*\|[ \t]*{k}[ \t]*=[ \t]*)([^\n]*?)([ \t]*\r?)$", re.MULTILINE
    )
    for k in ("name_ja_kana", "name_ja_kanji", "name_ja_romaji")
}

ok, skipped = [], []
for title, op_list in sorted(ops.items()):
    page = pywikibot.Page(site, title)
    text = page.text
    summaries = []
    try:
        for op in op_list:
            if op[0] == "set_kana":
                _, field, old, new = op
                m = FIELD_RE[field].search(text)
                assert m, f"{field} 字段未找到"
                cur = m.group(2).strip()
                assert cur == old.strip(), f"{field} 现值 {cur!r} != 计划旧值 {old!r}"
                text = text[: m.start(2)] + new + text[m.end(2) :]
                summaries.append(f"假名同步 en: {old} -> {new}")
            elif op[0] == "clear_override":
                _, old = op
                m = FIELD_RE["name_ja_romaji"].search(text)
                assert m, "name_ja_romaji 字段未找到"
                cur = m.group(2).strip()
                assert cur == old.strip(), f"override 现值 {cur!r} != 计划旧值 {old!r}"
                text = text[: m.start(2)] + text[m.end(2) :]
                summaries.append(
                    "移除 name_ja_romaji 手动值（假名无汉字，由模块自动生成）"
                )
            elif op[0] == "set_override":
                _, new = op
                m = FIELD_RE["name_ja_romaji"].search(text)
                assert m, "name_ja_romaji 字段未找到"
                assert not m.group(2).strip(), f"override 已有值 {m.group(2)!r}"
                text = text[: m.start(2)] + " " + new + text[m.end(2) :]
                summaries.append(f"补 name_ja_romaji（含汉字，模块无法转写）: {new}")
        page.text = text
        page.save(summary="；".join(summaries)[:250], bot=True)
        ok.append(title)
        print(f"OK {title}: {'; '.join(summaries)[:120]}")
    except AssertionError as ex:
        skipped.append((title, str(ex)))
        print(f"SKIP {title}: {ex}")
    time.sleep(0.5)

print(f"\n成功 {len(ok)}，跳过 {len(skipped)}")
with open("logs/bc_apply_result.json", "w", encoding="utf-8") as f:
    json.dump({"ok": ok, "skipped": skipped}, f, ensure_ascii=False, indent=1)
