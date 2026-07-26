# pywikibot 自带脚本速查

原则：**能直接用 `pywikibot/scripts/` 里的现成脚本就别手写**。手写只用于现成脚本确实覆盖不了的场景（如 `scripts/re0_*.py` 那 4 个）。

运行方式（仓库根目录）：

```bash
PYTHONPATH= .venv/Scripts/python.exe pywikibot/pwb.py <script> [生成器] [脚本选项] [-simulate]
```

- 干跑一律先加 `-simulate`；`-always` 跳过逐页确认（`run_job` 会自动补）。
- 目标站默认就是 `zh:re0`（user-config.py），读别的语言站用 `-lang:en` 等。
- 例外：**transferbot 不接受 `-always`**（加了报错；它本来就会覆盖目标页）。

## jobs 里已在用的

`transferbot` / `interwiki` / `replace -fix:*` / `category remove` / `template` / `fixing_redirects` / `redirect` / `cosmetic_changes` / `noreferences` / `touch`——见 `jobs/jobs.py`，不赘述。

## 未入 jobs 但对常见任务有用的

| 任务 | 脚本 | 说明与示例 |
|---|---|---|
| 批量移动页面（改前缀、整理英文前缀残留页） | `movepages` | `-from:X -to:Y` 单个；`-pairsfile:文件` 批量（每行 `旧名<Tab>新名`，也支持空格分隔）；`-noredirect` 不留重定向；`-notalkpage` / `-nosubpages`；`-prefix:角色` 给生成器选出的整批页加前缀（会先去掉旧前缀）。比手搓 `rename.py` 的流程正规。 |
| 批量在页首/页尾加文字 | `add_text` | `-text:"..."`（`\n` 表换行）或 `-textfile:路径`；`-up` 加到页首；`-create` 页面不存在则创建；`-createonly` 只建不改。例：给某分类所有页页首补模板：`add_text -cat:某分类 -text:"{{某模板}}" -up -always` |
| 批量删除 / 恢复页面 | `delete` | 需 zh 站管理员权限。`-undelete` 反向操作；`-isorphan` 提示还有页面链入；`-always`。 |
| 删除页面前先清掉全站链入 | `unlink` | `unlink "页面名" -namespace:0 -always`，把所有 `[[页面名]]` 变成纯文本。删页前置步骤。 |
| 分类整理 | `category` | jobs 只用了 `remove`。还有 `add`（批量加分类）、`move`（整分类改名迁移）、`tidy`（收进子分类）、`tree`（打印分类树，只读）、`listify`（导出成员列表到文件）、`clean`（去掉冗余的孙分类）。 |
| 模板盘点 | `templatecount` | `-count` 数引用次数 / `-list` 列引用页面，配 `-namespace:0` 过滤。改模板前先摸底。 |
| 页面盘点（只读调查） | `listpages` | 按生成器列页面标题，`-format:3` 输出纯标题，`-save:文件` 存盘。排查问题页第一步。 |
| 图片替换/移除 | `image` | `image 旧图名 新图名` 全站换图；只给一个名字 = 移除。`-loose` 宽松匹配。 |
| 从文本文件批量建页/覆盖页 | `pagefromfile` | UTF-8 文件，`-begin:`/`-end:` 标记页边界，`-notitle` + `-titlestart:`/`-titleend:` 指定标题来源。大批量导入翻译稿时可用。 |
| 回退某用户（或自己）的近期编辑 | `revertbot` | `-username:X`（默认自己）、`-limit:n`、`-rollback` 用 rollback（无 diff 确认）。bot 出事故后的补救手段。 |
| 保护/解除保护 | `protect` | 需管理员。`-unprotect`、`-edit:autoconfirmed` 等。 |
| 死链检查（只读报告） | `weblinkchecker` | 不改页面，死链记到 `deadlinks/` 目录，一周后二次确认才报。适合定期跑。 |
| 交互式消歧义 | `solve_disambiguation` | 人工逐个选目标链接，交互式，不适合无人值守。 |
| 沙盒复位 | `clean_sandbox` | `-text:"..."` 重置沙盒内容，`-hours:x` 周期运行。 |

不适用的（Wikimedia 专属或本 wiki 无对应设施）：`interwikidata`/`claimit`/`newitem`/`illustrate_wikidata`（Wikibase）、`commonscat`/`nowcommons`/`imagetransfer`/`upload`（Commons 向；本 fork 已有 re0_image 做 en→zh 图片同步）、`welcome`/`patrol`/`archivebot`（社区流程类）、`misspelling`（需 wiki 侧拼写模板）、`reflinks`（需按站配置）。

## 页面生成器（pagegenerators）速查

所有带 `&params;` 的脚本都吃这套参数，可叠加（默认并集；加 `-intersect` 取交集）：

| 参数 | 作用 |
|---|---|
| `-page:"标题"` | 单个页面 |
| `-file:路径` | 从文本文件读页面列表（每行一个 `[[标题]]`） |
| `-cat:分类名` / `-catr:` | 分类成员（`-catr` 递归子分类） |
| `-start:!` / `-start:某标题` | 按字母序遍历（jobs 的 `starts.py` 即拼 `-start:ns:!`） |
| `-prefixindex:前缀` | 标题以某前缀开头的所有页（整理 `角色:` 等伪命名空间时最顺手） |
| `-transcludes:模板名` | 引用了某模板的所有页 |
| `-links:页面` / `-ref:页面` | 某页链出的 / 链入某页的所有页 |
| `-search:"关键词"` | MediaWiki 搜索结果 |
| `-newpages:x` / `-recentchanges:x` | 最新 x 个新页面 / 最近改动 |
| `-random:x` / `-randomredirect:x` | 随机页面 / 随机重定向 |
| `-lonelypages:x` / `-unusedfiles:x` / `-uncat` | 孤立页 / 未使用文件 / 未分类页 |
| `-wantedpages:x` 等 | 被引用但不存在的页/分类/文件/模板 |
| `-usercontribs:用户名` | 某用户编辑过的页面 |
| `-withoutinterwiki` | 缺跨语言链接的页 |

过滤器（与生成器叠加）：

- `-ns:0,10` / `-ns:not:2` — 按命名空间过滤
- `-grep:正则` / `-grepnot:正则` — 按正文过滤
- `-titleregex:正则` / `-titleregexnot:` — 按标题过滤
- `-limit:n` — 只取前 n 个
- `-redirect` / `-redirect:no` — 只要/不要重定向
- `-subpage:n` — 只要第 n 层子页面

全局选项：`-simulate`（不写 wiki）、`-always`（免确认）、`-lang:`/`-family:`、`-summary:"..."`（多数脚本支持）。

## 注意

- replace 系脚本（replace/cosmetic_changes/noreferences 等走 textlib 的）都尊重 fork 加的 `<div class="as-is">` 保护标签，不想被 bot 动的内容包进这个 div。
- `run_job` 子进程输出乱码是 `encoding="mbcs"` 的锅，排查先看 AGENTS.md「坑」。
- 写入红线不变：测试只用 `User:IchiSanNi/沙盒`，批量写入需用户明确指示，绝不写 zh 以外语言站。
