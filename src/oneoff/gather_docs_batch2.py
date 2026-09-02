"""只读：拉取 event/bd/music/著作权六件套的 /doc，检查哪些提到 label 或英文文本需同步。"""

import os

os.environ.pop("PYTHONPATH", None)

import pywikibot

site = pywikibot.Site("zh", "re0")

for t in [
    "Template:Infobox event/doc",
    "Template:Infobox bd/doc",
    "Template:Infobox music/doc",
    "Template:CC-BY-SA/doc",
    "Template:Fairuse/doc",
    "Template:From Wikimedia/doc",
    "Template:Other free/doc",
    "Template:PD/doc",
    "Template:Self/doc",
]:
    print(f"\n----- {t} -----")
    print(pywikibot.Page(site, t).text)
