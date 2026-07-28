# 模板信息架构与维护

2026-07 全站模板盘点的结果、实测技术约定、维护待办。
索引页在 wiki 上（`ReZero Wiki:模板`），各模板的用法文档在其 `/doc` 子页，本文件是仓库侧的盘点与待办。

## 信息分层（在哪放什么）

| 信息 | 位置 | 受众 |
|---|---|---|
| 模板用法（参数、示例） | wiki 各模板 `/doc` 子页（由 `Template:Documentation` 渲染进模板页） | wiki 编辑者 |
| 全站模板索引 | wiki `ReZero Wiki:模板` | 人类维护者 + agent 检索 |
| bot 依赖的结构约定 | 本仓库 `AGENTS.md`「wiki 侧结构」（页首顺序、`Init`/`To do` 语义、`as-is` 保护等） | bot 维护者/agent |
| 盘点数据与待办 | 本文件 | bot 维护者/agent |

与译名表（同一份数据的两种表达、需双向手动同步）不同：模板信息**按受众分层、内容不重叠**，两边各存各的、互留指针即可，没有同步负担。

## 盘点数据（2026-07-27 刷新）

盘点脚本：`scripts/template_inventory.py`（只读；输出到 `logs/template_inventory.json`）。
引用量用 `Page.embeddedin()` 逐模板统计（Fandom 不支持 `mostlinkedtemplates`）。

- Template 命名空间共 218 页（2026-07-28 删 8 模板 + 8 `/doc` + 12 零引用重定向、Auto ruby 并入 R、删重定向 Infobox Events 后）：79 顶层模板（其中 5 个重定向）+ 139 子页（`Tab/*` 116 个、`/doc` 22 个）。
- 文档覆盖（74 个非重定向顶层模板）：**30 个有文档，44 个缺失**。文档统一放在 `/doc` 子页（经 `{{Documentation}}` 渲染进模板页）——2026-07-28 已将全部内联形式（`{{Documentation|content=...}}` 8 个、`<noinclude>` 内联说明 1 个）迁入 `/doc`，今后新增模板文档一律用 `/doc` 子页，templatedata 也放 `/doc`（TemplateData 扩展会读，先例 `Blur/doc`）。
- 分类：~~94 个顶层模板无分类~~（2026-07-26 待办 3 已清零，顶层模板全部入树）。
- 引用量：全命名空间**真零引用模板 32 个**（见待办 2，已处理）。

## 技术约定（实测）

- **防分类泄漏靠 `<onlyinclude>`**：把模板体包在 `<onlyinclude>` 里后，标签之外的 `[[Category:...]]`（即使没放 `<noinclude>`）不会被引用页继承。Infobox 系、`Blur` 等都是这个写法。给模板加自身分类时，放 `<noinclude>` 或 onlyinclude 之外均可，但放 onlyinclude **里面**就会泄漏到每个引用页。
- **有意给引用页加分类的模板**（设计如此，勿当 bug「修」掉）：

| 模板 | 给引用页加的分类 |
|---|---|
| `To do` | 待修撰 |
| `Delete` | 请求删除 |
| `Anime` | 剧集 |
| `Re:Zero BD` | 圆盘 |
| `Seirei or Elf` / `Yousei or Elf` | 需复核译名 |
| `Ruby` 系（Ruby、Ruby-ja、Ruby-zh-b/zh-p/zh-ja） | Ruby transclusions with too many parameters（异常追踪） |
| `Category redirect` | 已重定向的分类、尚未清空的已重定向分类 |

