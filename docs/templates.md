# 模板信息架构与维护

2026-07 全站模板盘点的结果与实测技术约定。
索引页在 wiki 上（`ReZero Wiki:模板`），各模板的用法文档在其 `/doc` 子页，本文件是仓库侧的盘点数据与技术约定。

## 信息分层（在哪放什么）

| 信息 | 位置 | 受众 |
|---|---|---|
| 模板用法（参数、示例） | wiki 各模板 `/doc` 子页（由 `Template:Documentation` 渲染进模板页） | wiki 编辑者 |
| 全站模板索引 | wiki `ReZero Wiki:模板` | 人类维护者 + agent 检索 |
| bot 依赖的结构约定 | 本仓库 `AGENTS.md`「wiki 侧结构」（页首顺序、`Init`/`To do` 语义、`as-is` 保护等） | bot 维护者/agent |
| 盘点数据与技术约定 | 本文件 | bot 维护者/agent |

与译名表（同一份数据的两种表达、需双向手动同步）不同：模板信息**按受众分层、内容不重叠**，两边各存各的、互留指针即可，没有同步负担。

## 盘点数据（2026-07-29 刷新）

盘点脚本：`scripts/template_inventory.py`（只读；输出到 `logs/template_inventory.json`）。
引用量用 `Page.embeddedin()` 逐模板统计（Fandom 不支持 `mostlinkedtemplates`）。

