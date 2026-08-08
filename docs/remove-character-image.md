# 移除角色介绍图自动列举机制（方案）

2026-08-08 设计。机制：`Template:Infobox character` 经 `Module:Character image` 按「&lt;条目名&gt; &lt;媒介&gt; &lt;子分类&gt;角色介绍图.&lt;扩展名&gt;」命名约定穷举候选文件名，实际存在的文件自动进信息框图库。移除动机：依赖文件名与条目名严格对应，太脆弱；此命名格式的图已多年无人补充。

## 机制现状（实测）

- 模板 5 处 `#invoke:Character image|gen`：a/n/g/c 四个 panel section 的 `<format>` 与 `<default>` 各一份，m（其他）section 的 `<default>` 一份（`subs['m']` 为空表，m 的 invoke **本就是死调用**，产出空串）。
- 条目名取自 `{{#sub:{{SUBPAGENAME}}|3}}`——`SUBPAGENAME` 对主空间伪前缀页返回含前缀全题（`角色:菜月·昴`），`#sub|3` 恰好剥掉 `角色:`。**机制目前是活的**，不是摆设。
- 候选穷举范围写死在模块源码：媒介 4 类（动画/漫画/游戏/文库）× 子分类（TV/OVA、SP、第1~9章、冰结之绊、剑鬼恋歌、7 个游戏、3 个画师）× 扩展名 5 种（gif/png/jpg/jpeg/webp）。文件名中空格与下划线等价（MediaWiki 标题归一），模块生成的 `TV_OVA` 能命中实际文件名 `TV OVA`。

## 影响面（2026-08-08 实测，脚本 `logs/char_image_impact.py`）

- 全站 `*角色介绍图*` 文件 137 个。
- **当前真正被自动列举渲染的：44 个角色页、79 张图**。其中 38 页仅游戏《虚假的王选候补》1 张；图最多的是 爱蜜莉雅（16）、菜月·昴（13）、莱茵哈鲁特（5）、碧翠丝（3）、库珥修/陶德·方古（2）。
- **56 个文件已死**（存在但不渲染）：旧译名（艾米莉娅 21 个、蕾姆、佩特拉、菜月昴、露伊/鲁伊、亚拉基亚、芙蕾得莉卡等）、格式不符（`EX` 段、缺媒介段、`.PNG` 大写、`..webp` 双点、全角 `／`、未知子分类 たけはらみのる/坂井久太）、页面不存在（Mazeran）。
- 全站无任何页面显式设置 `image_a/n/g/c` 参数（201 页设置的 `image` 参数走 m section，与本机制无关）——a/n/g/c 的 `<format>` 分支目前全站未触发，可自由重定义语义。
- 配套资产：`Template:Tab/Character image`（仅挂在模板页/模块页/模块 /doc 三处）、`Module:Character image/doc`、`File:角色介绍图示例图.jpg`（零引用）。模板 `/doc` 未提及此机制。

## 目标状态

信息框图片完全改为显式参数，渲染保持逐像素等价：

- 模板 a/n/g/c 各 section 改为：

```xml
<image source="image_a">
  <format>{{#tag:gallery|{{{image_a}}}}}</format>
</image>
```

- 页面侧参数值 = 换行分隔的 `文件名{{!}}caption` 清单（caption 经 `{{!}}` 转义竖线，否则被当成模板参数分隔符；本站图库页已有同款写法先例）。caption 沿用现状（子分类名：TV/OVA、第1章、INFINITY……）。
- m section 仅摘除死 invoke，其余不动。
- 今后信息框加图 = 手动填参数，与译名改名、页面移动完全解耦。

## 执行步骤（沿用参数改名 SOP 的 fallback 三段式）

1. **模板加 fallback**：a/n/g/c 的 `<format>` 先改为纯 `{{#tag:gallery|{{{image_a}}}}}`，`<default>` 的 invoke 保留。此刻全站零页面设这些参数，渲染零变化（抽样 parse 验证）。
2. **写显式参数**：一次性脚本按实测 live 清单给 44 页信息框插入 `image_<sec>` 参数（多行值、`{{!}}` caption 分隔，插入位置在 `image`/`name` 参数前，对齐 doc 的 a/n/g/c 顺序），另把 3 张未使用的非重复死文件补进对应页（见决策记录）。逐页编辑前后 `action=parse` 快照对比（purge 后取快照防陈旧缓存；归一化 pi-tab 随机 hash、data-source 属性、HTML 注释，先例 `scripts/oneoff/snapshot_renders.py` / `compare_snapshots.py`）。
3. **摘除机制**：复扫确认 44 页全部带参后，模板删 5 处 invoke + 4 个 `<default>` + noinclude 里 `{{Tab/Character image}}`。再次全量快照对比（44 页应零差异；其余 292 页 default 本就渲染空图库，亦应零差异）。
4. **删除配套资产**：`Module:Character image` 及其 `/doc`、`Template:Tab/Character image`。模板改动后模块 embeddedin 需 `purge(forcelinkupdate=True)` 才会归零，删前确认。
5. **文档同步**：`Template:Infobox character/doc` 补 image_a/n/g/c 参数说明（若已有条目则更新语义）；wiki `ReZero Wiki:模板` 索引；本仓库 `docs/modules.md` 引用量表删 Character image 行、`docs/templates.md` Lua 重写评估段的相应表述；本文件移入完成记录或删除。
6. 脚本归档 `scripts/oneoff/`（迁移 + 快照对比），提交信息 `feat(wiki): 移除角色介绍图自动列举机制`（wiki 侧改动无 git，仓库提交只含脚本与文档）。

## 决策记录（2026-08-08 用户拍板）

- **死文件不删**；其中不重复的补充进对应角色页。2026-08-08 梳理：56 个「死文件」绝大多数是旧译名**重定向**（指向现名文件，无害，不动）；真未被任何页面使用且内容不重复的仅 3 张，补充方式：
  - `佩特拉 游戏 虚假的王选候补角色介绍图.jpg` → `角色:佩特拉·莱特` `image_g`
  - `安娜塔西亚 游戏 虚假的王选候补角色介绍图.jpg` → `角色:安娜塔西亚·合辛` `image_g`
  - `爱蜜莉雅 动画 たけはらみのる角色介绍图.png` → `角色:爱蜜莉雅` `image_a`（内容即 SP 图——`艾米莉娅 动画 SP角色介绍图.png` 重定向到它，caption 用 SP）
  - 卡萝/格林/罗兹瓦尔·J·梅札斯的剑鬼恋歌图、幼年爱蜜莉雅 2 张**早已被各页 `image` 画廊显式使用**，无需补。
- **`File:角色介绍图示例图.jpg` 不删**。它唯一的使用处是 `ReZero Wiki:施工计划表`「搬运组·长期」的「全角色介绍图」待办（含 `#invoke:Character image` 命名一览）；该页 2026-04-01 由用户删除（摘要「废除计划，自由编辑」，最后修订 revid 235488），待办描述已随之消失，无需再清理。历史待办存档见 `docs/todo.md`。
- **文件名中的旧译名不处理**；译名自动统一任务本来就不覆盖 File 空间。
