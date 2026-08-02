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

## 盘点数据（2026-07-29 刷新）

盘点脚本：`scripts/template_inventory.py`（只读；输出到 `logs/template_inventory.json`）。
引用量用 `Page.embeddedin()` 逐模板统计（Fandom 不支持 `mostlinkedtemplates`）。

- Template 命名空间共 227 页：55 顶层模板（**重定向已清零**）+ 172 子页（`Tab/*` 114 个、`/doc` 56 个、其他 2 个：`Quote/main`、`T/piece`）。
- 文档覆盖（55 个顶层模板）：**55/55 全覆盖**（2026-07-29 最后 10 个补齐，见待办 1）。文档统一放在 `/doc` 子页（经 `{{Documentation}}` 渲染进模板页）——2026-07-28 已将全部内联形式（`{{Documentation|content=...}}` 8 个、`<noinclude>` 内联说明 1 个）迁入 `/doc`，今后新增模板文档一律用 `/doc` 子页，templatedata 也放 `/doc`（TemplateData 扩展会读，先例 `Blur/doc`）。
- 分类：~~94 个顶层模板无分类~~（2026-07-26 待办 3 已清零，顶层模板全部入树）。
- 引用量：全命名空间**真零引用模板 32 个**（见待办 2，已处理）。
- **Lua 重写评估（2026-07-30）**：复杂度扫描脚本 `scripts/template_complexity.py`（只读，输出 `logs/template_complexity.json`，指标 = parser function 数/嵌套深度/长度）。结论：无值得 Lua 化的模板——最复杂的 `Infobox character`（36 个 parser 函数）的难逻辑（图库生成/罗马音/英译）已在 Module:Character image、Kana2Romaji、Interwiki 中，剩余壳是 Portable Infobox 声明式 XML（与扩展的契约，Lua 化只能手搓 HTML、丢主题与 Mercury 渲染，不动）；次复杂的 `Bot`（嵌套 #switch×4 层）全站仅 2 引用、收益为零；其余 ≤4 个 parser 函数或纯格式。模板层已是「薄壳 → Module」的理想架构。

## 技术约定（实测）

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
| `Ruby` 系（Ruby、Ruby-ja、Ruby-zh-ja） | Ruby transclusions with too many parameters（异常追踪） |
| `Category redirect` | 已重定向的分类、尚未清空的已重定向分类 |

