"""生成实况标记映射 ep_marks.json（tid → 标记）。
规则（用户裁决）：以长月自己的 #rezeroneko 为准，不增不减。
- 首播窗口：en 日历播出日 12:00 JST +42h，带 tag → S3第N集/S4第N集
- 再放送窗口：2024-11-27/12-04→51（再编集前后编），12-11→52、12-18→53、12-25→54、
  2025-01-08→55、01-15→56、01-22→57、01-29→58（他自报的再放送进度），带 tag 同上
- 2025-03-09 带 tag 4 条（明写「アニメ63話」）→ S3第63集
- 2025-04-02 愚人节延長戦：无归属集数，不标（用户裁决）
"""

import json
from datetime import datetime, timedelta, timezone

from . import DATA

JST = timezone(timedelta(hours=9))
EPOCH = 1288834974657

cal_path = DATA / "ep_calendar.json"
if not cal_path.exists():
    # 新 clone 基线不含日历；既有条目标记已在 src 里，新集标记待 runbook 步骤重建日历
    print("无播出日历，跳过（不改动现有 marks）")
    raise SystemExit(0)
cal = json.loads(cal_path.read_text(encoding="utf-8"))
cal["67"] = "April 8, 2026"

windows = []  # (start_dt, ep)
for n, d in cal.items():
    n = int(n)
    if n < 51 or not d:
        continue
    dd = datetime.strptime(d, "%B %d, %Y").date()  # noqa: DTZ007 只取日期
    windows.append((datetime(dd.year, dd.month, dd.day, 12, 0, tzinfo=JST), n))
# 再放送
rerun = {
    "2024-11-27": 51,
    "2024-12-04": 51,
    "2024-12-11": 52,
    "2024-12-18": 53,
    "2024-12-25": 54,
    "2025-01-08": 55,
    "2025-01-15": 56,
    "2025-01-22": 57,
    "2025-01-29": 58,
}
for d, ep in rerun.items():
    dd = datetime.strptime(d, "%Y-%m-%d").date()  # noqa: DTZ007 只取日期
    windows.append((datetime(dd.year, dd.month, dd.day, 12, 0, tzinfo=JST), ep))


def snow(tid):
    return datetime.fromtimestamp(((int(tid) >> 22) + EPOCH) / 1000, tz=JST)


tw = json.loads((DATA / "tweets.json").read_text(encoding="utf-8"))
marks = {}
for tid, rec in tw.items():
    if rec.get("author") != "nezumiironyanko":
        continue
    ja = rec.get("text", "")
    if "rezeroneko" not in ja.lower():
        continue
    dt = snow(tid)
    if dt.strftime("%Y-%m-%d") == "2025-04-02":
        continue  # 愚人节延長戦：无归属不标
    ep = None
    for start, n in windows:
        if start <= dt < start + timedelta(hours=42):
            ep = n
            break
    if ep is None and dt.strftime("%Y-%m-%d") == "2025-03-09":
        ep = 63  # 明写「アニメ63話」
    if ep:
        marks[tid] = f"S{3 if ep <= 66 else 4}第{ep}集"

(DATA / "ep_marks.json").write_text(
    json.dumps(marks, ensure_ascii=False), encoding="utf-8"
)
from collections import Counter

c = Counter(marks.values())
print(
    "标记总数:",
    len(marks),
    "｜ S3:",
    sum(v for k, v in c.items() if k.startswith("S3")),
    "S4:",
    sum(v for k, v in c.items() if k.startswith("S4")),
)
print(
    "各集:",
    dict(sorted(c.items(), key=lambda x: (len(x[0]), x[0]))),
)
