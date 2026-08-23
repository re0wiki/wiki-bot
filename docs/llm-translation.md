# LLM 翻译管线（en → zh 全站内容翻新）

zh 站大部分条目处于未翻译/机翻/过时状态（全站 1657 页挂 `Category:待修撰`，2026-08-19 统计）。
本管线用 LLM（K3）对照 en 站源码逐页翻译，直接覆盖 zh 页，不留人工逐页审核环节——机翻稿严格优于英文原文残留或劣质旧译。机翻标记由 `[[Category:机翻待校对]]` 承载（说明写在分类页），作为人工校对介入的入口：校对后由人类手动摘除分类。

## 职责划分

机械环节全部在 `scripts/tools/llm_translate.py`，LLM 只做一件事：翻译 prose。

```
refresh（重建选页队列）→ prepare（取队首、机械转换备料）→ agent 直接编辑 zh 页 → done（核验）
```

- **refresh**：重建 `.cache/llm_translate/queue.json`（全量扫描 + 标记扫描重定冷度，约 5 分钟，低频跑）。
- **prepare**：取队列最冷的一页，拉 en 源码+revid、zh 现文，**本地机械转换**（en→zh 骨架，见「机械转换层」节），落工作文件到 `.cache/llm_translate/work/`；途中对机械可判定的页面（无 en 源 / en 仅标题骨架）自动打标记跳过。
- **agent**：以骨架为基础直接编辑 zh 页（pywikibot 普通编辑），只翻 prose；摘要与同步标记用 `stamp` 子命令生成的标准行。
- **done**：对 wiki 只读——以 prepare 时的 zh 现文与骨架为基线做事后机械核验（标记/页首/内链/模板/分类），通过即输出 NOTIFY 行。脚本对 wiki 的唯一写入是 skip/auto-skip 的机械打标记。

## 机械转换层（prepare 的 en→zh 骨架生成）

`convert_en_body` 把 en 正文离线转成 zh 半成品骨架，本地复刻 replace.py 的应用路径（fix 表规则不经 wiki、不碰沙盒）：

