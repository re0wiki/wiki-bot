# AGENTS.md — wiki-bot

Re:Zero Fandom Wiki（<https://rezero.fandom.com/zh>）的维护机器人，基于 Pywikibot。
主要工作：把英文站内容同步到中文站，并对中文站做译名/格式规范化。

## 知识归处（仓库文档 vs Hermes skill）

- 与本仓库/wiki 绑定的知识**只写进本仓库文档**（AGENTS.md 放精简规则与指针，`docs/` 放详细配方），随 git 提交——这是唯一权威来源。**不要存为 Hermes skill**：skill 在仓库之外、不随代码走，曾经因此漂移出相互矛盾的副本。任务结束时的「save as skill」惯例对本仓库知识不适用，改为写进 `docs/`。
- 判断标准是「知识从哪里来、在哪里验证」，不是「理论上能不能用在别处」：源自本仓库实践的 pywikibot / Fandom / Cloudflare 限流 / 模板审计等知识，即使看似通用，**也算本仓库知识**，进 `docs/`。（有过教训：曾被重新框架成「通用 Fandom 知识」存成 skill。）
- 分工：把知识写进 `docs/` 是**主 agent**（有文件工具）的职责，任务收尾时主动做。回合结束后的后台 skill review（只有 memory/skill 工具的 fork agent）对本仓库知识应**直接放弃**（'Nothing to save'）——它碰不了仓库文件，不要建/改 skill，也不要把知识代为塞进 memory。
- skill 只用于跨仓库/跨资源的流程（例如译名核验横跨 OCR 语料库与 gh issue）。新建 skill 前检查内容不与 `docs/` 重复。
- **文档记录原则**：规则、原因、不变量进文档；**仓库自身的变更事件**（何时改了什么、谁改的）归 git log，不写编年史——文档里出现「2026-xx-xx 改了某文件」类句子即腐化信号。两类例外保留日期：对外部系统的实测观测（Fandom/Cloudflare 行为，日期=时效元数据）、wiki 侧决策与状态（wiki 没有决策日志，这里是唯一记录处）。

## 环境

- **Python 3.14**（`.python-version`，`pyproject.toml` 要求 `>=3.14`），uv 管理，有 `uv.lock`。
- 安装：`uv sync`（`default-groups = "all"`）。pywikibot 的全部可选依赖以 extras 形式声明在 dev 组（`pywikibot[html,http,...]`），覆盖其 requirements.txt，随 submodule 更新自动跟随。
- 运行脚本：`PYTHONPATH= .venv/Scripts/python.exe <script>`（Windows 上 Hermes 会注入指向自身 venv 的 PYTHONPATH，必须清空，否则 import 错包）。
- **pywikibot 是 git submodule**（fork：`github.com/re0wiki/pywikibot`，upstream 是 wikimedia/pywikibot）。克隆要 `--recurse-submodules`（否则 `uv sync` 会因路径缺失失败）。更新 submodule 后提交信息写 `chore: update pywikibot`。
- pywikibot 通过 `[tool.uv.sources]` 以 **editable 方式从 submodule 路径装入 venv**（`{ path = "pwb", editable = true }`），submodule gitlink 是唯一版本锁，无需再同步 uv.lock 里的 commit。`pyproject.toml` 里的 `[tool.ty.environment] extra-paths = ["./pwb"]` 是必须的：ty 无法静态解析 PEP 660 editable finder，删掉会导致全项目 unresolved-import。
- Lint：`ruff check` / `ruff format`（PATH 里没有 ruff 时用 `uv run ruff ...`，ty 同理；`pyproject.toml` 里 extend-exclude 了 pwb 子模块、logs/ 与 *.md（保留手工对齐的代码块注释），不要给它们 lint；`scripts/oneoff/` 归档脚本纳入正常检查，归档前需先过 lint/format/ty）。类型检查用 `ty`（`src.exclude` 排除 pwb 与 logs/，正常应为 0 诊断）。
- 离线单测：`pytest tests/`（不触 wiki；覆盖译名表一致性、watchdog 纯函数；`PYWIKIBOT_DIR` 由 tests/conftest.py 设置）。**临时探索脚本写成 .py 放 `scripts/` 下、从仓库根目录跑**（`PYTHONPATH= .venv/Scripts/python.exe scripts/_foo.py`），跑完即删；从 `scripts/` 子目录跑则 pywikibot 找不到 `user-config.py`（cwd 不参与配置发现时按用户目录找）。Wiki 侧改动验证方式仍是 `-s/--simulate` 干跑 + 上 wiki 查编辑结果。
- Secrets：`user-password.py`（BotPasswords，gitignored，勿读勿提交）。

