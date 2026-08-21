# pywikibot submodule 更新流程

把 fork（`re0wiki/pywikibot` 的 `main`）rebase 到 upstream 最新版的完整流程。**定制提交清单的唯一权威是 AGENTS.md「pywikibot fork 的定制」节**——本文不重复列举文件名与抽查命令（曾经列举过，漂移后比 AGENTS.md 落后数个补丁才被发觉）。

## 步骤

```bash
cd pwb
git fetch upstream
git branch backup/pre-rebase-$(git rev-parse --short main) main   # 安全网
git rebase upstream/master main
```

- 冲突通常很少：定制集中在上游很少改动的区域。定制涉及的文件以 AGENTS.md 清单为准；若清单里的文件在上游侧有新提交，rebase 时重点核对该定制是否仍成立（语义冲突不一定产生文本冲突）。
- `GIT_EDITOR=true git rebase --continue` 避免弹编辑器。

## 验证（比冲突解决更重要）

```bash
# 1. range-diff：每个旧定制提交都应一一对应新提交；
#    标记 ! 的一般只是上下文漂移（上游改了邻近行），确认 + 行内容没变即可
git range-diff <old-base>..backup/pre-rebase-xxx upstream/master..main

# 2. 提交级与文件级核对：定制提交数、触及文件应与 AGENTS.md 清单一一对应
git log upstream/master..main --oneline
git diff upstream/master...main --stat
```

再按 AGENTS.md 清单逐条抽查定制点仍在（每条定制都写了标志代码，如 keep 标签、`format=original` 等，grep 即可）。

主仓验证：

```bash
uv sync                                                          # editable 重装
uv run python scripts/tools/verify_wiki_access.py   # 期望 ALL CHECKS PASSED
```

冒烟测试可直接在仓库根跑 `uv run python -c "import pywikibot"`；设 `PYWIKIBOT_NO_USER_CONFIG=1` 可跳过配置加载。

## 收尾

```bash
git -C pwb push --force-with-lease origin main   # rebase 必改写历史
# 主仓：uv.lock 里 pywikibot 版本号也会变，一起提交
git add pwb uv.lock
git commit -m "chore: update pywikibot"
```

确认线上正常后再删 backup 分支：`git -C pwb branch -D backup/pre-rebase-xxx`。
