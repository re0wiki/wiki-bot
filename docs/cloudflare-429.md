# Cloudflare 429（Fandom 限流）根因与对策

Fandom 前端接 Cloudflare，按 **TLS 指纹 + 请求速率**限流。本文是实测根因记录；
限速配置的日常结论见 `docs/wiki-access.md`「实测结论与坑」节。

## 已证伪的假设

- **User-Agent 不是诱因**：同一 IP 下 `curl` 带 `Pywikibot/...` UA 得 200，pywikibot 得 429。
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
- pywikibot 11.x 默认值（`config.py`）：`minthrottle=0.1`、`put_throttle=10`、`maxthrottle=60`、
  `maxlag=5`、`max_retries=15`、`retry_wait=5`、`retry_max=120`。

## 诊断流程

1. 排除 UA 封禁：用 curl 分别带 pywikibot UA / 浏览器 UA / curl UA 打 api.php，全 200 则是行为限流。
2. 归因先查自己：把 `user-config.py` 与 `pywikibot/config.py` 默认值做 diff——
   用户自定义值是首要嫌疑；过时的模板残留（如 `pickle_protocol=2`，上游已改 5）会静默覆盖新默认值，删掉。
3. 用裸 requests +  pacing 实测 tolerated rate，再下定论。

## 实测耐受速率（rezero.fandom.com）

- 读：50 页一批的 `prop=revisions` GET，间隔 ~0.5–1s → 28228 页零 429（2026-07）。
- 写：间隔 ~5s，BotPassword 登录会话 → 293 次编辑零 429（2026-07）。
- UA 无关：pywikibot UA / 浏览器 UA / curl UA 对照测试全 200。
- 事故前配置 `minthrottle=0, put_throttle=0`：~7-8 req/s 读，约 4500 次请求 / 10 分钟后触发 429。
- 复测（2026-07，探测脚本 `scripts/probe_read_rate.py` / `probe_write_rate.py`）：
  - 读：`list=allpages` GET，间隔 0.35s / 0.25s / 0.20s 各 300 请求（~3.8 req/s 持续 4.5 分钟）→ 零 429。
  - 写：沙盒连续小编辑，间隔 2s×10 + 1s×10 → 零 429（样本小，故配置取 2s 而非 1s）。
- 边界未探明：0.2s 到 7-8 req/s（事故速率）之间没测，越靠近事故速率惩罚风险越大，不建议再往上探。

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