## 架构地图

| 文件 | 作用 |
|---|---|
| `main.py` | 循环任务入口。`python main.py <任务名或编号>...` 依次跑指定任务（可多个，编号随插入平移，名字稳定，`-h` 列全部），`-s` 模拟；不传参数 = 无限循环所有任务，**每轮结束休眠 1 小时**（`CYCLE_SLEEP`，2026-08-13 起，Cloudflare 累计量限流对策，见 docs/cloudflare-429.md）。任务失败（子进程非零退出）即以相同码退出等待人工修复，不继续后续任务 |
| `jobs/jobs.py` | 任务列表（`Job(name, cmd)`，name 是稳定引用；fix 类任务名与 `-fix:` 参数一致），分 6 组：跨站同步 → 整理新搬运页 → 模板维护 → 重定向 → 语法规范化 → 内容规范化 → 杂项 |
| `jobs/run_job.py` | 子进程包装：`build_cmd` 拼 `sys.executable pwb/pwb.py ...`（不用裸 `python`，PATH 上可能是无项目依赖的其他版本），自动加 `-always`（interwiki 加 `-auto -force`，transferbot 不加） |
| `jobs/starts.py` | namespace → `-start:ns:!` 生成器参数。`ns_base`=主/project/template/category，`ns_more` 再加 module/mediawiki |
| `user-config.py` | pywikibot 配置：family=re0, mylang=zh, 账号 IchiSanNi（只给 zh 配账号，外站匿名读——Fandom 现在跨站登录会互踢会话，见文件内注释） |
| `user-fixes.py` | **核心资产**。自定义 fix 集：misc/date/anti-ve/para/gallery/heading/**translation**/HTML/syntax 等。`translation` 用「相似字符 → 正则」机制（`f()`/`p2o()`/`p2n()`）把几百个别名归一到标准译名 |
| `scripts/` | 常驻/可复用脚本：7 个 `re0_*` 任务脚本（见下行）、`recent_changes_watchdog.py`、诊断（`verify_wiki_access.py`/`test_pwb_throttle.py`）、429 探测 `probe_*`（见 `docs/cloudflare-429.md`）、审计工具（`dump_modules.py`/`template_inventory.py`/`template_complexity.py`/`recheck_template_usage.py`/`scan_title_prefixes.py`/`check_css_imports.py`/`audit_wikipedia_links.py`——全站维基百科外链审计）。`scripts/oneoff/` 是已完成任务的一次性脚本归档（pwb.py 按名字找不到，重跑要传路径）。docs 里的 `logs/xxx.py` 引用是历史出处——`logs/` 整体 gitignore，不在仓库内 |
| `scripts/re0_*.py` | 7 个自定义脚本：gallery（用 en 站图库覆盖 zh，en 链接从源码解析）、image（图片差量同步）、redirect（给 `前缀:词干` 页建裸词干重定向，词干存在性批量检查）、move（标题命中 translation 规则的页面自动移到简体标准名，留重定向；与正文替换的差异是标题一律归一简体、不保留繁体；目标已存在时跳过待人工合并）、fixing_redirects（把源码中指向重定向的链接改写为最终目标；重定向表与链接都从源码本地解析）、transferbot（en 主空间缺失页批量搬运：标题集内存比对 + fork 补丁同款页首；三者均为 2026-08-13 429 事故后的高效化改造，见 docs/cloudflare-429.md 与 docs/todo.md）、nekoquote（语录增量同步：Discord bot token 拉中文服务器 FBK 转发频道新消息 → 全链上月表；token 在 discord-bot-token.txt，gitignored；本地基线缺失时自动从 wiki 重建——管线代码在 `nekoquote/` 包，运行期数据在 gitignored 的 logs/） |
| `scripts/verify_wiki_access.py` | 只读诊断：验证 pywikibot 库与裸 API 两条 wiki 通路和凭据是否有效，期望输出 `ALL CHECKS PASSED` |
| `scripts/recent_changes_watchdog.py` | 最近改动巡查 watchdog：rcid 水位线去重（状态 `.cache/rc_watchdog.json`，已 gitignore），排除 IchiSanNi 全部编辑（含无 flag 的手动编辑，修改时已自查）与其他账号的 bot 标记编辑。输出两段：NEW_CHANGES 逐条清单、MERGED_DIFFS（同用户同页**相邻**连续编辑合并后的 diff 增删行，⟦⟧/〔〕 标行内增删，超长截断标注）。曾有 RED_LINKS 红链实测段，2026-08-06 移除——中文站有繁简自动转换，繁体写法链接会被 MediaWiki 自动解析到简体页面，检测几乎只产误报。取数/解析固定由脚本完成（曾由 LLM 现写代码，踩过手工分组漏项、td class 多值匹配抓空、stdout 截断三个坑）；水位线在 diff 全部拉取成功后才推进，失败非零退出下轮重试，不静默漏审。区间与触发时间解耦：不设时间窗口，翻页拉取至水位线即停——漏触发（任意停机时长）、手动触发、改间隔均安全，改动超单页 500 条也不漏。由 Hermes cron job「wiki 最近改动自动巡查」每天 10:00 调用（profile `scripts/` 下同名片是 wrapper），LLM 只做判断与分流，发现问题发 Discord `#wiki编辑事务【qq互联】`；但 NiSanIchi（维护者本人的个人账号，与 bot 账号 IchiSanNi 勿混淆）的改动发现问题时只在 cron 回复中说明，不发 Discord。报告范围：机翻覆盖/语法破坏/恶意内容（译名不巡查——登记别名由 translation 任务自动归一） |
| `docs/` | `todo.md`（跨任务待办与待决策项）、`wiki-access.md`（读写配方）、`cloudflare-429.md`（限流根因与对策）、`template-usage-audit.md`（零引用模板审计工作流）、`templates.md`（模板盘点数据与技术约定）、`modules.md`（Module/Lua 审查结论与约定）、`pywikibot-update.md`（submodule rebase 上游流程）、`pywikibot-scripts.md`（自带脚本选用速查）、`nekoquote-incremental.md`（NekoQuote 增量收录：循环任务 re0_nekoquote 自动同步为主，Discrub 导出 + 一键管线为手动备份） |
| `families/re0_family.py` | re0 family 定义，12 个语言子站（de/en/es/fr/it/ko/nl/pl/pt-br/ru/uk/zh 都在 rezero.fandom.com，en 无路径前缀其余 `/<code>`）。注意 family 文件注释说 "do not commit" 但本项目故意提交了。另有 `w_family.py`（community.fandom.com，即 Fandom 中央站 `w:` 前缀），同理会故意提交 |
| `tests/` | 离线单测（pytest，不触 wiki）：译名表一致性（RULES 与 re0_move 共享）、watchdog 纯函数、re0_gallery `merge_galleries`、re0_move `resolve_move`、re0_fixing_redirects 链接改写/链解析、run_job 命令拼装。模块经 `tests/repo_loader.py` 按路径加载（scripts/ 非包） |
| `pwb/` | submodule（pywikibot fork；目录不叫 `pywikibot` 是为了避免根目录运行时以 namespace package 遮蔽已安装的包），含 re0wiki 定制补丁（见下） |