- **Fandom 的 templatelinks 不记录 `#tag`/解析器函数参数内的模板调用**：`{{!}}` 在 143 个图库页的 `{{#tag:tabber}}` 参数里真实使用，`embeddedin()` 计数却为 0（2026-07-26 实测）。判「零引用」不能只看 embeddedin，须辅以全站 wikitext grep：用 `generator=allpages` 逐命名空间取 `rvprop=content`，正则搜 `\{\{\s*(subst:\s*)?名称\s*[|}]` 调用形态（含 subst 残留）。
- **元模板分类**（2026-07-27 由「元模板/子模板」两分类合并而成）：`Category:元模板` = 被其他模板调用、不直接用于文章页的模板。判据是机制而非修辞——MediaWiki 模板只有宏展开，没有继承，「派生」（如 `Tab/LN` 预填参数调 `Tab`）与「组成」（如 `T` 调 `T/piece`）是同一种 transclusion，拆两类无可判定标准故合并。成员：`Tab`（noinclude 里声明「用于派生分页模板」+ 挂分类；原 `{{元模板标记}}` 全站仅此一处使用，已内联并删除该模板及旧名重定向 `Template:元模板`）、`MW`、`T category`、`T/piece`、`Documentation`。原 `Category:子模板` 已删除。
- **模板的归类入口可能在其 `/doc` 子页**：`T`、`T/piece` 的分类是 `/doc` 里 `<includeonly>[[Category:...]]</includeonly>` 经 `{{Documentation}}` 注入的，模板本体 wikitext 里搜不到。改挂这类分类后分类表不会立即刷新，需 `page.purge(forcelinkupdate=True)` 触发重解析。

## 待办

### 1. `/doc` 子页补全（工作量大，分批做）

按主空间引用量排序的优先级清单（前 20，做完即覆盖绝大部分实际使用）：

| 引用数 | 模板 |
|---|---|
| 1000+ | Init |
| 719 | Infobox book |
| 692 | Tab |
| 388 | Clear |
| 202 | Kana2Romaji |
| 175 | Anime |
| 145 | R |
| 125 | Seirei |
| 72 | QUOTE |
| 54 | Seiyu |
| 51 | Ringa、Tooltip |
| 45 | Seirei or Elf |
| 40 | Ruby-zh-ja |
| 38 | Music |
| 37 | Elf |
| 34 | T category |
| 31 | Infobox battle、Twitter |

完整清单见 `logs/template_inventory.json`（`has_doc_subpage`/`doc_via_content_param`/`inline_doc_in_noinclude` 全 false 者）。
原清单中属零引用模板的条目已随待办 2 的删除自然消失。

### 2. ~~零引用模板评审~~（2026-07-26 已完成）

32 个零引用模板经全站 wikitext grep 复核（发现 embeddedin 盲区，见技术约定）后处置：

