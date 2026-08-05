# AGENTS.md — wiki-bot

Re:Zero Fandom Wiki（<https://rezero.fandom.com/zh>）的维护机器人，基于 Pywikibot。
主要工作：把英文站内容同步到中文站，并对中文站做译名/格式规范化。

## 知识归处（仓库文档 vs Hermes skill）

- 与本仓库/wiki 绑定的知识**只写进本仓库文档**（AGENTS.md 放精简规则与指针，`docs/` 放详细配方），随 git 提交——这是唯一权威来源。**不要存为 Hermes skill**：skill 在仓库之外、不随代码走，曾经因此漂移出相互矛盾的副本。任务结束时的「save as skill」惯例对本仓库知识不适用，改为写进 `docs/`。
- 判断标准是「知识从哪里来、在哪里验证」，不是「理论上能不能用在别处」：源自本仓库实践的 pywikibot / Fandom / Cloudflare 限流 / 模板审计等知识，即使看似通用，**也算本仓库知识**，进 `docs/`。（有过教训：曾被重新框架成「通用 Fandom 知识」存成 skill。）
- 分工：把知识写进 `docs/` 是**主 agent**（有文件工具）的职责，任务收尾时主动做。回合结束后的后台 skill review（只有 memory/skill 工具的 fork agent）对本仓库知识应**直接放弃**（'Nothing to save'）——它碰不了仓库文件，不要建/改 skill，也不要把知识代为塞进 memory。
- skill 只用于跨仓库/跨资源的流程（例如译名核验横跨 OCR 语料库与 gh issue）。新建 skill 前检查内容不与 `docs/` 重复。

## 环境

- **Python 3.14**（`.python-version`，`pyproject.toml` 要求 `>=3.14`），uv 管理，有 `uv.lock`。
- 安装：`uv sync`（`default-groups = "all"`，会把 dev + pwb 组全装上）。
- 运行脚本：`PYTHONPATH= .venv/Scripts/python.exe <script>`（Windows 上 Hermes 会注入指向自身 venv 的 PYTHONPATH，必须清空，否则 import 错包）。
- **pywikibot 是 git submodule**（fork：`github.com/re0wiki/pywikibot`，upstream 是 wikimedia/pywikibot）。克隆要 `--recurse-submodules`（否则 `uv sync` 会因路径缺失失败）。更新 submodule 后提交信息写 `chore: update pywikibot`。
- pywikibot 通过 `[tool.uv.sources]` 以 **editable 方式从 submodule 路径装入 venv**（`{ path = "pywikibot", editable = true }`），submodule gitlink 是唯一版本锁，无需再同步 uv.lock 里的 commit。`pyproject.toml` 里的 `[tool.ty.environment] extra-paths = ["./pywikibot"]` 是必须的：ty 无法静态解析 PEP 660 editable finder，删掉会导致全项目 unresolved-import。
- Lint：`ruff check` / `ruff format`（`pyproject.toml` 里 extend-exclude 了 pywikibot 子模块、logs/ 与 scripts/oneoff/（一次性脚本归档，不再运行），不要给它们 lint；md 文件也被排除以保留手工对齐的代码块注释）。类型检查用 `ty`（`src.exclude` 同样排除 pywikibot、logs/ 与 scripts/oneoff/，正常应为 0 诊断）。
- 离线单测：`pytest tests/`（不触 wiki；覆盖译名表一致性、re0_nav、watchdog 纯函数）。注意 `python -m pytest` 会把仓库根注入 sys.path，导致根目录的 `pywikibot/` 目录以 namespace package 遮蔽已安装的包（同理，仓库根下 `python -c "import pywikibot"` 也是坏的）——tests/conftest.py 已处理；其他临时脚本要么从子目录跑，要么先清 sys.path。Wiki 侧改动验证方式仍是 `-s/--simulate` 干跑 + 上 wiki 查编辑结果。
- Secrets：`user-password.py`（BotPasswords，gitignored，勿读勿提交）。

