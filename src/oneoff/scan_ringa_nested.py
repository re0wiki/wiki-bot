"""只读：扫描全部 Ringa 引用页，找出嵌套在 <ref> 内使用 {{Ringa}} 的页面。"""

import os
import re

os.environ.pop("PYTHONPATH", None)

import pywikibot

site = pywikibot.Site("zh", "re0")

tpl = pywikibot.Page(site, "Template:Ringa")
REF_RE = re.compile(r"<ref[^>]*>.*?</ref>", re.DOTALL)

nested, normal = [], []
for p in tpl.embeddedin(namespaces=0):
    text = p.text
    if "{{Ringa" not in text:
        continue
    in_ref = any("{{Ringa" in m.group(0) for m in REF_RE.finditer(text))
    (nested if in_ref else normal).append(p.title())

print(f"嵌套在 <ref> 内（脚注失效 + 引用错误）: {len(nested)} 页")
for t in nested:
    print("  -", t)
print(f"\n正常使用: {len(normal)} 页")