1. `split_en_body` 剥离 en 框架：页首模板行、页尾分类/语言链接、页尾 `==Navigation==` 导航区（navbox 全在 template-remove 清单，zh 系列导航由 Tab/* 承担）；
2. 模板名映射（`jobs/jobs.py` 的 `_template_replacements`，唯一事实源）；
3. `cosmetic_changes` 本地复用（`CosmeticChangesToolkit` 以真实页名的惰性 Page 构造，不拉取内容）：标题等号内侧空格归一（`cleanUpSectionHeaders`，fix:heading 的前置）、列表空格、空段清理等，与循环任务同套件同语义（`ignore=METHOD`）；
4. fix 表规则依次应用：para（参数名归一 + 多语言堆积拆分）→ heading（标题归一）→ date（日期 ISO 化）→ misc（间隔号/引号等）→ anti-ve（prose `<br>` 转段落；模板内受例外保护）；
5. 内链目标替换：resolve_links 映射（en 标题 → zh 同名页 → 跟随重定向——与 fixing-redirects 同链路等效，此处离线单遍完成）把 `[[X]]` 改写为 `[[zh 最终目标|X]]`，显示文字留 agent 翻译；解析失败（en 有 zh 无）保留 en 原名并列进报告；
6. **信息框字段级合并**（`merge_structure`，zh 策展内容不丢）：zh 同名参数值含中文（已策展）→ 保留 zh 行，英文残留/空值 → 用 en 转换值；zh 独有参数行（isbn_ko/painter/voice_zh_* 等）块尾保留；zh 有 image_a/n/g/c 分媒介图库时丢弃 en 的单 image 参数；previous/next 与 character 的 name_ja_romaji（fix:para 删除对象）永不带回；zh 独有的整个信息框（en 无对应）整块前置保留。

译名归一不在转换层——LLM 按译名表翻译，残留别名由主循环的 fix:translation 对成稿机械兜底。

## 选页：编辑者冷度

冷度键为以下时间中**最近**者：

- 最近一次非 IchiSanNi 编辑时间，若存在（NiSanIchi 及其他账号均算人类）；
- 创建时间（搬运页的内容新鲜度即搬运日）；
- 已打标页的标记时间（编辑或 skip 打标都意味着「截至该时间 zh 与 en 已确认同步」，skip 即确认 en 无增量/无内容可搬）。

按冷度升序处理：最近有人类活动或刚被管线处理的页自然排队尾，避免与活跃编辑者（如 2026 年中活跃的 Nekomeow151）撞车，也避免反复追踪 en 微小更新而挤占从未翻过的远古条目。

2026-08-19 全量统计（`list=allrevisions` 排除 IchiSanNi 流式扫描 + 搬运页创建时间补正）：

| 距最后编辑 | 页数 | 占比 |
|---|---|---|
| <1个月 | 304 | 18.3% |
| 1-3个月 | 229 | 13.8% |
| 3-6个月 | 381 | 23.0% |
| 6-12个月 | 347 | 20.9%（含 192 搬运页） |
| >1年 | 396 | 23.9% |

第一阶段工作面 = >1 年的 396 页。

**prepare 的队首实际冷度校正**：queue.json 一周一建，间隔期内冷度会陈旧，walk 顺带校正：

- 对每个未处理候选取**实际冷度**：与 refresh 同规则——`rvexcludeuser` 精确取最近一次非 IchiSanNi 编辑时间，无人类编辑的搬运页取创建时间。
- 陈旧冷度单调偏低（时间只往前走），故扫到「下一条陈旧冷度 ≥ 当前最优候选实际冷度」即确定真队首；人类活动稀疏时每 tick 只多查一两页。
- 算出的实际冷度与已同步页的标记时间顺手写回 queue.json，懒修复排序。

效果：refresh 间隔期内被人类编辑的队首页在下一 tick 即让位，避让活跃编辑者不受 7 天重建周期限制。

## 同步标记（唯一状态载体）

每个处理过的条目源码末尾（正文末、语言链接块之前）带一个 HTML 注释标记，编辑（done）与跳过（skip/auto-skip）统一以此落账——状态随页面走，标记格式变更只是普通编辑：

- `<!-- K3: revid <en_revid>; <ISO 时间> -->`：已同步到 en 该版本（含「en 仅标题骨架」「en 无增量」等无内容可搬的确认）。revid 为 `-` 表示无 en 源：zh 源码无 `[[en:...]]` 链接（zh 原创页，如 角色:沃尔夫），或 en 页不存在。

prepare 的 walk 逐页读 zh 源码解析标记（源码本来必读）：

- 标记 revid 与 en 当前一致 → 跳过；**不一致即自动复活**重入处理（追更路径由此承载）。无 en 链接时 en 侧 revid 视为 `-`——zh 原创页后来加了 en 链接、悬空链接的 en 页被创建，都走 revid 不一致复活，无需专门分支。
- 无标记 → 处理；其中机械可判定的两种情况由 prepare 直接打标记跳过：无 en 源（标记 revid 为 `-`）、en 仅标题骨架（剥离后正文无一超过 20 字符的非标题行）。「en 无增量」由 agent 判断后 `skip <slug> [理由]` 打标记。

prepare 有 wip 守卫：`work/` 里已有未完成项时拒绝再备新页。

## 页面构成规则（agent 编辑时遵守，done 逐项核验）

agent 直接产出整页新源码。页首以 zh 现文为准机械保留，done 以 prepare 基线逐行比对：

- 页首：`{{Init}}`、`{{To do}}`、`{{Tab/...}}` 等行首模板块原样保留，**唯一允许的改动**是清理 `{{To do}}` 参数中的翻译类标注（机翻标记由 `[[Category:机翻待校对]]` 承载，`{{To do}}` 里的翻译标注是冗余）：K3 标注段与「本页翻译结果不准确…重新翻译」「AI翻译，待校对」等翻译任务类标注段（管线处理即完成其任务）按「；」分段丢弃，清空则还原裸 `{{To do}}`；**其他参数**（如「列表格式待整理」「内容待补充」）原样保留。裸 `{{To do}}` 不动（其 `Category:待修撰` 归入是队列数据源）。
- 正文：翻译规则见下节。
  - en 侧页首模板（如 `{{Parent Tab}}`）、页尾 `[[Category:...]]`、语言链接与 `==Navigation==` 导航区不带入（split_en_body 机械剥离）——分类由 Module:Init 按前缀/后缀自动打，语言链接以 zh 为准，系列导航由 Tab/* 承担。
  - **末尾必须挂 `[[Category:机翻待校对]]`**：有分类段则并入。人类校对后手动摘除；若管线再次处理（en 有新内容 = 新机翻内容）会重新挂上。
  - **分类之后放一行同步标记注释**（`stamp` 子命令输出的第二行，原位替换已有标记）。
- 页尾：zh 现文的语言链接行保留（不增删、不改目标）；相对顺序由循环任务的 cosmetic_changes 归一。

## 内链处理

prepare 把 en 正文里的 `[[wikilink]]` 批量解析成 zh 最终目标（en 标题 → zh 同名页 → 跟随重定向，即 transferbot 搬运 + re0_move 移动留重定向的链路），并在骨架里机械改写为 `[[zh 最终目标|原显示文字]]`——agent 只翻译显示文字，不碰目标。`#` 锚点不参与 API 查询（非法标题字符会静默落空），按裸标题解析后接回最终目标。解析失败的（en 有而 zh 无对应页）保留 en 原名并在报告中列出。done 侧的白名单核验见「护栏」。

## 护栏（done 的事后机械核验，不靠 LLM 自检）

1. **标记核验**：zh 页最新编辑必须是本账号，且源码含且仅含一个同步标记、revid 与 meta 的 en_revid 一致——防止「没编辑就记完成」与标记漂移。
2. **框架不变量**：页首模板块（仅 To do 翻译类标注可按规则清理）以 prepare 时的 zh 现文为基线逐行比对（核验前先从新源码摘除标记行）。
3. **白名单**：正文内链目标（按 页面/文件/分类/语言链接 分类）⊆ link_map ∪ 未解析名 ∪ zh 现文已有目标（文件另含骨架出现的，分类另含机翻待校对）；正文模板调用 ⊆ conv 骨架 ∪ zh 现文。另核验 `[[Category:机翻待校对]]` 必挂（漏挂拒绝）。
4. **失败响亮**：核验不过非零退出，工作文件保留供排查；wiki 上的编辑由 agent 修正（重编 wiki）后重新 done。

## agent 翻译规则

- **直接编辑 zh 页**（pywikibot 普通编辑，bot=False minor=False），产出整页新源码；编辑前以重读的最新源码为基础（prepare 后若有人类编辑，将其改动融入处理，不要覆盖）。摘要与同步标记用 `stamp <slug>` 子命令输出的两行原样使用（第一行填摘要，第二行放正文末尾、原位替换已有标记）。完成后 `done <slug>` 核验。
- 页首/页尾按「页面构成规则」保留；**正文以 `{slug}.conv.txt` 半成品骨架为基础**（结构转换与字段合并已由 prepare 机械完成，见「机械转换层」节）——agent 只做翻译：
  - prose 段落、参数里的英文散文值、内链显示文字、未归一的标题（映射表外的如 `Chapters`）；引号用「」，人名/专名用 wiki 通行译名（残留别名由主循环 fix:translation 兜底）；
  - 骨架里含中文的 zh 策展内容（信息框合并保留的字段等）原样不动；
  - `{slug}.body.en.txt` 是骨架的生成源（en 原文，拿不准骨架某处转换是否正确时对照它），`{slug}.zh.txt` 是 prepare 时的 zh 现文（查看被保留策展内容的上下文时看它）——两者仅供核对。
- 仅当 en 无增量且 zh 无英文残留时才不编辑，直接 `skip`——「en 无增量」要对照 en 全文判定（含发售日期/封面/出处等字段），zh 已是中文不代表无增量。
- 译名表查无的专名追加到 `.cache/llm_translate/nouns.jsonl`（page/term/origin/note 一行一条）。

## 状态与产出

- 处理状态由**条目源码末尾的同步标记**承载（见「同步标记」节）——随页面走、格式可演进。机器判定只看同步标记；编辑摘要（`K3: revid <en_revid>（…）`）只是人类可读的说明。
- `.cache/llm_translate/`（gitignored）：`queue.json`（选页队列）、`work/`（进行中的工作文件）、`nouns.jsonl`（**未登记专名清单**——LLM 翻译时遇到译名表查无的专名逐条追加，攒一批后人工裁决登记进 `user-fixes.py`，由 fix:translation 全站归一；不主动推送）。

## 运行形态

Hermes cron 驱动，watchdog 同款「script + agent」两段式。cron 的 script 段（profile `scripts/llm_translate_daily.py` wrapper → 仓库脚本）每 tick 依次：

1. **积压闸门**：`Category:机翻待校对` 条目数 ≥ 5（仓库脚本的 `BACKLOG_LIMIT`，由 `backlog` 子命令判定）时只输出 `{"wakeAgent": false}`，cron 跳过 agent 段、本 tick 静默——等人类校对摘除分类后自动恢复。
2. **refresh**：queue.json 超 7 天未更新才跑（约 5 分钟纯 API，零 token；失败沿用旧队列，下 tick 重试）。
3. **prepare**：备料，stdout 注入 agent prompt。

agent 只做编辑与收尾。频率与每次页数随 token 预算调整（改 cron schedule 或 prompt 循环次数），token 富余时也可手动触发（`cronjob run`）或直接在会话里走 prepare → 编辑 → done 流程。

done 成功时输出 `NOTIFY: [[zh 条目]] <时长>无人类编辑，已由 Bot 根据 [[en:条目]] 自动更新 <url>` 固定格式行，由 cron agent 原样转发到 Discord `#wiki编辑事务【qq互联】`（与自动巡查同频道，方式同 watchdog：主 profile `hermes send -t discord:<频道ID>`）；无编辑的 skip 不推送。

## 当前限制

- en 正文里的模板调用（罕见）原样保留，由既有 jobs 的模板替换接管。
- 映射表外的 en 模板参数名原样透传进骨架，由 agent 按语义合并或丢弃；高频出现再登记进 fix:para。
- 多语言堆积拆分遇保守判据（表外标注/分册/嵌套模板）跳过，对应参数保持堆积形态留 agent/人工。
