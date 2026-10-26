---
name: nekoquote-incremental
description: "Use when 维护 NekoQuote 语录同步（月表/增量收录/排查回潮）。Runbook 与故障处理。"
version: 1.0.0
---

# NekoQuote 增量收录 Runbook

**主通道：循环任务 `nekoquote`（`src/scripts/re0_nekoquote.py`）全自动同步**——FxTwitter v2 拉取长月原创（含 Note Tweet 长文，RT 剥除），复用 `src/nekoquote/` 包的采集器与管线，随 main.py 循环执行、无需人工或 Discord token。`.cache/nekoquote/sync_state.json` 记录 `source` 与 `last_original_id`，全链成功才推进；FBK 旧 `last_id` 状态首次迁移时回扫至 2026-08-18，补收其漏转内容。以下手动导出流程保留为备份/排障手段（EN 与中文频道同为 FBK 转发，**不互为独立兜底**；FBK/nitter 是共同单点）。

长月新推的手动备份流程（2026-08-15 定稿）走英文社区 Discord 转发频道的**定期手动导出 + 一键管线**。直连采集与备用来源见下节；wayback CDX 被动滞后，只作补漏。

## 直连采集与备用来源

- **FxTwitter API v2（自动主通道）**（[文档](https://docs.fxembed.com/api/introduction)、[OpenAPI](https://api.fxtwitter.com/2/openapi.json)）：无密钥，采集器为 `src/nekoquote/fxtwitter.py`。时间线混有转推、同页时间序不严格且可能重复，按 id 去重、按 `author.screen_name` / `reposted_by` 过滤；`count=100` 实测仍每页 20，必须按 `cursor.bottom` 翻页。每轮从最新页扫到上次全链成功的 `last_original_id` 所在页，处理完该页后停止；FBK 旧状态首轮改用 `stop_before=2026-08-18`，全新 wiki 基线以全时间线数值最大的原创 id 播种、不收录存量（当次实测 164 页）。`since` 只对不带游标的请求生效，后续游标页会回到未过滤时间线，生产不依赖它；无界扫描遇 204/空页正常结束，有界扫描若 204、空页或游标耗尽仍未抵达边界则非零且不推进，游标重复、HTTP/API 错误同样非零。长文 `is_note_tweet=true` 时 `text` 仍含完整全文；公共实例无 SLA。2026-10-26 隔离数据真实干跑：首轮 90 页补出 3 篇长文，第二轮 5 页命中边界且零新增。`/2/search` 当次 `from:` 查询返回 404，不用于发现。
- **teapaw HTML**（`https://teapaw.org/nezumiironyanko?filter=posts`）：首页 20 条原创即含 10-12 两篇与 10-18 一篇长文；`.timeline-item` 可关联状态 id，`.tweet-content` 含长文全文与结尾，可作免费补漏/对账来源。RSS 与 HTML 覆盖不同，当次 RSS（含 `?filter=posts` 变体）不含这三条，不能以 RSS 覆盖推断原创停更。HTML 不是稳定接口，结构变化须响亮失败。
- **X 官方 API**（[用户时间线](https://docs.x.com/x-api/users/get-posts)、[定价](https://docs.x.com/x-api/getting-started/pricing)）：文档支持 `since_id`、游标分页、排除转推及长文全文字段；现行按量付费无订阅，Posts Read 为 **$0.005/返回条数**。需开发者账号与 credits，本仓库尚未做凭据实测。
- **ReZeroDB 作者推存档**（[入口](https://rezerodb.com/series_meta/author_tweets)）：作品向筛选友好，但页面自述每三个月更新，只宜低频对账/补漏，不宜承担及时同步。

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
.venv/Scripts/python.exe -m src.nekoquote.merge <导出目录>
```

一键完成：解析（content/embeds/递归组件三路全扫、双布局兼容、RT 剥除）→ 新推入 `.cache/nekoquote/tweets.json` → K3.1 Pro 翻译（断点续跑；译名表 ja 面形态确定性检出 → prompt 注入译名对照）→ 构建月表 → round-trip 校验 → 增量部署 → 更新 `lua_live` 快照。pending（已删推清单）命中自动划账。

自动与手动入库都会先写全链恢复标记 `.cache/nekoquote/chain_pending.json`，只有全链成功才清除。任一阶段失败后，下轮即使「库外新推 0」也会续跑，不会提前推进同步边界。共享缓存的读改写、全链和状态提交由 `state.lock` 串行化，JSON 以同目录临时文件原子替换。

**幂等**：同一份导出可反复跑，已入库 id 自动跳过（「库外新推 0」即无新增）。

建议频率：每月一次，或明知有新内容（生日问答场次、动画播出期）时。

**动画播出期追加步骤（实况集数标记）**：管线本身不带集数标记。新集播出后——① en 站对应 `Episode N` 页补了 Air Date 后重跑 `src/nekoquote/epcalendar.py`（`python -m src.nekoquote.epcalendar`）（覆盖 51-90 集，更新 `.cache/nekoquote/ep_calendar.json`）；② 重跑 `src/nekoquote/epmarks.py`（`python -m src.nekoquote.epmarks`） 再生成 `.cache/nekoquote/ep_marks.json`（规则：#rezeroneko ∧ 播出窗口；映射文件由构建器 merge 期落地）；③ 照常构建部署；④ 新建对应 `动画:第n集/猫语`（格式 `{{Init}}\n{{Q|S4第n集}}`），季页无需动。

## 故障处理

- **wiki 侧改月表后必须回写源数据**：月表条目构建期只读本地数据（lua_base 零变换重放、zh.json/tweets.json 经 merge_raw 重新生成），只在 wiki 上改（如 `{{Seirei or Elf}}` 复核消歧、fix:translation 命中 jt 字段）不落回本地，下轮增量同步重建即回潮（2026-08-23 实证：08-20 的复核消歧只改了 wiki，增量同步把 `{{Seirei}}` 回潮成 `{{Seirei or Elf}}`、jt 里的 `{{Yousei}}` 回潮成原文）。改完跑 `uv run python -m src.nekoquote.pull_wiki`——lua_base 月份整文件刷新（其条目是 P8 时代管线生成的，加工逻辑与 raw_tweet_entry 不同，不做逐字段比对），其余月份逐字段回写 zh.json（t/q）与 tweets.json（jt/jq）。wiki 侧 t/q 清空或删除会删除本地译文键并写 `zh_deleted`/`qzh_deleted` 抑制标记，translate 跳过这些字段；wiki 补回非空 t/q 时可新建本地记录并解除对应抑制。raw 条目消失会响亮报错并阻止盲目重建；回写后完整重建月表，只有线上与生成结果逐月一致才把接受的线上版本刷新到 `lua_live`，否则保留旧部署基线并非零退出。
- **部署遇到线上漂移会中止**：部署逐月比较线上现文、`lua_live` 与新构建，比较时忽略 MediaWiki 文件尾换行差异；线上不同于上次部署快照时不覆盖未知版本，线上页面已存在但无基线同样停机。先只读核对差异，再按需运行 `pull_wiki` 合并；线上已等于新构建时不重写月表，但仍幂等检查 `/doc`，使上次 `/doc` 失败的部署可续跑。既有页保存绑定已读 revid，新页使用 create-only，任何保存冲突均中止。
- **模型截断不等于翻译成功**：任何 `finish_reason=length` 都不入库；可拆批次自动二分，单条仍截断则非零终止。不要用已有部分 content 冒充完整译文。
- **本地基线只认完整发布**：bootstrap 在临时目录抓完所有月表后成对发布 `lua_base`/`lua_live`，发布期间保留旧版本备份，目录或完成标记任一步失败都回滚；`lua_base.complete` 只在两张目录均发布成功后写入。异常退出留下的备份由下次 bootstrap 先恢复或清理；`run_chain` 在完成标记缺失时拒绝启动，先运行 `uv run python -m src.nekoquote.bootstrap`。
- **Kimi content_filter 误伤**（"high risk" 400）：管线已自动二分隔离并跳过该条，跑完后查 `.cache/nekoquote/zh_blocked.json`；用其他模型（Gemini）译出后，把译文写进 `.cache/nekoquote/zh.json` 对应 tid 的 `zh` 字段再重跑构建+部署。**日文原文若触发过滤，不要让它进 LLM 上下文**（有先例）。
- **译名保障 = 注入而非后处理**：翻译期把推文中出现的译名表实体（ja 面形态确定性检出，歧义面不注入）以「ja = zh」对照注入 prompt；译文即终稿，不对 zh.json 跑规则归一（归一打在源数据上的误伤不可逆）。修正译文译名需同时改 zh.json 与 wiki 月表。
- **FBK 时期的「无库外新推」不等于长月没发原创（长文漏转）**：2026-10-26 对照 X 原创时间线与本地库，确认 `2109591572061020504`、`2109607854743400823`（10-12）和 `2111733988796899816`（10-18）三条 `#リゼロ小話` 长文漏收；回查中文 FBK 频道同时段 400 条消息也无这三个 id，普通短推与转推仍持续到达。当时任务正常报「无库外新推」只代表 FBK 没供稿；手动 Discord 备份排查停更时仍须对照 [X 原创时间线](https://x.com/nezumiironyanko?filter=posts)（可用 teapaw 镜像辅助读取），重跑 FBK 同步或改走 EN 频道都无法补回未转发消息。
- **导出缺最近内容**：先怀疑解析覆盖——正文可能在新版组件里（递归 walk）或与头部同组件链接之后；`src/nekoquote/parse.py` 的注释有三种格式的完整判例。
- **部署后 wiki 上没变化**：查 `.cache/nekoquote/lua_live` 快照是否滞后（每次部署后必须同步，deploy 链已自动做）。

## 数据流备查

```
FxTwitter v2（自动主通道） → re0_nekoquote.py（fxtwitter 采集） ─┐
EN Discord 导出（Discrub JSON，手动备份） → merge.py（parse 解析） ─┴→ 新推入 tweets.json
  → chain.py 链：translate.py（K3.1 Pro 补译 → zh.json）→ build.py（lua_base + raw 合流 → lua/）
    → verify_rt.py（既有条目零缺失校验，失败非零并阻断部署）→ deploy.py（增量部署，vs lua_live）
```

译文在 `zh.json` 逐条记录 `provider`/`model`，构建按记录署名；正文译文缺失署名元数据时构建报错。
