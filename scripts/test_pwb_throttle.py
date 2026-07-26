# -*- coding: utf-8 -*-
"""pywikibot 限速配置实测：读 100 页 + 沙盒写一次。

验证 user-config.py 的 minthrottle/put_throttle 调整后，
pywikibot 通路在 Cloudflare 下不再触发 429。
"""

import time

import pywikibot
from pywikibot import pagegenerators

site = pywikibot.Site("zh", "re0")

# --- 读测试：批量预载 100 个主空间页面 ---
t0 = time.time()
gen = site.allpages(namespace=0, total=100)
loaded = list(pagegenerators.PreloadingGenerator(gen, groupsize=50))
texts = sum(len(p.text) for p in loaded)
print(f"[read] {len(loaded)} 页, {texts} 字符, {time.time() - t0:.1f}s")

# --- 写测试：沙盒追加一行时间戳 ---
site.login()
assert site.user() == "IchiSanNi", site.user()
sandbox = pywikibot.Page(site, "User:IchiSanNi/沙盒")
old = sandbox.text
t0 = time.time()
sandbox.text = old + f"\nthrottle 配置测试 {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
sandbox.save(summary="throttle 配置测试（可回退）")
print(f"[write] 沙盒写入成功, {time.time() - t0:.1f}s")

print("ALL CHECKS PASSED")