## 架构地图

| 文件 | 作用 |
|---|---|
| `main.py` | 循环任务入口。`python main.py <任务名或编号>` 跑单个任务（编号随插入平移，名字稳定，`-h` 列全部），`-s` 模拟；`231` = 无限循环所有任务。任务失败（子进程非零退出）即以相同码退出等待人工修复，不继续后续任务 |
| `jobs/jobs.py` | 任务列表（`Job(name, cmd)`，name 是稳定引用；fix 类任务名与 `-fix:` 参数一致），分 6 组：跨站同步 → 整理新搬运页 → 模板维护 → 重定向 → 语法规范化 → 内容规范化 → 杂项 |
| `jobs/run_job.py` | 子进程包装：`build_cmd` 拼 `sys.executable pywikibot/pwb.py ...`（不用裸 `python`，PATH 上可能是无项目依赖的其他版本），自动加 `-always`（interwiki 加 `-auto -force`，transferbot 不加） |
| `jobs/starts.py` | namespace → `-start:ns:!` 生成器参数。`ns_base`=主/project/template/category，`ns_more` 再加 module/mediawiki |
| `user-config.py` | pywikibot 配置：family=re0, mylang=zh, 账号 IchiSanNi（只给 zh 配账号，外站匿名读——Fandom 现在跨站登录会互踢会话，见文件内注释） |
| `user-fixes.py` | **核心资产**。自定义 fix 集：misc/date/anti-ve/para/gallery/heading/**translation**/HTML/syntax 等。`translation` 用「相似字符 → 正则」机制（`f()`/`p2o()`/`p2n()`）把几百个别名归一到标准译名 |
| `scripts/` | 常驻/可复用脚本：5 个 `re0_*` 任务脚本（见下行）、`recent_changes_watchdog.py`、诊断（`verify_wiki_access.py`/`test_pwb_throttle.py`）、429 探测 `probe_*`（见 `docs/cloudflare-429.md`）、审计工具（`dump_modules.py`/`template_inventory.py`/`template_complexity.py`/`recheck_template_usage.py`/`scan_title_prefixes.py`/`check_css_imports.py`）、`sync_jobs_status_page.py`。`scripts/oneoff/` 是已完成任务的一次性脚本归档（pwb.py 按名字找不到，重跑要传路径）。docs 里的 `logs/xxx.py` 引用是历史出处——`logs/` 整体 gitignore，不在仓库内 |
| `scripts/re0_*.py` | 5 个自定义脚本：gallery（用 en 站图库覆盖 zh）、image（图片差量同步）、nav（编译 Wiki-navigation）、redirect（给 `前缀:词干` 页建裸词干重定向）、move（标题命中 translation 规则的页面自动移到简体标准名，留重定向；与正文替换的差异是标题一律归一简体、不保留繁体；目标已存在时跳过待人工合并） |
| `scripts/verify_wiki_access.py` | 只读诊断：验证 pywikibot 库与裸 API 两条 wiki 通路和凭据是否有效，期望输出 `ALL CHECKS PASSED` |
| `scripts/recent_changes_watchdog.py` | 最近改动巡查 watchdog：rcid 水位线去重（状态 `.cache/rc_watchdog.json`，已 gitignore），排除 IchiSanNi 全部编辑（含无 flag 的手动编辑，修改时已自查）与其他账号的 bot 标记编辑。输出三段：NEW_CHANGES 逐条清单、MERGED_DIFFS（同用户同页**相邻**连续编辑合并后的 diff 增删行，⟦⟧/〔〕 标行内增删，超长截断标注）、RED_LINKS（新增内容红链实测，已跟重定向）。取数/解析固定由脚本完成（曾由 LLM 现写代码，踩过手工分组漏项、td class 多值匹配抓空、stdout 截断三个坑）；水位线在 diff 全部拉取成功后才推进，失败非零退出下轮重试，不静默漏审。区间与触发时间解耦：不设时间窗口，翻页拉取至水位线即停——漏触发（任意停机时长）、手动触发、改间隔均安全，改动超单页 500 条也不漏。由 Hermes cron job「wiki 最近改动自动巡查」每天 10:00 调用（profile `scripts/` 下同名片是 wrapper），LLM 只做判断与分流，发现问题发 Discord `#wiki编辑事务【qq互联】`；但 NiSanIchi（维护者本人的个人账号，与 bot 账号 IchiSanNi 勿混淆）的改动发现问题时只在 cron 回复中说明，不发 Discord。报告范围：机翻覆盖/语法破坏/恶意内容（译名不巡查——登记别名由 translation 任务自动归一） |
| `docs/` | `todo.md`（跨任务待办与待决策项）、`wiki-access.md`（读写配方）、`cloudflare-429.md`（限流根因与对策）、`template-usage-audit.md`（零引用模板审计工作流）、`templates.md`（模板盘点数据与技术约定）、`modules.md`（Module/Lua 审查结论与约定）、`pywikibot-update.md`（submodule rebase 上游流程）、`pywikibot-scripts.md`（自带脚本选用速查） |
| `families/re0_family.py` | re0 family 定义，12 个语言子站（de/en/es/fr/it/ko/nl/pl/pt-br/ru/uk/zh 都在 rezero.fandom.com，en 无路径前缀其余 `/<code>`）。注意 family 文件注释说 "do not commit" 但本项目故意提交了。另有 `w_family.py`（community.fandom.com，即 Fandom 中央站 `w:` 前缀），同理会故意提交 |
| `tests/` | 离线单测（pytest，不触 wiki）：译名表一致性（RULES 与 re0_move 共享）、re0_nav 编译规则、watchdog 纯函数、re0_gallery `merge_galleries`、re0_move `resolve_move`、run_job 命令拼装。模块经 `tests/repo_loader.py` 按路径加载（scripts/ 非包） |
| `pywikibot/` | submodule，含 re0wiki 定制补丁（见下） |

