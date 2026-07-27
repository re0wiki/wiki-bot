# -*- coding: utf-8 -*-
"""async 并发验证：全速读 + 后台异步沙盒写同时进行，观察是否触发 429。

复现 cosmetic_changes -async 的最坏工况：
- 主线程 PreloadingGenerator 全速预载页面（读）
- 后台 page_put_queue 守护线程按 put_throttle 保存沙盒（写）

关注输出中的 "Sleeping for N seconds"（N>2 即 throttle 升级/retry_after）。
"""

import time

import pywikibot
from pywikibot import pagegenerators

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"
sandbox = pywikibot.Page(site, "User:IchiSanNi/沙盒")

t0 = time.time()
pages_read = 0
saves_queued = 0
gen = site.allpages(namespace=0, total=2000)
for page in pagegenerators.PreloadingGenerator(gen, groupsize=50):
    _ = len(page.text)
    pages_read += 1
    # 每 25 页排一次异步写（≈put_throttle 饱和）
    if pages_read % 25 == 0:
        sandbox.text = (
            f"async 并发验证 {time.strftime('%H:%M:%S')} pages_read={pages_read}\n"
        )
        sandbox.save(summary="async 并发验证（可回退）", asynchronous=True)
        saves_queued += 1
    if time.time() - t0 > 180:  # 3 分钟上限
        break

print(
    f"scan done: {pages_read} pages read, {saves_queued} saves queued, "
    f"{time.time() - t0:.0f}s; waiting for queue to drain..."
)
pywikibot.stopme()  # 等后台保存线程排空队列
print(f"retry_after after run: {site.throttle.retry_after}")
print("ALL CHECKS PASSED")
