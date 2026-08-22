# pywikibot 自带脚本速查

原则：**能直接用 `pwb/pywikibot/scripts/` 里的现成脚本就别手写**。手写只用于现成脚本确实覆盖不了的场景（如 `scripts/re0_*.py` 那几个）。

运行方式（仓库根目录）：

```bash
uv run python pwb/pwb.py <script> [生成器] [脚本选项] [-simulate]
```

- 干跑一律先加 `-simulate`；`-always` 跳过逐页确认（`run_job` 会自动补）。
- 目标站默认就是 `zh:re0`（user-config.py），读别的语言站用 `-lang:en` 等。
- 例外：**transferbot 不接受 `-always`**（加了报错；它本来就会覆盖目标页）。

## jobs 里已在用的

`transferbot` / `interwiki` / `replace -fix:*` / `category remove` / `template` / `fixing_redirects` / `redirect` / `cosmetic_changes` / `noreferences` / `touch`——见 `jobs/jobs.py`，不赘述。

## 未入 jobs 但对常见任务有用的

| 任务 | 脚本 | 说明与示例 |
|---|---|---|
| 批量移动页面（改前缀、整理英文前缀残留页） | `movepages` | `-from:X -to:Y` 单个；`-pairsfile:文件` 批量（每行 `旧名<Tab>新名`，也支持空格分隔）；`-noredirect` 不留重定向；`-notalkpage` / `-nosubpages`；`-prefix:角色` 给生成器选出的整批页加前缀（会先去掉旧前缀）。译名驱动的改名不需要它——re0_move + fix:translation 自动覆盖主命名空间标题与全站正文。 |
| 批量在页首/页尾加文字 | `add_text` | `-text:"..."`（`\n` 表换行）或 `-textfile:路径`；`-up` 加到页首；`-create` 页面不存在则创建；`-createonly` 只建不改。例：给某分类所有页页首补模板：`add_text -cat:某分类 -text:"{{某模板}}" -up -always` |
| 批量删除 / 恢复页面 | `delete` | 已实测可用（bot 账号在 zh 站有删除权限）。例：`delete -cat:单行本漫画 -titleregex:'第3章第.*卷' -summary:'删除以重新搬运'`；`-undelete` 反向操作；`-isorphan` 提示还有页面链入；`-always`。 |
| 删除页面前先清掉全站链入 | `unlink` | `unlink "页面名" -namespace:0 -always`，把所有 `[[页面名]]` 变成纯文本。删页前置步骤。 |
| 分类整理 | `category` | jobs 只用了 `remove`。还有 `add`（批量加分类，目标分类用 `-to:` 指定，不给生成器则默认交互式 `-links`）、`move`（整分类改名迁移）、`tidy`（收进子分类）、`tree`（打印分类树，只读）、`listify`（导出成员列表到文件）、`clean`（去掉冗余的孙分类）。 |
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

## 实战配方（来自实际操作历史，已验证可用）

### 手动译名/文本替换的固定配方

user-fixes.py 收录之前的一次性替换，历史上反复使用的完整形态：

```bash
uv run python pwb/pwb.py replace -automaticsummary \
  -exceptinside:'\[\[:?(zh|de|en|es|fr|it|nl|pl|pt-br|ru|uk|wp|wikipedia)\s?:[^\]]*\]\]' \
  -start::! -start:project:! -start:template:! -start:category:! -start:module:! -start:mediawiki:! \
  '旧文本' '新文本' -always
```

- `-exceptinside:` 的正则跳过跨语言链接内部（`[[en:...]]` 等），避免把外语链接文本替换掉。
- 六个 `-start:ns:!` = `jobs/starts.py` 的 starts_more（主/project/template/category/module/mediawiki 全扫）。`-start::!` 注意是**双冒号**（空 ns 名 = 主空间）。
- 限定范围可用 `-transcludes:模板名` 或 `-page:X`（可多个）替代 `-start` 系列。
- 先 `-page:某页` 单页验证 regex，再放开到全站——历史上删模板参数时 `[^}]*` 会跨行吃多，正确写法是 `[^}\n]*\n?`。
- `-regex` 模式下替换串里 `\1` 引用捕获组；`-nocase` 对中文无意义可省。

### 译名改名三件套（标准顺序）

