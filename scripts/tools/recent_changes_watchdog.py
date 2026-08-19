#!/usr/bin/env python3
"""最近改动巡查 watchdog：为 Hermes cron job 提供「上次审查以来的新改动」清单 + 已解析 diff。

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
- diff 拉取/解析由本脚本固定完成（曾由 LLM 每次现写代码，踩过三个坑：
  手工分组漏项、diff HTML 的 td class 是多值导致精确匹配抓空、
  stdout 截断）。水位线在全部 diff 拉取成功后才推进——任何一步失败都
  非零退出且不推进，下次运行重试，不静默漏审。

输出（stdout，注入 cron job 的 prompt 作为上下文）：
- 无新改动：NO_NEW_CHANGES
- 有新改动：两段
  1. NEW_CHANGES：每行一条，含 rcid/revid/old_revid/标题/用户/时间/字节变化/摘要
  2. MERGED_DIFFS：同用户同页的**相邻**连续编辑已合并（最早 old_revid→最晚 revid），
     每节是提取出的增删行：行首 +/- 为整行增删，⟦…⟧ 为行内新增片段，〔…〕为行内删除片段。
     单节超 MAX_GROUP_LINES 截断为头+尾并标注 [TRUNCATED]；type=new 给全文并标注。
  （曾有第三段 RED_LINKS 红链实测，2026-08-06 移除：中文站有繁简自动转换，
  繁体写法链接会被 MediaWiki 自动解析到简体页面，检测几乎只产误报。）

只读脚本；API 拉取失败时非零退出（cron 会因此报错，不会静默漏审）。
"""

import html
import json
import os
import re
import sys
import time

import requests

API = "https://rezero.fandom.com/zh/api.php"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(REPO_ROOT, ".cache", "rc_watchdog.json")

EXCLUDE_USERS = {"IchiSanNi"}  # bot 账号
UA = "re0wiki-rc-watchdog/1.0 (https://github.com/re0wiki/wiki-bot)"

THROTTLE = 1.1  # 秒，API 调用间隔（Cloudflare 429 预防，见 docs/cloudflare-429.md）
MAX_GROUP_LINES = 200  # 单组 diff 行数上限，超出截断为头+尾
GROUP_HEAD, GROUP_TAIL = 160, 30
MAX_TOTAL_LINES = 2500  # diff 总行数预算，超出的组不拉取，列出 rev 范围由 LLM 补拉

_last_call = 0.0


