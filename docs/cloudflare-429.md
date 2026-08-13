# Cloudflare 429（Fandom 限流）根因与对策

Fandom 前端接 Cloudflare，按 **TLS 指纹 + 请求速率**限流。本文是实测根因记录；
限速配置的日常结论见 `docs/wiki-access.md`「实测结论与坑」节。

## 已证伪的假设

- **User-Agent 不是诱因**：同一 IP 下 `curl` 带 `Pywikibot/...` UA 得 200，pywikibot 得 429。
- **`retry_after` 无客户端持久化**（2026-08-10 再确认）：`throttle.py:92` 仅内存赋值、
  `http.py:337-339` 从响应头写入，无任何落盘——「删掉某个文件即可恢复」不存在，
  新进程首发 429 是 Cloudflare 服务端滚动惩罚，只能等窗口。
- **惩罚按 TLS 指纹分别计数**（2026-08-10 实锤）：同一时刻 curl GET api.php 200、
  python requests/pywikibot 429；curl GET 始终可读，但 curl POST action=edit 立即返回
  **error code 1015**（Cloudflare 限流 block 页，非 JSON）。
- Retry-After  escalation 上限刷新：实测 6896s（此前记录 3594s），确认随触发次数持续增长。
- 本次诱因：main.py 常驻循环与 agent 会话脚本叠加（忘记先停循环）。
- **`throttle.ctrl` 不积累惩罚**：pywikibot 11.x 里它只是记录并发进程数的 PID 文件，
  删除它对 429 恢复无效（过去的「改善」是时间巧合）。

## 真正的根因

1. **请求速率过高**：`user-config.py` 曾 `minthrottle = 0` / `put_throttle = 0`，
   零间隔打 Fandom，被 Cloudflare 行为识别判为 bot。
2. **`retry_after` 无上限**：Cloudflare 429 响应带巨大的 `Retry-After`（实测 1500s+，越罚越重），
   pywikibot `Throttle.get_delay()` 无条件睡满它（`maxthrottle` 管不住，
   `retry_after` 在 `min(delay, maxdelay)` 之外）。
3. **死亡螺旋**：429 → 睡 25 分钟 → 全速恢复 → 立即再 429 → …

## pywikibot 11.x 内部机制（读 installed 源码，别凭记忆推测）

- `throttle.py` `Throttle.get_delay()` = `max(mindelay, retry_after, min(delay, maxdelay))`：
  `retry_after` 在 `min(delay, maxdelay)` 钳制**之外**，所以 `maxthrottle` 管不住它。
- `comms/http.py` `request()` 对**每个**响应执行
  `site.throttle.retry_after = int(response.headers.get('retry-after', 0))`——
  429 把它设成巨值，下一个成功响应（无此头）重置为 0：进程内自愈，不落盘。
- 日志里有两层独立的等待，别混淆：
  - `Waiting X seconds before retrying` = API 重试层（`retry_wait`→`retry_max` 倍增）；
  - `Sleeping for N seconds` = throttle 层在执行 `Retry-After`（实测 1542s → 2980s → 3594s 递增）。
- **惩罚窗口**：429 风暴刚过，全新进程（`retry_after=0`、无 throttle.ctrl）首发请求也会
  立即吃 429（实测 `Retry-After: 474`）——Cloudflare 按请求模式/IP 维持短期滚动惩罚，
  与客户端状态无关。测试修复时别把首发 429 当成「修复失败」，等窗口过去或用已证安全的速率测。
  **2026-08-13 修正**：窗口并非必须睡满 Retry-After——当天首个 429 带 `Retry-After: 3600`，
  彻底停手后 ~10-15 分钟即解除（curl / python requests / pywikibot 本体三种客户端同 UA 实测全 200）。
  8-10 观测到的「窗口期内新进程也 429」很可能是停手期间持续探测在续罚。
  **处罚记忆跨天保留**：距上次事故 3 天后，当天首个 429 直接给阶梯中段值 3600（非初犯小值）。
- pywikibot 11.x 默认值（`config.py`）：`minthrottle=0.1`、`put_throttle=10`、`maxthrottle=60`、
  `maxlag=5`、`max_retries=15`、`retry_wait=5`、`retry_max=120`。

## 诊断流程

