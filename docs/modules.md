# Module（Lua）审查

2026-07-30 对 Module 命名空间 43 个页面（15 个功能模块 + 28 个鼠色猫语录数据表）的全量审查。
源码快照脚本 `scripts/dump_modules.py`（输出 `logs/modules/`），引用量与疑点验证 `scripts/verify_module_findings.py`。

**文档惯例**：Module 的 `/doc` 子页由 Scribunto 自动转置渲染在代码上方（与模板 `{{Documentation}}` 机制无关），所以 Lua 头注释无需写「文档见 /doc」之类的指针；模块文档直接写进 `/doc` 子页即可（先例 `Module:Kana2Romaji/doc`）。

## 引用量总览（embeddedin，全命名空间）

| Module | 引用 | 说明 |
|---|---|---|
| Init / AutoTab / Title / Utils | 2210 | 每篇文章经 `{{Init}}` 间接引用 |
| Interwiki | 2200 | 信息框英文名/英译 |
| Tab | 1143 | 新 tab 系统（`{{Tab}}` → Tab/* 派生页） |
| Infobox book | 719 | |
| Character image | 339 | Infobox character 图库 |
| Kana2Romaji | 274 | |
| 鼠色猫语录 | 209 | |
| Auto ruby | 151 | 经 `{{R}}` |
| Bili | 24 | 经 `{{BV}}` |
| NoteTA / WikitextLC | 2 | 维基百科移植件 |
| **Set** | **0** | **孤儿模块** |

## 确认的问题

### Bug

1. **Kana2Romaji ヴ系假名未处理**（实测）：`ヴィルヘルム → ヴィruherumu`（ヴィ 原样漏出，威尔海姆的罗马字生成是坏的）、`ヴァルグレン → varuguren`（首字母未大写）。根因：`table2` 只有 `ヴァ` 一条且在大写化之后执行；ヴィ/ヴ/ヴェ/ヴォ 全缺。修法：补全ヴ系 5 条并进主表（大写化之前）。
2. **Kana2Romaji 全局变量泄漏**：`s, num = mw.ustring.gsub(...)` 的 `num` 未 local。
3. **生产代码残留调试日志**：`Title.parse_title` 每次调用 `mw.logObject`（2210 页 × 每页数次）；`AutoTab._tab` 每个 tab 链接 2 条 `mw.log`；`Auto ruby`、`Infobox book` 同。刷屏 Scribunto 调试台且白耗 Lua 时间，应删。

### 卫生问题

4. **Module:Set 孤儿**（embeddedin=0，无任何 require）：删除，同 Module:assert 先例。
5. **AutoTab 头部注释已过时**：「性能有问题，等新 tab 写好会删掉」——新 Module:Tab 早已上线（1143 引用），AutoTab 仍被 Init 依赖。要么把 Init 迁到 Module:Tab 后删 AutoTab，要么更新注释。
6. **Infobox book**：4 个函数未 local（`getDefaultName` 等污染全局）；`require("Module:title")` 大小写不规范；languages 用 `pairs` + 仅按日期排序，日期并列（含全空）时语序在渲染间不稳定；`local string = ...` 遮蔽标准库。
7. **NoteTA 死路径**：`Module:CGroup/*` 全站 0 页（已验证），CGroup 分支永不命中；全模块函数未 local；仅 2 引用。
8. **鼠色猫语录 4 个空数据子模块**：帕克/福尔图娜/Web连载网站上评论/动画实况解说均为空 `list`/`abbr` 占位。
9. **Utils**：lcp/lcs 的注释是大段 ChatGPT 问答实录，可精简为两行说明。
10. **Auto ruby**：`#args.romaji` 等对缺省参数不做 nil 防御（当前模板调用全传空串，无实际触发）。

### 验证后排除的疑点

- `Bili.lua` 的 `mw.ustring.sub(id, 0, 0)`：实测 `{{BV}}` 正确渲染 `data-bv`（Scribunto 对 0 索引的钳制行为与预期一致），**不是 bug**，但 `sub(id, 1, 1)` 更可读。
- `Init.display_title` 的 9 变体 `-{T|...}-`：冗余但正确（hans+hant 两条即可覆盖全部变体回退链），改动会触发 2210 页重渲染，不值得。

## 处置记录

2026-07-30 用户决定本轮全部不修，上述问题留作待办。执行修复时注意：Module 编辑会触发引用页重渲染（Init 链 2210 页），分批观察。

- **Kana2Romaji 已重写**（2026-07-30，用户指示）：旧实现（顺序 gsub 大表）废弃，重写为音拍 tokenize 的完整平文式——补全ヴ系（ヴァ/ヴィ/ヴ/ヴェ/ヴォ，修掉 `ヴィルヘルム→ヴィruherumu` 漏假名与首字母不大写两个 bug）与外来拗音（ファ/ティ/チェ/ツァ等）、ん 同化（b/p/m 前→m、元音/y 前→n'）、促音 tch、长音 macron 直接作用于前一元音（含 ē，旧「ee→ei」约定废除）、`num` 全局泄漏修复。接口与「无假名→空串」契约不变（`p._Kana2Romaji(s)` + `p.Kana2Romaji(frame)` 兼容 `kana=` 与位置参数 1）。部署+回归脚本 `scripts/deploy_kana2romaji.py`（幂等：内容相同则跳过保存；19 例测试矩阵全过），`Template:Kana2Romaji/doc` 规则描述已同步更新，`角色:菜月·昴` 信息框罗马字渲染抽查通过。模块文档（接口/契约/转换规则/示例）随后按惯例迁入 `Module:Kana2Romaji/doc` 子页（首行保留 `{{Tab/Ruby}}` 导航），Lua 头注释只留标题行（/doc 自动渲染在代码上方，无需指针注释——用户指正）。行为变化点：えー/エー 现在得 ē（旧为 ei）、っち 现在得 tchi（旧为 cchi）、んb/p/m 同化为 m、・（U+30FB）现在也转空格。