- **`{{!}}`、`{{=}}` 是 MediaWiki 内置 magic word**（1.24/1.39 起，Fandom 跑 1.43.x），不产生 transclusion，同名模板永不执行。2026-07-26 曾把 `!` 的 embeddedin=0 误判为「templatelinks 不记录 `#tag` 参数内调用」的盲区；2026-07-28 用 `action=parse&prop=templates` 实测更正：143 个图库页的 `{{!}}` 走 magic word，删同名模板不影响任何渲染（`!`、`=`、`!!` 已删）。教训：**grep 命中的是语法不是语义**，magic word 会截胡同名模板——判「模板是否真被调用」最可靠的手段是 `action=parse` 的 templates 列表。判零仍须 embeddedin + grep 双通道（grep 负责覆盖别名语法与 includeonly 死代码，见 `docs/template-usage-audit.md`）。
- **嵌套 tabber 的正确写法**（参考 `角色:爱蜜莉雅/图库`）：外层字面 `<tabber>`，内层 `{{#tag:tabber|...}}`，内层内容里深度 0（不在 `{{}}`/`[[]]` 内）的 `|` 全部转义为 `{{!}}`——所以分隔符写作 `{{!}}-{{!}}`，表格的 `{|`、`|-` 同样要转。字面嵌套两层 `<tabber>` 会让内层被转义成纯文本；模板 transclusion 时内层 tabber 能工作是因为「先展开模板再解析标签」的时序——2026-07-28 Portal 链内联首页时实测证实。
- **Portal 链已内联进首页**（2026-07-28）：`Portal`、`Portal Left/Right`、`Slider`、`Welcome`、`Announcements`、`Latest Volume`（+/LN、/Manga）、`Social Media` 10 个模板删除，首页内容直接编辑首页即可。内联生成器 `scripts/oneoff/inline_portal_preview.py`（含渲染等价验证），存档 `logs/deleted_portal_chain_2026-07-28.json`；空分类 `Category:首页模板` 一并删除。
- **元模板分类**（2026-07-27 由「元模板/子模板」两分类合并而成）：`Category:元模板` = 被其他模板调用、不直接用于文章页的模板。判据是机制而非修辞——MediaWiki 模板只有宏展开，没有继承，「派生」（如 `Tab/LN` 预填参数调 `Tab`）与「组成」（如 `T` 调 `T/piece`）是同一种 transclusion，拆两类无可判定标准故合并。成员：`Tab`（noinclude 里声明「用于派生分页模板」+ 挂分类；原 `{{元模板标记}}` 全站仅此一处使用，已内联并删除该模板及旧名重定向 `Template:元模板`）、`T category`、`T/piece`、`Documentation`（`MW` 已于 2026-07-28 随 USERNAME 内联删除）。原 `Category:子模板` 已删除。
- **单点使用模板已内联**（2026-07-28）：`Web Novel Chapter List`→小说：Web、`USERNAME`/`MW`→攻略指南（mediaWikiData span）、`Facebook`/`Instagram`→两个声优页（es 站搬运的西语文本保留，用户另行专项清理）；`DISPLAYTITLE`（唯一调用在重定向页 纱提拉 上、本就无意义，摘除）、`Example`（空模板，唯一「使用」是他人沙盒的空调用骨架）直接删。每页编辑前后 parse 对比渲染等价。存档 `logs/deleted_single_use_inline_2026-07-28.json`。en 仅 `Web Novel Chapter List` 有同名（1 引用、无 zh 对应名，未来搬运重引入时在 新搬运待整理 人工处理）。**内联取舍判据**：同页多次调用的组件（`Copy`×48、`T/piece`×20）与体系族成员（`Tab/*`）不内联——模板在这些场景是正确的抽象。
- **Tab 挂载惯例**（2026-07-28 排查确立；审计 `scripts/oneoff/audit_tab_placement.py`、修复 `scripts/oneoff/fix_tab_placement.py`）：
  - **每页只挂自己系列的一个 tab**，位置在 `{{To do}}` 行之后。跨章/跨季导航链接不算应挂——`Tab/Anime S2` 链接 `动画:第1集`（S2 导航到 S1 首集），但该页只挂 `Tab/Anime S1`。
  - **Manga Arc Chapter tab 的双块结构**：块 0 = 章导航（粗体标记本章），块 1 = 本章各话列表；应挂页只取块 1。单块 tab（Volume、Synopsis、单作品）全部链接页都应挂。
  - **Module/MediaWiki 页的 tab 挂在其 `/doc` 页**（Module 命名空间不渲染 wikitext，Gadget CSS 同理）——审计时这些是误报。
  - 2026-07-28 修复：Manga 系 7 个 tab（Arc 1~4 Chapter、Manga Volume、剑鬼恋歌 Chapter/Volume）历史上从未挂进任何漫画页，共补挂 194 页；另修 `Tab/Sword Demon Battle Ballad Act` 繁体死链（終幕→终幕）、`Tab/Ruby` 摘除已删 `R/ja` 导航项；`小说:…日报/KILL4` 原挂不存在的 `Tab/KILL`，换挂正确 tab；删除与 `Tab/The Great Spirit Puck's Side Story` 逐字节重复的零引用 `Tab/The Great Spirit Puck`。
  - 审计坑：`allpages(prefix="Tab/")` 返回的标题**已含** `Tab/` 前缀（别再拼一次，且 pywikibot 对不存在页面 `.text` 返回空串不报错——要 assert 防空转）；tab 内 `<!-- -->` 注释的链接不算应挂；分类链接要区分 `[[:分类:X]]` 冒号内联（导航链接，参与比对）与裸 `[[Category:X]]`（归类赋值，跳过），且链接标题要经 pywikibot 归一化再与携带页比对（`Tab/Content` 的分类矩阵全是冒号内联 + wikitable 在 `{{Tab}}` 块外）。上述惯例判例（导航块、Module/doc、注释、分类形式）已内置进审计脚本，输出仅剩真失配与红链（红链=未搬运内容或未建分类页，建页后补挂即可）。
