# 鼠色猫语录全量迁移计划

2026-08-09 定。缘起与审计结论见 `docs/todo.md`「鼠色猫语录迁移质量修复」节；本文档是执行计划，优先级与状态以 todo.md 为准。

## 目标

`Module:鼠色猫语录` 数据子表 = **全量原档（日文）+ 中文（现有译文 + LLM 补译）+ 英文（英译回填）**；
全部完成后删除 `Category:存档` 存档页（删除是最后一步，前置是双向覆盖审计零缺失）。

## 决策记录（2026-08-09 用户拍板）

1. 未翻译内容**全量入库**，缺的中文用 LLM 补译（用户：现在 LLM 翻译质量已经不错）
2. ask 从 639 节选扩到**全量**（askfm 备份 2571 条）
3. narou 评论 560 条**建条目**（`鼠色猫语录/Web连载网站上评论` 空占位启用）
4. 十周年问答：**录音转写 + 英文对照**；能传 wiki 的原始资源尽量传
5. 英译字段（es/eq/ea）**尽量补全**（reddit 英译索引链接齐全）
6. LLM 选型：批量对齐/初翻用 **DeepSeek Flash**（用户提供 API），疑难与抽审用 Kimi K3

## 数据源

| # | 源 | 内容 | 形态 |
|---|---|---|---|
| S1 | wiki 存档页 31 页 | 中文译文（部分含日文/英文） | logs/archive_audit/archives.json 已快照 |
| S2 | `动画推特解说【全】rezeroneko.xlsx` | 实况解说日文推文全量 3044 推/79 天/2016-04~2021-03 | twint 结构化表 |
| S3 | `askfm 1.xlsx` | ask QA 日文全量 2571 条（2014-05~2015-10，含联动推链接） | 结构化表 |
| S3b | `askfm备用.docx` / `askfm 2xlsx.txt` | ask 同时段原始 dump / Q:A 文本 | 交叉验证用 |
| S4 | `Web连载网站上评论narou.xlsx` | なろう评论+作者回复 560 行 | 结构化表 |
| S5 | `2022_04_20_十周年问答.mp3` + witchculttranslation.com 英文总结 | 十周年 Space 问答 | 88MB 音频 + 英译 |
| S6 | reddit r/Re_Zero/wiki/translation | 英译索引（QA 全系列 + 实况 S1 13-25/新编 3-13+OVA/S2 全） | Wayback 快照 logs/archive_audit/reddit_translation_index.html |
| S7 | 原推 56 条 | 生日问答等原推（fxtwitter 可机读；问答 thread 抓取方案待定） | 在线 |
| S8 | 现有模块 27 子表 | 含存档外扩充（菲莉丝 46% 等）——**不可丢弃** | logs/archive_audit/modules.json 已快照 |
| S9 | 签名会日文 Collapse | **孤本**（privatter 已死无快照） | 在 S1 存档页内 |

原档备份目录：`C:\Users\ccxxx\Desktop\长月qa原档备份`（用户本地工作副本，不入 git；归档副本在 OneDrive `文档\杂项\re0\长月qa原档备份`）。

## 技术约束与风险

- **性能约束的实测结论（2026-08-09，4 倍规模模拟）**：Lua 侧远未触限（4x 数据 require+扫描 CPU 仅 0.4s，Scribunto 限 10s）；`frame:preprocess` 贡献仅 ~10% 且**不可去**（无 preprocess 时 `<ref>` 变字面文本、`{{Seirei}}` 等模板不展开）。**真正的硬约束是 MediaWiki post-expand include size 2MB 上限**（与页面源码 2048KB 上限同为 2MiB，对同一数据量级触发）：当前全量输出 1.1MB，4 倍后 ~4.4MB → 输出被整体丢弃（仅剩警告链接）。对策已定（2026-08-09 用户裁决）：`table=` 参数已上线（按名懒加载单表，向后兼容逐字节验证），`/all` 页届时拆为**动态子页**（每页 1-3 次 `query|table=` 调用，各自独立 2MB 预算），不引入 bot 编译层——静态编译不推高容量墙（编译产物同样撞 2048KB 源码限），且语录数据改动不频繁、一次性检查即可，无需常驻巡检。拆分粒度按表/按季等有逻辑的单位（如实况解说按季拆子表），**具体拆法待 P2 测得各表展开大小后定**。当日曾短暂上线静态编译试点（re0_quotes_all + jobs quotes-all + /all 静态化）并已整体撤销
- **Fandom 上传**：允许 mp3 ✓、**xlsx ✗**；文件大小限制待实测（88MB mp3 可能超限，备选 archive.org 托管 + wiki 外链）；xlsx 类原档归宿已定（2026-08-09 用户手动归档至 OneDrive `文档\杂项\re0\长月qa原档备份`，re0-corpus 与 wiki 均不适合 xlsx）
- **译名一致性**：LLM 翻译**不注入译名表**（2026-08-09 用户裁决：生成时不注入，入库后对相关 Module 子表手动跑一遍 translation 替换收尾即可）；`fix:translation` 的 generator 不覆盖 Module 命名空间是**有意为之**（动 Lua 代码风险大），手动替换时需显式指定目标子表
- **对齐留痕**：zh↔ja 对齐（实况 66 集、ask 639 条）全部产出映射表存 logs/，按比例人工抽查，不许静默通过
- 入库统一简体；模块字段值是 wikitext（`:wikitext()` 渲染），`{{Seirei}}` 等模板可用，字面 `}}` 是 bug 要杜绝（旧迁移教训）
- reddit 等被反爬源：用户已连接本地浏览器可实时抓取；Wayback 快照偏旧作兜底（快照已验证可用）。tieba 译文帖经 browser 工具实测可读（2026-08-09：p/4621079261、p/6423124322 全文+回复完整；偶发「百度安全验证」由用户手动清除后重试；p/4731166958 首访撞验证，真实状态待复查）——但百度有吞帖/吞回复史，优先级低

