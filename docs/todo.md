# 待办与待决策项

跨任务的待办与决策记录。单个领域（模板/Module）的领域知识归 `templates.md` / `modules.md`。
已完成的待办若不再需要相关信息就直接删除，不留完成记录（有长期价值的知识并入对应领域文档；执行历史查 git）。

## 待处理

### jobs 性能与数据源审计（2026-08-13，随 re0_fixing_redirects 换装所做）

换装后单轮请求估算 ~7-9k（原 ~17k+）。剩余按优先级：

**性能（请求放大）**（耗时为 2026-08-13 第 1 轮 170 分钟实测，commands.log 逐任务计时）

- [ ] **transferbot 15.8 min（9.3%）、~2500-4000 请求/轮**：全 en 主空间逐页迭代 + 逐页 `targetpage.exists()` 单独查询。修法：en/zh 标题集合各 500/批拉取（~30 请求）内存比对，只搬运缺失页。中工程——须保留 fork 补丁行为（页首 {{Init}}{{To do}} + 来源链接 + [[Category:新搬运待整理]]）。
- [ ] **re0_redirect 18.3 min（10.7%）、~2000 请求/轮**：逐页 `Page(词干).exists()` 单独查询，且 `Re:...` 等带冒号标题大量误中词干正则。修法：收集全部候选词干后 prop=info 50/批批量查存在性（~50 请求）。小工程。
- [ ] **replace fix ×11 合计 ~4.5 min（2.6%）、≈ 600 请求/轮**：replace.py 支持单次多 `-fix`（`fixes_set.append`），同 generator 的 fix 可合并为一次全扫，省 ~500。注意：各 fix generator 不同（base/more/`-catr:图库`），合并后取并集会扩大部分 fix 的扫描面；摘要与故障隔离粒度也会变——需裁决。
- interwiki 5.5 min ~1000/轮：跨站查询结构使然，无放大。
- touch 4.4 min 678/轮：设计内（缓存刷新），不动。
- noreferences 18.6 min（10.9%）是 **CPU 密集**（预载已批量，~52 请求），不占 API 预算，429 视角无需处理；fixing/redirect/transferbot 修完后它将占循环时长 ~40%，届时若要压墙钟时间再做纯 CPU 优化。

**数据源（派生表遗漏风险，参照「信息框参数链接不进 links 表」机理）**

- [x] **re0_gallery**：`iterlanglinks` 走 langlinks 派生表（2026-08-08 脏数据实锤）→ 可能漏同步/错配 en 图库。**已修（2026-08-13）**：改从源码扫 `[[en:...]]`（`find_en_title`，单测覆盖内联冒号链接/空目标特例），「摘链退出同步」语义不变。
- category remove ×2 / template replace：依赖 categorylinks/templatelinks——#invoke 参数内的分类/调用不登记，但本站信息框参数不含分类、被替换模板均顶层调用，**风险低，暂不处理**。
- redirect-do/br：redirect 表抽查与现实一致（pageid 8004 等），**风险低**。
- interwiki（textlib 源码解析语言链接）/ replace 各 fix / re0_move（标题匹配）/ noreferences（源码）：均无派生表依赖。

### 鼠色猫语录迁移质量修复（2026-08-09 审计发现）

**执行计划已独立成文：`docs/quotes-migration.md`**（范围决策、数据源、阶段划分、验收标准；2026-08-09 用户拍板全量入库 + LLM 补译）。以下保留审计发现备查。

存档页（`Category:存档`，31 页）→ `Module:鼠色猫语录` 数据子表的旧迁移质量差。审计：logs/dump_archive_audit.py 抓全量 → logs/analyze_archive_coverage.py 两边去 wikitext/Lua 标记 + NFKC/繁简归一化逐句比对，缺失明细 logs/archive_audit/misses.txt，逐条人工复核完成。结论：20 个问答存档页正文已覆盖。**P1 无损小修已完成（2026-08-09，脚本 logs/p1_apply.py）**：佩特拉/弗雷德莉卡重复键 bug 拆分修复、8 处多行答案截断补全、罗兹瓦尔/莱茵哈鲁特零散补录、奥托 2017 节 9 组 QA 补录、签名会日文孤本 159 行已入 js 字段；复跑审计缺失项仅剩 boilerplate/译者注/措辞差异。

**不要全量重迁**：反向覆盖（模块中文句 → 存档页，logs/reverse_coverage.py）96.6% 命中，但 菲莉丝（46% 未命中）/安娜塔西亚 等表含存档页之外的扩充内容（其他来源 QA、jq/ja 字段），全量重迁会丢这些数据。走增量补齐，全部补完才可讨论删除存档页。

- [x] **A. 动画实况解说 4 页整体未迁移**（最大头，~87KB；即计划 P2）——**2026-08-10 完成**：64 集全量对齐补译，3 子表上线（旧版 1419 / 新编 702 / 第二季 1011，条目与推文一一对应），含存档整缺的旧版 2-6 集与 09-26 完结杂谈场
- [x] **早期ask 全量迁移（计划 P3）——2026-08-12 完成**：639 节选 → 2764 条全量（614 存档译文对齐 + 1955 K3 补译 + 170 docx 主页存档独有 + 25 孤儿）；拆两子表（渲染超 post-expand 墙）；细节见 quotes-migration.md P3 行

备注：帕克/问答、福尔图娜/问答、Web连载网站上评论 三个存档页本身无正文（仅来源链接），对应空占位表无可迁移内容；存档页的原推/译者署名等信息部分已入模块 `abbr` 注解。

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

### probe_* 五个探测脚本不合并且保留样板重复

`docs/cloudflare-429.md` 按文件名逐一引用这些脚本作为实证出处（哪个脚本跑出哪组数据），
合并会破坏可追溯性；它们是一次性研究脚本而非维护中的工具，重复的样板没有维护成本。