- **模板的归类入口可能在其 `/doc` 子页**：`T`、`T/piece` 的分类是 `/doc` 里 `<includeonly>[[Category:...]]</includeonly>` 经 `{{Documentation}}` 注入的，模板本体 wikitext 里搜不到。改挂这类分类后分类表不会立即刷新，需 `page.purge(forcelinkupdate=True)` 触发重解析。
- **文档盒也可能挂在 `Tab/*` 导航子页上**（2026-07-29 QUOTE 批实测）：`Tab/Quote` 曾用 `{{Documentation|Quote/doc}}` 给 QUOTE/Quote/Quote/main 三个页面共享渲染 Quote/doc。给模板挂 `{{Documentation}}` 前先在模板页 parse 确认现有文档盒来源，否则双盒；摘共享调用后须在被波及的其余模板体上补偿挂载。
- **索引页分节与模板分类保持对齐**（2026-07-29 确立）：`ReZero Wiki:模板` 的分节按功能分类树组织，条目归类以模板自身 `[[Category:...]]` 为准。两者冲突时改**分类**而非迁就分节——判据是功能而非形式：`Kana2Romaji`（音译，非字词转换）字词转换→注音、`Bot`（站务声明）消息框→维护、`Category redirect` 摘除消息框留重定向、4 个信息框（anime/music/bd/game）内容→信息框。分类清空即删（`内容模板`、`消息框模板` 当日删除，同 `请求删除`/`首页模板` 先例）。索引页条目提到的模板必须存在——删模板时同步清索引（当日补清 `Quote/big`、`Quote/small`、`AV` 残留条目，补收漏网的 `BV`）。
- **文档写作约定**（2026-07-28 修订全部 19 个 `/doc` 后确立）：文档用简体中文；结构 `;说明`/`;语法`/`;示例` + templatedata。当日修订：著作权六件套（CC-BY-SA/Fairuse/From Wikimedia/Other free/PD/Self）与 `T`、`T/piece`、`Documentation` 的英文文档全部翻译，`Bot`/`NoteTA` 繁体转简体；修正过期/错误信息——`Quote/doc` 仍称 Quote/QUOTE 是已删 `Quote/small`/`Quote/big` 的别名、`NoteTA/doc` m 上限写 10（Module 实测循环 G1..G30）、`BV/doc` templatedata 把参数 1 标 required 却演示全省略用法、`Documentation/doc` 仍教 `content=` 内联旧写法与英文分类；`Infobox character/doc` 补 `name_ja_romaji`、图片参数顺序对齐模板体（a/n/g/c）、templatedata 补全 description；`Self` 分类 模板→著作权模板（与其余著作权模板一致）。（当晚续：`{{BV}}` 的无参调试默认值 `BV1jt4y1D714` 已删——全站 24 处调用全带参、零无参用例，文档无参演示块同删、templatedata 参数 1 恢复 required。注意 BV 的 **av 兼容不是死代码**：`设定集、画集:Art Works Re:BOX`、`动画:迷你动画` 各集在用 av 号，Module:Bili 的 data-av 分支须保留。）（2026-07-29 续：**文档中的字面 wikitext 必须包 `<nowiki>`**——`-{ }-` 转换标记在 `<code>` 里会被语言转换器解析掉（`Init/doc`、`加护/doc` 由 bot 修复，`R/doc`、`Ruby-ja/doc`、`Ruby-zh-ja/doc` 由用户补修，扫描脚本 `logs/scan_langconv_literal.py`）；`<code>[[页面|文字]]</code>` 会渲染成红链（用户修 `Tab/doc`）。**文档里链到模板用 `{{T|模板名}}`**，不要写 `{{[[Template:X|X]]}}`（同 `Tab/doc` 修正）。无信息量的空 `-{}-` 示例直接删除即可，不必一律 nowiki（用户对 `Bot/doc` 的处理）。模板体内的功能性 `-{ }-`（防转换包裹、zh-hans/zh-hant 规则）不要动。验证渲染时 `{` 在 HTML 中是 `&#123;`，比对前先 unescape。）

## 待办

### 4. 2026-08-02 全站模板复查

