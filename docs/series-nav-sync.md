# 系列导航（Tab/*）与 en 同步 SOP

系列跳转（前后集/前后卷/前后篇）全部由 `Tab/*` 页首标签条承担，信息框不声明
previous/next（约定见 `docs/templates.md`）。en 站用信息框 Previous/Next 字段 +
页底 navbox 双轨；zh 不跟随该方案，但 **en 的 prev/next 链是系列结构的权威规格书**。

## 不变量

- en 侧新增/合并/拆分系列内容后，zh 有两处不会自动跟随：
  1. **新搬运页不带 Tab**——transferbot 只搬 en 内容，en 没有 Tab 体系；
  2. **Tab 模板条目滞后**——新话数/新卷要手动补进对应 Tab。
- transferbot 带入的 `| previous/next =` 残留由 fix:para 常驻删行，无需处理。
- en 的合并/拆分调整要跟随（zh 拆分页结构与 en Part 结构一一对应）。

## 审计工具：`src/scripts/tools/series_nav_audit.py`

只读、匿名可达（≤50 titles/批 prop 查询），跑法：

```bash
uv run python src/scripts/tools/series_nav_audit.py
```

输出两项检查，全部干净时退出码 0，有待办则 1：

1. **覆盖检查**：en 每个 prev/next 目标的 zh 对应页 ∈ 该页 Tab 链接集
   （分层 Tab 两跳判定：本页 Tab 链接的季/章总页自带下一层 Tab，如
   `动画:第50集` 经 `动画:第三季` 的 Tab 覆盖 `第51集`）。
   - `未覆盖（页面无 Tab）` → 新搬运页待挂 Tab，或整个系列缺 Tab；
   - `未覆盖（目标不在 Tab 链接集）` → Tab 条目待补；
   - `N/A（zh 无对应页）` → en 已更新 zh 未搬运，正常待搬运状态，无需动作。
2. **拆分对应检查**：zh 前/中/后篇拆分页 vs en Part N（篇数一致、
   前→Part 1、中→Part 2、后→末位 Part；单成员且 en 链接非 Part 页的视为
   作品名后缀，如「蜜月背后篇」）。

实现要点（改动前必读）：en→zh 映射用 zh 页源码的 `[[en:…]]` 建立（langlinks
派生表不可靠）；参数值匹配用 `[ \t]*` 不用 `\s*`（`\s` 吃换行，空值行会吞
下一行）。

## 同步步骤

1. 跑审计工具，未覆盖清单即工作队列（也可由 watchdog 发现新搬运页后触发）。
2. 目标页未搬运 → 等 transferbot（re0_transferbot 循环任务），不急。
3. 已搬运但无 Tab → 挂载：页首顺序 `{{Init}}` → `{{To do}}` → `{{Tab/…}}`；
   注意 `{{To do}}{{#infobox` 粘连形态（无独立 To do 行时锚到 Init 后）。
4. Tab 缺条目 → 补进对应 Tab，链最终目标页（不链重定向）：
   - 拆分话/篇写双条目（`[[…前篇|N]]` + `[[…后篇|后]]`）；
   - 命名沿英文系列名惯例（`Tab/Manga Arc 5 Chapter`、`Tab/Music`）；
   - 多行结构：季/章行在前（含当前位加粗），内容行在后；
   - zh 未搬运的条目用 HTML 注释暂存（`<!--暂未搬运--><!--|[[…]]-->`）。
5. en 合并/拆分调整 → 跟随：拆分组核验见工具第 2 项，Tab 同步改链。
6. 复跑审计工具至未覆盖清零。

## en 侧数据特点（实测）

- en 会事后合并/拆分章节（曾拆分后合并的章，其 Part 页变重定向），
  redirects=1 归一后以现结构为准。
