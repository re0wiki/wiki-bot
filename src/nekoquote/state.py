"""NekoQuote 全链待完成状态；存在标记即表示入库内容尚未完成部署。"""

from pathlib import Path

from . import DATA

PENDING = DATA / "chain_pending.json"


def mark_pending(path: Path = PENDING) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def clear_pending(path: Path = PENDING) -> None:
    path.unlink(missing_ok=True)
