"""NekoQuote 共享状态：全链待完成标记、跨进程锁与原子 JSON 写入。"""

import json
import os
import tempfile
from pathlib import Path

from filelock import FileLock

from . import DATA

PENDING = DATA / "chain_pending.json"


def mark_pending(path: Path = PENDING) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def clear_pending(path: Path = PENDING) -> None:
    path.unlink(missing_ok=True)


def state_lock(data: Path = DATA) -> FileLock:
    """串行化共享缓存的读改写、全链和状态提交。"""
    data.mkdir(parents=True, exist_ok=True)
    return FileLock(str(data / "state.lock"))


def write_json(path: Path, data) -> None:
    """同目录临时文件 + 原子替换；失败不破坏既有 JSON。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
