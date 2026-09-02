# 一次性探测：Disambiguator 扩展 + preloadpages(pageprops) 能否缓存 isDisambig
import sys

sys.path = [
    p
    for p in sys.path
    if p and not p.replace("\\", "/").rstrip("/").endswith("GitHub/wiki-bot")
]
import pywikibot

site = pywikibot.Site("zh", "re0")
print("has Disambiguator ext:", site.has_extension("Disambiguator"))

pages = [pywikibot.Page(site, t) for t in ["角色:菜月·昴", "Template:Tab"]]
loaded = list(site.preloadpages(pages, pageprops=True, quiet=True))
for p in loaded:
    print(p.title(), "-> isDisambig:", p.isDisambig(), "(无额外请求即成功)")
