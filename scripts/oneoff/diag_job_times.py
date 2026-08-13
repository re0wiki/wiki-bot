# 一次性统计：从 commands.log 计算各任务耗时与占比
import re
from datetime import datetime
from pathlib import Path

lines = Path("logs/commands.log").read_text(encoding="utf-8", errors="replace").splitlines()
pat = re.compile(r"^(2026-08-13 \d\d:\d\d:\d\d) .*?Python \S+ (\S+)")
events = []
for line in lines:
    m = pat.match(line)
    if m:
        events.append((datetime.fromisoformat(m.group(1)), m.group(2)))

# 第 1 轮完整循环：09:03 首次 transferbot 起，到 11:53 第 2 轮 transferbot 止
start = next(i for i, (t, c) in enumerate(events) if c == "transferbot")
end = next(i for i, (t, c) in enumerate(events) if i > start and c == "transferbot" and t.hour == 11)
cycle = events[start:end]
cycle_end = events[end][0]

rows = []
for (t0, c0), (t1, _) in zip(cycle, cycle[1:]):
    rows.append((c0, (t1 - t0).total_seconds()))
rows.append((cycle[-1][1], (cycle_end - cycle[-1][0]).total_seconds()))

total = sum(d for _, d in rows)
print(f"第 1 轮总时长 {total/60:.1f} 分钟\n")
for name, dur in sorted(rows, key=lambda r: -r[1]):
    print(f"{name:20s} {dur/60:6.1f} min  {dur/total*100:5.1f}%")

rest = total - dict(rows)["fixing_redirects"]
print(f"\n== 换装 fixing 后预估单轮 {rest/60:.1f} 分钟，剩余任务占比 ==")
for name, dur in sorted(rows, key=lambda r: -r[1]):
    if name != "fixing_redirects" and dur >= 60:
        print(f"{name:20s} {dur/60:6.1f} min  {dur/rest*100:5.1f}%")