def _get(params: dict, retries: int = 3) -> dict:
    global _last_call
    for attempt in range(retries):
        wait = THROTTLE - (time.time() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.time()
        try:
            resp = requests.get(
                API, params=params, headers={"User-Agent": UA}, timeout=60
            )
        except requests.RequestException:
            if attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            raise
        if resp.status_code in (429, 500, 502, 503, 504) and attempt < retries - 1:
            retry_after = resp.headers.get("Retry-After")
            try:
                delay = (
                    float(retry_after) if retry_after is not None else 5 * (attempt + 1)
                )
            except (TypeError, ValueError):
                delay = 5 * (attempt + 1)
            time.sleep(min(delay, 65))  # Fandom 的 Retry-After 可达数千秒，封顶防卡死
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError("unreachable")


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


def group_consecutive(pending: list[dict]) -> list[dict]:
    """同用户同页的**相邻**连续编辑合并为一组（最早 old_revid→最晚 revid）。

    必须按相邻合并而不能按 (user,title) 全局合并：中间隔着他人编辑时
    （如 A 编辑 → B 编辑 → A 回退 B），全局合并会把他人改动藏进合并区间。
    """
    groups: list[dict] = []
    for c in sorted(pending, key=lambda c: c["rcid"]):
        user = c.get("user", "?")
        if groups and groups[-1]["user"] == user and groups[-1]["title"] == c["title"]:
            g = groups[-1]
            g["to_rev"] = c["revid"]
            g["rcids"].append(c["rcid"])
        else:
            groups.append(
                {
                    "user": user,
                    "title": c["title"],
                    "from_rev": c["old_revid"],
                    "to_rev": c["revid"],
                    "rcids": [c["rcid"]],
                    "is_new": c["type"] == "new" or c["old_revid"] == 0,
                }
            )
    return groups


_DIFF_CELL_RE = re.compile(
    r'<td class="(diff-addedline|diff-deletedline)[^"]*">(.*?)</td>', re.DOTALL
)


def parse_diff(body: str) -> list[tuple[str, str]]:
    """从 compare API 的 HTML body 提取增删行。

    注意 td 的 class 是多值（diff-addedline diff-side-added），精确匹配会抓空。
    行内变更 <ins>/<del> 转成 ⟦⟧/〔〕 标记保留。
    """
    lines: list[tuple[str, str]] = []
    for m in _DIFF_CELL_RE.finditer(body):
        kind, cell = m.group(1), m.group(2)
        cell = re.sub(r"<ins[^>]*>", "⟦", cell)
        cell = re.sub(r"</ins>", "⟧", cell)
        cell = re.sub(r"<del[^>]*>", "〔", cell)
        cell = re.sub(r"</del>", "〕", cell)
        cell = re.sub(r"<[^>]+>", "", cell)
        cell = html.unescape(cell).strip()
        if cell:
            lines.append(("+" if "added" in kind else "-", cell))
    return lines


def fetch_group_lines(g: dict) -> list[str]:
    """拉取并解析一组改动，返回带行首标记的文本行。"""
    if g["is_new"]:
        data = _get(
            {
                "action": "query",
                "prop": "revisions",
                "revids": g["to_rev"],
                "rvprop": "content",
                "rvslots": "main",
                "format": "json",
                "formatversion": "2",
            }
        )
        content = data["query"]["pages"][0]["revisions"][0]["slots"]["main"]["content"]
        return [f"+ {line}" for line in content.splitlines() if line.strip()]
    data = _get(
        {
            "action": "compare",
            "fromrev": g["from_rev"],
            "torev": g["to_rev"],
            "format": "json",
            "formatversion": "2",
        }
    )
    pairs = parse_diff(data.get("compare", {}).get("body", ""))
    return [f"{k} {v}" for k, v in pairs]


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
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_rcid": last_rcid, "last_run": now}, f)
        return 0

    changes = fetch_new_changes(last_rcid)
    max_rcid = max((c["rcid"] for c in changes), default=last_rcid)

    pending = [
        c
        for c in changes
        if c["rcid"] > last_rcid
        and c.get("user") not in EXCLUDE_USERS
        and not c.get("bot")  # formatversion=2 下 "bot" 键恒存在，须判断值
    ]

    def advance_waterline() -> None:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_rcid": max_rcid, "last_run": now}, f)

    if not pending:
        advance_waterline()
        print("NO_NEW_CHANGES")
        return 0

    out: list[str] = [
        f"NEW_CHANGES count={len(pending)} (since rcid>{last_rcid}, UTC 时间)"
    ]
    for c in sorted(pending, key=lambda c: c["rcid"]):
        delta = c.get("newlen", 0) - c.get("oldlen", 0)
        out.append(
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

    # 第二段：合并 diff。任何一组拉取失败都抛异常 → 非零退出且水位线不推进，
    # 下次运行重试，不静默漏审。
    groups = group_consecutive(pending)
    sections: list[str] = [
        f"\nMERGED_DIFFS count={len(groups)} (同用户同页相邻连续编辑已合并)"
    ]
    total = 0
    budget_exceeded = False
    for idx, g in enumerate(groups, 1):
        header = (
            f"### [{idx}] {g['title']} | {g['user']} | "
            f"rev {g['from_rev']}→{g['to_rev']} (rcid {','.join(map(str, g['rcids']))})"
        )
        if g["is_new"]:
            header += " [新页面，以下为全文]"
        if budget_exceeded:
            sections.append(header)
            sections.append("[超出输出预算，未拉取；请用 compare API 自行补拉本组]")
            continue
        lines = fetch_group_lines(g)
        omitted = 0
        if len(lines) > MAX_GROUP_LINES:
            omitted = len(lines) - GROUP_HEAD - GROUP_TAIL
            lines = (
                lines[:GROUP_HEAD]
                + [
                    f"… [TRUNCATED 省略 {omitted} 行；如需审查请用 compare API 拉全量] …"
                ]
                + lines[-GROUP_TAIL:]
            )
        total += len(lines)
        if total > MAX_TOTAL_LINES:
            budget_exceeded = True
        sections.append(header)
        sections.extend(lines if lines else ["(无文本差异)"])

    # 全部成功后才推进水位线
    advance_waterline()
    print("\n".join(out + sections))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001 - watchdog 任何异常都必须非零退出让 cron 告警
        print(f"rc_watchdog ERROR: {e!r}", file=sys.stderr)
        sys.exit(1)