1. 排除 UA 封禁：用 curl 分别带 pywikibot UA / 浏览器 UA / curl UA 打 api.php，全 200 则是行为限流。
2. 归因先查自己：把 `user-config.py` 与 `pywikibot/config.py` 默认值做 diff——
   用户自定义值是首要嫌疑；过时的模板残留（如 `pickle_protocol=2`，上游已改 5）会静默覆盖新默认值，删掉。
3. 用裸 requests +  pacing 实测 tolerated rate，再下定论。

## 实测耐受速率（rezero.fandom.com）

**注意**：本节所有零 429 验证都是**短时孤立负载**（≤3000 请求/14 分钟，或批量读
565 次请求/28228 页），从未覆盖「常驻循环数小时持续打站」场景——后者已于 2026-08-13
被证伪（见下节），0.25/2 配置只对短时任务安全。

- 读：50 页一批的 `prop=revisions` GET，间隔 ~0.5–1s → 28228 页零 429（2026-07）。
- 写：间隔 ~5s，BotPassword 登录会话 → 293 次编辑零 429（2026-07）。
- UA 无关：pywikibot UA / 浏览器 UA / curl UA 对照测试全 200。
- 事故前配置 `minthrottle=0, put_throttle=0`：~7-8 req/s 读，约 4500 次请求 / 10 分钟后触发 429。
- 复测（2026-07，探测脚本 `scripts/probe_read_rate.py` / `probe_write_rate.py`）：
  - 读：`list=allpages` GET，间隔 0.35s / 0.25s / 0.20s 各 300 请求（~3.8 req/s 持续 4.5 分钟）→ 零 429。
  - 写：沙盒连续小编辑，间隔 2s×10 + 1s×10 → 零 429（样本小，故配置取 2s 而非 1s）。
- 边界探测（2026-07，`scripts/probe_read_boundary.py` / `probe_write_boundary.py`）：
  - 读：间隔 0.15s → 0.10s → 0.05s → 0.02s → **全速** 逐级加压，共 3000 请求 / 14 分钟
    → **零 429**。单连接被 RTT（~0.26s）锁死在 ~3.8 req/s，根本达不到 Cloudflare 触发点。
    推论：`minthrottle ≤ 0.25` 后继续调低**不会再变快**（周期 = max(minthrottle, RTT)），
    该值只剩「RTT 变好时的安全天花板」作用。
  - 写：0.5s×20 + 0.25s×20 通过后，全速档在第 40+ 次编辑被拦——但不是 Cloudflare 429，
    是 **MediaWiki 自身编辑限速**（见下节）。

## 2026-08-13 事件：常驻循环的多小时累计量触发 429

与既往事故的「瞬时速率超标」不同，本次触发时一切合规：

- 配置未变（0.25/2），无并发进程，被拦的 fixing_redirects 轮次**纯读零编辑**，
  逐分钟统计速率恒定 ~2.7 req/s（低于 7 月实测耐受的 3.8 req/s 全速），无尖峰。
- 负载形态才是关键：main.py 常驻循环**周期间零休眠**，一轮 ~2h50m（09:03→11:53），
  其中 fixing_redirects 单轮扫 6 个命名空间全部页面，跑 **~90 分钟 ≈ 1.5 万请求**
  （占全天请求量 >95%；24/7 即 ~8.5 轮/天 ≈ 13 万请求/天的持续负载）。
  当天经 commands.log 核实为 2 轮：第 1 轮 09:03 完整跑完（fixing 09:55→11:25），
  第 2 轮 11:53 起，fixing 12:39 启动仅 ~22 分钟、2221 次请求即于 13:02:00 吃首个 429。
  全天累计 ~1.8 万次请求。
- 结论：0.25/2 的「安全」只对短时任务成立；数小时持续循环的累计请求量
  （叠加 8-10 事故留下的跨天处罚记忆）足以触发 429。Cloudflare 具体配额窗口
  从外部不可实证，但「常驻循环按现配置无限打」已证伪。
- 解除方式验证：彻底停手 ~10-15 分钟后三种客户端（curl/python requests/pywikibot
  本体，同 UA 同 TLS 指纹）实测全 200——出 429 后**整个循环停十几分钟**即可，
  不需要睡满 Retry-After。

## MediaWiki ratelimits（写操作的第二道限流，与 Cloudflare 无关）