- Template 命名空间共 227 页：55 顶层模板（**重定向已清零**）+ 172 子页（`Tab/*` 114 个、`/doc` 56 个、其他 2 个：`Quote/main`、`T/piece`）。
- 文档覆盖（55 个顶层模板）：**55/55 全覆盖**（2026-07-29 最后 10 个补齐）。文档统一放在 `/doc` 子页（经 `{{Documentation}}` 渲染进模板页）——2026-07-28 已将全部内联形式（`{{Documentation|content=...}}` 8 个、`<noinclude>` 内联说明 1 个）迁入 `/doc`，今后新增模板文档一律用 `/doc` 子页，templatedata 也放 `/doc`（TemplateData 扩展会读，先例 `Blur/doc`）。
- 分类：~~94 个顶层模板无分类~~（2026-07-26 已清零，顶层模板全部入树）。
- 引用量：全命名空间**真零引用模板 32 个**（已全部处置，处置记录见 git 历史）。
- **2026-08-09 收录范围对齐 en 站**：54 个 `声优:` + 8 个 `制作人员:` + `动画:异世界四重奏`（en 均无对应条目，原为跟随 es 的并集收录）及其 2 个 /猫语子页全部删除，56 处链入改指维基百科（zh>en>ja；`[[wikipedia:zh:X|..]]` 经 en.wikipedia 301 跳转，渲染为普通蓝链）。随之零引用的 `Infobox seiyu`/`Infobox staff`/`Twitter`/`MG`（含 /doc 共 8 页）与 5 个空分类（声优/声优猫语/制作人员/声优页面/制作人员页面）一并删除；两前缀自 Module:Title 与 user-fixes.py 同步取消登记，`Template:Tab/Content` 矩阵摘两列；指向它们的 184 个重定向留 redirect-br 自动清理。信息框由此减至 8 个（book/character/anime/music/bd/game/event/battle）。「唯一保留的非蛇形参数：Twitter 的 `#`」一条随 Twitter 删除成为历史。
- **2026-08-15 P7/P8 语录迁移的模板面变更**：`Tab/Author`（P8 切流，语录模块重构为 NekoQuote 月表）与 `Tab/Comment`、`QA`、`QA list`（P7，存档页退役后零转置）及各自 /doc 已删；新建 `Tab/NekoQuote`（仅一行 invoke 的壳，导航逻辑在 `Module:Tab/NekoQuote`——同日续：导航逻辑并入新建的 `Module:NekoQuoteDoc` 且年份上限自动生成，Tab/NekoQuote 族随之删除；新建 `Template:NekoQuoteDoc` 统一 204 张月表 /doc 骨架，见 modules.md）。`存档:` 伪前缀退役（user-fixes.py 与 Module:Title 双注册点同步摘除），Tab/Content 矩阵摘存档列（10 处），`Category:存档`、`Category:存档页面` 删除。QA 参数小写化（EQ/EA/JQ/JA）一条随之成为历史。
- **Lua 重写评估（2026-07-30）**：复杂度扫描脚本 `scripts/template_complexity.py`（只读，输出 `logs/template_complexity.json`，指标 = parser function 数/嵌套深度/长度）。结论：无值得 Lua 化的模板——最复杂的 `Infobox character`（36 个 parser 函数）的难逻辑（罗马音/英译）已在 Module:Kana2Romaji、Interwiki 中（图库生成原在 Module:Character image，2026-08-08 随自动列举机制移除而删除，见下条），剩余壳是 Portable Infobox 声明式 XML（与扩展的契约，Lua 化只能手搓 HTML、丢主题与 Mercury 渲染，不动）；次复杂的 `Bot`（嵌套 #switch×4 层）全站仅 2 引用、收益为零；其余 ≤4 个 parser 函数或纯格式。模板层已是「薄壳 → Module」的理想架构。
- **Infobox character 罗马字全量自动生成，`name_ja_romaji` 废弃**（2026-08-11）：模板罗马字行摘除 `source`（写法同英译行），恒为 `{{Kana2Romaji|kana→kanji}}`。字段语义定死：`name_ja` 填日文名原文（汉字名填汉字本体），`name_ja_kana` 仅在汉字名时填读音（先例菜月·昴；本次补 菜月贤一/菜穗子/蒂亚斯/土蜘蛛/黑蛇/大兔/白鯨/黑狗/白羊 9 页，Leilani Alnair 纯片假名只删 romaji）。同日信息框字段改名 `name_ja_kanji` → `name_ja`（en 把假名填进 Kanji 参数导致旧名名不副实）：全站内容页一次性批量迁移（logs/rename_name_ja.py），7 模板 + Module:Infobox book + 全部 /doc 同步，fix:para 的 `Kanji` 映射改指 `name_ja` 并常驻 `name_ja_kanji`→`name_ja` 自改名规则收残留。输出与 en 手写值的受控分歧：统一按模块的标准平文式（`Ken'ichi` 带撇号、`Oousagi` おお 不转长音、`Kuroinu`/`Shirohitsuji` 不分词）——en 自身写法不统一，不跟随；特判仅限不加就残留假名的情况（メィ/リィ 先例），罗马字分歧不加特判。kanji 字段含 `<br>（舊名）` 注释的页面（威尔海姆等）罗马字行会带出注释，作为 feature 保留。残留死行由 fix:para 的作用域正则自动删除（见 modules.md Kana2Romaji 条/AGENTS.md 坑节）。其他 6 个信息框（anime/music/bd/game/event/battle）维持手动：其日文名多为整句标题，自动生成需逐条录入带分词的读音（工作量与手填罗马字等同）且模块不处理助词（は→wa）与 う 段长音（おう→ō 等，语境相关无法可靠自动化），评估后不动。
- **角色信息框图片为纯显式参数**（2026-08-08 移除 `Module:Character image` 自动列举机制）：`image_a/n/g/c`（及 m 段的 `image`）单图填文件名、多图填 `<gallery>` 图库块。原机制按「&lt;条目名&gt; &lt;媒介&gt; &lt;子分类&gt;角色介绍图.&lt;扩展名&gt;」命名约定自动列图，因依赖文件名与条目名严格对应太脆弱、且多年无人按此命名补图而移除。迁移实况：44 页 79 张自动图全部转为显式 gallery 参数（parse 快照对比逐段验证等价，脚本 `scripts/oneoff/migrate_character_image.py` + `build_char_image_migration.py`）；3 张未被使用的图按用户决策补进 佩特拉·莱特/安娜塔西亚·合辛/爱蜜莉雅；潘多拉/阿拉基亚/陶德·方古 的 n 段已有显式 gallery 未动（其自动图本就被 format 分支吞掉不渲染）。`Module:Character image`（+/doc）与 `Template:Tab/Character image` 已删；`*角色介绍图*` 文件与旧译名重定向**全部保留**（含 `File:角色介绍图示例图.jpg`——其唯一使用处是 2026-04-01 删除的 `ReZero Wiki:施工计划表`，历史待办存档见 `docs/todo.md`）。