## 阶段计划

| 阶段 | 内容 | 产出 | 估时 | 依赖 |
|---|---|---|---|---|
| **P0 基础设施与试点** | LLM 接入脚本（OpenCode Zen 端点 + 429 退避）；Lua 生成器骨架（wikitext 转义、引号/花括号校验）；性能分解实测与架构方案（**主模块等价重写 + table= 参数已完成** 2026-08-09，见 modules.md；/all 拆动态子页的具体分法待 P2 测各表大小后定）；**用 OVA（17 条）走通全流程**：xlsx→对齐→补译→生成→上传→渲染验证 | 管线脚本 + OVA 上线 | 1 会话 | OpenCode key（已实测可用） |
| **P1 无损小修** ✅ 2026-08-09 完成 | F（重复键 ×2）、C（截断 8 处）、E（零散 2 条）、D（奥托 2017 9 组）、B（签名会 js 孤本 159 行）——已上线并通过复跑审计与渲染抽查（logs/p1_apply.py） | 直接修模块 | 实际 0.5 会话 | 无 |
| **P2 动画实况解说** | xlsx 按日期→集数映射（注意 2016 深夜档次日偏移）；66 集 LLM 对齐 zh bullet↔ja tweet；无中文推文补译 ~2000 条；生成上传；渲染验证 | `鼠色猫语录/动画实况解说` 全量 | 3-4 会话 | P0 |
| **P3 ask 全量** | 现有 639 条中文 ↔ xlsx 日文对齐；剩余 ~1900 条补译；docx/txt 交叉验证完整性；src 填 xlsx 日期 | `鼠色猫语录/早期ask` 全量 | 2-3 会话 | P0 |
| **P4 narou 评论** | 格式：q=读者评论、a=作者回复（字段语义待确认）；全量补译 560 条 | `鼠色猫语录/Web连载网站上评论` | 1-2 会话 | P0 |
| **P5 十周年问答** | mp3 转写（本地 faster-whisper 或 API）；与英文总结对照整理 QA 条目；翻译；mp3 传 wiki（大小限制实测，超限走 archive.org） | 新数据表 + File 页 | 1-2 会话 | P0 |
| **P6 QA 重核 + 英译回填** | 生日问答原推 thread 抓取（方案待定：syndication/浏览器）；对照 S7 重核现有条目、补 jq/ja；reddit QA 英译（Wayback）回填 eq/ea；实况英译回填 es | 全表 jq/eq 系字段补齐 | 2-3 会话 | P2/P3 后效率更高 |
| **P7 收尾** | 双向覆盖审计复跑（零缺失）；存档页 31 页删除 + 链入处理 + `Category:存档` 清理；原始资源归宿落实；AGENTS.md/docs 更新 | 存档页删除 | 1 会话 | 全部 |

P1 与 P0 可并行；P3/P4/P5 相互独立，P0 完成后可任意顺序。

## 验收标准

- 双向覆盖审计（logs/analyze_archive_coverage.py + reverse_coverage.py）零缺失
- 每批 LLM 产物（对齐/翻译）有映射表 + 抽查记录
- 渲染验证：修改子表前后 parse 对比（注意 PortableInfobox/parse 缓存坑，见 modules.md）
- 性能：全量架构下关键词查询 < 10s CPU；/all 按既定方案（动态子页）完成拆分

## 用户侧待提供

- [x] LLM API：**OpenCode Zen**（`https://opencode.ai/zen/v1`，OpenAI 兼容）的免费模型 `deepseek-v4-flash-free`，2026-08-09 实测可用：日译中质量合格（译名注入生效）、~5s/条、10 并发无压力（10 并发 10 条总耗时 5.6s）；是 reasoning 模型，`reasoning_content` 与 `content` 分离且共享 max_tokens，调用时 max_tokens 要留足（建议 ≥4000）；另有 deepseek-v4-pro 与计费 API 备选。key 由用户持有，**不入 git 不入 memory**；管线脚本读 `OPENCODE_API_KEY` 环境变量，或 gitignored 的 `logs/api_keys.json`
- [ ] 录音转写偏好：本机有 RTX 4090，可本地 faster-whisper；质量待 P5 实测，不行再走 Whisper API（约 $0.5）
- [x] 浏览器：用户已连接本地浏览器（reddit 等被反爬源可改走实时抓取；Wayback 快照偏旧，作兜底）