`userinfo?uiprop=ratelimits` 实测（2026-07）。IchiSanNi 同时属 user/bot/sysop 组，
MediaWiki 对**所有适用组**的窗口分别计数、任一超限即拒绝（报 `ratelimited` API 错误，
非 HTTP 429；pywikibot 会自动退避重试，但浪费请求）：

| 动作 | 适用窗口 | 生效上限 | 安全间隔 |
|---|---|---|---|
| edit | user 40/60s，bot 80/60s | **40 次/分** | ≥1.5s，配置取 2s |
| move | bot 80/60s，sysop 20/60s | **20 次/分** | ≥3s（put_throttle=2 大批量移动必撞重试，属预期） |

旧事故时把 bot 打慢的除了 Cloudflare 429，可能也混有这道 ratelimited 重试。

## `-async` 任务的并发分析（interwiki / cosmetic_changes）

结论：**`-async` 不产生不受控的并发**，当前配置下安全。机制与实测：

- `-async` = `page.save(asynchronous=True)` → 请求进 `page_put_queue`，
  由**单个**后台守护线程（`_putthread`，`pywikibot.async_manager`）串行取出执行。
  不是多线程并发写，写仍然排队逐个发。
- 后台保存走的还是同一个 `site.throttle`（线程安全），`put_throttle=2` 照常生效。
- 唯一真并发现象：throttle 读写锁分离，写只等 `last_write`（不等读），
  所以一次写可以紧跟在读之后发出。最坏合计 ≈ 读 3.8 + 写 0.5 ≈ **4.3 req/s**，
  仍远低于事故线 7-8 req/s。
- interwiki 跨 12 个语言站：每个 `Site` 有**独立** Throttle，`minthrottle` 不跨站协调；
  但 interwiki 没有读线程（无 Thread 调用），跨站查询是单线程顺序的，
  合计速率仍被 RTT 锁死在 ~3.8 req/s。`-async` 只影响保存。
- 实证（`scripts/probe_async_concurrency.py`）：主线程全速预载 2000 页 +
  80 次异步沙盒写并发交叠，结束 `retry_after=0`，零 429。
- 推论：旧事故的 ~7-8 req/s 很可能就是 `minthrottle=0, put_throttle=0` 时代
  `-async` 让读、写两条线同时无限制发请求的叠加产物。

## 对策：配置限速（唯一治理方式）

`user-config.py`：

```python
minthrottle = 0.25  # 读间隔 ≥0.25s（实测 0.2s 零 429，留余量）
put_throttle = 2    # 写间隔 ≥2s（实测 1s 零 429，样本小留余量）
maxthrottle = 60    # 常规延迟硬顶（管不住 retry_after，见上）
```

实测规模：2900+ 次读（translation 干跑 85s）、2600+ 次读（cosmetic_changes 全命名空间 145s）
+ 沙盒写，**零 429**（1/5 配置下）；0.25/2 配置的探测数据见上节。

**明确不给 fork 打 `retry_after` 钳制补丁**（`throttle.py` 里 `min(retry_after, maxthrottle)`）：
为保持 fork 干净、方便合并上游，治理靠「不触发 429」而非「触发后睡短一点」。
曾误判为 throttle.ctrl 持久化惩罚，已证伪（见上）。

## 什么时候绕开 pywikibot

配置限速生效后**默认都走 pywikibot**（含 `site.simple_request` 调裸 API），
裸 `requests` 只是最后的逃生舱：

| 场景 | 用法 |
|---|---|
| pywikibot 任务、批量扫描、批量编辑、交互式探索 | 一律 pywikibot（配置限速已实测零 429） |
| pywikibot 未封装的功能 | `site.simple_request`（复用已认证会话与限速） |
| 仅当 pywikibot 本身故障，或脚本无法加载仓库 `user-config.py`（在仓库外跑、无配置限速保护） | 才裸 `requests`，且写间隔 ≥0.5s |

裸 `requests` 的 BotPassword 登录完整流程见 `scripts/verify_wiki_access.py`；
**login POST 也必须走带 429 退避的重试封装**，不能裸发。

## 验证

`scripts/test_pwb_throttle.py`：100 次读 + 1 次沙盒写走 pywikibot，验证配置下零 429，
并断言 `Throttle.get_delay()` 反映配置值。期望输出 `ALL CHECKS PASSED`。
