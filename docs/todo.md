# 待办与待决策项

跨任务的待办与决策记录。单个领域（模板/Module）的领域知识归 `templates.md` / `modules.md`。
已完成的待办若不再需要相关信息就直接删除，不留完成记录（有长期价值的知识并入对应领域文档；执行历史查 git）。

## 待办：2026-08-03 全站模板复查（第二轮）

数据来源：当日刷新的 `logs/template_inventory.json` + `logs/template_usage_recheck_2026-08-03.json` + ns10 全量 wikitext 离线分析（`logs/recheck_2026-08-03_round2.py` 系列）+ `action=parse` 实证。

### A. 明确错误（建议直接修）

1. **5 个 /doc 残留 8 处 `{{[[Template:X|X]]}}`**（上午一轮扫漏）：QUOTE×2、Tooltip×2、Yousei or Elf×2、Yousei×1、加护×1。修法同上午：改 `{{T|X}}`。
2. **`Template:Documentation` 源码繁简混杂**：`編輯模板文件页面`、`這如何運作？`（含注释里 `有時`）——同 08-02 B9 类（Bot/Category redirect/Disambiguation 已修，此个漏网）。chrome 文本渲染在全部 55 个模板页上。
3. **`Template:Documentation` 自身不调 `{{Documentation}}`**：/doc 存在且已中文化但孤儿化（访问模板页看不到文档盒）。修法：并入其已有 `<noinclude>` 内（防引入换行）。

### B. 待决策

4. **`Seirei or Elf`/`Yousei or Elf` 索引节与分类不一致**：索引列在「页首与维护」，自身分类是 `字词转换模板`。功能双重属性（字词转换机制 + 译名复核追踪），先例「冲突改分类」不适用（改成维护模板更不对）。选项：索引挪入/增列「字词转换」节，或维持现状。
5. **`Sandbox` 仍占索引「格式与工具」节条目**：当日上午已清空为最小占位并摘除分类，索引条目失去归类依据。选项：摘除索引条目，或保留作占位说明。
6. **（顺手）Documentation chrome 标题「模板文件」与 /doc 约定用语「模板文档」不一致**：改标题会影响全部 55 个模板页渲染文本，纯措辞统一，可与 A2 一并做或不做。

### 本轮确认正常（排除项）

- 换行 transclude 类已清零：静态候选（BV/Kana2Romaji/Q/QA/R + Infobox 系）经 parse 实证均为 onlyinclude 保护或块级无害；上午修的 9 个复扫干净。
- 结构稳定：227 页 / 55 顶层 / 重定向 0 / 文档 55/55；`Category:模板` 直属成员 0；零引用仅 Sandbox（有意）。
- 「有意加分类」19 个模板与 `docs/templates.md` 表完全一致；templatedata 全部合法 JSON；`<code>` 内 `-{ }-` 全部已 nowiki。
- CSS 链 22 个 @import 全部存在；索引 60 条目全部存在、55 顶层全部进索引。

## 已决策（2026-07-31）

### 图片删除/改名不同步（re0_image 只增不删）——维持现状

残留图片基本无害；删除还要同步更新引用，不值得处理。限制已注明在 `calc_diff` docstring。

### `.idea/` 已跟踪文件——维持现状

自带 .gitignore 模板没忽略那些文件所以提交了；项目无其他维护者，交上去至少无害。

### re0_redirect 对未登记前缀建重定向——维持现状

多余重定向无用但无害。

## 已评估、决定不做

### probe_* 五个探测脚本不合并且保留样板重复

`docs/cloudflare-429.md` 按文件名逐一引用这些脚本作为实证出处（哪个脚本跑出哪组数据），
合并会破坏可追溯性；它们是一次性研究脚本而非维护中的工具，重复的样板没有维护成本。
