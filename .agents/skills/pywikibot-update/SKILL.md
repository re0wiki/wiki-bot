---
name: pywikibot-update
description: "Use when 更新 pwb submodule 或 rebase 上游 pywikibot。含 fork 定制补丁清单（唯一权威）。"
version: 1.0.0
---

# pywikibot submodule 更新流程

把 fork（`re0wiki/pywikibot` 的 `main`）rebase 到 upstream 最新版的完整流程。本 skill 同时是 **fork 定制提交清单的唯一权威**——rebase 时必须逐条保留。

**fork 历史可任意重写（force push 常态化）**：只保留上游 → 定制终态的最短路径。补丁的演进中间态（加了又改、又删）一律重写抹平，不留在历史里；补丁「是什么、为什么」以本清单的当前描述为准。

## 定制提交清单（rebase 上游时必须保留）

每个定制一个独立提交：

- 全库 `import re` → `import regex as re`（80 文件机械替换，setup.py 除外）+ requirements.txt 加 regex：译名合并 alternation（1000+ 分支）靠 regex 的 trie 优化（stdlib re 逐位置顺序试探，167KB 页 8.9s → 0.03s）。regex 默认 VERSION0 与 re 行为对齐。
- `replace.py`：`generate_summary` 支持 callable 替换的 `take_summary_pairs()` 协议——回读本页实际命中的（原文， 目标）对并清空；合并 alternation 的编辑摘要打印真实转换（-菲爾歐蕾 +菲尔欧蕾）而非整条 pattern。
- `textlib.py`：`replaceExcept` 加快速路径（marker 为空且不 allowoverlap 时）：异常区间预计算一次（合并排序），编辑后区间随 delta 平移，替代原版「每个候选匹配 × 每个异常正则」的全文重扫——保护行密集的页面（NekoQuote 月表，200KB）上 10x+ 加速。行为锚点测试在主仓 `tests/test_fork_replaceexcept.py`。
- `textlib.py` + `fixes.py`：新增 `keep` 标签 = `<!--as-is-->...<!--/as-is-->` 注释对，textlib 加 regex，HTML/syntax/isbn/specialpages fixes 的 exceptions 里加 `keep` —— wiki 上可以用这对注释保护内容不被 bot 改。注释零渲染、可行内使用，行内内容整词包裹即可（如 `<!--as-is-->精灵<!--/as-is-->`）。标记不配平时该区域失去保护（静默失效，扫描时可查配平）。
- `fixes.py`：HTML fix 把 `<br>` 归一到不闭合形式（MediaWiki 渲染等价，不闭合是本 wiki 惯例）。
- `fixes.py`：syntax fix 注释掉外链竖线规则（误报太多）。
- `textlib.py`：`replaceLanguageLinks` 的 CategorySelect 分支加守卫，模板页（含子页）改走 noinclude 感知分支——否则 `getCategoryLinks` 不识别 `<noinclude>` 包裹，会把分类从 noinclude 里拽出来放到页尾（Fandom 有 CategorySelect 扩展，cosmetic_changes 的 standardizePageFooter 必踩）。
- `_filepage.py`：下载 URL 加 `&format=original`，否则 Fandom API 返回 webp。同时必须去掉上游的 suffix 调整：它从 URL 路径取扩展名，而 Fandom URL 以 `/revision/latest` 结尾（无扩展名），留着会把下载文件的真扩展名剥掉（Wikimedia 的 URL 路径以文件名结尾，所以上游留着没事）。
- `noreferences.py`：zh 参考资料段标题首选「注释」；预载带 `pageprops`——`skip_page` 对每页调 `isDisambig()`（`use_disambigs=False`）读 `prop=pageprops`，默认预载不含它导致每页一次查询（全扫 ~18 min），带上后随内容同批缓存（~25 s）。背景：本站按对齐 en 的策略不加 `__DISAMBIG__`（en 不加，zh 单加会破坏 interwiki；用户尝试给 en 加被回退），该检查恒为空——故选零成本的语义保留方案而非改 `use_disambigs=None` 的假设性跳过。
- `scripts/listpages.py`：`-notitle`（含 `-format:` 空值）抑制标题后 `treat()` 不再 pop 空 `output_list`——上游 bug：非 preloading 且无 `-tofile` 时逐页 `pop()`，首页即 IndexError 崩溃。
- `pagegenerators/_factory.py`：恢复多个 `-start` 的并集语义。上游 fa0c6f6c7（T425882，11.3 引入 `-until`）把 `-start` 改为惰性合并进单个 `_allpages_args`，导致多个 `-start` 只有第一个命名空间生效（jobs 的 `starts.py` 全依赖多 `-start`）。补丁在再遇 `-start` 时把挂起的参数实例化为独立 allpages 生成器，`-start`+`-until` 配对行为不变。
- `site/_decorators.py`：`need_right` 权限检查失败且当前为匿名会话（`user() is None`）但配置了账号时，先 `_relogin()` 重登一次再复查，复查仍失败才抛 `UserRightsError`。覆盖「进程启动后首次取 userinfo 时会话已被服务端作废」的盲区——该场景下缓存里从未有过登录态，`api._requests` 的 userinfo 不符自愈（要求 `user() is not None`）不会触发，会直接以 `User "None"` 抛错退出。重登失败则 `NoUsernameError` 照常传播（响亮失败）。