pywikibot 自带脚本（movepages/add_text/delete/listpages/category/template 等）的选用速查见 `docs/pywikibot-scripts.md`——能用现成脚本就别手写。

## wiki 侧结构（zh 站）

- **伪命名空间**：没有注册自定义 namespace，文章页靠标题前缀分类（全在主空间）。登记前缀的唯一权威清单是 `user-fixes.py` 的 `PSEUDO_PREFIXES`：`角色:`、`术语:`、`小说:`、`漫画:`、`动画:`、`游戏:`、`音乐:`、`设定集、画集:`（`存档:` 已于 2026-08-15 随存档页全删退役——P7，语录内容迁入 Module:NekoQuote 月表）。**收录范围 2026-08-09 起对齐 en 站**（此前是 es 与 en 的并集）：54 个 `声优:` + 8 个 `制作人员:` + `动画:异世界四重奏`（en 均无对应条目）及其 2 个 /猫语子页全部删除，56 处链入改指维基百科（zh>en>ja；Fandom 无 zh 维基 interwiki 前缀，`[[wikipedia:zh:X|..]]` 经 en.wikipedia 301 跳转、渲染为普通蓝链；2026-08-18 全站外链审计后把有 zh 条目的 16 处 en/es 链接（15 个目标）升级为 zh，剩 5 处无 zh 条目保持 en），零引用的 Infobox seiyu/staff、Twitter、MG 与 5 个空分类一并删除，两前缀自 Module:Title 与本清单同步取消登记。前缀只认简体：Module:Init 按简体前缀自动分类，繁体前缀不会入分类；繁体前缀页（`小說:`/`術語:`）已于 2026-07-31 清零（当时仅剩 4 个零链入重定向，已删除，`logs/delete_traditional_prefix_redirects.py`）。原 `特典:` 前缀已废（唯一页面 `特典:劇場前惡意` 已移入 `小说:` 并留重定向）；英文前缀页（`Re:`、`Sword Demon Love Story:` 等）是待整理的搬运残留。改前缀 = 移动页面，走 bot 而非手动。前缀审计可跑 `scripts/scan_title_prefixes.py`。
- **页首模板**：`{{Init}}`（`{{#invoke:Init|main}}`，Tab 系统初始化，几乎每篇文章都有）+ `{{To do}}`（归入 `Category:待修撰`，大部分文章常态携带，不是积压事故）。`/图库` 子页由 bot 自动同步、无需人工整理，**不带** `{{To do}}`（2026-07-31 批量移除）。`/猫语` 子页由关键词查询生成、无可修改内容，同样**不带** `{{To do}}`（2026-08-16 批量移除，200 页）。**同步配对机制**：re0_gallery 经 /图库 页的 en 链接 `iterlanglinks` 找 en 图库并整段覆盖——**摘掉 en 链接即退出自动同步**（无 en 链接的图库页：角色：維格·阿德加德/图库、角色：沃尔夫/图库——后者 2026-08-08 摘链恢复为 Wolf 专属内容，此前被 Salum 图库覆盖过，见跨语言链接条）。新搬运页另有 `[[Category:新搬运待整理]]`（见 fork 定制节），人工整理后摘除——该分类是真实待办队列。页首顺序固定：`{{Init}}` → `{{To do}}` → `{{Tab/...}}`（部分页才有）→ 其他内容。
- **模板体系**：`Tab/*` 子页族（每部作品一套页面顶部标签，配 `{{Tab}}` 使用）；信息框统一 `Infobox X` 命名（X 小写英文）：book/character/anime/music/bd/game/event/battle 共 8 个（seiyu/staff 已于 2026-08-09 随声优/制作人员条目删除而删除，见伪命名空间条；更早 2026-07-29 由 Anime/Seiyu/Music/Re:Zero BD/Staff/Re:Zero Game 改名而来，en 同名的 4 个旧名由 jobs 模板替换接管；未用的 album/episode/item/location/quest 与母版 `Infobox` 已于 2026-07-28 删除）；注音族 `Ruby-zh-ja`（中日双语 ruby）/`R`/`Ruby-ja`（零引用的 Ruby-zh-b/zh-p 与 R/ja 已于 2026-07-28 删除）；`QUOTE`（页首引语 + voice 音频）。全站模板索引在 wiki 的 `ReZero Wiki:模板`，模板信息分层（wiki/仓库各存什么）、盘点数据与技术约定见 `docs/templates.md`。
- **导航**：`MediaWiki:Wiki-navigation` 内容为 `{{#invoke:Wiki-navigation|main}}`——wiki 上的 Module:Wiki-navigation 用 `mw.title.getContent` 实时读取 `Project:Wiki-navigation` 并按历史 re0_nav.py 的规则编译（非 `*` 行丢弃、层级 +3、词干剥 `[]`、裸词干补 `|`）。2026-08-16 由 bot 定期编译任务换装（实测 #invoke 在该消息中生效，展开输出与原编译产物逐字节一致；templatelinks 已登记 Project 页依赖，源页编辑会使消息解析缓存失效）。**模块返回值不会被二次展开模板**（expandtemplates/action=parse 均实证）——导航源里写模板会原样漏出，须直接写展开后的内容（`{{Seirei}}` 已内联为 `精<!--nobot-->灵`）。验证渲染改动要登录后查看：Fandom 对未登录用户的缓存刷新慢，匿名视图可能长期是旧内容。原脚本 `scripts/re0_nav.py` 已删除（git 历史可查）。
- **导航简繁转换（Custom-nav- 消息）**：导航显示文本一律写成 `[[目标|Custom-nav-<英文 key>]]`（裸标签直接 `Custom-nav-<英文 key>`），显示值按**界面语言（uselang，与 ?variant= 无关——variant 只转页面正文）**取 `MediaWiki:Custom-nav-<key>/zh-hans` / `/zh-hant`；缺 hant 时自动 fallback 到 hans 内容（2026-08-16 全量迁移完成：975 个 key，同日加 nav- 前缀以区分用途——系统消息惯例；一次性脚本在 `scripts/oneoff/nav_custom_*` 与 `nav_prefix.py`）。约定：hans 值**不包** as-is——fix:translation 的 generator_more 含 mediawiki 命名空间，译名归一会自动修正；hant 值包 `<div class="as-is">` 防被归一成简体，由繁体使用者维护。key 惯例取 en 站条目名（结构性标签拟名），`/ `需消毒为 ` - `（否则被子页化）。导航片段缓存独立于页面缓存：purge 消息页或内容页都不立即刷新（实测），等其 TTL 自愈。写法约定同步在 Project:Wiki-navigation 页首「简繁转换」节。
- **子页后缀**：注册点是**两处**，改动必须同步——`Module:Title` 的 `suffixes` 数组（Init 分类与 Tab 探测的数据源）+ `Template:Tab/Content` 的 前缀×后缀 分类矩阵（一个后缀 = 一整行 13 个分类）。现有后缀：关系/梗概/图库/猫语/语录/改动/攻略/短篇。`梗概` 统一对应 en /Synopsis——角色生平与作品剧情不分两个后缀（2026-08-08 合并：原 zh 原创的 `经历` 后缀整体并入 `梗概`，27 个 `角色:X/经历` 已移至 `/梗概` 并留重定向，`分类:角色经历`→`分类:角色梗概`；en 本来就只有 /Synopsis 一个后缀，合并后与 en 1:1）。`攻略` 语义是**玩法数值数据**（在用实例：`游戏:INFINITY/攻略`），不是剧情路线——en 的 /Routes 类内容无对应后缀（2026-08-08 裁决：不为单个条目新增矩阵行，`游戏:Lost in Memories/梗概` 保持 en /Synopsis+/Routes 合并，是全站唯一的多对一例外）。
- **跨语言链接**：页尾语言链接块按 de/en/es/fr/pl/pt-br/ru/uk 字母序。**审计的正确方式**（用户定，logs/audit_langlinks_v3.py，只读）：en→zh 映射 = 遍历 en 主空间每个非重定向页 → zh 同名页 → 最终重定向目标（transferbot 保原名搬运、人工移到中文名留重定向的链路保证同名页存在）；zh→en 映射 = 全页**源码**扫 `[[en:...]]`（不用 langlinks 派生表，见坑节）；双向比对。2026-08-08 首跑+修复后复跑：1852 en 正文页全部有 zh 同名页（未搬运=0），1850 一致；剩余例外均为裁决后的有意状态：首页用 `[[en:]]` 空目标特例（脚本不匹配此写法，会恒报 missing）、游戏:Lost in Memories/梗概 是 en /Synopsis+/Routes 两页合并（链接取 Synopsis，唯一多对一）、沃尔夫与沃尔夫/图库为 zh 原创条目（en 把 Wolf 并入 Salum Pristis 但 zh 不跟随合并，en 链接已摘除——裁决：页面合并/拆分跟随 en，但 zh 编者自行编写的内容比 en 更充实的条目可作为 zh 原创保留）。**子页链接规则**：/梗概 等子页只在 en 有对应子页时带 en 链接（/Synopsis↔梗概 等）；en 无对应子页时（如菲莉丝/梗概——en 的历史在 Ferris 主页面章节里）子页不带链接，更不用 `[[en:X#章节]]` 形式（2026-08-08 摘除），否则一个 en 条目会被多个 zh 页声称对应。角色正史/游戏版本拆分（琉兹本体/复制体、狄加/莎克拉/希蓉的 Game Canon 页）经复查系跟随 en 的既有拆分（en 有 /Game Canon 与 (original)/(copy) 页），1:1 满足。曾修复： Blessing Day en 名重定向错指（Rem-rin's Day→雷姆琳之日）、3 组重复页转重定向（An Ordinary Day / Hansel and Gretel / World Guide）、Star Chanter 重定向页摘链接。补链接只加到最终目标页、并入既有语言链接块的字母序位置。en 子页命名：/Synopsis（=梗概）、/Relationships（=关系）、/Image Gallery（=图库）；en 不收声优/制作人员条目、无 /Quotes 类子页；`/猫语`、`/改动`、`存档:`、`鼠色猫语录` 是 zh 原创无对照。
- **状态页**：wiki 上 `User:IchiSanNi/jobs` 手工维护，与 `jobs/jobs.py` 的任务对应。格式约定（2026-08-14 重整）：任务以列表项呈现（粗体任务名 + 一句话描述），不展示命令行（非维护者不需要）、不记「最后检查于」（易过时）。
- 译名表与译名工作流见下节；`<div class="as-is">` 保护机制见 fork 定制节。