复查方式：`template_inventory.py` 刷新（数据与 07-29 完全一致：227 页 / 55 顶层 / 重定向 0 / 文档 55/55）+ `recheck_template_usage.py` 全命名空间复核（真零引用仍仅 `Sandbox` 一个，有意保留）+ 55 个顶层模板 wikitext 逐个人工审读 + CSS/JS 依赖链核查（新增审计脚本 `scripts/check_css_imports.py`：Common.css @import 清单 vs 页面实际存在性）。确认正常、**排除**的疑似点：19 个「分类在 noinclude 外」均为 onlyinclude 保护或有意设计；模板页 `[[en:…]]`/`[[es:…]]` 跨语言链接经 parse langlinks 实证生效且目标页存在（指向 en 旧名 `Character`/`Re:Zero Light Novel Volumes`/`Infobox Events` 是正确的——en 侧它们仍是本体，`en:Template:Infobox character` 反而不存在）；`Template:Copy` 的复制 JS 在 `dev:CopyText/code.js`（ImportJS 加载，选择器 `.copy-to-clipboard-button` + `data-text` 与模板标记完全匹配），功能正常；`dev:BilibiliVideo.js` 必须保留（Module:Bili 渲染时产出 `div.BilibiliVideo`，insource 搜不到是 Lua 生成）。

#### A. ~~明确错误~~（2026-08-02 已修复）

1. ~~**`Template:Category redirect` 的 `style:"` 是全角冒号**~~ → 已改半角。
2. ~~**`MediaWiki:Common.css` @import 仍引用已删除的 `MediaWiki:Gadget-Poll.css`**~~ → 已摘除。
3. ~~**`MediaWiki:Gadget-Assert.css` 是断言体系的漏网孤儿**~~ → 已删页面并摘除 @import。
4. ~~**`MediaWiki:ImportJS` 仍加载 `dev:AjaxPoll.js`**~~ → 已摘除。
   执行/验证脚本 `scripts/oneoff/fix_batch_a_2026_08_02.py` / `verify_batch_a_2026_08_02.py`（删前扫荡：assert-pass/assert-fail 与两个 CSS 页面名全站零残留）。注意 `insource:` 对含 `:`/`-`/`."` 的词会分词漏配（扫荡时连 Common.css 自身都搜不到），此类排查要靠 `check_css_imports.py` 的定向核查而非全文搜索。

#### B. ~~中文化/本地化一致性~~（2026-08-02 已完成）

5. ~~**`Template:Infobox staff` 的 label 是西班牙语**~~ → 已中文化（英译/日文/罗马字/出生/监督/剧本/设计/作曲），与 C10 参数归一并入同次编辑。
6. ~~**`Template:Infobox event` label 全英文**~~ → 已中文化（日文/罗马字/时间/地点/结果/别名）。
7. ~~**`Infobox bd`/`Infobox music` 英文 label**~~ → bd：圆盘序列/前一卷/后一卷；music：日文/罗马字。
8. ~~**著作权六件套显示文本全英文**~~ → 已中文化；`id` 按模板名区分（c-cc-by-sa/c-fairuse/c-from-wikimedia/c-other-free/c-pd/c-self），CC-BY-SA 链接改用 deed.zh。
9. ~~**源码繁简混杂**~~ → `Bot` 全文转简体（#switch 的繁体 key 保留兼容，外站链接目标不动）；`Category redirect`/`Disambiguation` 统一简体（`-{ }-` 转换标记保留）。

#### C. ~~待决策~~（2026-08-02 已完成，用户批准）

10. ~~**seiyu/staff 的西语参数名**~~ → 归一为 image/Caption/name/name_en/name_ja_romaji/birth/(death)/(role|script/design/composer)，62 个调用页批量同步；模板用 `<default>{{{旧名|}}}</default>` 保持向后兼容（未来 es 搬运页无需立即改写，**fallback 不可摘**）。
11. ~~**`Template:Quote/main` 的内联 templatedata**~~ → 已迁入 `Quote/doc`（三页共享文档，templatedata 随文档盒注入）。
12. ~~**`Template:Infobox anime` 参数名风格**~~ → Volume/Air Date/Opening/Ending 归一为 volume/air_date/opening/ending，175 个调用页批量同步；旧名同样经 `<default>` 兼容（en 搬运页安全网，不可摘）。

执行脚本 `scripts/oneoff/`：`fix_batch_bc_templates.py`（16 个模板体）+ `fix_quote_doc_templatedata.py` + `rename_infobox_params_batch.py`（237 页扫描、235 页编辑、零残留）+ `fix_batch_bc_docs.py`（5 个 /doc 同步）。验证：改动前 parse 快照 `logs/batch_bc_parse_snapshot.json`，`verify_batch_bc_templates.py` 全部样本渲染等价（归一化项：HTML 注释噪音、PI `data-source` 属性——后者随参数名变化是有意元数据差异，已确认全站无 CSS/JS 依赖它）；`verify_music_bd_labels.py`（music/bd label）；`verify_params_renamed.py`（旧参数名零残留）。PI 的 `<default>` 可作参数别名 fallback 是本次确立的新手法（先例：Infobox character 的 `{{{Name|}}}` default；本次推广到 image/caption/title/data 全类型）。