## 步骤

```bash
cd pwb
git fetch upstream
git branch backup/pre-rebase-$(git rev-parse --short main) main   # 安全网
git rebase upstream/master main
```

- 冲突通常很少：定制集中在上游很少改动的区域。定制涉及的文件以上方清单为准；若清单里的文件在上游侧有新提交，rebase 时重点核对该定制是否仍成立（语义冲突不一定产生文本冲突）。
- `GIT_EDITOR=true git rebase --continue` 避免弹编辑器。
- 嵌套 submodule `scripts/i18n` 的 gitlink 随上游升级：gerrit 直连可能 403，走 GitHub 镜像同步——`git -C scripts/i18n fetch https://github.com/wikimedia/pywikibot-i18n.git master && git -C scripts/i18n checkout <目标 commit>`（目标 commit 用 `git ls-tree upstream/master scripts/i18n` 查；镜像 HEAD 通常就是它）。

## 验证（比冲突解决更重要）

```bash
# 1. range-diff：每个旧定制提交都应一一对应新提交；
#    标记 ! 的一般只是上下文漂移（上游改了邻近行），确认 + 行内容没变即可
git range-diff <old-base>..backup/pre-rebase-xxx upstream/master..main

# 2. 提交级与文件级核对：定制提交数、触及文件应与上方清单一一对应
git log upstream/master..main --oneline
git diff upstream/master...main --stat

# 3. regex 替换不变量：全库 `^import re$` 应只剩 setup.py；
#    上游新增/改动的文件若引入新的 `^import re$`，一并换掉并折进 regex 提交
grep -rln '^import re$' --include='*.py' . | grep -v scripts/i18n
```

再按上方清单逐条抽查定制点仍在（每条定制都写了标志代码，如 keep 标签、`format=original` 等，grep 即可）。

主仓验证：

```bash
uv sync                                                          # editable 重装
uv run python src/tools/verify_wiki_access.py   # 期望 ALL CHECKS PASSED
```

import 冒烟时留意新版本弃用的配置变量警告（如 11.8 起 `maxlag`→`write_maxlag`），同步改主仓 `user-config.py` 并一起提交。冒烟测试可直接在仓库根跑 `uv run python -c "import pywikibot"`；设 `PYWIKIBOT_NO_USER_CONFIG=1` 可跳过配置加载。

## 变更总结

更新完成后向用户总结上游主要变更：

- 版本亮点：ROADMAP.rst 只保留当前版本，历史版本亮点从发布提交处取——`git log <old-base>..upstream/master --grep='publish Pywikibot'` 找提交，`git -C pwb show <commit>:ROADMAP.rst` 读 Release 小节。
- 提交主题聚类：`git -C pwb log <old-base>..upstream/master --format='%s'`，按 area 前缀分桶归纳主题。
- 明确标注对本仓库有适配义务的项（配置弃用、API 改名、fork 补丁被上游覆盖等）。

## 收尾

```bash
# 主仓提交（uv.lock 里 pywikibot 版本号随 submodule 一起变）：
git add pwb uv.lock
git commit -m "chore: update pywikibot"
```

push 及之后均由用户手动执行，agent 不执行：

```bash
git -C pwb push --force-with-lease origin main   # rebase 必改写历史
git push
# 确认线上正常后删 backup 分支：
git -C pwb branch -D backup/pre-rebase-xxx
```
