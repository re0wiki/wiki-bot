"""增量链执行器：翻译 → 归一 → 构建 → 校验 → 部署 → 同步部署快照。

任一阶段非零退出即 SystemExit（调用方据此不推进水位线/状态）。
子进程清掉 PYTHONPATH（防外部注入的 venv 路径遮蔽本项目依赖）。
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAGES = ("translate", "normalize", "build", "verify_rt", "deploy")


def run_chain(stages: tuple[str, ...] = STAGES) -> None:
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["PYTHONIOENCODING"] = "utf-8"
    for s in stages:
        r = subprocess.run(
            [sys.executable, "-m", f"nekoquote.{s}"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            check=False,
        )
        print((r.stdout or "")[-400:])
        if r.returncode != 0:
            print(r.stderr[-800:])
            raise SystemExit(f"nekoquote.{s} 失败")
    live = ROOT / "logs/nekoquote/lua_live"
    shutil.rmtree(live, ignore_errors=True)
    shutil.copytree(ROOT / "logs/nekoquote/lua", live)
