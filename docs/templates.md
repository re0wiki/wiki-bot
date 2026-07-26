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

## 盘点数据（2026-07-26）

盘点脚本：`scripts/template_inventory.py`（只读；输出到 `logs/template_inventory.json`）。
引用量用 `Page.embeddedin()` 逐模板统计（Fandom 不支持 `mostlinkedtemplates`）。

- Template 命名空间共 279 页：129 顶层模板（其中 15 个重定向）+ 150 子页（`Tab/*` 116 个、`/doc` 25 个）。
  （2026-07-26 待办 2 清理删除 26 顶层 + 3 子页后约为 103 顶层 + 147 子页，下次盘点时刷新。）
- 文档覆盖：37/129 有某种文档（`/doc` 子页 24、调用 `{{Documentation}}` 31、noinclude 内联说明 8）；**77 个非重定向模板无任何文档**。
- 分类：`Category:模板` 直属成员仅 11 个 + 12 个子分类；**94 个顶层模板 wikitext 里没有任何分类**。
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

- `Category:模板` 旧文案自称「应覆盖全站模板」，实际远未覆盖（见待办 3）。
- **Fandom 的 templatelinks 不记录 `#tag`/解析器函数参数内的模板调用**：`{{!}}` 在 143 个图库页的 `{{#tag:tabber}}` 参数里真实使用，`embeddedin()` 计数却为 0（2026-07-26 实测）。判「零引用」不能只看 embeddedin，须辅以全站 wikitext grep：用 `generator=allpages` 逐命名空间取 `rvprop=content`，正则搜 `\{\{\s*(subst:\s*)?名称\s*[|}]` 调用形态（含 subst 残留）。

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
| 145 | Auto ruby、R |
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

完整清单见 `logs/template_inventory.json`（`has_doc_subpage`/`uses_Documentation_tpl`/`inline_doc_in_noinclude` 全 false 者）。
原清单中属零引用模板的条目已随待办 2 的删除自然消失。

### 2. ~~零引用模板评审~~（2026-07-26 已完成）

32 个零引用模板经全站 wikitext grep 复核（发现 embeddedin 盲区，见技术约定）后处置：

- **删除 26 个模板 + 连带孤儿 6 页**：Assert empty、Assert eq、Auto link、角色分类、Navbar、Navbox Advanced、Transclude、Doc、Border-radius、Cc-by-sa-3.0、Permission、Header、InfoboxGrid、Jiro Onofy、Lowercase title、Mainpage right、Nomobile、Notice、Poll、Theme、To en、晚街与灯，及零引用重定向 Character、CopyText、Tl；连带删除 Mainpage Staff、Tab/Assert、Module:assert（+/doc）、MediaWiki:Gadget-Poll.css、Cc-by-sa-3.0/doc、Permission/doc。删除前 wikitext 存档在 `logs/deleted_templates_2026-07-26.json`。
- **保留 6 个**：`!`（143 个图库页在 `#tag:tabber` 参数里使用，embeddedin 盲区实锤）、`!!`、`=`（转义元模板备用）、`Ruby-zh-b`/`Ruby-zh-p`（注音族 zh 分工：b=竖排注音符号、p=拼音，暂无使用场景但族内保留）、`Sandbox`（Tab 用法试验场，近半年仍在用）。
- **待定**：`RailModule`（空页，但 `ReZero Wiki:Wiki-navigation` 导航菜单有入口，删除需先改导航源并重编译）；`Category:断言模板`（断言体系删除后已空）。

### 3. 分类补全与子分类整理

- 94 个顶层模板无分类。待决策：全部平铺进 `Category:模板`，还是按现有子分类体系细分（信息框/分页/著作权/消息框/维护/外部链接/字词转换/引文/首页/重定向/元模板/子模板）。
- 子分类怪异点：`Category:元模板` 只有 `Tab` 一个成员；`Category:子模板` 的成员是 `T category` 和 `元模板`（像是误用）。整理时一并处理。
- 加分类时遵守 onlyinclude/noinclude 约定（见上），别泄漏进引用页。
