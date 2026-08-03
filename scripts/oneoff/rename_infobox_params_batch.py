"""C10/C12：批量把调用页的 infobox 参数名改为归一后的新名（模板已用 default 兼容旧名，本批是源码规范化）。

- Infobox seiyu（54 页）：image1→image, caption1→Caption, title1→name, nombre→name_en,
  rōmaji→name_ja_romaji, nacimiento→birth, personaje→role
- Infobox staff（8 页）：同上 + guión→script, diseño→design, compositor→composer
- Infobox anime（175 页）：Volume→volume, Air Date→air_date, Opening→opening, Ending→ending

只在 {{Infobox X ...}} 调用块内替换（大括号配对），幂等。
"""

import os

os.environ.pop("PYTHONPATH", None)

import re

import pywikibot

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi", site.user()

RENAMES = {
    "Infobox seiyu": {
        "image1": "image",
        "caption1": "Caption",
        "title1": "name",
        "nombre": "name_en",
        "rōmaji": "name_ja_romaji",
        "nacimiento": "birth",
        "personaje": "role",
    },
    "Infobox staff": {
        "image1": "image",
        "caption1": "Caption",
        "title1": "name",
        "nombre": "name_en",
        "rōmaji": "name_ja_romaji",
        "nacimiento": "birth",
        "guión": "script",
        "diseño": "design",
        "compositor": "composer",
    },
    "Infobox anime": {
        "Volume": "volume",
        "Air Date": "air_date",
        "Opening": "opening",
        "Ending": "ending",
    },
}


def find_call_block(text, tpl_name):
    """返回 {{tpl_name ...}} 调用块的 (start, end)（大括号配对），无则 None。"""
    m = re.search(r"\{\{\s*" + re.escape(tpl_name) + r"(?=\s*[|}])", text)
    if not m:
        return None
    depth, i = 0, m.start()
    while i < len(text) - 1:
        two = text[i : i + 2]
        if two == "{{":
            depth += 1
            i += 2
        elif two == "}}":
            depth -= 1
            i += 2
            if depth == 0:
                return m.start(), i
        else:
            i += 1
    return None


def rename_in_block(block, mapping):
    changed = []
    for old, new in mapping.items():
        pat = re.compile(r"(\|\s*)" + re.escape(old) + r"(\s*=)")
        if pat.search(block):
            block = pat.sub(r"\g<1>" + new + r"\g<2>", block)
            changed.append(f"{old}→{new}")
    return block, changed


total_pages = 0
total_edits = 0
for tpl_name, mapping in RENAMES.items():
    tpl = pywikibot.Page(site, f"Template:{tpl_name}")
    for page in tpl.embeddedin(namespaces=0):
        total_pages += 1
        text = page.text
        loc = find_call_block(text, tpl_name)
        if not loc:
            print(f"!! {page.title()}: 未找到 {tpl_name} 调用块，跳过")
            continue
        start, end = loc
        block, changed = rename_in_block(text[start:end], mapping)
        if not changed:
            print(f"-- {page.title()}: 无需改动")
            continue
        page.text = text[:start] + block + text[end:]
        page.save(
            summary=f"{tpl_name} 参数名归一：{', '.join(changed)}（模板已兼容旧名）",
            bot=True,
        )
        total_edits += 1
        print(f"OK {page.title()}: {', '.join(changed)}")

print(f"\nDONE: {total_pages} 页扫描，{total_edits} 页编辑")