## 读写 wiki

- **红线**：写入测试只允许在 zh 站的测试页面——`User:IchiSanNi` 的所有子页面，或任意命名空间的 `Sandbox`/`沙盒` 页及其子页面；正式批量写入需用户明确指示；**绝不写 zh 以外的语言站**；不读不打印 `user-password.py`（pywikibot 会自己加载）。
- 以 pywikibot 库方式为主，在仓库根目录跑（`user-config.py`/`families/` 都在根目录）：

```python
import pywikibot

site = pywikibot.Site("zh", "re0")   # 读任意语言站都可以，写只限 zh
site.login()                          # 写入前必须
assert site.user() == "IchiSanNi"
p = pywikibot.Page(site, "角色:菜月·昴")
p.text                                # 读
p.save(summary="...", bot=False, minor=False)  # 手动编辑（save 默认 bot=True/minor=True，须显式关）；批量脚本用 bot=True
```

- 完整配方（pagegenerators 生成器、simple_request 裸 API、BotPassword 逃生舱、实测坑）见 `docs/wiki-access.md`；凭据有效性验证跑 `scripts/verify_wiki_access.py`。

## pywikibot fork 的定制（rebase 上游时必须保留）

每个定制一个独立提交（2026-07-27 起由单个大 commit 拆分；历史上另有 `import regex as re` 全库替换、requirements 加 regex、redirect offset、TokenWallet csrf-first、fixes 默认 generator 五个补丁，2026-07 验证不再必要后摘除——generator 已改为在 `jobs/jobs.py` 里显式传 `starts_base`；transferbot 搬运标记两个补丁 2026-08-13 随 re0_transferbot 换装摘除）：

