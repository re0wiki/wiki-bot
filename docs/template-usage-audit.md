# 零引用模板审计（Fandom 模板删除前检查）

背景：审查 `embeddedin()` 报告零引用的模板，决定删除还是保留。
2026-07 模板清理实测：32 个候选，全站 11,207 页扫描。
每次盘点的数据与逐模板结论记录在 `docs/templates.md`，本文是可复用的工作流。

## 为什么 embeddedin 单独不可信

Fandom 的 templatelinks 至少漏两种真实使用：

1. **`#tag:` 扩展内容**：`{{#tag:tabber|...}}` 里的 `{{!}}`（`{{!}}-{{!}}` 行分隔符）
   渲染时是活的模板调用，但从不记入 templatelinks。实测：`Template:!` embeddedin=0，
   但 143 页有字面 `{{!}}`（全部 `*/图库` 页 + 多个 Infobox）——删了会弄坏所有 tabber。
2. **未使用模板里的 `<includeonly>` 调用**：死模板体内 `<includeonly>{{SomeOther}}</includeonly>`
   在自身页面上永不解析，`SomeOther` 显示 0 引用，但源码里依赖存在。

结论：对每个候选名跑全站 wikitext dump + 正则 grep
（`\{\{\s*(?:subst\s*:\s*)?Name\s*[|}]`，首字母不区分大小写），
元模板另查字面 `{{!}}` / `{{!!}}` / `{{=}}`。grep 命中 ⊇ templatelinks，以 grep 为准。

## grep 的三个坑（2026-07-28 复核实测，曾造成漏判/误判）

1. **必须排除模板自身与自身 `/doc`**：模板文档里的示例调用（`{{StructuredQuote|...}}` 之类）
   会被 grep 算作「使用」——2026-07-26 首轮复核因此把 `StructuredQuote`、未用 Infobox 系、
   `Tocright` 误判为 used 而漏删，2026-07-28 排除自身后才暴露。
2. **重定向别名的用量记在目标上**：页面写 `{{R}}` 时按本名 grep `Auto ruby` 是 0，
   但 `embeddedin(Auto ruby)`=151——templatelinks 会把经重定向的引用归到目标页。
   判「零」要 embeddedin 交叉验证（或 grep 时把所有重定向别名并进模式）；
   反过来，embeddedin 有的盲区（上节）靠 grep 补。**两法都零才算零**。
3. **别漏命名空间**：授权模板（`Fairuse`/`PD` 等）只用在 File 页（ns 6），
   维护模板可能在 User/Project 页——dump 范围要含 0/2/4/6/8/10/14/828
   （本节的旧配方排除 ns 6/7，只适用于当时已知名单，不复用）。

复核脚本：`scripts/recheck_template_usage.py`（全命名空间批量 dump + 逐模板 grep，
排除自身/自身子页，输出零引用清单与重定向标注）。

## 全站 dump 配方（全命名空间，默认限速下 ~11k 页 ~3 分钟）

```python
from pywikibot.data.api import QueryGenerator
for nsid in [i for i in site.namespaces if i >= 0 and i not in (6, 7)]:
    for pg in QueryGenerator(site=site, generator="allpages",
                             gapnamespace=str(nsid), gaplimit="max",
                             prop="revisions", rvprop="content"):
        text = pg["revisions"][0].get("slots", {}).get("main", {}).get("*", "")
```

- `QueryGenerator` 配 generator 直接产出**页面 dict**——不要再解 `result["query"]["pages"]`
  （那样静默拿不到东西）。
- `gapnamespace="*"` 会被拒（`badvalue`）——显式迭代命名空间 id。
- 多页 generator 查询禁止 `rvlimit`/`rvdir=newer`（`invalidparammix`）——省略即可，
  `prop=revisions` 本来就只返回每页最新版本。（单页查首版本另发 `simple_request`
  带 `rvdir=newer, rvlimit=1`。）

## 分类法（32 候选 → 三层）

- **Tier A — 必须保留，embeddedin 错了**：有 grep 命中的元模板（`!`）。平凡兄弟（`!!`、`=`）
  也保留——同类，保留成本≈0，误删代价是静默破坏。Ruby 族成员（`Ruby-zh-b/p`）即使 0 引用
  也按族保留：族分工（注音符号竖排 / 拼音 / 日语）是 documented design，且族在持续扩展。
- **Tier B — 死依赖链**：未使用模板，grep 命中只来自**其他未使用模板**
  （如 `Navbar` ← `Navbox Advanced`；`Transclude` ← `Navbar`；`Assert eq` ← `Assert empty`；
  `Auto link` ← `角色分类`）。整链一起删，并检查链删除后的二级孤儿（Lua 模块、Tab 子页、
  gadget、链引用过的 MediaWiki: CSS 页）。
- **Tier C — 历史遗留 / 到站即坏 / 测试页**：2015 建站导入的 starter-kit 模板
  （`Border-radius`、`Cc-by-sa-3.0`、`Permission`、`Mainpage right`、`Poll`…）、
  引用缺失模板/模块而坏的、被清空的、个人测试页。以「坏」为由删除前，
  先核实被引用的模板/模块确实不存在。
- **重定向单列一类**：别名重定向（`Tl` → `T`、`Character` → `Infobox character`）
  零引用是正常的；删不删价值都低。**用户偏好：随批次一起删**（2026-07 确认——
  `Character`、`CopyText`、`Tl` 均已按请求删除）——整洁优先。
- 分类工具坑：`Page.isRedirectPage()` 对 `#重定向 [[...]]` 的页面可能返回 `False`——
  分类时信 wikitext 不信标志位。

## 执行阶段（删除 + 清理清单）

1. **先备份**：删除前把每个候选的 wikitext 存 JSON 归档
   （仓库 `logs/deleted_templates_YYYY-MM-DD.json`）。管理员能 undelete，
   但本地归档让自助恢复/diff 变得 trivial。
2. **删前 whatlinkshere 扫荡**——`page.backlinks(follow_redirects=False)`
   （snake_case 参数；camelCase 会 TypeError）。它能抓到 embeddedin 和源码 grep **都**看不见的用法：
   - 经辅助模板链接的索引页（`{{t|Name}}`——源码里没有字面 `Template:Name`，grep 漏掉，
     但渲染链接会变死链）；
   - 导航/菜单源（实例：`ReZero Wiki:Wiki-navigation` 有指向空模板 `Template:RailModule`
     的菜单项——删了会让全站导航红链；需先改导航源 + 重新编译，扣住模板问用户）；
   - 删除后会孤儿的支撑页：被删模板的 `/doc` 子页（`Cc-by-sa-3.0/doc`、`Permission/doc`）、
     Module 的 `/doc`（`Module:Assert/doc`）、gadget CSS（`MediaWiki:Gadget-Poll.css`）。
     同批次一起删。
   - 存档论坛/讨论页评论里的链接：可接受红链，忽略。
3. **删除**：`site.login()`，`assert site.user() == <bot 账号>`，然后逐页
   `p.delete(reason=..., prompt=False)`。每页约 `put_throttle` 秒（32 页 ≈ 3 分钟）——
   放后台跑，别前台干等。
4. **事后检查**：对每个候选重新 `exists()`（应全部不存在）；再扫荡二级残留——
   被清空的分类（实例：`Category:断言模板`——报给用户，别自动删）、wiki 侧索引页
   （摘掉死条目；普通编辑，不加 bot flag）、仓库 todo 文档（记录结论和日期，提交）。
