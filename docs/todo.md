# 全项目 Review 待办清单

2026-07-31 全项目 review 的产出，按优先级排列。每条附定位与建议修法；完成一条删一条。

已完成：run_job 改用 `sys.executable`（并补 `build_cmd` 单测）；re0_image 补 `handle_args` + simulate 守卫，`-s` 干跑不再真实上传；run_job 不再吞 `CalledProcessError`，任务失败 main.py 以相同码退出等人工修复（231 循环故障期空转问题随之解决）；`scan_title_prefixes.py` 收编进 `scripts/`、一次性脚本归档 `scripts/oneoff/`、状态页表述降级为名实相符、usernames 折叠为通配 `"*"`；GitHub Actions CI（ruff + format + ty + pytest）；run_job 去除 `shell=True`（考古确认它是裸 python 时代的解释器解析 workaround，`sys.executable` 后动机已消；`encoding="mbcs"` 查实必须保留，GBK 字节流换 utf-8 反而解坏）。

## 🟢 低优先级

### 1. 杂项小点

- `user-fixes.py:81`：参数名 `mouth` 是 `month` 笔误。
- `re0_gallery.py` 手写嵌套模板正则可考虑换依赖里已有的 `mwparserfromhell`（「能跑就别动」也成立）。