### 1. ~~`/doc` 子页补全~~（2026-07-29 已完成）

- **Infobox 文档已补全**（2026-07-29）：9 个信息框模板（book/anime/seiyu/music/battle/bd/event/game/staff）全部新建 `/doc`（说明/语法/示例/templatedata），模板体内联语法小节（残留旧名 `{{Anime}}`/`{{Seiyu}}`/`{{Music}}`/`{{Re:Zero BD}}`/`{{Re:Zero Game}}`/`{{Staff}}` 与西语 `== Usos ==` 标题）全部迁入 `/doc` 并改挂 `{{Documentation}}`；book 新增 `{{Documentation}}` 调用。写入脚本 `logs/write_infobox_docs.py`，渲染与自动分类验证 `logs/verify_infobox_docs.py`。实测 quirks 已写进各 `/doc`：seiyu/staff 参数名为西班牙语（es 搬运）；battle 的参战方/指挥官/军队/伤亡只有 1–3 号参数（旧文档与部分页面里的 4 号是死参数）；book 的「英文名」与 battle 的「英译」由 `Module:Interwiki` 自动生成；game 的 `Name_en` 渲染为副标题。
- **注音族与精灵族文档已补全**（2026-07-29）：10 个模板（`Ruby`/`Ruby-ja`/`Ruby-zh-ja`/`R`/`Kana2Romaji` + `Seirei`/`Elf`/`Yousei`/`Seirei or Elf`/`Yousei or Elf`）全部新建 `/doc`；`Ruby`/`R`/`Kana2Romaji` 模板体内的内联 templatedata、`Ruby-ja`/`Ruby-zh-ja` 的内联英文说明迁入 `/doc`，10 个模板体均改挂 `<noinclude>{{Documentation}}</noinclude>`。写入脚本 `logs/write_ruby_seirei_docs.py`，验证 `logs/verify_ruby_seirei_docs.py`（模板页「模板文件」盒 + /doc parse + 10 个引用页改动前后 parse 对比，渲染与自动分类全等价）。实测 quirks 已写进各 `/doc`：`Ruby`/`Ruby-ja`/`Ruby-zh-ja` 给第 3 个位置参数会加追踪分类 Ruby transclusions with too many parameters；`Ruby-ja` 的正文/注音与 `R` 的日文部分包在 `-{ }-` 中防繁简转换；`R` 由 `Module:Auto ruby` 实现（中文加粗 + 英文上标 + 括号内假名/罗马音，罗马音留空自动经 `Module:Kana2Romaji` 转换，转不出则只显示假名）；`Kana2Romaji` 无匹配假名时输出空串，主要由 `Infobox character` 的 `name_ja_romaji` 默认值自动调用（主空间几乎无直接调用）；`Seirei`/`Yousei` 源码含 `<!--nobot-->` 注释防 bot 译名归一。**坑**：给模板追加第二个独立 `<noinclude>{{Documentation}}</noinclude>` 时，两个 noinclude 之间的换行会被 transclude 到引用页（多一个换行 = 段落分裂，精灵族首轮踩过）；应把 `{{Documentation}}` 并入已有 noinclude 内部。（当晚续：精灵族 5 个 `/doc` 的工作流描述已修正——`Seirei or Elf`/`Yousei or Elf` 占位模板是 bot 把条目中直接书写的「精灵」「妖精」自动替换而来（`user-fixes.py` translation fix，精灵骑士/精灵术/精灵使与人工/自然/契约/大/邪/微/准精灵等复合词除外），非编辑者手动占位；「半精灵」直接替换为 半`{{Elf}}` 不经复核；修正脚本 `logs/fix_elf_docs.py`。）
- **站务机制 8 个模板文档已补全**（2026-07-29）：`Init`/`Tab`/`T category`/`QUOTE`/`Category redirect`/`Soft redirect`/`Disambiguation`/`Sandbox` 全部新建 `/doc`；`Tab`、`T category` 的内联 templatedata 与 `Category redirect` 的内联繁体说明（转简体）迁入 `/doc`，8 个模板体均挂 `{{Documentation}}`（有 noinclude 的并入内部，无 noinclude 且 includeonly 包裹的才新建）。写入脚本 `logs/write_mechanism_docs.py`，改动前快照 `logs/snapshot_mechanism_before.py`（`logs/mechanism_parse_snapshot.json`），验证 `logs/verify_mechanism_docs.py`（8 模板页「模板文件」盒 + 8 个 /doc parse + 7 个引用页改动前后 parse 对比全等价，ALL CHECKS PASSED）。实测 quirks 已写进各 `/doc`：`Init`（Module:Init）做三件事——标题 `-{T|…}-` 繁简转换、按标题前缀/子页面后缀加分类（无前缀页面入「杂项」）、生成顶部分页导航（2026-07-30 起 AutoTab 已并入 Init，拼接经 Module:Tab），仅限主命名空间；`Tab` 是元模板，主空间 317 个 embeddedin 全部是经 `Tab/*` 派生页的间接引用、无直接调用（templatelinks 计嵌套），文档示例取自 `Tab/Anime S1`；`T category` 主空间 34 引用也全间接（Infobox battle→战役、Disambiguation→消歧义）；`Sandbox` 全站零引用（Tab 试验场，如实写入文档）。**坑**：`Tab/Quote` 原挂 `{{Documentation|Quote/doc}}` 给 QUOTE/Quote/Quote/main 三页共享渲染 Quote/doc——QUOTE 挂自有 /doc 前须先摘除（否则双文档盒），并在 Quote、Quote/main 模板体上补偿挂载保持各自文档盒（已同步处理，见技术约定）。
- **最后 10 个模板文档已补全**（2026-07-29，55/55 全覆盖）：`Clear`/`Collapse`/`MG`/`Main`/`QA list`/`Ringa`/`Tooltip`/`Twitter`/`WP`/`加护` 全部新建 `/doc`；`Collapse`/`Tooltip`/`MG`/`WP` 的内联 templatedata（含 CSS 链接小节）迁入 `/doc`，10 个模板体均挂 `{{Documentation}}`（并入已有 noinclude 内部；`Collapse`/`Tooltip` 原为「双 noinclude」结构，合并为一个并保持 transclude 输出逐字节等价）。写入脚本 `logs/write_final_docs.py`，改动前快照 `logs/snapshot_final_docs_before.py`（`logs/final_docs_snapshot.json`），验证 `logs/verify_final_docs.py`（10 模板页各恰好 1 个文档盒 + 10 个 /doc parse + 10 个引用页改动前后 parse 对比渲染与自动分类全等价，ALL CHECKS PASSED）。实测 quirks 已写进各 `/doc`：`Tooltip` 主空间 51 个引用全部是经 `Seirei or Elf`/`Yousei or Elf` 的间接调用，文章页无直接调用；`Twitter` 参数名为 `#`（井号），调用须写 `|#=用户名`；`Collapse` 的 `id` 默认 0（默认同组联动）；`加护` 与 Elf/Seirei 同型但经 `{{R|加护||加護|Kago}}` 实现、无 `<!--nobot-->` 注释；`Ringa` 是带同名脚注（`name="ringa"`）的字词转换模板（as-is + onlyinclude 包裹）。**坑**：验证「恰好 1 个文档盒」不能用字符串 `模板文件` 计数——单个文档盒渲染就含 2 处（盒标题 + 底部「編輯模板文件页面」链接），应计 `<b>模板文件</b>`。