## 技术约定（实测）

- **信息框参数命名约定**（2026-08-02 归一）：全站统一小写蛇形英文（`name_ja`/`date_ja`/`also_known_as` 等）。en/es 搬运旧名由 fix:para 长期归一（`user-fixes.py` para 列表——transferbot 每次搬运都会重新带入 en 侧旧名，故条目常驻），模板一律不保留旧名 fallback。battle/event 的 `date/place/result` 与书籍/音乐/游戏类的 `date_ja` 语义不同（事件时间 vs 发售日期），各自保留不合并。（2026-08-03 续：`another translation`（台版译名，全站唯一带空格的参数名）归一为 `name_zh_tw`，333 个角色页经 fix:para 替换 + fallback 摘除 + templatedata 补声明，同 SOP 七步；填法按 wiki `ReZero Wiki:译名表`：官方繁中译名**无条件**记录于此栏，无「与通用译名不同才填」的限制。同日续二：voice 系连字符 `voice_zh-cn/tw/hk` 归一为下划线（仅 菜月·昴 + 1 用户沙盒 + doc 使用；fix:para 生成器**不含 ns2**，沙盒类页面要手动补改）、`Disambiguation` 的 `page-title` → `page_title`（零真实调用，直接改无需 fallback）。同日续三（用户决定取消全部命名例外后执行）：`Caption` → `caption`（7 个信息框，83 页经 fix:para + fallback 摘除 + 7 个 /doc 同步）；`Name_en` → `subtitle`（game 副标题，零使用页直改；与 game 的 `name_en`「英译」是两个参数，**不能**加 para 映射——nocase 会把 `| name_en =` 一起吞掉，这是唯一未常驻 para 列表的改名）；QA 的 `EQ/EA/JQ/JA` → 小写（唯一使用页 `存档:菲莉丝/问答` 239 处 + 模板 + /doc，显示标签保留大写；早先「经评估保留」的结论已被用户推翻）。唯一保留的非蛇形参数：Twitter 的 `#`（符号参数，位置参数的功能别名）。）
- **anime/book 的 Previous/Next 是有意丢弃**（2026-08-02 用户确认）：前后集/前后卷导航由 `Tab/*` 承担，信息框不声明这两个参数——en 搬运页带入的 `| Previous/Next =` 是死参数（fix:para 已归一小写，但 anime 模板与 Module:Infobox book 均不读取，勿当 bug「修」掉）。bd 例外：`previous`/`next` 是正常声明字段（圆盘序列）。
- **参数改名 SOP**（2026-08-02 实证，~110 页 + 9 模板 + 5 /doc）：① 全命名空间区分大小写预扫描（注意 nocase 误判——`re.IGNORECASE` 会把已合规的小写用法算成旧名；也要防 `| Date =` 这类通用名碰撞）；② 模板先加「新名 source + `<default>{{{旧名|}}}</default>` fallback」；③ 样本页 parse 快照；④ `main.py fix:para` 正式跑；⑤ 复扫确认旧名零残留；⑥ 摘 fallback + 手动同步 /doc（**replace.py 默认例外含 pre/nowiki，/doc 的语法示例与 templatedata JSON 键不会被任务触及**）；⑦ 快照对比渲染等价（normalize 掉 data-source 属性、HTML 注释、pi-tab 随机 hash）。步骤⑤复扫要排除 `/doc` 页（其语法示例本就是⑥的手动同步对象，会误报残留）。脚本归档 `scripts/oneoff/`（prescan_param_rename / round1_add_fallbacks / round2b_character_and_docs / snapshot_renders / compare_snapshots / round4_step1 / round4_step2）。
- **防分类泄漏靠 `<onlyinclude>`**：把模板体包在 `<onlyinclude>` 里后，标签之外的 `[[Category:...]]`（即使没放 `<noinclude>`）不会被引用页继承。Infobox 系、`Blur` 等都是这个写法。给模板加自身分类时，放 `<noinclude>` 或 onlyinclude 之外均可，但放 onlyinclude **里面**就会泄漏到每个引用页。
- **含 `<ref>` 的模板双重约束**（2026-07-29 `Ringa` 清理实证）：① 必须包 `div class="as-is"` + `<onlyinclude>`——否则 noreferences 任务会对其反复自动追加「注释与外部链接」段（`Template:Ringa` 2021 年残留的 5 段重复 references 即此产物，原作者晚街与灯故意留作活教材；当日已清理，机制要点并入 `Ringa/doc`）；② **不能嵌套在另一个 `<ref>` 内使用**（Cite 不支持 ref 嵌套）——嵌套时内层脚注失效、页尾报「引用错误：`name` 未在前文内使用」，`角色:阿尔` 曾踩（引用小说原文的注释里写 `{{Ringa}}`，当时改纯文本；全站扫描仅此 1 页，扫描脚本 `logs/scan_ringa_nested.py`）。（当日晚些时候用户决定 `Ringa` 弃用 ref、改用 `{{Tooltip}}` 呈现注记，两个约束就此绕开，`角色:阿尔` 的嵌套调用也随之恢复合法；上述约束仍适用于未来新建含 ref 的模板。）
- **有意给引用页加分类的模板**（设计如此，勿当 bug「修」掉）：

