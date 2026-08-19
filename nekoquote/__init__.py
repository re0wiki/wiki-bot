"""NekoQuote 语录管线包。

代码在仓库内（本包），运行期数据在 logs/（gitignored）：
- logs/nekoquote/lua_base/   月表基线（缺失时由 nekoquote.bootstrap 从 wiki 重建）
- logs/nekoquote/lua/        构建产物
- logs/nekoquote/lua_live/   上次部署快照
- logs/nekoquote/tweets.json / zh.json / ep_marks.json / ep_calendar.json
- secrets.json（仓库根）LLM key 等在 "llm" 字段下（{"kimi": {...}, ...}）

各阶段以 `python -m nekoquote.<阶段>` 从仓库根运行（logs/ 相对路径依赖 CWD）。
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "logs"
