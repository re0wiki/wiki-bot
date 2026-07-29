#!/usr/bin/env python3
"""最近改动巡查 watchdog：为 Hermes cron job 提供「上次审查以来的新改动」清单。

设计要点：
- 用 rcid 水位线去重：状态存于 .cache/rc_watchdog.json（已 gitignore），
  每次运行只输出 rcid 大于上次水位线的改动，随后推进水位线。
  水位线按「拉取到的全部改动（含被过滤的 bot 编辑）」的最大 rcid 推进，
  否则 bot 自己的编辑会永远卡住水位线。
- 审查区间与触发时间解耦：拉取不设时间窗口，从最新向水位线翻页、碰到
  rcid <= 水位线即停。因此漏触发（停机任意时长）、手动触发、改触发间隔
  都不影响正确性；翻页也保证两次运行之间改动超过单页 500 条（如 bot 全站
  任务）时不漏掉中间的人类编辑。
- 排除 bot：EXCLUDE_USERS 里的账号（IchiSanNi）**全部**编辑都排除——无论是否带
  bot 标记，因为该账号的编辑（含手动）在修改时已自查；其他账号带 bot 标记的编辑也排除。
- 首次运行只播种水位线，不输出（避免把历史改动全部报一遍）。

输出（stdout，注入 cron job 的 prompt 作为上下文）：
- 无新改动：NO_NEW_CHANGES
- 有新改动：每行一条，含 rcid/revid/old_revid/标题/用户/时间/是否新页/字节变化/摘要

只读脚本；API 拉取失败时非零退出（cron 会因此报错，不会静默漏审）。
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request

API = "https://rezero.fandom.com/zh/api.php"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(REPO_ROOT, ".cache", "rc_watchdog.json")

EXCLUDE_USERS = {"IchiSanNi"}  # bot 账号
UA = "re0wiki-rc-watchdog/1.0 (https://github.com/re0wiki/wiki-bot)"


def _get(params: dict) -> dict:
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def fetch_new_changes(last_rcid: int) -> list[dict]:
    """从最新向水位线方向翻页拉取 recentchanges，碰到 rcid <= last_rcid 即停。

    不用时间窗口，纯水位线锚定：正确性与触发时间、触发间隔、停机时长完全解耦
    （漏触发多久都能补拉；手动触发、改间隔都无影响）。翻页保证两次运行之间
    改动超过单页 500 条（如 bot 全站任务）时不会漏掉中间的人类编辑。
    """
    out: list[dict] = []
    cont: dict = {}
    while True:
        data = _get(
            {
                "action": "query",
                "list": "recentchanges",
                "rcprop": "title|ids|sizes|flags|user|comment|timestamp",
                "rctype": "edit|new",
                "rclimit": "500",
                "format": "json",
                "formatversion": "2",
                **cont,
            }
        )
        rc = data["query"]["recentchanges"]
        if not rc:
            break
        out.extend(rc)
        if min(c["rcid"] for c in rc) <= last_rcid:
            break  # 已到水位线，更旧的无需再看
        if "continue" not in data:
            break
        cont = data["continue"]
    return out


def main() -> int:
    state = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            state = json.load(f)

    now = time.time()
    last_rcid = int(state.get("last_rcid", 0))

    if last_rcid == 0:
        # 首次运行：取当前最大 rcid 播种水位线，不输出（基线）
        latest = _get(
            {
                "action": "query",
                "list": "recentchanges",
                "rcprop": "ids",
                "rctype": "edit|new",
                "rclimit": "1",
                "format": "json",
                "formatversion": "2",
            }
        )["query"]["recentchanges"]
        last_rcid = max((c["rcid"] for c in latest), default=0)

    changes = fetch_new_changes(last_rcid)
    max_rcid = max((c["rcid"] for c in changes), default=last_rcid)

    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_rcid": max_rcid, "last_run": now}, f)

    if not state.get("last_rcid"):
        # 首次运行只播种
        return 0

    pending = [
        c
        for c in changes
        if c["rcid"] > last_rcid
        and c.get("user") not in EXCLUDE_USERS
        and not c.get("bot")  # formatversion=2 下 "bot" 键恒存在，须判断值
    ]
    if not pending:
        print("NO_NEW_CHANGES")
        return 0

    print(f"NEW_CHANGES count={len(pending)} (since rcid>{last_rcid}, UTC 时间)")
    for c in sorted(pending, key=lambda c: c["rcid"]):
        delta = c.get("newlen", 0) - c.get("oldlen", 0)
        print(
            "| ".join(
                [
                    f"rcid={c['rcid']}",
                    f"revid={c['revid']}",
                    f"old_revid={c['old_revid']}",
                    f"title={c['title']}",
                    f"user={c.get('user', '?')}",
                    f"time={c['timestamp']}",
                    f"type={c['type']}",
                    f"bytes={delta:+d}",
                    f"comment={c.get('comment', '')!r}",
                ]
            )
        )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001 - watchdog 任何异常都必须非零退出让 cron 告警
        print(f"rc_watchdog ERROR: {e!r}", file=sys.stderr)
        sys.exit(1)
