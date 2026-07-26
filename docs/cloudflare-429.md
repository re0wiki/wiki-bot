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

## 对策：配置限速（唯一治理方式）

`user-config.py`：

```python
minthrottle = 1    # 读间隔 ≥1s
put_throttle = 5   # 写间隔 ≥5s
maxthrottle = 60   # 常规延迟硬顶（管不住 retry_after，见上）
```

实测规模：2900+ 次读（translation 干跑 85s）、2600+ 次读（cosmetic_changes 全命名空间 145s）
+ 沙盒写，**零 429**。

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
