# 全项目 Review 待办清单

2026-07-31 全项目 review 的产出，按优先级排列。每条附定位与建议修法；完成一条删一条。

已完成：run_job 改用 `sys.executable`（并补 `build_cmd` 单测）；re0_image 补 `handle_args` + simulate 守卫，`-s` 干跑不再真实上传；run_job 不再吞 `CalledProcessError`，任务失败 main.py 以相同码退出等人工修复（231 循环故障期空转问题随之解决）。

## 🟡 仓库一致性

### 1. AGENTS.md 引用了不在仓库里的文件

- `logs/` 整体被 gitignore（`.gitignore:295`），但 AGENTS.md 架构地图与「伪命名空间」节引用了 `logs/delete_traditional_prefix_redirects.py`、`logs/scan_title_prefixes.py`——fresh clone 里是指针悬空。
- 修法：两个可复用审计脚本移入 `scripts/` 并提交，或在引用处注明「本地一次性脚本」。

### 2. scripts/ 一次性脚本与常驻脚本混放

- AGENTS.md 说「5 个自定义脚本」，实际 `scripts/` 有 ~40 个文件，其中约 35 个是已完成的一次性脚本（`delete_*`、`fix_*`、`deploy_*`、`probe_*` 等）。
- 修法：移入 `scripts/oneoff/` 或按日期归档。注意 `probe_*` 系列被 `docs/cloudflare-429.md` 引用，移动时同步更新引用。

### 3. 状态页同步脚本名不副实

- 位置：`scripts/sync_jobs_status_page.py:22`
- 问题：AGENTS.md 称 wiki 上 `User:IchiSanNi/jobs` 与 `jobs/jobs.py`「一一对应」，但该脚本只靠行首字符串硬匹配同步 template 替换任务一行，其余全手工。
- 修法：扩成全量生成，或把文档表述降级为「手工维护，脚本只同步 template 行」。

## 🟢 低优先级

### 4. 没有 CI

- `.github/` 只有 issue 模板与 renovate/restyled；ruff + ty + pytest 全靠本地手动。
- 修法：加一个 uv 的 GitHub Actions workflow（`uv sync` → `ruff check` → `ty check` → `pytest tests/`）。

### 5. run_job 去掉 `shell=True`

- 位置：`jobs/run_job.py`
- list 参数在 Windows 上不需要 shell，去掉可消除 list2cmdline 引号 mangling 隐患；`encoding="mbcs"` 乱码坑可顺带评估换 `utf-8` + `errors="replace"`。

### 6. 杂项小点

- `user-fixes.py:81`：参数名 `mouth` 是 `month` 笔误。
- `re0_gallery.py` 手写嵌套模板正则可考虑换依赖里已有的 `mwparserfromhell`（「能跑就别动」也成立）。
