"""C10/C12 收尾验证：237 个调用页不应再出现旧参数名（在 infobox 调用块内）。"""

import os
import re

os.environ.pop("PYTHONPATH", None)

import pywikibot

site = pywikibot.Site("zh", "re0")

CHECKS = {
    "Infobox seiyu": [
        "image1",
        "caption1",
        "title1",
        "nombre",
        "rōmaji",
        "nacimiento",
        "personaje",
    ],
    "Infobox staff": [
        "image1",
        "caption1",
        "title1",
        "nombre",
        "rōmaji",
        "nacimiento",
        "guión",
        "diseño",
        "compositor",
    ],
    "Infobox anime": ["Volume", "Air Date", "Opening", "Ending"],
}

bad = 0
for tpl_name, olds in CHECKS.items():
    tpl = pywikibot.Page(site, f"Template:{tpl_name}")
    for page in tpl.embeddedin(namespaces=0):
        text = page.text
        for old in olds:
            if re.search(r"\|\s*" + re.escape(old) + r"\s*=", text):
                print(f"!! {page.title()} 仍有 | {old} =")
                bad += 1
print(f"\n{'CLEAN' if bad == 0 else f'{bad} 处残留'}")
