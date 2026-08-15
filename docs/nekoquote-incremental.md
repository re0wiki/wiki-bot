# NekoQuote 增量收录 Runbook

长月新推的持续收录流程（2026-08-15 定稿）。自动抓取通道全不可靠（fxtwitter 无时间线枚举、wayback CDX 被动滞后、nitter 半死），走英文社区 Discord 转发频道的**定期手动导出 + 一键管线**。

## 上游：EN Discord 转发频道

频道经 nitter 持续追 `nezumiironyanko`（另有 `Rezero_official` 等）。三个转发账号：
- `Tappei Nagatsuki`——长月专线 webhook（旧式 content 格式，尾部带 `[Link](url)` 行）
- `FBK`——混合 bot（Discord 新版组件布局，content/embeds 全空，正文在组件树里；附机翻段）
- `Re:Zero Official`——官推（不收）

## 导出（Discrub）

用 **Discrub**（浏览器扩展）导出频道全部消息，JSON 格式，分页文件放一个目录（如 `Desktop/tappei_tweets/`）。

> [!WARNING] 不要用 DiscordChatExporter 配用户 token——有已知的封号问题（[issue #1497](https://github.com/Tyrrrz/DiscordChatExporter/issues/1497)，Discord 判平台滥用）。

## 执行

```bash
cd wiki-bot 仓库根
PYTHONPATH= .venv/Scripts/python.exe logs/p8_discord_merge.py <导出目录>
```

一键完成：解析（content/embeds/递归组件三路全扫、双布局兼容、RT 剥除）→ 新推入 `logs/p8_tweets.json` → K3 翻译（断点续跑）→ 译名归一 → 构建月表 → round-trip 校验 → 增量部署 → 更新 `lua_live` 快照。pending（已删推清单）命中自动划账。

**幂等**：同一份导出可反复跑，已入库 id 自动跳过（「库外新推 0」即无新增）。

建议频率：每月一次，或明知有新内容（生日问答场次、动画播出期）时。

## 故障处理

- **Kimi content_filter 误伤**（"high risk" 400）：管线已自动二分隔离并跳过该条，跑完后查 `logs/p8_zh_blocked.json`；用其他模型（Gemini）译出后，把译文写进 `logs/p8_zh.json` 对应 tid 的 `zh` 字段再重跑构建+部署。**日文原文若触发过滤，不要让它进 LLM 上下文**（2026-08-15 先例：原文隔离在 logs/blocked_jp.txt）。
- **导出缺最近内容**：先怀疑解析覆盖——正文可能在新版组件里（递归 walk）或与头部同组件链接之后；`logs/p8_discord_merge.py` 的 extract 注释有三种格式的完整判例。
- **部署后 wiki 上没变化**：查 `logs/p8/lua_live` 快照是否滞后（每次部署后必须同步，deploy 链已自动做）。

## 数据流备查

```
EN Discord 导出（Discrub JSON）
  → p8_discord_merge.py：extract → p8_tweets.json（src=dc_en/dc_en_fbk）
  → p8_translate.py：K3 补译 → p8_zh.json
  → p8_normalize.py：translation fix 规则归一
  → p8_build.py：lua_base + raw 合流 → p8/lua/*.lua
  → p8_verify_rt.py：既有条目零缺失校验
  → p8_deploy3.py：增量部署（vs p8/lua_live）
```
