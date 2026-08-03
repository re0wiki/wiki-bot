# 待办与待决策项

跨任务的待办与决策记录。单个领域（模板/Module）的领域知识归 `templates.md` / `modules.md`。

## 待办：2026-08-03 全站模板复查发现

数据来源：`logs/template_inventory.json` + `logs/template_usage_recheck_2026-08-03.json`（当日刷新）。

1. **行内模板尾部换行被 transclude**（`action=parse` 实证：输出带 `\n`，HTML 折叠为空格，行内使用出现多余间隙）。修法 = 把内容后的换行并入 `<noinclude>` 内部：
   - `Ruby`（双份：内容后一个 + 两个独立 noinclude 之间一个，正是「{{Documentation}} 要并入已有 noinclude」坑）
   - `Elf` / `Seirei` / `Yousei` / `加护`（内容 `\n` 在 noinclude 外）
   - `Copy`（两个独立 noinclude 之间的换行，48 处调用全在 `ReZero Wiki:译名表`）
   - `Tooltip`（尾部换行经 `Ringa`、`Seirei or Elf`、`Yousei or Elf` 二级泄漏到 31+ 个引用页）
2. **9 个 /doc 违反「链到模板用 `{{T|模板名}}`」约定**，仍写 `{{[[Template:X|X]]}}`：Disambiguation、Elf、Kana2Romaji、QA list、Ringa、Ruby-ja、Seirei or Elf、Seirei、T category。
3. **`Blur` 分类错放**：自身挂根 `Category:模板`（该分类唯一直属成员），索引页已把它列在「格式与工具」节——按「冲突改分类」原则应改挂 `Category:格式模板`。
4. **索引页与分类不一致**：`NoteTA` 列在索引「格式与工具」节，自身分类是 `字词转换模板`（功能判据也支持后者）——把索引条目挪到字词转换相关节。
5. **`Twitter` 参数设计脆弱**：参数名是字面 `#`，位置参数 `{{Twitter|user}}` 静默失效（实证渲染 `http://www.twitter.com//`）。31 处现存调用全部正确用了 `|#=`，无实际坏链。改进方向：模板体改为 `{{{1|{{{#|}}}}}}` 兼容位置参数；顺手 `http://` → `https://`。
6. **`Template:Sandbox`**：零引用，内容是过时的 67 集动画 Tab 硬编码测试，且占着 `Category:格式模板`。建议清空为最小占位（分类摘除或改挂维护说明），与 `Module:Sandbox` 的沙盒惯例对齐。

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