### 2. ~~零引用模板评审~~（2026-07-26 已完成）

32 个零引用模板经全站 wikitext grep 复核（发现 embeddedin 盲区，见技术约定）后处置：

- **删除 26 个模板 + 连带孤儿 6 页**：Assert empty、Assert eq、Auto link、角色分类、Navbar、Navbox Advanced、Transclude、Doc、Border-radius、Cc-by-sa-3.0、Permission、Header、InfoboxGrid、Jiro Onofy、Lowercase title、Mainpage right、Nomobile、Notice、Poll、Theme、To en、晚街与灯，及零引用重定向 Character、CopyText、Tl；连带删除 Mainpage Staff、Tab/Assert、Module:assert（+/doc）、MediaWiki:Gadget-Poll.css、Cc-by-sa-3.0/doc、Permission/doc。删除前 wikitext 存档在 `logs/deleted_templates_2026-07-26.json`。
- **保留 6 个**：`!`（143 个图库页在 `#tag:tabber` 参数里使用，embeddedin 盲区实锤）、`!!`、`=`（转义元模板备用）、`Ruby-zh-b`/`Ruby-zh-p`（注音族 zh 分工：b=竖排注音符号、p=拼音，暂无使用场景但族内保留）、`Sandbox`（Tab 用法试验场，近半年仍在用）。（后续更正：`!`/`=`/`!!` 已于 2026-07-28 删除——`{{!}}`、`{{=}}` 是 MW 内置 magic word，「143 处使用」从不构成模板调用，embeddedin=0 并非盲区而是真相；`!!` 零引用随族清理。`Ruby-zh-b`/`Ruby-zh-p`/`R/ja`/`Delete` 同日删除——用户判断零引用即无保留价值；连带删除空分类 `Category:请求删除`。见技术约定。）
- **待定项已处理**：`RailModule` 确认无使用需求（侧栏自定义内容展示位，当前无可放内容）——已摘除 Wiki-navigation 导航项并重编译、删除模板；`Category:断言模板`（断言体系删除后空分类）已一并删除。
- **2026-07-28 复核补刀**：发现首轮复核未排除模板自身/自身文档里的示例调用，导致一批真零模板被误判为使用中。排除后重跑全站（含 ns 6，双法交叉，配方见 `docs/template-usage-audit.md`「grep 的三个坑」），追加删除 8 模板 + 8 个 `/doc`：`StructuredQuote`（连 `#SQuote:` 解析器函数也零使用）、`Infobox`（母版，实际无人调用）、`Infobox album/episode/item/location/quest`、`Tocright`；索引页同步摘除。存档 `logs/deleted_templates_2026-07-28.json`。
- **复核中确认非遗漏**：`Auto ruby`（151 处经重定向别名 `R` 使用）、`Infobox event`（2 处经 `Infobox Events`）——grep 按本名统计为 0 是别名归账问题，非真零。（后续：`Auto ruby` 已于 2026-07-28 并入 `R`——`R` 由重定向转为模板本体，`Auto ruby` 与其零引用子页 `/ja` 删除、`/ja` 随迁为 `R/ja`，`Tab/Ruby` 链接与索引页同步；存档 `logs/deleted_auto_ruby_2026-07-28.json`。en 站无 `Auto ruby`，无搬运风险。）
- **保留**：`Delete`（请求删除流程件，虽当前零引用）。（后续：已于 2026-07-28 删除，连 `/doc` 与空分类 `Category:请求删除`；存档 `logs/deleted_final_zero_2026-07-28.json`。）
- **零引用重定向 12 个已删**（2026-07-28 晚些时候）：`Infobox novel`、`Re:Zero Light Novel Volumes`、`Re:Zero Arc 4/5 Manga`、`Re:Zero Bond(s) of Ice Manga`、`Re:Zero Daiisshou~Daiyonshou Manga`、`Re:Zero Daigoshou Manga`、`Re:Zero Ex Manga`（均曾指向 `Infobox book`）。en 站有同名的 9 个已加入 `jobs/jobs.py` 模板替换任务（搬运页里的旧名由 bot 批量替换为 `Infobox book`，故无需保留重定向）；en 无同名的 3 个（`Infobox novel`、`Bond of Ice`（单数）、`Ex Manga`）直接删。存档 `logs/deleted_redirects_2026-07-28.json`。
- **重定向 `Infobox Events` 已删**（同日）：确认为 en 站搬运名（en 有 `Template:Infobox Events`，无 `Infobox event`），已加入 jobs 替换（→ `Infobox event`），zh 现存 2 处调用（术语：王室疫病、术语：王族誘拐案）已先行改名。存档 `logs/deleted_redirect_infobox_events_2026-07-28.json`。
- **重定向 `Infobox battles`、`Re:Zero Manga Volumes` 已删**（同日）：同为 en 搬运名（en 各 31/44 引用），已加入 jobs 替换（→ `Infobox battle` / `Infobox book`），zh 现存 3 处调用已先行改名。至此索引页重定向节清空，en 旧名全部由 bot 批量替换接管。存档 `logs/deleted_redirects_round3_2026-07-28.json`。
- **零引用子页重定向 `Tab/Infobox novel` 已删**（同日，Infobox novel → Infobox book 改名残留）。存档 `logs/deleted_tab_infobox_novel_2026-07-28.json`。
- **Module 侧改名残留已清**（2026-07-29）：novel→book 改名时漏了 Module 侧——`Module:Infobox novel`（内容为 shim `return require [[Module:Infobox book]]`）与 `Module:Infobox novel/doc`（重定向）零引用、全站无 `Infobox novel` 字样，已删（en 站 Module 空间无 Infobox 模块，无搬运重引入风险）。存档 `logs/deleted_module_infobox_novel_2026-07-29.json`。至此全站 Infobox 命名统一为 `Infobox X`（X 小写英文）：Template 4 个（battle/book/character/event）+ Module 1 个（book）+ 1091 个引用页的调用写法全部规范。
- **信息框命名统一补漏**（2026-07-29）：首轮只查了名字带 Infobox 的页面，漏了**实现为信息框但名字不带 Infobox** 的 6 个模板（判据：wikitext 含 `<infobox>` 标签或 `#invoke` infobox 模块）。改名（移动不留重定向，308 个主空间引用页同步替换）：`Anime`→`Infobox anime`、`Seiyu`→`Infobox seiyu`、`Music`→`Infobox music`、`Re:Zero BD`→`Infobox bd`、`Staff`→`Infobox staff`、`Re:Zero Game`→`Infobox game`。en 有同名的 4 个（Anime/Music/Re:Zero BD/Re:Zero Game）已加入 jobs 模板替换任务接管搬运页；`Seiyu`/`Staff` 是 es 站搬运（en 无同名、不经 transferbot），无需替换任务。索引页 `ReZero Wiki:模板` 同步。至此 10 个信息框全部 `Infobox X` 命名。迁移脚本 `scripts/oneoff/rename_infobox_templates.py`，存档 `logs/renamed_infobox_templates_2026-07-29.json`。
- **别名收敛**（同日，用户定名）：`BV` 为正（B 站现行 ID 格式），21 处 `{{AV}}` 已批量改 `{{BV}}`、jobs 加替换、删 `AV`；`QUOTE`、`Quote` 由重定向转为模板本体（`Quote/big`、`Quote/small` 零直接调用，内容并入后删除；`Quote/main` 共用实现保留；`Tab/Quote` 链接、`BV/doc` 别名行同步）。至此 Template 命名空间**重定向清零**。存档 `logs/deleted_aliases_2026-07-28.json`。

