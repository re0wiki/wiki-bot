"""同步 User:IchiSanNi/jobs 状态页的 template 任务命令行（与 jobs/jobs.py 对齐）。"""

import sys
from pathlib import Path

import pywikibot

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from jobs.jobs import jobs

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

# 找到 template 替换任务（非 -remove）
task = next(j for j in jobs if j[0] == "template" and "-remove" not in j)
cmd = "python pywikibot/pwb.py " + " ".join(f'"{a}"' for a in task)

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