| 模板 | 给引用页加的分类 |
|---|---|
| `To do` | 待修撰 |
| `Infobox anime` | 剧集（仅主命名空间） |
| `Infobox bd` | 圆盘（仅主命名空间） |
| `Infobox battle` | 战役（经 `T category`） |
| `Infobox event` | 事件（分类在 onlyinclude 内，不限命名空间） |
| `Seirei or Elf` / `Yousei or Elf` | 需复核译名 |
| `Soft redirect` | 软重定向（onlyinclude 内） |
| `Ruby` 系（Ruby、Ruby-ja、Ruby-zh-ja） | Ruby transclusions with too many parameters（异常追踪） |
| `Category redirect` | 已重定向的分类、尚未清空的已重定向分类 |

- **`{{!}}`、`{{=}}` 是 MediaWiki 内置 magic word**（1.24/1.39 起，Fandom 跑 1.43.x），不产生 transclusion，同名模板永不执行。2026-07-26 曾把 `!` 的 embeddedin=0 误判为「templatelinks 不记录 `#tag` 参数内调用」的盲区；2026-07-28 用 `action=parse&prop=templates` 实测更正：143 个图库页的 `{{!}}` 走 magic word，删同名模板不影响任何渲染（`!`、`=`、`!!` 已删）。教训：**grep 命中的是语法不是语义**，magic word 会截胡同名模板——判「模板是否真被调用」最可靠的手段是 `action=parse` 的 templates 列表。判零仍须 embeddedin + grep 双通道（grep 负责覆盖别名语法与 includeonly 死代码，见 `docs/template-usage-audit.md`）。
- **嵌套 tabber 的正确写法**（参考 `角色:爱蜜莉雅/图库`）：外层字面 `<tabber>`，内层 `{{#tag:tabber|...}}`，内层内容里深度 0（不在 `{{}}`/`[[]]` 内）的 `|` 全部转义为 `{{!}}`——所以分隔符写作 `{{!}}-{{!}}`，表格的 `{|`、`|-` 同样要转。字面嵌套两层 `<tabber>` 会让内层被转义成纯文本；模板 transclusion 时内层 tabber 能工作是因为「先展开模板再解析标签」的时序——2026-07-28 Portal 链内联首页时实测证实。
- **Portal 链已内联进首页**（2026-07-28）：`Portal`、`Portal Left/Right`、`Slider`、`Welcome`、`Announcements`、`Latest Volume`（+/LN、/Manga）、`Social Media` 10 个模板删除，首页内容直接编辑首页即可。内联生成器 `scripts/oneoff/inline_portal_preview.py`（含渲染等价验证），存档 `logs/deleted_portal_chain_2026-07-28.json`；空分类 `Category:首页模板` 一并删除。
- **元模板分类**（2026-07-27 由「元模板/子模板」两分类合并而成）：`Category:元模板` = 被其他模板调用、不直接用于文章页的模板。判据是机制而非修辞——MediaWiki 模板只有宏展开，没有继承，「派生」（如 `Tab/LN` 预填参数调 `Tab`）与「组成」（如 `T` 调 `T/piece`）是同一种 transclusion，拆两类无可判定标准故合并。成员：`Tab`（noinclude 里声明「用于派生分页模板」+ 挂分类；原 `{{元模板标记}}` 全站仅此一处使用，已内联并删除该模板及旧名重定向 `Template:元模板`）、`T category`、`T/piece`、`Documentation`（`MW` 已于 2026-07-28 随 USERNAME 内联删除）。原 `Category:子模板` 已删除。
- **单点使用模板已内联**（2026-07-28）：`Web Novel Chapter List`→小说：Web、`USERNAME`/`MW`→攻略指南（mediaWikiData span）、`Facebook`/`Instagram`→两个声优页（es 站搬运的西语文本保留，用户另行专项清理）；`DISPLAYTITLE`（唯一调用在重定向页 纱提拉 上、本就无意义，摘除）、`Example`（空模板，唯一「使用」是他人沙盒的空调用骨架）直接删。每页编辑前后 parse 对比渲染等价。存档 `logs/deleted_single_use_inline_2026-07-28.json`。en 仅 `Web Novel Chapter List` 有同名（1 引用、无 zh 对应名，未来搬运重引入时在 新搬运待整理 人工处理）。**内联取舍判据**：同页多次调用的组件（`Copy`×48、`T/piece`×20）与体系族成员（`Tab/*`）不内联——模板在这些场景是正确的抽象。
- **Tab 挂载惯例**（2026-07-28 排查确立；审计 `scripts/oneoff/audit_tab_placement.py`、修复 `scripts/oneoff/fix_tab_placement.py`）：
  - **每页只挂自己系列的一个 tab**，位置在 `{{To do}}` 行之后。跨章/跨季导航链接不算应挂——`Tab/Anime S2` 链接 `动画:第1集`（S2 导航到 S1 首集），但该页只挂 `Tab/Anime S1`。
  - **Manga Arc Chapter/Volume tab 的双块结构**：块 0 = 章导航（粗体标记本章），块 1 = 本章各话/各卷列表（当前话/卷靠自链接自动粗体）；应挂页只取块 1。单块 tab（Synopsis、单作品）全部链接页都应挂。（2026-08-17 起 Volume 与 Chapter 同构，见下条。）
  - 2026-08-17 漫画卷 Tab 双层化：`Tab/Manga_Volume`（单块扁平 1-1…4-8，缺第4章 9~13 卷与整个第5章）拆为 `Tab/Manga Arc 1~5 Volume` 五个 per-arc 双块模板，34 个卷页全部换装/补挂（26 页替换、8 页新挂；第4章实际 13 卷、第5章 3 卷）。脚本 `scripts/oneoff/migrate_manga_volume_tab.py`。旧 `Tab/Manga_Volume` 随之零引用，当日删除。
  - **Module/MediaWiki 页的 tab 挂在其 `/doc` 页**（Module 命名空间不渲染 wikitext，Gadget CSS 同理）——审计时这些是误报。
  - 2026-07-28 修复：Manga 系 7 个 tab（Arc 1~4 Chapter、Manga Volume、剑鬼恋歌 Chapter/Volume）历史上从未挂进任何漫画页，共补挂 194 页；另修 `Tab/Sword Demon Battle Ballad Act` 繁体死链（終幕→终幕）、`Tab/Ruby` 摘除已删 `R/ja` 导航项；`小说:…日报/KILL4` 原挂不存在的 `Tab/KILL`，换挂正确 tab；删除与 `Tab/The Great Spirit Puck's Side Story` 逐字节重复的零引用 `Tab/The Great Spirit Puck`。
  - 审计坑：`allpages(prefix="Tab/")` 返回的标题**已含** `Tab/` 前缀（别再拼一次，且 pywikibot 对不存在页面 `.text` 返回空串不报错——要 assert 防空转）；tab 内 `<!-- -->` 注释的链接不算应挂；分类链接要区分 `[[:分类:X]]` 冒号内联（导航链接，参与比对）与裸 `[[Category:X]]`（归类赋值，跳过），且链接标题要经 pywikibot 归一化再与携带页比对（`Tab/Content` 的分类矩阵全是冒号内联 + wikitable 在 `{{Tab}}` 块外）。上述惯例判例（导航块、Module/doc、注释、分类形式）已内置进审计脚本，输出仅剩真失配与红链（红链=未搬运内容或未建分类页，建页后补挂即可）。