pywikibot 自带脚本（movepages/add_text/delete/listpages/category/template 等）的选用速查见 `docs/pywikibot-scripts.md`——能用现成脚本就别手写。

## wiki 侧结构（zh 站）

- **伪命名空间**：没有注册自定义 namespace，文章页靠标题前缀分类（全在主空间）。登记前缀的唯一权威清单是 `user-fixes.py` 的 `PSEUDO_PREFIXES`：`角色:`、`术语:`、`小说:`、`漫画:`、`动画:`、`游戏:`、`音乐:`、`设定集、画集:`、`声优:`、`制作人员:`、`存档:`。前缀只认简体：Module:Init 按简体前缀自动分类，繁体前缀不会入分类；繁体前缀页（`小說:`/`術語:`）已于 2026-07-31 清零（当时仅剩 4 个零链入重定向，已删除，`logs/delete_traditional_prefix_redirects.py`）。`特典:` 是唯一的未登记前缀（仅 `特典:劇場前惡意` 一页，待整理）；英文前缀页（`Re:`、`Sword Demon Love Story:` 等）是待整理的搬运残留。改前缀 = 移动页面，走 bot 而非手动。前缀审计可跑 `scripts/scan_title_prefixes.py`。
- **页首模板**：`{{Init}}`（`{{#invoke:Init|main}}`，Tab 系统初始化，几乎每篇文章都有）+ `{{To do}}`（归入 `Category:待修撰`，大部分文章常态携带，不是积压事故）。`/图库` 子页由 bot 自动同步、无需人工整理，**不带** `{{To do}}`（2026-07-31 批量移除，唯一例外是无 en 链接的 `角色:維格·阿德加德/图库`）。新搬运页另有 `[[Category:新搬运待整理]]`（见 fork 定制节），人工整理后摘除——该分类是真实待办队列。页首顺序固定：`{{Init}}` → `{{To do}}` → `{{Tab/...}}`（部分页才有）→ 其他内容。
- **模板体系**：`Tab/*` 子页族（每部作品一套页面顶部标签，配 `{{Tab}}` 使用）；信息框统一 `Infobox X` 命名（X 小写英文）：book/character/anime/music/bd/game/seiyu/staff/event/battle 共 10 个（2026-07-29 由 Anime/Seiyu/Music/Re:Zero BD/Staff/Re:Zero Game 改名而来，en 同名的 4 个旧名由 jobs 模板替换接管；未用的 album/episode/item/location/quest 与母版 `Infobox` 已于 2026-07-28 删除）；注音族 `Ruby-zh-ja`（中日双语 ruby）/`R`/`Ruby-ja`（零引用的 Ruby-zh-b/zh-p 与 R/ja 已于 2026-07-28 删除）；`QUOTE`（页首引语 + voice 音频）。全站模板索引在 wiki 的 `ReZero Wiki:模板`，模板信息分层（wiki/仓库各存什么）、盘点数据与技术约定见 `docs/templates.md`。
- **导航**：`MediaWiki:Wiki-navigation` 由 `Project:Wiki-navigation` 经 `scripts/re0_nav.py` 编译生成，勿手动编辑。
- **状态页**：wiki 上 `User:IchiSanNi/jobs` 手工维护，与 `jobs/jobs.py` 的任务对应；`scripts/sync_jobs_status_page.py` 只同步 template 替换任务那一行，其余改动要手动改 wiki 页。
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
p.save(summary="...")                 # 手动编辑不加 bot flag；批量脚本用 bot=True
```

- 完整配方（pagegenerators 生成器、simple_request 裸 API、BotPassword 逃生舱、实测坑）见 `docs/wiki-access.md`；凭据有效性验证跑 `scripts/verify_wiki_access.py`。

## pywikibot fork 的定制（rebase 上游时必须保留）

每个定制一个独立提交（2026-07-27 起由单个大 commit 拆分；历史上另有 `import regex as re` 全库替换、requirements 加 regex、redirect offset、TokenWallet csrf-first、fixes 默认 generator 五个补丁，2026-07 验证不再必要后摘除——generator 已改为在 `jobs/jobs.py` 里显式传 `starts_base`）：

- `textlib.py` + `fixes.py`：新增 `keep` 标签 = `<div class="as-is">...</div>`，textlib 加 regex，HTML/syntax/isbn/specialpages fixes 的 exceptions 里加 `keep` —— wiki 上可以用这个 div 保护内容不被 bot 改。
- `fixes.py`：HTML fix 把 `<br>` 归一到不闭合形式（MediaWiki 渲染等价，不闭合是本 wiki 惯例）。
- `fixes.py`：syntax fix 注释掉外链竖线规则（误报太多）。
- `textlib.py`：`replaceLanguageLinks` 的 CategorySelect 分支加守卫，模板页（含子页）改走 noinclude 感知分支——否则 `getCategoryLinks` 不识别 `<noinclude>` 包裹，会把分类从 noinclude 里拽出来放到页尾（Fandom 有 CategorySelect 扩展，cosmetic_changes 的 standardizePageFooter 必踩）。
- `transferbot.py`：搬运时不写编辑历史子页，改为在页首加 `{{Init}}{{To do}}` + 来源链接 + `[[Category:新搬运待整理]]`（namespace 8/828 除外）。
- `_filepage.py`：下载 URL 加 `&format=original`，否则 Fandom API 返回 webp。同时必须去掉上游的 suffix 调整：它从 URL 路径取扩展名，而 Fandom URL 以 `/revision/latest` 结尾（无扩展名），留着会把下载文件的真扩展名剥掉（Wikimedia 的 URL 路径以文件名结尾，所以上游留着没事）。
- `noreferences.py`：zh 参考资料段标题加「注释与外部链接」。

## 译名维护工作流（最常见的改动）

1. 译名表的给人看版本在 wiki 上（`ReZero Wiki:译名表`，含选取规则：官方简中 > 官方繁中 > 民间 > 保留英文）；bot 实际执行的唯一权威是 `user-fixes.py`，两边手动同步。用户通过 GitHub Issues 报译名问题（模板：新增/修改译名、遗漏替换、错误替换），wiki 页面明确告诉用户「不要手动移动页面或替换文本，提议通过后 Bot 会批量修改」。
2. 改译名 = 改 `user-fixes.py` 里 `translation` fix 的两个列表：主列表 `translation_names`（`p2o()` 自动生成别名正则）+ 手动替换组 `translation_manual`。拿不准相似字符覆盖面的，先 `python main.py fix:translation -s` 干跑。标题含别名的页面由 `re0_move` 任务用同一张表自动移动，无需另行处理。
3. 提交信息遵循 Conventional Commits：`feat(translation): add X` / `fix(translation): 旧 -> 新`。
4. `_ = [...]` 列表是「特判太麻烦、明确不处理」的别名，别删。

## 坑

- MediaWiki API `formatversion=2` 下 recentchanges 的 `bot`/`new`/`minor` 键**恒存在**（值为 true/false），过滤必须判断值而不是键存在性——`"bot" not in c` 会把所有编辑都滤掉。
- `run_job` 给子进程注入 `PYTHONIOENCODING=utf-8`，管道输出按 UTF-8 解码——不再依赖 mbcs/系统 ANSI 代码页（历史上 `67fd586` 用 mbcs 治 GBK 乱码，2026-07 改为源头强制 UTF-8）。231 循环子进程继承控制台走 WriteConsoleW 宽字符 API，显示不受此变量影响。（`shell=True` 已去除——它 2026-01 加入时是裸 `python` 解释器解析错误的 workaround，`sys.executable` 绝对路径后动机已消。）
- Windows 上 ruff 无法检查可执行位，shebang 文件的 EXE001 只在 Linux（CI）触发——新增带 shebang 的脚本记得 `git update-index --chmod=+x`。
- `scripts/recent_changes_watchdog.py` 由 Hermes cron 经 runpy 跑在 Hermes 自带的 Python 3.11 下（不走本项目 3.14 venv），语法必须兼容 3.11：pyproject.toml 里对该文件设了 ruff `per-file-target-version = py311`，否则 ruff 0.16+ 会按 requires-python 3.14 把多异常 except 的括号脱掉（PEP 758），脚本在 3.11 下起不来（50ae561→708571f 的教训）。
- pwb.py 对**用法级失败**（脚本名拼错、replace 缺替换对、未知 pwb 参数）退出码仍为 0——`wrapper.py` 的 `execute()` 返回 False 只打印用法文档；只有未捕获异常（崩溃类：网络断开/登录失败/脚本 bug）才非零退出。因此 `run_job` 的「失败即退出」覆盖的是崩溃类失败；用法级失败要靠 `-s` 干跑先看输出。
- Fandom 已接入 Cloudflare：失速会被 429 且 `Retry-After` 高达数千秒。`user-config.py` 保持 `minthrottle>=0.25`、`put_throttle>=2` 预防，根因与对策见 `docs/cloudflare-429.md`。
- `jobs/jobs.py` 的 interwiki 任务不带 `-auto`（由 run_job 补），直接手敲 pwb.py 跑要记得加。
- transferbot **不接受 `-always`**（加了会报错）；它不加也会自动覆盖目标页。
- `touch -random:128` 在任务列表末尾，是为了触发缓存刷新，不是无意义操作。
- 常驻方式：本机跑 `python main.py 231`（无限循环所有任务）。
- 在线状态页：wiki 上 `User:IchiSanNi/jobs`。
