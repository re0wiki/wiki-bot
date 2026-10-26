"""FxTwitter v2 时间线采集：长月原创（含 Note Tweet 长文）。"""

TIMELINE_URL = "https://api.fxtwitter.com/2/profile/nezumiironyanko/statuses"
AUTHOR = "nezumiironyanko"


def _is_original(item: dict) -> bool:
    author = item.get("author") or {}
    return (
        item.get("type") == "status"
        and str(item.get("id", "")).isdigit()
        and author.get("screen_name", "").casefold() == AUTHOR
        and not item.get("reposted_by")
    )


def _pages(session):
    cursor = None
    seen_cursors = set()
    while True:
        params = {"count": 100, "with_replies": "1"}
        if cursor:
            params["cursor"] = cursor
        resp = session.get(TIMELINE_URL, params=params, timeout=60)
        if resp.status_code == 204:
            return
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 200:
            raise RuntimeError(f"FxTwitter 返回错误 code={data.get('code')}")
        results = data["results"]
        if not results:
            return
        yield results
        cursor = data.get("cursor", {}).get("bottom")
        if not cursor:
            return
        if cursor in seen_cursors:
            raise RuntimeError("FxTwitter 分页游标重复")
        seen_cursors.add(cursor)


def fetch_quotes(
    session, *, stop_id: str | None = None, stop_before: int | None = None
) -> tuple[dict[str, str], str | None]:
    """抓取时间线中的原创，返回 {推 id: 正文} 与见过的最新原创 id。

    有界扫描须抵达 stop_id / stop_before；边界页处理完才停止，未抵达则报错。
    """
    quotes: dict[str, str] = {}
    newest: str | None = None
    stopped = False
    for results in _pages(session):
        for item in results:
            if not _is_original(item):
                continue
            tid = item["id"]
            if newest is None or int(tid) > int(newest):
                newest = tid
            if tid == stop_id or (
                stop_before is not None and int(item["created_timestamp"]) < stop_before
            ):
                stopped = True
            if (
                stop_id is not None
                and int(tid) <= int(stop_id)
                or stop_before is not None
                and int(item["created_timestamp"]) < stop_before
            ):
                continue
            text = (item.get("text") or "").strip()
            if text:
                quotes.setdefault(tid, text)
        if stopped:
            break
    if (stop_id is not None or stop_before is not None) and not stopped:
        raise RuntimeError("FxTwitter 时间线遍历结束，未抵达指定边界")
    return quotes, newest


def latest_original_id(session) -> str:
    """当前时间线最新原创 id；用于新基线播种，不收录其历史内容。"""
    newest: str | None = None
    for results in _pages(session):
        for item in results:
            if not _is_original(item):
                continue
            tid = item["id"]
            if newest is None or int(tid) > int(newest):
                newest = tid
    if newest is None:
        raise RuntimeError("FxTwitter 时间线未找到长月原创")
    return newest
