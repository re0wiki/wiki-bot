"""移除角色介绍图自动列举机制：迁移与验证脚本。

用法：
  snapshot <stage>           purge + parse 46 个受影响页，存 logs/char_image_snapshots/<stage>.json
  compare <stageA> <stageB>  归一化后逐页对比
  template-step1             模板 4 个 <format> 摘除 auto invoke（<default> 保留）
  template-step3             模板摘 4 个 <default> + m 死 invoke + noinclude 的 Tab/Character image
  fill [--only 标题]         给受影响页写显式 <gallery> 参数（skip 非空显式参数段）
  delete-assets              删除 Module:Character image + /doc + Template:Tab/Character image

数据：logs/char_image_migration.json（由 build_char_image_migration.py 生成）。
"""

import argparse
import json
import os
import re

import pywikibot

MIGRATION = "logs/char_image_migration.json"
SNAP_DIR = "logs/char_image_snapshots"
TEMPLATE = "Template:Infobox character"

site = pywikibot.Site("zh", "re0")

with open(MIGRATION, encoding="utf-8") as f:
    DATA = json.load(f)
LIVE = DATA["live"]
SUPPLEMENT = DATA["supplement"]
PAGES = sorted(set(LIVE) | set(SUPPLEMENT))

INVOKE = "{{#invoke:Character image|gen|acgnm=%s| name = {{#sub:{{SUBPAGENAME}}|3}}}}"


def purge_parse(title):
    p = pywikibot.Page(site, title)
    p.purge()
    req = site.simple_request(action="parse", page=title, prop="text", formatversion=2)
    return req.submit()["parse"]["text"]


def cmd_snapshot(stage):
    os.makedirs(SNAP_DIR, exist_ok=True)
    out = {}
    for i, t in enumerate(PAGES, 1):
        out[t] = purge_parse(t)
        print(f"  [{i}/{len(PAGES)}] {t}")
    path = f"{SNAP_DIR}/{stage}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    print(f"saved {path} ({len(out)} pages)")


def normalize(html):
    html = re.sub(r"<!--[\s\S]*?-->", "", html)
    return re.sub(r"pi-tab(panel)?-[0-9a-f]+-", r"pi-tab\1-H-", html)


def cmd_compare(a, b):
    with open(f"{SNAP_DIR}/{a}.json", encoding="utf-8") as f:
        before = json.load(f)
    with open(f"{SNAP_DIR}/{b}.json", encoding="utf-8") as f:
        after = json.load(f)
    ok = True
    for t in before:
        ba, aa = normalize(before[t]), normalize(after.get(t, ""))
        if ba == aa:
            print(f"✓ {t}")
        else:
            ok = False
            print(f"⚠️ {t}")
            for i, (x, y) in enumerate(zip(ba, aa)):
                if x != y:
                    print(f"    before: …{ba[max(0, i - 100) : i + 150]!r}")
                    print(f"    after:  …{aa[max(0, i - 100) : i + 150]!r}")
                    break
            print(f"    len {len(ba)} -> {len(aa)}")
    print("\nALL EQUIVALENT" if ok else "\nDIFFS FOUND")
    return ok


def edit_template(transform, summary):
    site.login()
    assert site.user() == "IchiSanNi"
    p = pywikibot.Page(site, TEMPLATE)
    old = p.text
    new = transform(old)
    assert new != old, "template transform produced no change"
    p.text = new
    p.save(summary=summary, bot=False)  # 模板关键改动走人工审查通道，不加 bot flag
    print(f"saved {TEMPLATE}: {summary}")


def cmd_template_step1():
    def tr(text):
        for sec in "angc":
            param = "{{{" + "image_" + sec + "}}}"
            old = (
                param
                + "{{#tag:gallery|"
                + param
                + "}}"
                + "{{#tag:gallery|"
                + INVOKE % sec
                + "}}"
            )
            assert old in text, f"format pattern for {sec} not found"
            text = text.replace(old, param + "{{#tag:gallery|" + param + "}}")
        return text

    edit_template(
        tr,
        "角色介绍图机制移除 step1：image_a/n/g/c 的 format 不再附带自动图库（default 保留，渲染不变）",
    )


