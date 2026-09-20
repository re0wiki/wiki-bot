# AGENTS.md — wiki-bot

Re:Zero Fandom Wiki（<https://rezero.fandom.com/zh>）的维护机器人，基于 Pywikibot。
主要工作：把英文站内容同步到中文站，并对中文站做译名/格式规范化。

## 知识归处（docs/ vs project skill vs profile skill）

- 与本仓库/wiki 绑定的知识**只写进本仓库、随 git 提交**——这是唯一权威来源。两个落点：
  - **`docs/`**：数据/记录/被代码消费的文档（模板盘点、Module 审查、429 考据、翻译管线、todo 等）；
  - **`.agents/skills/`**：流程型知识（project-local skills，Hermes 按 description 索引触发、按需加载）。
- 项目 skill 的维护：用文件工具编辑 + git 提交，**不用 `skill_manage`**（其 create 写进 profile 目录）；curator 不会改项目 skill。新 clone 后 Hermes 需在本仓库跑一次 `hermes skills trust` 才加载（banner 会提示）。
- **profile skill（`~/.hermes/skills/`）禁止存仓库知识**：它在仓库之外、不随代码走，曾漂移出相互矛盾的副本。任务收尾时的知识落盘是**主 agent**（有文件工具）的职责；回合结束后的后台 skill review（只有 memory/skill 工具的 fork agent）对本仓库知识应**直接放弃**（'Nothing to save'）。
- 判断标准是「知识从哪里来、在哪里验证」，不是「理论上能不能用在别处」：源自本仓库实践的 pywikibot / Fandom / Cloudflare 限流 / 模板审计等知识，即使看似通用，**也算本仓库知识**。
- profile skill 只用于跨仓库/跨资源的流程（例如译名核验横跨 OCR 语料库与 gh issue）。新建前检查内容不与 `docs/`、`.agents/skills/` 重复。
- **文档记录原则**：规则、原因、不变量进文档；**仓库自身的变更事件**（何时改了什么、谁改的）归 git log，不写编年史——文档里出现「2026-xx-xx 改了某文件」类句子即腐化信号。两类例外保留日期：对外部系统的实测观测（Fandom/Cloudflare 行为，日期=时效元数据）、wiki 侧决策与状态（wiki 没有决策日志，这里是唯一记录处）。

## 环境

- **Python 3.14**（`.python-version`，`pyproject.toml` 要求 `>=3.14`），uv 管理，有 `uv.lock`。
- 安装：`uv sync`（`default-groups = "all"`）。pywikibot 的全部可选依赖以 extras 形式声明在 dev 组（`pywikibot[html,http,...]`），覆盖其 requirements.txt，随 submodule 更新自动跟随。
- 运行脚本：`uv run python <script>`（仓库根目录）。uv 按 cwd 的 pyproject.toml 定位项目 `.venv`，天然绕过 PATH 上 Hermes 自身 venv 的裸 `python`（3.11、无项目依赖），且每次运行顺带校验环境与 uv.lock 同步（开销可忽略，`--no-sync` 可跳过）。
- **pywikibot 是 git submodule**（fork：`github.com/re0wiki/pywikibot`，upstream 是 wikimedia/pywikibot）。克隆要 `--recurse-submodules`（否则 `uv sync` 会因路径缺失失败）。fork 上的 re0wiki 定制补丁 rebase 上游时必须逐条保留——**清单与流程的唯一权威是 pywikibot-update skill**。更新 submodule 后提交信息写 `chore: update pywikibot`。
- pywikibot 通过 `[tool.uv.sources]` 以 **editable 方式从 submodule 路径装入 venv**（`{ path = "pwb", editable = true }`），submodule gitlink 是唯一版本锁，无需再同步 uv.lock 里的 commit。`pyproject.toml` 里的 `[tool.ty.environment] extra-paths = ["./pwb"]` 是必须的：ty 无法静态解析 PEP 660 editable finder，删掉会导致全项目 unresolved-import。
- Lint：`ruff check` / `ruff format`（PATH 里没有 ruff 时用 `uv run ruff ...`，ty 同理；`pyproject.toml` 里 extend-exclude 了 pwb 子模块、logs/ 与 *.md（保留手工对齐的代码块注释），不要给它们 lint；`src/oneoff/` 归档脚本纳入正常检查，归档前需先过 lint/format/ty）。类型检查用 `ty`（`src.exclude` 排除 pwb 与 logs/，正常应为 0 诊断）。Windows 上 ruff 无法检查可执行位，shebang 文件的 EXE001 只在 Linux（CI）触发——新增带 shebang 的脚本记得 `git update-index --chmod=+x`。
- 离线单测：`pytest tests/`（不触 wiki；覆盖译名表一致性、watchdog 纯函数；`PYWIKIBOT_DIR` 由 tests/conftest.py 设置）。临时探索脚本写成 .py 放 `scratch/`（gitignored）、从仓库根目录跑（`uv run python scratch/_foo.py`）；docs 只写结论不引用其路径。从子目录跑则 pywikibot 找不到 `user-config.py`（cwd 不参与配置发现时按用户目录找）。Wiki 侧改动验证方式仍是 `-s/--simulate` 干跑 + 上 wiki 查编辑结果。
- Secrets：`user-password.py`（BotPasswords，gitignored，勿读勿提交）。

