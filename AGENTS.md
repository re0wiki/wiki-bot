# AGENTS.md — wiki-bot

Re:Zero Fandom Wiki（<https://rezero.fandom.com/zh>）的维护机器人，基于 Pywikibot。
主要工作：把英文站内容同步到中文站，并对中文站做译名/格式规范化。

## 环境

- **Python 3.14**（`.python-version`，`pyproject.toml` 要求 `>=3.14`），uv 管理，有 `uv.lock`。
- 安装：`uv sync`（`default-groups = "all"`，会把 dev + pwb 组全装上）。
- 运行脚本：`PYTHONPATH= .venv/Scripts/python.exe <script>`（Windows 上 Hermes 会注入指向自身 venv 的 PYTHONPATH，必须清空，否则 import 错包）。
- **pywikibot 是 git submodule**（fork：`github.com/re0wiki/pywikibot`，upstream 是 wikimedia/pywikibot）。克隆要 `--recurse-submodules`。更新 submodule 后提交信息写 `chore: update pywikibot`。
- Lint：`ruff check` / `ruff format`（`pyproject.toml` 里 extend-exclude 了 pywikibot 子模块，不要给它 lint）。类型检查用 `ty`。
- 没有测试套件。验证方式 = `-s/--simulate` 干跑 + 上 wiki 查编辑结果。
- Secrets：`user-password.py`（BotPasswords，gitignored，勿读勿提交）。`logs/`、`apicache/`、`throttle.ctrl` 是运行时产物，别动。

## 架构地图

| 文件 | 作用 |
|---|---|
| `main.py` | 循环任务入口。`python main.py <index>` 跑单个任务，`-s` 模拟；`231` = 无限循环所有任务 |
| `jobs/jobs.py` | 任务列表（每条是一个 pwb.py 参数列表），分 6 组：跨站同步 → 整理新搬运页 → 模板维护 → 重定向 → 语法规范化 → 内容规范化 → 杂项 |
| `jobs/run_job.py` | 子进程包装：拼 `python pywikibot/pwb.py ...`，自动加 `-always`（interwiki 加 `-auto -force`，transferbot 不加） |
| `jobs/starts.py` | namespace → `-start:ns:!` 生成器参数。`ns_base`=主/project/template/category，`ns_more` 再加 module/mediawiki |
| `user-config.py` | pywikibot 配置：family=re0, mylang=zh, 账号 IchiSanNi（12 个语言站同账号） |
| `user-fixes.py` | **核心资产**。自定义 fix 集：misc/date/anti-ve/para/gallery/heading/**translation**/HTML/syntax 等。`translation` 用「相似字符 → 正则」机制（`f()`/`p2o()`/`p2n()`）把几百个别名归一到标准译名 |
| `scripts/re0_*.py` | 4 个自定义脚本：gallery（用 en 站图库覆盖 zh）、image（图片差量同步）、nav（编译 Wiki-navigation）、redirect（给 `前缀:词干` 页建裸词干重定向） |
| `families/re0_family.py` | re0 family 定义，12 个语言子站（de/en/es/fr/it/ko/nl/pl/pt-br/ru/uk/zh 都在 rezero.fandom.com，en 无路径前缀其余 `/<code>`）。注意 family 文件注释说 "do not commit" 但本项目故意提交了 |
| `rename.py` | 交互式改名工具：移动页面 + 全站替换文本（只打印命令不执行） |
| `pywikibot/` | submodule，含 re0wiki 定制补丁（见下） |

## wiki 侧结构（zh 站）

