# LLM 翻译管线（en → zh 全站内容翻新）

zh 站大部分条目处于未翻译/机翻/过时状态（全站 1657 页挂 `Category:待修撰`，2026-08-19 统计）。
本管线用 LLM（K3）对照 en 站源码逐页翻译，直接覆盖 zh 页，不留人工逐页审核环节——机翻稿严格优于英文原文残留或劣质旧译，`{{To do}}` 保留并加参数标注「待校对润色」，作为未来人工介入的入口。

## 职责划分

机械环节全部在 `scripts/tools/llm_translate.py`，LLM 只做一件事：翻译 prose。

```
refresh（重建选页队列）→ prepare（取队首、备料）→ agent 处理 → publish（全量翻译：校验、写入）
                                                            或 原地编辑 + synced（增量同步）
```

- **refresh**：重建 `logs/llm_translate/queue.json`（全量扫描，约 3 分钟，低频跑）。
- **prepare**：取队列最冷的一页，拉 en 源码+revid、zh 现文，解析内链映射，落工作文件到 `logs/llm_translate/work/`。
- **agent**：读 `*.body.en.txt`，产出 `*.body.zh.txt`（只含正文，不含页首页尾）。
- **publish**：结构不变量校验 + 人编冲突检查 → 拼装页首页尾 → pywikibot 写入 → 状态落盘。

## 选页：编辑者冷度

冷度键 = **最近一次非 IchiSanNi 编辑时间**（NiSanIchi 及其他账号均算人类）；页面由 IchiSanNi 创建且从无人类编辑的（transferbot 搬运页），取**创建时间**（内容新鲜度由搬运日决定，en 侧后续编辑由 revid 跟踪兜底）；**已翻译/已同步页取处理时间**——处理即对齐了 en 最新人工改动，视为热页排队尾，避免反复追踪 en 微小更新而挤占从未翻过的远古条目。按冷度升序处理：活跃人类（如 2026 年中活跃的 Nekomeow151）正在碰的页自然排队尾，避免与人类编辑者撞车。翻译/同步编辑**不带 bot flag**（非需抑制通知的批量编辑），摘要格式 `K3翻译: revid <en_revid>（<时长>无人类编辑）`（publish 全量）/ `K3同步: revid <en_revid>（<时长>无人类编辑）`（增量同步，由 `summary` 子命令机械生成，防止手写漂移）——两种前缀都可被历史解析识别；附冷度是为了让其他编辑者理解 bot 自动处理该页的原因。

2026-08-19 全量统计（`list=allrevisions` 排除 IchiSanNi 流式扫描 + 搬运页创建时间补正）：

| 距最后编辑 | 页数 | 占比 |
|---|---|---|
| <1个月 | 304 | 18.3% |
| 1-3个月 | 229 | 13.8% |
| 3-6个月 | 381 | 23.0% |
| 6-12个月 | 347 | 20.9%（含 192 搬运页） |
| >1年 | 396 | 23.9% |

第一阶段工作面 = >1 年的 396 页。

跳过规则分两档：

- **永久跳过**（字符串条目）：zh 源码无 `[[en:...]]` 链接（zh 原创页，如 角色:沃尔夫）等结构性原因，只有页面本身变化才会改观，不复查。
- **en 跟踪跳过**（dict 条目，记 `en_title` + `en_revid`）：已处理（publish/synced）且 en 未变化、en 无实质内容、en 页不存在。prepare 开头批量复查这些条目的 en 当前 revid（50/批），**revid 变化即自动复活**重入队列——追更路径由此承载，不被 skip 堵死。做过实际编辑的条目（publish/synced 两条路径）一律带 `translated_at`，refresh 据此把冷度重定为处理时间；未做编辑的 skip（en 无增量等）不带，冷度不变。「en 仅标题骨架」（剥离后正文无一超过 20 字符的非标题行）由 prepare 机械判定自动记入；其他不宜翻译的情形由 agent 用 `skip <slug> [理由]` 记入。prepare 有 wip 守卫：`work/` 里已有未完成项时拒绝再备新页。
- state.json 丢失的恢复：prepare 对不在 state 里的页会解析 zh 历史摘要里的 `K3翻译: revid N` / `K3同步: revid N` 与 en 当前 revid 比对，一致则补记跳过，不会重复处理。

## 页面拼装

publish 只替换**正文**，页首页尾从 zh 现文机械提取保留：

- 页首：`{{Init}}`、`{{To do}}`、`{{Tab/...}}` 等行首模板块原样保留（单行模板判定须容忍嵌套花括号——`{{To do|…（{{#invoke:interwiki|get_en}}）…}}` 这类行用 `[^{}]*` 会漏判成正文而被静默丢弃）。`{{To do}}` 标注分三类处理（2026-08-19 源码普查：裸 1550 页、带参数 107 页）：裸模板 → 替换为 `{{To do|由 K3 翻译自英文站，待校对润色}}`；参数本身是**翻译任务类旧标注**（「本页翻译结果不准确…重新翻译」74 页、「AI翻译，待校对」等——K3 翻译即完成其任务）→ 同样替换为 K3 标注；**其他参数**（如「列表格式待整理」「内容待补充」）→ 合并为 `原说明；由 K3 翻译自英文站，待校对润色`，保留人工标注；已含 K3 标注的不动（幂等）。`Template:To do` 的 `{{{1}}}` 会渲染在页首 indicator 里。
- 正文：en 源码剥离 en 侧页首模板（如 `{{Parent Tab}}`）、页尾 `[[Category:...]]` 与语言链接后，交由 LLM 翻译。
- 页尾：zh 现文的语言链接块原样保留（en 侧的分类与语言链接直接丢弃——分类由 Module:Init 按前缀/后缀自动打，语言链接以 zh 为准）。

