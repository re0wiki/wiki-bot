# 待办与待决策项

跨任务的待办与决策记录。单个领域（模板/Module）的领域知识归 `templates.md` / `modules.md`。
已完成的待办若不再需要相关信息就直接删除，不留完成记录（有长期价值的知识并入对应领域文档；执行历史查 git）。

## 待处理

### Module:Infobox book 语言家族扩展（印尼语/德语等）

fix:para 的多语言堆积拆分只产出 Module `languages` 表内的 12 种语言后缀；en 侧已出现 Indonesian（漫画第2章各卷、小说:1卷）、PAL 区（游戏:虚假的王选候补）、JP 简写（设定集、画集:Re:zeropedia）等表外标注，这些参数的堆积行被保守跳过。要收录就往 Module 的 `languages` 表加条目（标签如「印尼语」）+ `user-fixes.py` 的 `CRAM_LANGS` 同步加映射（两个事实源，注释已互指）。

## 已决策

### MediaWiki 命名空间的 JS 页面不为纯规范化改动

每次改动需 Fandom 人工审核，无功能更改就不要动（缘起：`Common.js` 一处繁体注释，决定保留）。

### 图片删除/改名不同步（re0_image 只增不删）——维持现状

残留图片基本无害；删除还要同步更新引用，不值得处理。限制已注明在 `calc_diff` docstring。

### re0_redirect 对未登记前缀建重定向——维持现状

多余重定向无用但无害。