- **伪命名空间**：没有注册自定义 namespace，文章页靠标题前缀分类（全在主空间）：`角色:`、`术语:`、`小说:`、`漫画:`、`动画:`、`游戏:`、`音乐:`、`设定集、画集:`、`声优:`、`制作人员:`、`存档:`。偶见繁体 `小說:` 残留；英文前缀页（`Re:`、`Sword Demon Love Story:` 等）是待整理的搬运残留。改前缀 = 移动页面，走 bot 而非手动。
- **页首模板**：`{{Init}}`（`{{#invoke:Init|main}}`，Tab 系统初始化，几乎每篇文章都有）+ `{{To do}}`（归入 `Category:待修撰`，大部分文章常态携带，不是积压事故）。新搬运页另有 `[[Category:新搬运待整理]]`（见 fork 定制节），人工整理后摘除——该分类是真实待办队列。
- **模板体系**：`Tab/*` 子页族（每部作品一套页面顶部标签，配 `{{Tab}}` 使用）；`Infobox character/book/novel/episode/location/item/quest/event/album/battle` 等信息框；注音族 `Ruby-zh-ja`（中日双语 ruby）/`R`/`Ruby-zh-b/zh-p/ja`；`QUOTE`（页首引语 + voice 音频）。
- **导航**：`MediaWiki:Wiki-navigation` 由 `Project:Wiki-navigation` 经 `scripts/re0_nav.py` 编译生成，勿手动编辑。
- **状态页**：wiki 上 `User:IchiSanNi/jobs` 与 `jobs/jobs.py` 的任务一一对应。
- 译名表与译名工作流见下节；`<div class="as-is">` 保护机制见 fork 定制节。

## pywikibot fork 的定制（rebase 上游时必须保留）

提交 `dc44b42b9 chore: apply re0wiki customizations` + `f053e27e8`（`import re` → `import regex as re`）：

- `textlib.py`：新增 `keep` 标签 = `<div class="as-is">...</div>`，fixes 的 exceptions 里普遍加了 `keep` —— wiki 上可以用这个 div 保护内容不被 bot 改。
- `transferbot.py`：搬运时不写编辑历史子页，改为在页首加 `{{Init}}{{To do}}` + 来源链接 + `[[Category:新搬运待整理]]`（namespace 8/828 除外）。
- `_filepage.py`：下载 URL 加 `&format=original`，否则 Fandom API 返回 webp。
- `_tokenwallet.py`：先取 csrf token（绕过 Fandom bug：一起取时只有部分 token 能拿到且不触发 pywikibot 重试；先取 csrf 会失败一次但触发自动重试，第二次成功。丑陋但可用）。
- `fixes.py`：HTML fix 允许 `<br>` 不闭合、syntax fix 去掉了误报多的外链竖线规则、几个 fix 补了 generator。
- `redirect.py`：moved-pages offset 允许 0。

## 译名维护工作流（最常见的改动）

1. 译名表的给人看版本在 wiki 上（`ReZero Wiki:译名表`，含选取规则：官方简中 > 官方繁中 > 民间 > 保留英文）；bot 实际执行的唯一权威是 `user-fixes.py`，两边手动同步。用户通过 GitHub Issues 报译名问题（模板：新增/修改译名、遗漏替换、错误替换），wiki 页面明确告诉用户「不要手动移动页面或替换文本，提议通过后 Bot 会批量修改」。
2. 改译名 = 改 `user-fixes.py` 里 `translation` fix 的两个列表：主列表（`p2o()` 自动生成别名正则）+ 手动替换组。拿不准相似字符覆盖面的，先 `python main.py <translation对应index> -s` 干跑。
3. 提交信息遵循 Conventional Commits：`feat(translation): add X` / `fix(translation): 旧 -> 新`。
4. `_ = [...]` 列表是「特判太麻烦、明确不处理」的别名，别删。

## 坑

- `run_job` 用 `shell=True` + `encoding="mbcs"`（Windows GBK 控制台），子进程输出乱码先怀疑这里。
- `jobs/jobs.py` 的 interwiki 任务不带 `-auto`（由 run_job 补），直接手敲 pwb.py 跑要记得加。
- transferbot **不接受 `-always`**（加了会报错）；它不加也会自动覆盖目标页。
- `touch -random:128` 在任务列表末尾，是为了触发缓存刷新，不是无意义操作。
- 常驻方式：本机跑 `python main.py 231`（无限循环所有任务）。
- 在线状态页：wiki 上 `User:IchiSanNi/jobs`。
