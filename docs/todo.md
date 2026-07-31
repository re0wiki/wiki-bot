# 待办与待决策项

跨任务的待办清单。单个领域（模板/Module）的待办仍各归 `templates.md` / `modules.md`。

## 已决策（2026-07-31）

### 图片删除/改名不同步（re0_image 只增不删）——维持现状

残留图片基本无害；删除还要同步更新引用，不值得处理。限制已注明在 `calc_diff` docstring。

### `.idea/` 已跟踪文件——维持现状

自带 .gitignore 模板没忽略那些文件所以提交了；项目无其他维护者，交上去至少无害。

### re0_redirect 对未登记前缀建重定向——维持现状

多余重定向无用但无害（`特典:`、英文残留前缀的裸词干重定向由 `redirect br -delete` 自愈）。

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