- `textlib.py` + `fixes.py`：新增 `keep` 标签 = `<div class="as-is">...</div>`，textlib 加 regex，HTML/syntax/isbn/specialpages fixes 的 exceptions 里加 `keep` —— wiki 上可以用这个 div 保护内容不被 bot 改。
- `fixes.py`：HTML fix 把 `<br>` 归一到不闭合形式（MediaWiki 渲染等价，不闭合是本 wiki 惯例）。
- `fixes.py`：syntax fix 注释掉外链竖线规则（误报太多）。
- `textlib.py`：`replaceLanguageLinks` 的 CategorySelect 分支加守卫，模板页（含子页）改走 noinclude 感知分支——否则 `getCategoryLinks` 不识别 `<noinclude>` 包裹，会把分类从 noinclude 里拽出来放到页尾（Fandom 有 CategorySelect 扩展，cosmetic_changes 的 standardizePageFooter 必踩）。
- `_filepage.py`：下载 URL 加 `&format=original`，否则 Fandom API 返回 webp。同时必须去掉上游的 suffix 调整：它从 URL 路径取扩展名，而 Fandom URL 以 `/revision/latest` 结尾（无扩展名），留着会把下载文件的真扩展名剥掉（Wikimedia 的 URL 路径以文件名结尾，所以上游留着没事）。
- `noreferences.py`：zh 参考资料段标题加「注释与外部链接」；预载带 `pageprops`——`skip_page` 对每页调 `isDisambig()`（`use_disambigs=False`）读 `prop=pageprops`，默认预载不含它导致每页一次查询（全扫 ~18 min），带上后随内容同批缓存（~25 s）。背景：本站按对齐 en 的策略不加 `__DISAMBIG__`（en 不加，zh 单加会破坏 interwiki；用户尝试给 en 加被回退），该检查恒为空——故选零成本的语义保留方案而非改 `use_disambigs=None` 的假设性跳过。
- `scripts/redirect.py`：`fix_moved_broken_redirects` 加移动日志环检测（`seen` 集合沿递归传递）——上游对 `moved_target()` 链的递归无环检测，A↔B 往返移动且两页均不存在时无限递归直至 RecursionError。

