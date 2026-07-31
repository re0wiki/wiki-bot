# 待办与待决策项

跨任务的待办清单。单个领域（模板/Module）的待办仍各归 `templates.md` / `modules.md`。

## 待用户决策

### 1. 图片删除/改名是否同步（re0_image）

`scripts/re0_image.py` 的 `calc_diff` 只增不删：en 侧删除或改名的图片会在 zh 侧永久残留孤儿图。
当前是保守策略（误删比残留难恢复）。可选方案：

- 维持现状（docstring 已注明限制）
- 加「en 已不存在 → zh 侧删除」任务（需排除 zh 本地自产图：哪些图是 zh 独有的？）
- 只报告不删除（定期清单，人工清理）

### 2. `.idea/` 已跟踪文件是否清理

`.idea/` 下的 `.iml`、`misc.xml`、`modules.xml` 等提交在仓库里（gitignore 模板只排除了 workspace.xml 等）。
若无意共享 IDE 配置，可整体 gitignore + `git rm -r --cached .idea`；若有意共享（PyCharm 打开即用），维持现状。

### 3. re0_redirect 对未登记前缀建重定向是否符合预期

`scripts/re0_redirect.py` 给**所有**含冒号的主空间标题建裸词干重定向，包括：

- 未登记前缀（如 `特典:劇場前惡意` → 建 `劇場前惡意`）
- 英文搬运残留前缀（如 `Sword Demon Love Story: ...`、`Re: ...` → 建裸词干）

后者在残留页整理/移动后会留下指向旧位置的裸词干重定向（由 `redirect br -delete` 任务自愈）。
需确认：这是期望行为，还是应限定只为登记前缀（`user-fixes.py` 的 `PSEUDO_PREFIXES`）建重定向？

## 已评估、决定不做

### probe_* 五个探测脚本不合并且保留样板重复

`docs/cloudflare-429.md` 按文件名逐一引用这些脚本作为实证出处（哪个脚本跑出哪组数据），
合并会破坏可追溯性；它们是一次性研究脚本而非维护中的工具，重复的样板没有维护成本。

## 已完成（2026-07-31，代码评审整改）

- main.py 任务支持稳定名字（`python main.py fix:translation -s`），编号仍可用来兼容肌肉记忆
- jobs.py 模板替换扁平参数结构化成 (旧, 新) 元组
- re0_image：`-s` 干跑跳过下载，只报告差量
- 伪命名空间前缀提为唯一权威常量 `user-fixes.py:PSEUDO_PREFIXES`，scan_title_prefixes 复用
- namespace 列表两处事实源（jobs/starts.py ↔ user-fixes.py）加交叉注释
- sync_jobs_status_page：sys.path 顺序要求入注释
- re0_gallery 抽纯函数 `merge_galleries` + tests/test_gallery.py 离线回归
- re0_move 抽纯函数 `resolve_move` + tests/test_move.py；test_translation 共享 RULES
- 删除空目录 data/