## 架构地图

| 文件 | 作用 |
|---|---|
| `src/` | **仓库自有代码伞包，顶层目录的唯一增长口**：`jobs/`（任务编排）、`nekoquote/`（功能包先例）、`scripts/`（pwb 入口）、`tools/`（常驻工具）、`oneoff/`（一次性归档）。今后新多模块功能一律 `src/<feature>/`，单文件工具 `src/tools/`，pwb 任务 `src/scripts/`。顶层目录冻结：pwb 契约物（`pwb/`、`families/`、`user-config.py`、`user-fixes.py`）+ `main.py`、`tests/`、`docs/`、`.agents/`（project skills）与运行期目录（`scratch/`、`logs/`、`.cache/`，均 gitignore），不再新增 |
| `main.py` | 循环任务入口。`python main.py <任务名或编号>...` 依次跑指定任务（可多个，编号随插入平移，名字稳定，`-h` 列全部），`-s` 模拟；不传参数 = 无限循环所有任务，**每轮结束休眠 1 小时**（`CYCLE_SLEEP`，Cloudflare 累计量限流对策，见 docs/cloudflare-429.md）。任务失败（子进程非零退出）即以相同码退出等待人工修复，不继续后续任务 |
| `src/jobs/jobs.py` | 任务列表（`Job(name, cmd)`，name 是稳定引用；fix 类任务名与 `-fix:` 参数一致），分 6 组：跨站同步 → 整理新搬运页 → 模板维护 → 重定向 → 语法规范化 → 内容规范化 → 杂项。列表末尾的 `touch -random:128` 是为触发缓存刷新，不是无意义操作 |
| `src/jobs/run_job.py` | 子进程包装：`build_cmd` 拼 `sys.executable pwb/pwb.py ...`（不用裸 `python`，PATH 上可能是无项目依赖的其他版本），自动加 `-always`（interwiki 加 `-auto -force`，transferbot 不加）。注入 `PYTHONIOENCODING=utf-8`、管道按 UTF-8 解码（勿移除，Windows 管道乱码）；循环模式子进程继承控制台走 WriteConsoleW 宽字符 API，不受此变量影响 |
| `src/jobs/starts.py` | namespace → `-start:ns:!` 生成器参数。`ns_base`=主/project/template/category，`ns_more` 再加 module/mediawiki |
| `user-config.py` | pywikibot 配置：family=re0, mylang=zh, 账号 IchiSanNi（只给 zh 配账号，外站匿名读——Fandom 现在跨站登录会互踢会话，见文件内注释）。**保持 `minthrottle>=0.25`、`put_throttle>=2`**（Cloudflare 429 预防，根因与对策见 docs/cloudflare-429.md） |
| `user-fixes.py` | **核心资产**。自定义 fix 集：misc/date/anti-ve/para/gallery/heading/**translation**/HTML/syntax 等。`translation` 把几百个实质别名归一到标准译名：名字规则（`p2st()` 简繁展开）与别名精确对/guard 合成单趟 alternation（统一按目标/别名原文长度降序、同位置只提交一次 = 真长匹配优先），大 alternation 靠 regex 模块 trie 优化；**仅繁简差异的写法命中后不改写**（`_AltSub` 的 t2s 判等：MediaWiki 简繁转换已覆盖显示与链接解析，源码归一毫无收益、只会误伤与繁体同形的日文如 聖域/神龍/加護——标题侧不受此限，re0_move 仍全量繁简归一）；NekoQuote 月表的日文原文字段（jq/jt Lua 字符串）与含假名的日文连段由 inside 异常保护不归一；译名数据已全部迁入 `translations.py` |
| `translations.py` | **译名表数据（唯一权威）**：`ENTRIES`（std=标准名 + ja/en/aliases/note；aliases 为写法字符串元组，guard 正则/字符类直接作为写法文本（只写简体：p2st 对裸字符与手写类内字符都自动补 s2t 繁体）；note=自由注释（分类/全名/称呼关系等），不进任何消费链；别名精确对按表顺序，名字规则生成时按目标长度降序；name 含 `{{` 的模板条目不生成名字规则）。纯数据无逻辑，供 user-fixes import 生成替换表，也供 LLM 翻译管线与 re0-corpus 审查管线直接消费 |
| `src/scripts/` | 只放 pwb 按名解析的任务脚本（`re0_*` ×7，见下行；搜索路径由 user-config.py 的 `user_script_paths = ["src.scripts"]` 指定；find_filename 不递归子目录，放进子目录即退出解析） |
| `src/tools/` | 非 pwb 的常驻/维护工具（直接 python 运行）：`recent_changes_watchdog.py`、诊断（`verify_wiki_access.py`/`test_pwb_throttle.py`）、翻译管线（`llm_translate.py`，见 docs/llm-translation.md）、审计（`dump_modules.py`/`template_inventory.py`/`template_complexity.py`/`recheck_template_usage.py`/`scan_title_prefixes.py`/`check_css_imports.py`/`audit_wikipedia_links.py`/`audit_langlinks.py`/`series_nav_audit.py`——系列导航 Tab 与 en prev/next 链一致性，见 series-nav-sync skill） |
| `src/oneoff/` | 一次性脚本归档（含 429 探测 `probe_*`，重跑传完整路径） |
| `scratch/`、`logs/`、`.cache/` | 运行期目录（均 gitignore）。**代码（含临时的）不进 logs/ 与 .cache/**：`scratch/` 收临时探索脚本与其一次性产出；`logs/` 收 pwb 自动日志与工具的可再生输出（如 dump_modules 快照）。分辨标准：常驻→src/tools/；一次性但 docs 引为出处或可能复跑→src/oneoff/（入 git）；纯探索→scratch/，且 **docs 只写结论、不引用 scratch/ 与 logs/ 路径**（防新 clone 悬空引用）。**按「删掉的后果」分**：scratch/ 与 logs/ 删了无任何后果；`.cache/` 删了有代价（常驻任务的跨运行状态如水位线、基线、队列，或重建昂贵的缓存）——状态文件的路径是接口，放错目录即断档事故 |
| `src/scripts/re0_*.py` | 7 个自定义脚本：gallery（用 en 站图库覆盖 zh，en 链接从源码解析）、image（图片差量同步；en 的 `video/youtube` 外部视频按名称差量经 Fandom 视频导入端点从 YouTube 重导入，配方见 wiki-access skill）、redirect（给 `前缀:词干` 页建裸词干重定向，词干存在性批量检查）、move（标题命中 translation 规则的页面自动移到简体标准名，留重定向；目标已存在时跳过待人工合并；File 空间无有效扩展名的标题硬性跳过——那是 YouTube 原标题，归一会破坏同名比对）、fixing_redirects（把源码中指向重定向的链接改写为最终目标；重定向表与链接都从源码本地解析）、transferbot（en 主空间缺失页批量搬运：标题集内存比对 + fork 补丁同款页首，页首含 `[[Category:新搬运待整理]]` 与 en 链接）、nekoquote（语录增量同步：Discord bot token 拉中文服务器 FBK 转发频道新消息 → 全链上月表；token 在 secrets.json（gitignored）；本地基线缺失时自动从 wiki 重建——管线代码在 `src/nekoquote/` 包，运行期数据在 `.cache/nekoquote/`（gitignored，路径由 `src/nekoquote/__init__.py` 的 `DATA` 常量统一定义，勿散落字面量）；**wiki 侧改月表（复核消歧/人工修译文）后须跑 `src/nekoquote/pull_wiki.py` 回写本地源数据**，否则下轮增量同步回潮——流程见 nekoquote-incremental skill） |
| `src/tools/verify_wiki_access.py` | 只读诊断：验证 pywikibot 库与裸 API 两条 wiki 通路和凭据是否有效，期望输出 `ALL CHECKS PASSED` |
| `src/tools/recent_changes_watchdog.py` | 最近改动巡查 watchdog：rcid 水位线去重（状态 `.cache/rc_watchdog.json`，已 gitignore），排除 IchiSanNi 全部编辑（含无 flag 的手动编辑，修改时已自查）与其他账号的 bot 标记编辑。输出两段：NEW_CHANGES 逐条清单、MERGED_DIFFS（同用户同页**相邻**连续编辑合并后的 diff 增删行，⟦⟧/〔〕 标行内增删，超长截断标注）；无新改动时输出 NO_NEW_CHANGES 且末行 `{"wakeAgent": false}`（Hermes cron 唤醒门：脚本 stdout 末行是该 JSON 即抑制该次 agent 运行；脚本失败非零退出时门不生效、agent 照常醒，保住失败重试）。取数/解析固定由脚本完成；水位线在 diff 全部拉取成功后才推进，失败非零退出下轮重试，不静默漏审。区间与触发时间解耦：翻页拉取至水位线即停，漏触发/手动触发/改间隔均安全。由 Hermes cron job「wiki 最近改动自动巡查」每天 10:00 调用，**经 runpy 跑在 Hermes 自带的 Python 3.11 下——语法必须兼容 3.11**（pyproject.toml 已对该文件设 ruff `per-file-target-version = py311`）。发现问题发 Discord `#wiki编辑事务【qq互联】`；但 NiSanIchi（维护者本人的个人账号，与 bot 账号 IchiSanNi 勿混淆）的改动发现问题时只在 cron 回复中说明。报告范围：机翻覆盖/语法破坏/恶意内容（译名不巡查——登记别名由 translation 任务自动归一） |
| `.agents/skills/` | **project-local skills**（随 git；Hermes 信任本仓库后按 description 索引触发、按需加载）：`wiki-access`（wiki 读写配方与实测坑，**写任何 wiki 交互代码前必读**）、`template-usage-audit`（零引用模板审计）、`series-nav-sync`（系列导航与 en 同步 SOP）、`pywikibot-update`（submodule rebase 流程 + fork 补丁清单唯一权威）、`nekoquote-incremental`（语录收录 runbook）。维护规则见「知识归处」节 |
| `docs/` | `todo.md`（跨任务待办与待决策项）、`wiki-structure.md`（zh 站结构：伪命名空间/页首/模板/导航/子页后缀/跨语言链接/状态页）、`cloudflare-429.md`（限流根因与对策）、`templates.md`（模板盘点数据与技术约定）、`modules.md`（Module/Lua 审查结论与约定）、`pywikibot-scripts.md`（自带脚本选用速查）、`llm-translation.md`（LLM 翻译管线：en→zh 全站内容翻新；**面向管线维护**——agent 规则由 prepare 从该文「agent 规则」小节机械注入 prompt，执行 tick 无需读本文档，改 agent 规则只改该小节）、`wiki-search.md`（Fandom 搜索能力实测：无 insource 等 CirrusSearch 关键词） |
| `families/re0_family.py` | re0 family 定义，12 个语言子站（de/en/es/fr/it/ko/nl/pl/pt-br/ru/uk/zh 都在 rezero.fandom.com，en 无路径前缀其余 `/<code>`）。另有 `w_family.py`（community.fandom.com，即 Fandom 中央站 `w:` 前缀） |
| `tests/` | 离线单测（pytest，不触 wiki）：译名表一致性（RULES 与 re0_move 共享）、watchdog 纯函数、re0_gallery `merge_galleries`、re0_move `resolve_move`、re0_fixing_redirects 链接改写/链解析、run_job 命令拼装。模块经 `tests/repo_loader.py` 按路径加载（src/scripts/ 非包） |
| `pwb/` | submodule（pywikibot fork；目录不叫 `pywikibot` 是为了避免根目录运行时以 namespace package 遮蔽已安装的包） |

pywikibot 自带脚本（movepages/add_text/delete/listpages/category/template 等）的选用速查见 `docs/pywikibot-scripts.md`——能用现成脚本就别手写。

## wiki 侧结构（zh 站）

见 `docs/wiki-structure.md`：伪命名空间前缀清单与收录范围、页首模板约定、模板体系、导航与 Custom-nav- 简繁转换消息、子页后缀注册点、跨语言链接规则与审计基线、状态页约定。

## 读写 wiki

- **红线**：写入测试只允许在 zh 站的测试页面——`User:IchiSanNi` 的所有子页面，或任意命名空间的 `Sandbox`/`沙盒` 页及其子页面；正式批量写入需用户明确指示；**绝不写 zh 以外的语言站**；不读不打印 `user-password.py`（pywikibot 会自己加载）。
- **门规**：写任何 wiki 交互代码之前——含 scratch/ 下的一次性脚本、裸 API 调用——先加载 **wiki-access skill**（读写配方、生成器、限速、实测坑都在里面）。凭据有效性验证跑 `src/tools/verify_wiki_access.py`。

## 译名维护工作流（最常见的改动）

1. 译名选取规则见 wiki 的 `ReZero Wiki:译名表`（官方简中 > 官方繁体 > 民间 > 保留英文）。bot 执行的唯一权威是 `user-fixes.py`；译名表页面由人工随性维护、无逐条同步义务（bot 的 fix:translation 会自动归一页面上的别名写法），已有条目的标题与内容本身即译名表的作用，不另建清单页。用户通过 GitHub Issues 报译名问题（模板：新增/修改译名、遗漏替换、错误替换），wiki 页面明确告诉用户「不要手动移动页面或替换文本，提议通过后 Bot 会批量修改」。
2. 改译名 = 改 `translations.py` 的 `ENTRIES`：`std` 进主列表（标准名经 `p2st()` 简繁展开匹配简繁写法；**仅繁简差异的命中不改写**——MediaWiki 简繁转换已覆盖显示与链接解析，源码归一只会误伤与繁体同形的日文），**新变体一律登记 `aliases` 精确对**（写法字符串；别名位于更长他名内部时 guard 直接写进写法文本，如 `"(?<!梅)裘斯"`；读音全组合类变体（ai-mi-li-ya→爱蜜莉雅 族）写音位字符类一条收编（如 `"[艾爱][米蜜][莉利][娅亚雅]"`，类内只写简体、p2st 自动补繁），**先跑全历史碰撞扫描确认命中全在本族再启用**；guard 的作用验证要在 wiki 源码匹配**（官方语料 0 次不代表多余：无官方译名的实体本就不在语料里，如 `梅莉(?!奥)` 防 `角色:梅里欧·阿嘎玛`）；选择性展开用手写字符类表达，如 利格鲁/梅莉；不同日文名（真名/旧名/称呼）不互转，各自单记）。`translation_manual` 只剩模板替换规则。拿不准覆盖面的，先 `python main.py fix:translation -s` 干跑。繁体与日文原名同字的别名（王选前日谭/最优纪行/王族诱拐案 类）：含假名的日文连段由 translation fix 的 inside 异常自动保护（卷名、{{R}} 日文参数、日文引文等均在此列），纯汉字日文引用无假名可探测——wiki 上既有出现处已逐处 as-is 保护（出版信息、术语:王族诱拐事件 lead），**新增此类纯汉字日文引用必须包 `<!--as-is-->`**，否则会被 s2t 对归一。标题含别名的页面由 `re0_move` 任务用同一张表自动移动，无需另行处理。
3. 提交信息遵循 Conventional Commits：`feat(translation): add X` / `fix(translation): 旧 -> 新`。
4. 模板条目（如 `{{Elf}}`）不生成名字规则（name 含 `{{` 自动排除），正文归一由 `translation_manual` 结构规则处理。
5. 写替换规则正则（translations.py 的 guard 写法、user-fixes 的作用域正则）当心三处解析坑（2026-08-11 fix:para 死行删除规则实证）：`\{\{}` 不是 `{{`——`\}` 也是字面量，该写法匹配的是三字符 `{{}`，正确写法是 `(?!\{\{)`；DOTALL 下值匹配用 `.*` 会吞到文末，行值一律 `[^\n]*`；参数名/等号两侧的空白用 `[ \t]*` 不用 `\s*`——`\s` 含 `\n`，遇空值行（如 `|Next = ` 独占一行）会把下一行吞成值。验证这类规则必须断言 diff 只删目标行（仅看 `new != text` 会漏掉截尾事故）。

## 新增自动化：进 fix 表还是单建脚本

进 `user-fixes.py`（replace 任务）需**全部**满足；任一不满足即单建脚本：

- 变换是 源码→源码 的纯函数：不查 API、不读其他页面、无跨运行状态（替换函数的入参只有 `re.Match`——所需上下文必须能由正则捕获进 match，模板作用域是上限；先例：para 的 name_ja_romaji 删行、多语言堆积拆分）；
- 幂等：fix 任务在主循环里对全命名空间反复重跑，同一份源码重复应用必须收敛零伤害；
- 零误判由构造保证（保守判据宁可漏不可错，漏的留下轮或人工）；
- 收益依赖常驻性（新搬运页下轮自动收敛）而非一次性清理——一次性归 `src/oneoff/`。

单建脚本的典型触发：需要页外数据（存在性/重定向跟随/跨站读取）、动作不是改源码（移动/上传/建重定向）、跨运行状态（水位线/队列/基线）、需要审计报告输出。