1. `movepages` 移动页面 + 相关 file: 页面（**一条命令可带多对 `-from`/`-to`**）：
   ```bash
   pwb movepages -from:':角色:旧名' -to:':角色:新名' -from:'file:旧名头像.jpg' -to:'file:新名头像.jpg' -always
   ```
2. `replace` 按上面的固定配方全站替换正文文本。
3. `redirect do` 修双重重定向；之后让 `main.py` 的 translation fix 任务收尾。

### Tab 模板迁移工作流（大规模用过）

1. `template 'X tab' 'Tab/X'` — 全站把旧模板引用换成新 Tab/ 子页模板（**一条命令可带多对**）。
2. `add_text -up -text:'{{Tab/X}}' -links:Template:Tab/X` — 给引用页页首补 Tab 模板。
3. 用 `Category:Temp` 当工作清单：`category add -to:Temp <生成器>` 入队，处理完 `category remove -from:Temp -links:Template:Tab/X` 出队。
4. `touch -purge -transcludes:Module:X` — 改了 Module 后 purge 刷新引用页。

### template 脚本进阶

- 多对一次跑：`template "Re:Zero Ex Manga" "Infobox book" "Re:Zero Daisanshou Manga" "Infobox book" ...`
- 多 `-page:` 限定页面集合（拆季替换 Tab/Anime → Tab/Anime S1/S2/S3 就是这么干的）。
- `-titleregex:'第1章'` 按标题过滤引用页。
- `-subst 模板名` 把模板 subst 展开进页面（用于弃用 Od/Laguna 这类小模板）。
- `-remove` 全站移除模板。

### 试错回退

每次 replace/movepages 出问题，立即 `revertbot -limit:N` 回退自己最近 N 次编辑（N 先小后大），修正命令再跑。历史上这是标准的安全网。

### 其他实测用法

- `imagetransfer -lang:en -page:File:X.png -tolang:zh -keepname` — 单张图片 en→zh。
- `transferbot -lang:en -tolang:zh -start:Manga Arc 5` — `-start` 限定只搬运某字母段；配合先 `delete` 可「删除以重新搬运」。
- `add_text -up -text:"{{To do}}" -start -grepnot:'\{\{To do'` — 给所有缺模板的页补模板（`-grepnot` 过滤已含页）。
- `cosmetic_changes -async -ignore:method -page:'角色:X'` — 单页触发规范化（含修 `User:IchiSanNi/jobs`）。
- `listpages -catr:页面状态 -format:3 > all.txt` — `-format:3` 输出纯标题，重定向到文件做对比（`-format` 必须带编号）。
- `interwiki -quiet -async -auto -force -localonly -start::! ...` — 手敲 interwiki 必须带 `-auto -force`（run_job 会自动补，手敲不会）。
- `login -all` — 一次登录全部 12 个语言站；`login -test` 验证；`pwb.py shell` 交互式调试。

### 已踩过的坑（历史里的失败命令）

- `python pwb/pwb.py main.py ...` 是错的——`main.py` 在仓库根，不是 pwb 脚本，直接 `python main.py`。
- `-always-from:X`（参数粘连）、`imagetrasfer`（拼写）、`revert_bot`（下划线）、`-assubst`（应为 `-subst`）都是真实出现过的笔误，脚本只会报 unknown argument 或 script not found。
- PowerShell 里 `-grep:"require('Module:Tab')"` 会被剥引号剥坏，要整体加引号并转义：`"-grep:require\('Module:Tab'\)"`。git-bash 里用单引号即可。
- `category remove -from:Sandbox` 会把名为 Sandbox 的**分类**清空，操作前 `-simulate` 确认范围，必要时 `-nodelete`。

## 注意

- replace 系脚本（replace/cosmetic_changes/noreferences 等走 textlib 的）都尊重 fork 加的 `as-is` 注释对保护（`<!--as-is-->…<!--/as-is-->`），不想被 bot 动的内容包进这对注释（行内内容整词包裹即可）。
- `run_job` 子进程输出乱码的排查看 AGENTS.md「坑」节（PYTHONIOENCODING 条目）。
- 写入红线不变：测试只用 `User:IchiSanNi/沙盒`，批量写入需用户明确指示，绝不写 zh 以外语言站。