def cmd_template_step3():
    def tr(text):
        for sec in "angc":
            old = "<default>{{#tag:gallery|" + INVOKE % sec + "}}</default>"
            assert old in text, f"default pattern for {sec} not found"
            text = text.replace(old, "")
        old_m = "{{#tag:gallery|" + INVOKE % "m" + "}}"
        assert old_m in text
        text = text.replace(old_m, "")
        old_tab = "{{Tab/Character image}}\n"
        assert old_tab in text
        text = text.replace(old_tab, "")
        return text

    edit_template(
        tr,
        "移除角色介绍图自动列举机制：摘除 invoke 与 Tab/Character image（全站已改显式参数）",
    )


def gallery_value(items):
    lines = "\n".join(f"{fn}|{cap}" for fn, cap in items)
    return f"<gallery>\n{lines}\n</gallery>"


def fill_page(title, dry=False):
    p = pywikibot.Page(site, title)
    text = p.text
    targets = {}  # sec -> items
    for sec, items in LIVE.get(title, {}).items():
        targets.setdefault(sec, []).extend(items)
    for sec, items in SUPPLEMENT.get(title, {}).items():
        targets.setdefault(sec, []).extend(items)

    for sec in ["a", "n", "g", "c"]:
        if sec not in targets:
            continue
        param = "image_" + sec
        m = re.search(
            r"^\|[ \t]*" + param + r"[ \t]*=[ \t]*(.*?)[ \t]*$", text, re.MULTILINE
        )
        if m and m.group(1):
            print(f"  SKIP {title} {param}: 已有非空显式值（自动图在此段本就不渲染）")
            continue
        value = gallery_value(targets[sec])
        if m:  # 空参数行，就地替换整行
            line_start = text.rfind("\n", 0, m.start()) + 1
            text = text[:line_start] + f"| {param} = {value}" + text[m.end() :]
        else:  # 无此参数行，插到 | image 行前，其次 | name 行后
            anchor = re.search(r"^\|\s*image\s*=", text, re.MULTILINE) or re.search(
                r"^\|\s*name\s*=.*$", text, re.MULTILINE
            )
            assert anchor, f"{title}: 找不到插入锚点"
            if anchor.group(0).startswith("| name"):
                pos = text.find("\n", anchor.end() - 1) + 1
            else:
                pos = text.rfind("\n", 0, anchor.start()) + 1
            text = text[:pos] + f"| {param} = {value}\n" + text[pos:]
        print(f"  FILL {title} {param} ({len(targets[sec])} 图)")

    if text != p.text:
        if dry:
            print(f"  [dry] would save {title}")
        else:
            p.text = text
            p.save(
                summary="角色介绍图改显式参数（自动列举机制移除前置迁移）",
                bot=True,
            )
            print(f"  SAVED {title}")


def cmd_fill(only=None, dry=False):
    site.login()
    assert site.user() == "IchiSanNi"
    for t in PAGES:
        if only and t != only:
            continue
        fill_page(t, dry=dry)


def cmd_delete_assets():
    site.login()
    assert site.user() == "IchiSanNi"
    # 先确认 embeddedin 已归零（除自身/doc/tab 互链）
    mod = pywikibot.Page(site, "Module:Character image")
    lingering = [
        p.title()
        for p in mod.embeddedin(namespaces=None)
        if p.title() not in {"Module:Character image/doc", TEMPLATE}
    ]
    assert not lingering, f"模块仍有引用: {lingering}"
    for t in [
        "Module:Character image",
        "Module:Character image/doc",
        "Template:Tab/Character image",
    ]:
        p = pywikibot.Page(site, t)
        p.delete(
            reason="[[Module:Character image]] 角色介绍图自动列举机制已移除",
            prompt=False,
        )
        print(f"deleted {t}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "cmd",
        choices=[
            "snapshot",
            "compare",
            "template-step1",
            "template-step3",
            "fill",
            "delete-assets",
        ],
    )
    ap.add_argument("args", nargs="*")
    ap.add_argument("--only")
    ap.add_argument("--dry", action="store_true")
    ns = ap.parse_args()
    if ns.cmd == "snapshot":
        cmd_snapshot(ns.args[0])
    elif ns.cmd == "compare":
        cmd_compare(*ns.args[:2])
    elif ns.cmd == "template-step1":
        cmd_template_step1()
    elif ns.cmd == "template-step3":
        cmd_template_step3()
    elif ns.cmd == "fill":
        cmd_fill(only=ns.only, dry=ns.dry)
    elif ns.cmd == "delete-assets":
        cmd_delete_assets()
