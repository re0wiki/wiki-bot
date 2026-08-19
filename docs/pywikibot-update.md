# pywikibot submodule 更新流程

把 fork（`re0wiki/pywikibot` 的 `main`）rebase 到 upstream 最新版的完整流程。定制提交清单见 AGENTS.md「pywikibot fork 的定制」节。

## 步骤

```bash
cd pwb
git fetch upstream
git branch backup/pre-rebase-$(git rev-parse --short main) main   # 安全网
git rebase upstream/master main
```

- 冲突通常很少：定制只碰 4 个文件（fixes.py / textlib.py / _filepage.py / noreferences.py），上游很少动这些区域。
- `GIT_EDITOR=true git rebase --continue` 避免弹编辑器。

## 验证（比冲突解决更重要）

```bash
# 1. range-diff：每个旧定制提交都应一一对应新提交；
#    标记 ! 的一般只是上下文漂移（上游改了邻近行），确认 + 行内容没变即可
git range-diff <old-base>..backup/pre-rebase-xxx upstream/master..main

# 2. 定制点抽查（详见 AGENTS.md 定制清单）
git diff upstream/master main --stat   # 应只碰 fixes/textlib/_filepage/noreferences 4 个文件
grep '"keep"' pwb/pywikibot/fixes.py              # 4 处（HTML/syntax/isbn/specialpages）
grep 'as-is' pwb/pywikibot/textlib.py
grep 'format=original' pwb/pywikibot/page/_filepage.py
grep '注释与外部链接' scripts/noreferences.py
grep 'pageprops=True' scripts/noreferences.py
```

主仓验证：

```bash
uv sync                                                          # editable 重装
PYTHONPATH= .venv/Scripts/python.exe scripts/tools/verify_wiki_access.py   # 期望 ALL CHECKS PASSED
```

冒烟测试可直接在仓库根跑 `python -c "import pywikibot"`；设 `PYWIKIBOT_NO_USER_CONFIG=1` 可跳过配置加载。

## 收尾

```bash
git -C pwb push --force-with-lease origin main   # rebase 必改写历史
# 主仓：uv.lock 里 pywikibot 版本号也会变，一起提交
git add pwb uv.lock
git commit -m "chore: update pywikibot"
```

确认线上正常后再删 backup 分支：`git -C pwb branch -D backup/pre-rebase-xxx`。