## 译名维护工作流（最常见的改动）

1. 译名表的给人看版本在 wiki 上（`ReZero Wiki:译名表`，含选取规则：官方简中 > 官方繁中 > 民间 > 保留英文）；bot 实际执行的唯一权威是 `user-fixes.py`，两边手动同步。用户通过 GitHub Issues 报译名问题（模板：新增/修改译名、遗漏替换、错误替换），wiki 页面明确告诉用户「不要手动移动页面或替换文本，提议通过后 Bot 会批量修改」。
2. 改译名 = 改 `user-fixes.py` 里 `translation` fix 的两个列表：主列表 `translation_names`（`p2o()` 自动生成别名正则）+ 手动替换组 `translation_manual`。拿不准相似字符覆盖面的，先 `python main.py fix:translation -s` 干跑。标题含别名的页面由 `re0_move` 任务用同一张表自动移动，无需另行处理。
3. 提交信息遵循 Conventional Commits：`feat(translation): add X` / `fix(translation): 旧 -> 新`。
4. `_ = [...]` 列表是「特判太麻烦、明确不处理」的别名，别删。

## 坑

- **Fandom 派生表（langlinks 等）的读取可能与页面源码不一致，且与 HTTP 缓存无关**（api.php 响应头 `no-store`、无 Age/X-Cache，已实证排除 CDN 缓存）。2026-08-08 观测：langlinks 对希洛洛返回过源码史上从未存在的值（Toneriko，115 个修订逐版验证源码始终是 Tonerico）、对菜月父母返回过「无 en 链接」（实际 2021-02 起就有，当天两页零编辑），数小时后零编辑自愈——指向 Fandom 基础设施侧的派生表重建/迁移，外部无法定位。**审计「页面有没有某链接/某分类」一律扫源码（rvprop=content），不依赖 langlinks/categories 等派生表**。
- **Lua 信息框参数里的 `[[链接]]` 不进 links 表**（2026-08-13 实证：动画:第79集 等 4 页，源码有 `| previous = [[X]]` 而 prop=links 无，页面数天至数月未编辑）。#invoke 参数文本不经过链接登记——`linkedPages()`/`prop=links`/`linkshere` 对这类链接系统性漏报，依赖它们的工具（如上游 fixing_redirects）会永远漏改。链接审计/改写必须扫源码。其余任务已审计无此险（同日）：category remove/template replace（被操作对象均顶层调用）、redirect-do/br（redirect 表抽查一致）、interwiki/replace 各 fix/re0_move/noreferences（均源码驱动）。
- **Fandom 登录会话对读路径不可靠**（2026-08-13 实证）：cookie jar 会话会被同账号的跨语言站流量服务端作废（互踢，见 user-config.py 注释），而 pywikibot `login()` 有 jar 即跳过重新认证——于是依赖 apihighlimits 的 500 titles/批 prop 查询会间歇 `toomanyvalues: limit is 50`（同一 jar 连跪数次、显式重新登录后秒恢复）。pywikibot 发现会话匿名时会打 `Logged in as 'IP' instead of '...'. Forcing re-login` 自愈，但可能发生在失败之后。规则：**读路径一律匿名可达**——列表查询（allpages/allimages 的 limit 参数匿名上限即 500）或 ≤50 titles/批的 prop 查询；批量存在性判断用「全量标题集内存比对」（~21 次列表请求）而非逐批 prop=info（50/批更多请求且 500/批不稳）。**写路径无需防御**（同日沙盒实证）：save 的 userinfo 检查会发现匿名会话并 Forcing re-login 自愈；兜底失败形态是响亮异常（badtoken/permission）→ 非零退出停机，不存在静默损坏。且互踢本身不稳定（同日 en 登录未再踢掉 zh 会话），被踢频率低于预期。
- MediaWiki API `formatversion=2` 下 recentchanges 的 `bot`/`new`/`minor` 键**恒存在**（值为 true/false），过滤必须判断值而不是键存在性——`"bot" not in c` 会把所有编辑都滤掉。
- `run_job` 给子进程注入 `PYTHONIOENCODING=utf-8`，管道输出按 UTF-8 解码——不再依赖 mbcs/系统 ANSI 代码页（历史上 `67fd586` 用 mbcs 治 GBK 乱码，2026-07 改为源头强制 UTF-8）。循环模式子进程继承控制台走 WriteConsoleW 宽字符 API，显示不受此变量影响。（`shell=True` 已去除——它 2026-01 加入时是裸 `python` 解释器解析错误的 workaround，`sys.executable` 绝对路径后动机已消。）
- Windows 上 ruff 无法检查可执行位，shebang 文件的 EXE001 只在 Linux（CI）触发——新增带 shebang 的脚本记得 `git update-index --chmod=+x`。
- `scripts/recent_changes_watchdog.py` 由 Hermes cron 经 runpy 跑在 Hermes 自带的 Python 3.11 下（不走本项目 3.14 venv），语法必须兼容 3.11：pyproject.toml 里对该文件设了 ruff `per-file-target-version = py311`，否则 ruff 0.16+ 会按 requires-python 3.14 把多异常 except 的括号脱掉（PEP 758），脚本在 3.11 下起不来（50ae561→708571f 的教训）。
- pwb.py 对**用法级失败**（脚本名拼错、replace 缺替换对、未知 pwb 参数）退出码仍为 0——`wrapper.py` 的 `execute()` 返回 False 只打印用法文档；只有未捕获异常（崩溃类：网络断开/登录失败/脚本 bug）才非零退出。因此 `run_job` 的「失败即退出」覆盖的是崩溃类失败；用法级失败要靠 `-s` 干跑先看输出。
- Fandom 已接入 Cloudflare：失速会被 429 且 `Retry-After` 高达数千秒。`user-config.py` 保持 `minthrottle>=0.25`、`put_throttle>=2` 预防，根因与对策见 `docs/cloudflare-429.md`。
- `jobs/jobs.py` 的 interwiki 任务不带 `-auto`（由 run_job 补），直接手敲 pwb.py 跑要记得加。
- user-fixes 里写「不跨模板边界」的作用域正则要当心两处解析坑（2026-08-11 fix:para 死行删除规则实证）：`\{\{}` 不是 `{{`——`\}` 也是字面量，该写法匹配的是三字符 `{{}`，正确写法是 `(?!\{\{)`；DOTALL 下值匹配用 `.*` 会吞到文末，行值一律 `[^\n]*`。验证这类规则必须断言 diff 只删目标行（仅看 `new != text` 会漏掉截尾事故）。
- 上游 transferbot **不接受 `-always`**（加了会报错）；它不加也会自动覆盖目标页。jobs 已于 2026-08-13 换装 `re0_transferbot`（无此参数问题），此坑仅在手跑上游脚本时相关。
- `touch -random:128` 在任务列表末尾，是为了触发缓存刷新，不是无意义操作。
- 常驻方式：本机跑 `python main.py`（无限循环所有任务）。
- 在线状态页：wiki 上 `User:IchiSanNi/jobs`。