## 内链处理

prepare 把 en 正文里的 `[[wikilink]]` 批量解析成 zh 最终目标（en 标题 → zh 同名页 → 跟随重定向，即 transferbot 搬运 + re0_move 移动留重定向的链路），以映射表形式给 LLM。LLM 写 `[[zh 最终目标|显示文字]]`。解析失败的（en 有而 zh 无对应页）保留 en 原名并在报告中列出。publish 校验输出中的内链目标必须全部在映射值集合内（文件链接除外，目标原样保留、说明文字翻译）。

## 护栏（均为机械检查，不靠 LLM 自检）

1. **结构不变量**：输出正文的内链目标集合 ⊆ 映射值 ∪ 文件目标；正文模板调用集合与 en 源一致（梗概类页面正文正常无模板）。
2. **人编冲突**：publish 前比对 zh 当前 revid 与 prepare 时记录值，不一致即中止（prepare 后有人动过这页，含任何账号）。
3. **失败响亮**：校验不过不写 wiki，非零退出，工作文件保留供排查。

## agent 翻译规则

- 输出只有**正文**：页首页尾由 publish 拼装，en 侧的分类/语言链接/页首模板已剥离，不要补回。
- 内链用 meta 的 `link_map` 写 `[[zh 最终目标|显示文字]]`；文件链接目标原样、说明文字翻译；publish 会校验链接白名单与模板集合。
- **zh 现文已含结构化内容时（meta `zh_flags` 有 infobox/gallery）不整页替换，走原地增量同步**：zh 侧结构（已填好的信息框、图库）往往优于 en 转换结果，予以保留。但「已是中文」不等于「无需处理」——须**对照 en 找增量**：en 多出的实质信息（infobox 空缺字段、封面/发售日期/出处说明、缺失段落）与 zh 的英文残留/中英混杂都要补上。这与中文量无关：哪怕 zh 只剩骨架、实际等于重翻全部 prose，也原地编辑保留 zh 结构，不走 publish（其模板集合校验也容不下 zh 侧结构模板）。**全量 publish 与原地 synced 只是编辑技术选择，状态语义完全相同**——都记 `en_title`+`en_revid`+`translated_at`，en 更新都复活，冷度都按处理时间重定——处于两条路径模糊边界的页面任选其一即可，不影响后续调度。编辑用普通编辑（bot=False minor=False），摘要必须用 `summary <slug>` 子命令输出的标准行（`K3同步: revid <N>（<时长>无人类编辑）`）；完成后 `synced <slug> [理由]` 落盘——synced 会机械校验 wiki 最新编辑确为匹配摘要的同步编辑，摘要不符会拒绝落盘。仅当 en 无增量且无英文残留时才不编辑直接 `skip`。增量同步做了实际编辑的同样发 Discord 通知。（2026-08-20 教训：佩特拉页 zh 已是中文但 en 多出发售日期/封面/收录出处，被「只查英文残留」的旧规则误判 skip。）
- 译名表查无的专名追加到 `logs/llm_translate/nouns.jsonl`（page/term/origin/note 一行一条）。

## 状态与产出

- 处理状态由 **wiki 编辑摘要**承载：`K3翻译: revid <en_revid>（…）`（publish 全量）与 `K3同步: revid <en_revid>（…）`（synced 增量）两种前缀固定可解析（重跑时解析自身历史判断 en 是否已变化，无外部状态依赖）。
- `logs/llm_translate/`（gitignored）：`queue.json`（选页队列）、`state.json`（跳过清单及原因）、`work/`（进行中的工作文件）、`nouns.jsonl`（**未登记专名清单**——LLM 翻译时遇到译名表查无的专名逐条追加，攒一批后人工裁决登记进 `user-fixes.py`，由 fix:translation 全站归一；不主动推送）。

## 运行形态

Hermes cron 驱动，watchdog 同款「script + agent」两段式：cron 的 script 段（profile `scripts/llm_translate_daily.py` wrapper → 仓库脚本）每 tick 先跑机械准备——**queue.json 超 7 天未更新自动 refresh**（约 3 分钟纯 API，零 token；失败沿用旧队列下 tick 重试）+ prepare 备料，stdout 注入 agent prompt；agent 只做翻译与发布。频率与每次页数随 token 预算调整（改 cron schedule 或 prompt 循环次数），token 富余时也可手动触发（`cronjob run`）或直接在会话里走 prepare → 翻译 → publish 流程。

publish 成功时输出 `NOTIFY: [[zh 条目]] <时长>无人类编辑，已由 Bot 根据 [[en:条目]] 自动更新 <url>` 固定格式行，由 cron agent 原样转发到 Discord `#wiki编辑事务【qq互联】`（与自动巡查同频道，方式同 watchdog：主 profile `hermes send -t discord:<频道ID>`）；增量同步路径做了实际编辑的也推送（措辞「已根据 en 同步补充信息」）；无增量的 skip 不推送。

## 当前限制

- 一期只覆盖**正文以 prose+标题为主的页面**（/梗概 等，恰是冷队列主体）。含 en 信息框的主页面（角色/书籍等）需要参数级翻译与模板映射，后续按页面类型扩展。
- en 正文里的模板调用（罕见）原样保留，由既有 jobs 的模板替换接管。
