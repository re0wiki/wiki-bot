"""同步 User:IchiSanNi/jobs 状态页的 template 任务命令行（与 jobs/jobs.py 对齐）。"""

import sys
from pathlib import Path

# 顺序要求：必须先 import pywikibot 再把仓库根挂上 sys.path。仓库根的
# pywikibot/ 目录（submodule）可能以 namespace package 遮蔽已安装的包
# （见 tests/conftest.py 与 AGENTS.md 的坑节）；已入 sys.modules 则无虞。
import pywikibot

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from jobs.jobs import jobs

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

task = next(j for j in jobs if j.name == "template")
cmd = "python pywikibot/pwb.py " + " ".join(f'"{a}"' for a in task.cmd)

p = pywikibot.Page(site, "User:IchiSanNi/jobs")
lines = p.text.splitlines()
for i, line in enumerate(lines):
    if line.startswith('python pywikibot/pwb.py "template" "Character"'):
        old = line
        lines[i] = cmd
        break
else:
    raise SystemExit("未找到 template 替换任务行")

p.text = "\n".join(lines)
p.save(summary="状态页同步：template 替换任务参数与 jobs/jobs.py 对齐", bot=True)
print("已更新，旧行长度", len(old), "-> 新行长度", len(cmd))