- **模板的归类入口可能在其 `/doc` 子页**：`T`、`T/piece` 的分类是 `/doc` 里 `<includeonly>[[Category:...]]</includeonly>` 经 `{{Documentation}}` 注入的，模板本体 wikitext 里搜不到。改挂这类分类后分类表不会立即刷新，需 `page.purge(forcelinkupdate=True)` 触发重解析。
- **文档盒也可能挂在 `Tab/*` 导航子页上**（2026-07-29 QUOTE 批实测）：`Tab/Quote` 曾用 `{{Documentation|Quote/doc}}` 给 QUOTE/Quote/Quote/main 三个页面共享渲染 Quote/doc。给模板挂 `{{Documentation}}` 前先在模板页 parse 确认现有文档盒来源，否则双盒；摘共享调用后须在被波及的其余模板体上补偿挂载。同类案例（2026-08-03）：`Documentation` 自身**不需要也不能**自挂——其 chrome 机制（`{{{{{1|{{FULLPAGENAME}}/doc}}}}}`）在自身页面上本就会渲染自己的 /doc，曾误当「缺 {{Documentation}} 调用」补挂导致文档盒重复显示，当日回退。即「顶层模板缺 {{Documentation}} 调用」的检查对 Documentation 这个渲染器本身是误报。
- **索引页分节与模板分类保持对齐**（2026-07-29 确立）：`ReZero Wiki:模板` 的分节按功能分类树组织，条目归类以模板自身 `[[Category:...]]` 为准。两者冲突时修**功能上错的那一侧**（判据是功能而非形式）——改分类的先例：`Kana2Romaji`（音译，非字词转换）字词转换→注音、`Bot`（站务声明）消息框→维护、`Category redirect` 摘除消息框留重定向、4 个信息框（anime/music/bd/game）内容→信息框、`Blur` 根分类→格式模板；挪索引条目的先例：`NoteTA` 格式与工具→字词转换、`Seirei or Elf`/`Yousei or Elf` 页首与维护→字词转换（2026-08-03，二者分类 `字词转换模板` 功能正确——机制是字词转换，复核追踪只是副作用）。分类清空即删（`内容模板`、`消息框模板` 当日删除，同 `请求删除`/`首页模板` 先例）。索引页条目提到的模板必须存在——删模板时同步清索引（当日补清 `Quote/big`、`Quote/small`、`AV` 残留条目，补收漏网的 `BV`）。
- **文档写作约定**（2026-07-28 修订全部 19 个 `/doc` 后确立）：文档用简体中文；结构 `;说明`/`;语法`/`;示例` + templatedata。当日修订：著作权六件套（CC-BY-SA/Fairuse/From Wikimedia/Other free/PD/Self）与 `T`、`T/piece`、`Documentation` 的英文文档全部翻译，`Bot`/`NoteTA` 繁体转简体；修正过期/错误信息——`Quote/doc` 仍称 Quote/QUOTE 是已删 `Quote/small`/`Quote/big` 的别名、`NoteTA/doc` m 上限写 10（Module 实测循环 G1..G30）、`BV/doc` templatedata 把参数 1 标 required 却演示全省略用法、`Documentation/doc` 仍教 `content=` 内联旧写法与英文分类；`Infobox character/doc` 补 `name_ja_romaji`、图片参数顺序对齐模板体（a/n/g/c）、templatedata 补全 description；`Self` 分类 模板→著作权模板（与其余著作权模板一致）。（当晚续：`{{BV}}` 的无参调试默认值 `BV1jt4y1D714` 已删——全站 24 处调用全带参、零无参用例，文档无参演示块同删、templatedata 参数 1 恢复 required。注意 BV 的 **av 兼容不是死代码**：`设定集、画集:Art Works Re:BOX`、`动画:迷你动画` 各集在用 av 号，Module:Bili 的 data-av 分支须保留。）（2026-07-29 续：**文档中的字面 wikitext 必须包 `<nowiki>`**——`-{ }-` 转换标记在 `<code>` 里会被语言转换器解析掉（`Init/doc`、`加护/doc` 由 bot 修复，`R/doc`、`Ruby-ja/doc`、`Ruby-zh-ja/doc` 由用户补修，扫描脚本 `logs/scan_langconv_literal.py`）；`<code>[[页面|文字]]</code>` 会渲染成红链（用户修 `Tab/doc`）。**文档里链到模板用 `{{T|模板名}}`**，不要写 `{{[[Template:X|X]]}}`（同 `Tab/doc` 修正）。无信息量的空 `-{}-` 示例直接删除即可，不必一律 nowiki（用户对 `Bot/doc` 的处理）。模板体内的功能性 `-{ }-`（防转换包裹、zh-hans/zh-hant 规则）不要动。验证渲染时 `{` 在 HTML 中是 `&#123;`，比对前先 unescape。）
- **`insource:` 全文搜索会分词漏配**（2026-08-02 实证）：对含 `:`/`-`/`."` 的词（如 `Gadget-Assert.css`）连 Common.css 自身都搜不到——排查 CSS/JS 引用链要靠 `scripts/check_css_imports.py` 的定向核查而非全文搜索。
- **调用带标题 assert 模块的模板，invoke 必须包 `<includeonly>`**（2026-08-15 `Template:NekoQuoteDoc` 实证）：模板页自身会渲染自身代码——若被调模块对页面标题有断言（如 NekoQuoteDoc 限 `NekoQuote/YYYY-MM`），模板页与其 /doc 会被报「有脚本错误的页面」。修复 = invoke 包 includeonly + 文档里提及模板名处一律 nowiki（漏包一处 doc 里的 `{{NekoQuoteDoc}}` 同样触发）。
- **繁简扫描的已知有意例外**（2026-08-03 三轮复查实证，复扫勿再报）：`Infobox character` 的 `<label>髮色</label>` 与 `國語（臺灣）` 是**有意繁体**（源码注释「使用繁體，原因：轉換錯誤」——简体「发色」在繁体模式会被错转成「發色」，直接写繁体让 langconv 反向归一）；`加护` 体的 `{{R|加护||加護|Kago}}` 繁体是 R 的繁体写法参数；`Quote/doc` 命中的繁体字是 Fate 召唤咒文**日语文本**（`素に銀と鉄`）。静态繁简扫描的其余误报类：三花括号参数（`{{{EQ|}}}` 会被粗正则看成模板调用 `{{EQ}}`）、`{{{2<includeonly>|</includeonly>}}}` 技巧、`除` 等繁简同形字。
- **`{{Documentation}}` 要并入已有 `<noinclude>` 内部**：追加第二个独立 `<noinclude>{{Documentation}}</noinclude>` 时，两个 noinclude 之间的换行会被 transclude 到引用页（多一个换行 = 段落分裂，精灵族文档首轮踩过）。推广（2026-08-03 修复实证）：**行内模板内容与其后 `<noinclude>` 之间也不能有换行**——换行会被 transclude，HTML 折叠为空格，行内使用出现多余间隙（`（{{Seirei}}）族` → `（精灵 ）族`）。当日修复 `Elf`/`Seirei`/`Yousei`/`加护`/`Copy`/`Tooltip`/`Ruby`/`Seirei or Elf`/`Yousei or Elf` 共 9 个模板（Tooltip 的换行经 Ringa 等二级泄漏）；块级模板（Clear/Main/Bot 等）尾部换行无害，不用管。判定补充（2026-08-03 二轮复查）：**`<onlyinclude>` 包裹的模板天然免疫**（包裹外的换行不 transclude）——静态扫描会误报候选（BV/Kana2Romaji/Q/QA/R），一律 `action=parse` 实证后再动手。

