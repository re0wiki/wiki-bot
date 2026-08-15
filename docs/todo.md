# 待办与待决策项

跨任务的待办与决策记录。单个领域（模板/Module）的领域知识归 `templates.md` / `modules.md`。
已完成的待办若不再需要相关信息就直接删除，不留完成记录（有长期价值的知识并入对应领域文档；执行历史查 git）。

## 待处理

### 鼠色猫语录迁移（P0–P7 已全部完成，2026-08-09 ~ 08-15）

**执行计划与全程记录：`docs/quotes-migration.md`**（含 P8 全量推文时间线）。存档页 31 页已于 P7 删除、`存档:` 前缀退役；语录库现为 `Module:NekoQuote` 月表架构（12,833 条 / 162 张有内容月表）。

**仍开着的待办**：

- [ ] **LLM 内容级去重**（P8 衍生）：既有条目未链推 id 但内容与 raw 推重复的（罗兹瓦尔表 ask 抄录那类）
- [ ] **2026+ 新推持续收录（已定方案：手动导出 + 一键管线）**：自动抓取通道全不可靠（fx 无时间线枚举、CDX 被动滞后、nitter 半死），2026-08-15 用户拍板走 EN Discord 转发频道定期手动导出。流程：DiscordChatExporter 导出频道（json 放一目录）→ `PYTHONPATH= .venv/Scripts/python.exe logs/p8_discord_merge.py <目录>` 一键完成解析→入库→翻译→归一→构建→校验→部署（幂等，可反复跑同一份导出）。建议频率：每月或有新内容时
- [ ] **S3 实况解说回收（零の幻影 bilibili 专栏）**：长月 S3 实况推已删（播后删是惯例）。wiki Discord 转发频道已导出 3,663 条（2024-10~2025-10，533 条已删推回填 ✅）；频道外缺口走零の幻影 B 站专栏日译中爬取（2026-08-15 用户定暂不执行）
- [ ] **P8 已删推缺口（核销，不再投入）**：fxtwitter + 官方 oembed 双通道 404 实证作者删除；wayback/archive.today 无正文；Discord 回填后余 ~1,490 条。留档 `logs/p8_wb_pending.txt` + `~/p8_pending_tweets.md` + `logs/p8_discord.json`

**来源存活审计（2026-08-09，logs/check_source_liveness.py + check_wayback.py，结果 logs/archive_audit/source_status.json / wayback_status.json）**：

- **原推 56/56 全部存活**（fxtwitter API 逐条验证、正文可机读）——生日问答类一手重核可行。注意存档页链的多是「接受提问的预告推」，问答本体是作者后续的引用回答推，重核时需按时间线抓全（fxtwitter 单条接口不含 thread）
- **英肉 reddit 6 帖（去重）**：本机被反爬 403 无法直连验证，但 6/6 均有 Wayback 快照（79qvoo 经时间戳重定向确认）——内容可经 Wayback 取回
- **ask.fm/nezumiironyanko/best**（早期ask 一手出处）：直连 SSL 失败，Wayback 2016-08 快照含日文 QA 正文——但只有单页快照，ask 分页的完整覆盖未知
- **签名会一手 privatter：已失效且无 Wayback 快照**——wiki 存档里的日文 Collapse 原文已成孤本，补齐 js 字段（上方 B 项）优先级因此提高
- **Nico 生放送**：nicovideo 直播页存活（内容不可回放）；naver 韩文 blog（第二版来源）直连存活但无 Wayback 快照；星空宅梦 tieba 记录帖 403 未知
- **tieba 译文帖 29 个**：本机直连 403 反爬 + Wayback 基本无快照（仅 1/29 有）；**browser 工具 2026-08-09 实测可读**（p/4621079261、p/6423124322 全文+回复完整；偶发「百度安全验证」由用户手动清除后重试）——但百度有吞帖/吞回复史，即使帖在回复也可能不全；它们只是译文发布帖，一手出处是推特，优先级低
- ~~**资源汇总讨论帖**~~（/f/p/4400000000000025340，动画实况解说与早期ask 标注的「原文存档」）：**2026-08-09 用户已人工查看，无需再抓**——有用内容即 `C:\Users\ccxxx\Desktop\长月qa原档备份` 那批文件 + reddit `r/Re_Zero/wiki/translation` 英译索引（后者 Wayback 快照在 logs/archive_audit/reddit_translation_index.html）
- 巴哈姆特第22集译文帖 502 且无快照（S1/巴哈姆特其余只是译者署名链接，不影响考证）；pastebin 奥托2018英肉存活

**原档备份与英文索引（2026-08-09 用户提供）**：`C:\Users\ccxxx\Desktop\长月qa原档备份`（资源汇总帖的存档内容；归档副本在同日由用户手动放至 OneDrive `文档\杂项\re0\长月qa原档备份`——re0-corpus 与 wiki 均不适合 xlsx，归宿已定）+ reddit `r/Re_Zero/wiki/translation` 英译索引（本机被反爬，Wayback 快照可用，logs/archive_audit/reddit_translation_index.html）。