### 3. ~~分类补全与子分类整理~~（2026-07-26 已完成）

- 决策：按子分类细分（平铺会与 Template 命名空间作用重合）；新建 `注音模板`/`内容模板`/`格式模板` 3 个子分类，时共 15 个子分类（2026-07-27 子模板并入元模板后为 14；2026-07-29 `内容模板`（4 个信息框改挂 `信息框模板`）与 `消息框模板`（Bot→维护、Category redirect→重定向）清空删除后为 12）。
- 60 个无分类顶层模板全部归类：重定向 17、字词转换 7、注音 5、引文 6、外部链接 4、首页 3、消息框 1（Welcome）、维护 2（Init、Disambiguation）、内容 5、子模板 1（MW）、格式 8、直属 1（`=`）。原直属的 `T`、`Ruby-ja`、`Ruby-zh-ja`、`T/piece` 改挂对应子分类；终态 103 个顶层模板 100% 入树。
- 怪异点查明非误用（机制见技术约定）：`Template:元模板` 改名 `Template:元模板标记` 消歧并留重定向；`Category:元模板`（Tab 经引用元模板标记加入）与 `Category:子模板`（组成件）语义各自成立。
- 仍直属 `Category:模板` 的 3 个：Blur、DISPLAYTITLE、Self——均为通用工具模板（原 7 个中的 `!`、`!!`、`=`、`Tocright` 已删），如需可再细分（Blur→格式、Self→著作权），非必要。（后续：2026-07-28 `DISPLAYTITLE` 删除、`Self` 随文档修订改挂 `著作权模板`，直属仅剩 `Blur`。）
- 后续（2026-07-27）：`Category:子模板` 并入 `Category:元模板`（理由见技术约定）；`元模板标记` 内联进 `Tab` 后删除（含旧名重定向）；`Documentation` 移入元模板；索引页「模板工具（元模板）」节同步更新。
