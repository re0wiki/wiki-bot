# pywikibot submodule 更新流程

把 fork（`re0wiki/pywikibot` 的 `main`）rebase 到 upstream 最新版的完整流程。定制提交清单见 AGENTS.md「pywikibot fork 的定制」节。

## 步骤

```bash
cd pywikibot
git fetch upstream
git branch backup/pre-rebase-$(git rev-parse --short main) main   # 安全网
git rebase upstream/master main
```

- 冲突通常很少：第一个提交（`import re` → `import regex as re`，触及全库）最容易撞，一般是上游在 import 块附近加了行——保留上游新增行、同时把 `import re` 换成 `import regex as re` 即可。其余定制提交碰的文件上游很少动（transferbot 常年为 0 冲突）。
- `GIT_EDITOR=true git rebase --continue` 避免弹编辑器。

## 验证（比冲突解决更重要）

```bash
# 1. range-diff：每个旧定制提交都应一一对应新提交；
#    标记 ! 的一般只是上下文漂移（上游改了邻近行），确认 + 行内容没变即可
git range-diff <old-base>..backup/pre-rebase-xxx upstream/master..main

# 2. 定制点抽查（详见 AGENTS.md 定制清单）
grep -rn '^import re$' pywikibot/ scripts/   # 应为空
grep '"keep"' pywikibot/fixes.py              # 4 处（HTML/syntax/isbn/specialpages）
grep 'as-is' pywikibot/textlib.py
grep 'format=original' pywikibot/page/_filepage.py
grep 'csrf' pywikibot/site/_tokenwallet.py
grep '注释与外部链接' scripts/noreferences.py
grep '新搬运待整理' scripts/transferbot.py
```

主仓验证：

```bash
uv sync                                                          # editable 重装
PYTHONPATH= .venv/Scripts/python.exe scripts/verify_wiki_access.py   # 期望 ALL CHECKS PASSED
```

注意：不要在仓库根目录用 `python -c "import pywikibot"` 做冒烟测试——cwd 里的 `pywikibot/` 目录会被当作命名空间包 shadow 掉已安装的包（报 `module 'pywikibot' has no attribute '__version__'`）。换目录跑并设 `PYWIKIBOT_NO_USER_CONFIG=1`，或直接用仓库里的脚本。

## 收尾

```bash
git -C pywikibot push --force-with-lease origin main   # rebase 必改写历史
# 主仓：uv.lock 里 pywikibot 版本号也会变，一起提交
git add pywikibot uv.lock
git commit -m "chore: update pywikibot"
```

确认线上正常后再删 backup 分支：`git -C pywikibot branch -D backup/pre-rebase-xxx`。