- `动画推特解说【全】rezeroneko.xlsx`：#rezeroneko 推文全量抓取（twint 格式：id/日期/正文/链接），3044 推、79 天、2016-04~2021-03，覆盖旧版/新编/OVA/第二季全跨度。**量化出的搬运遗漏**：旧版 2-6 集推文全在 xlsx（~334 推）而存档页整缺（存档自注「1-6已找不到」）；且各集译文均为选译（推数约为 bullet 数 2-3 倍，如 新编第1集 81 推→19 条）
- `askfm 1.xlsx`：ask.fm QA 2571 条（2014-05~2015-10，清洗版含联动推链接）——模块早期ask 只有 639 条（存档自注「译者个人口味节选」）；`askfm备用.docx` 是同时段主页原始 dump（~14000 段，格式乱），`askfm 2xlsx.txt` 为 Q:/A: 纯文本
- `Web连载网站上评论narou.xlsx`：なろう评论+作者回复 560 行——对应空存档页/空占位表，**是全新内容**
- `2022_04_20_十周年问答.mp3`（88MB 录音）：wiki 无对应条目；reddit 索引有英文总结翻译（witchculttranslation.com 2022-08-02 文）
- reddit 英译索引的 Tappei Q&A Posts（全部生日问答 + ask QA 系列 + Niconico QA）与 Thoughts on episodes（S1 13-25 集、新编 3-13 集+OVA、第二季 1-25 集英译）链接齐全——可选用于回填 es/eq/ea 字段

**范围决策点（补全之外的扩项，各自独立）**：① 未翻译推文是否入库（js-only 条目 ~2000 条）还是只迁有中文的部分；② askfm 是否从 639 节选扩到全量；③ narou 评论 560 条是否建条目；④ 十周年问答是否建条目（录音转写 vs 从英文总结转译）；⑤ 是否回填英译字段。其中①影响 A 项工作量（只迁有中文的 ~950 条 vs 全量 3044 推）。

### 角色页日文名/罗马字的边角案例（2026-08-08 全角色审计 D 桶）

主流程已收敛（见 `docs/modules.md` Kana2Romaji 条）。已结案：白羊/黑狗已补 name_ja_kanji + name_ja_romaji；梅里欧·阿嘎玛回退为 zh 更完整的 `メリオ·アガマ`（不动 en）；希洛洛的 en 链接本来就对（早前"红链"判断是 Fandom API GET 缓存旧数据）；菜月菜穗子/菜月贤一的 [[en:...]] 链接其实一直存在（同遭缓存误报）。

~~剩余一项：菜月父母字段语义~~ **2026-08-11 随罗马字全量自动化解案**：字段语义定为 name_ja_kanji 填汉字名 + name_ja_kana 填读音，罗马字不再手动填写（两页已补 kana 并删 romaji，见 `docs/templates.md`）。

## 历史待办存档（ReZero Wiki:施工计划表）

该页原是面向编辑者的待办清单，因待办长期无人认领，2026-04-01 由用户删除（摘要「废除计划，自由编辑」；最后修订 revid 235488）。存档备查，暂不处理：

- 编写：各类短篇（特典SS/月刊CA短篇/短篇集/文库外传）故事梗概；主要角色的「梗概」「关系」子页（当时大部分角色梗概空缺）
- 审核：`Category:待审核` 逐条过审（通过后挂 `Template:Pass`）
- 搬运：贴吧《Re:zeropedia》、贴吧零学帖、Grasijuna 石墨文档整合（链接年代久远，多半已失效）
- 资讯：新闻存档条目建设（参考魔法禁书目录中文维基的新闻存档）
- ~~全角色介绍图~~（依赖 `Module:Character image` 自动列举机制，2026-08-08 随该机制移除彻底失效，见 `docs/templates.md`）
- 维护组待办当时在 Discord/开黑啦（链接已旧）

## 已决策（2026-08-03）

### MediaWiki 命名空间的 JS 页面不为纯规范化改动

每次改动需 Fandom 人工审核，无功能更改就不要动（缘起：`Common.js` 一处繁体注释，决定保留）。

## 已决策（2026-07-31）

### 图片删除/改名不同步（re0_image 只增不删）——维持现状

残留图片基本无害；删除还要同步更新引用，不值得处理。限制已注明在 `calc_diff` docstring。

### `.idea/` 已跟踪文件——维持现状

自带 .gitignore 模板没忽略那些文件所以提交了；项目无其他维护者，交上去至少无害。

### re0_redirect 对未登记前缀建重定向——维持现状

多余重定向无用但无害。

## 已评估、决定不做

### replace fix 合并（2026-08-13）

replace.py 支持单次多 `-fix`，11 个 fix 任务合并可省 ~3.5 min / ~500 请求每轮。
优化收尾时单轮已降至 ~20 min / ~2-3k 请求，收益太小；且各 fix generator 不同
（base/more/`-catr:图库`），合并取并集会扩大扫描面、摘要与故障隔离粒度变粗，
保持现状。

### pywikibot 读路径会话自愈补丁（2026-08-13）

机制可行（API 错误层捕 `toomanyvalues` → 强制重新认证重试一次），但：收益仅 ~10-30 请求/轮（transferbot 26→~10）；每个 fork 补丁都是 rebase 冲突面（参照 retry_after 钳制补丁的拒绝先例）；且若飘忽根因是后端节点会话状态不一致，重登可能落在不同节点使重试仍失败。维持「读路径匿名可达」的确定性设计。

### probe_* 五个探测脚本不合并且保留样板重复

`docs/cloudflare-429.md` 按文件名逐一引用这些脚本作为实证出处（哪个脚本跑出哪组数据），
合并会破坏可追溯性；它们是一次性研究脚本而非维护中的工具，重复的样板没有维护成本。