- **删除 26 个模板 + 连带孤儿 6 页**：Assert empty、Assert eq、Auto link、角色分类、Navbar、Navbox Advanced、Transclude、Doc、Border-radius、Cc-by-sa-3.0、Permission、Header、InfoboxGrid、Jiro Onofy、Lowercase title、Mainpage right、Nomobile、Notice、Poll、Theme、To en、晚街与灯，及零引用重定向 Character、CopyText、Tl；连带删除 Mainpage Staff、Tab/Assert、Module:assert（+/doc）、MediaWiki:Gadget-Poll.css、Cc-by-sa-3.0/doc、Permission/doc。删除前 wikitext 存档在 `logs/deleted_templates_2026-07-26.json`。
- **保留 6 个**：`!`（143 个图库页在 `#tag:tabber` 参数里使用，embeddedin 盲区实锤）、`!!`、`=`（转义元模板备用）、`Ruby-zh-b`/`Ruby-zh-p`（注音族 zh 分工：b=竖排注音符号、p=拼音，暂无使用场景但族内保留）、`Sandbox`（Tab 用法试验场，近半年仍在用）。
- **待定项已处理**：`RailModule` 确认无使用需求（侧栏自定义内容展示位，当前无可放内容）——已摘除 Wiki-navigation 导航项并重编译、删除模板；`Category:断言模板`（断言体系删除后空分类）已一并删除。
- **2026-07-28 复核补刀**：发现首轮复核未排除模板自身/自身文档里的示例调用，导致一批真零模板被误判为使用中。排除后重跑全站（含 ns 6，双法交叉，配方见 `docs/template-usage-audit.md`「grep 的三个坑」），追加删除 8 模板 + 8 个 `/doc`：`StructuredQuote`（连 `#SQuote:` 解析器函数也零使用）、`Infobox`（母版，实际无人调用）、`Infobox album/episode/item/location/quest`、`Tocright`；索引页同步摘除。存档 `logs/deleted_templates_2026-07-28.json`。
- **复核中确认非遗漏**：`Auto ruby`（151 处经重定向别名 `R` 使用）、`Infobox event`（2 处经 `Infobox Events`）——grep 按本名统计为 0 是别名归账问题，非真零。（后续：`Auto ruby` 已于 2026-07-28 并入 `R`——`R` 由重定向转为模板本体，`Auto ruby` 与其零引用子页 `/ja` 删除、`/ja` 随迁为 `R/ja`，`Tab/Ruby` 链接与索引页同步；存档 `logs/deleted_auto_ruby_2026-07-28.json`。en 站无 `Auto ruby`，无搬运风险。）
- **保留**：`Delete`（请求删除流程件，虽当前零引用）。
- **零引用重定向 12 个已删**（2026-07-28 晚些时候）：`Infobox novel`、`Re:Zero Light Novel Volumes`、`Re:Zero Arc 4/5 Manga`、`Re:Zero Bond(s) of Ice Manga`、`Re:Zero Daiisshou~Daiyonshou Manga`、`Re:Zero Daigoshou Manga`、`Re:Zero Ex Manga`（均曾指向 `Infobox book`）。en 站有同名的 9 个已加入 `jobs/jobs.py` 模板替换任务（搬运页里的旧名由 bot 批量替换为 `Infobox book`，故无需保留重定向）；en 无同名的 3 个（`Infobox novel`、`Bond of Ice`（单数）、`Ex Manga`）直接删。存档 `logs/deleted_redirects_2026-07-28.json`。
- **重定向 `Infobox Events` 已删**（同日）：确认为 en 站搬运名（en 有 `Template:Infobox Events`，无 `Infobox event`），已加入 jobs 替换（→ `Infobox event`），zh 现存 2 处调用（术语：王室疫病、术语：王族誘拐案）已先行改名。存档 `logs/deleted_redirect_infobox_events_2026-07-28.json`。

### 3. ~~分类补全与子分类整理~~（2026-07-26 已完成）

- 决策：按子分类细分（平铺会与 Template 命名空间作用重合）；新建 `注音模板`/`内容模板`/`格式模板` 3 个子分类，时共 15 个子分类（2026-07-27 子模板并入元模板后为 14）。
- 60 个无分类顶层模板全部归类：重定向 17、字词转换 7、注音 5、引文 6、外部链接 4、首页 3、消息框 1（Welcome）、维护 2（Init、Disambiguation）、内容 5、子模板 1（MW）、格式 8、直属 1（`=`）。原直属的 `T`、`Ruby-ja`、`Ruby-zh-ja`、`T/piece` 改挂对应子分类；终态 103 个顶层模板 100% 入树。
- 怪异点查明非误用（机制见技术约定）：`Template:元模板` 改名 `Template:元模板标记` 消歧并留重定向；`Category:元模板`（Tab 经引用元模板标记加入）与 `Category:子模板`（组成件）语义各自成立。
- 仍直属 `Category:模板` 的 7 个：`!`、`!!`、`=`、Blur、DISPLAYTITLE、Self、Tocright——均为通用工具模板，如需可再细分（Blur/Tocright→格式、Self→著作权），非必要。
- 后续（2026-07-27）：`Category:子模板` 并入 `Category:元模板`（理由见技术约定）；`元模板标记` 内联进 `Tab` 后删除（含旧名重定向）；`Documentation` 移入元模板；索引页「模板工具（元模板）」节同步更新。
