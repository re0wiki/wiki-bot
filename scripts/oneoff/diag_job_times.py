# 一次性统计：从 commands.log 计算最近一轮完整循环的各任务耗时与占比
import re
from datetime import datetime
from itertools import pairwise
from pathlib import Path

lines = (
    Path("logs/commands.log").read_text(encoding="utf-8", errors="replace").splitlines()
)
pat = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) .*?Python \S+ (\S+)")
events = []
for line in lines:
    m = pat.match(line)
    if m:
        events.append((datetime.fromisoformat(m.group(1)), m.group(2)))

# 循环边界 = 最后一次「re0_transferbot 紧接 re0_gallery」（真循环起点，排除干跑），
# 止于 touch-bot.log 最后写入
start_idx = max(
    i
    for i in range(len(events) - 1)
    if events[i][1] == "re0_transferbot" and events[i + 1][1] == "re0_gallery"
)
cycle = events[start_idx:]
cycle_end = datetime.fromtimestamp(Path("logs/touch-bot.log").stat().st_mtime)  # noqa: DTZ006 本地时间，与日志 naive 时间戳一致

rows = [(c0, (t1 - t0).total_seconds()) for (t0, c0), (t1, _) in pairwise(cycle)]
rows.append((cycle[-1][1], (cycle_end - cycle[-1][0]).total_seconds()))

# 同名任务（replace/category/template/redirect 多次出现）按 jobs.py 顺序归并展示
total = sum(d for _, d in rows)
print(f"最近一轮：{cycle[0][0]} → {cycle_end}，总时长 {total / 60:.1f} 分钟\n")
agg = {}
order = []
for name, dur in rows:
    if name not in agg:
        order.append(name)
    agg[name] = agg.get(name, 0) + dur
for name in sorted(agg, key=lambda n: -agg[n]):
    print(f"{name:20s} {agg[name] / 60:6.1f} min  {agg[name] / total * 100:5.1f}%")
