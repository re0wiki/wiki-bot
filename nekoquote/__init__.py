"""NekoQuote 语录管线包。

代码在仓库内（本包），运行期数据在 logs/（gitignored）：
- logs/p8/lua_base/   月表基线（缺失时由 nekoquote.bootstrap 从 wiki 重建）
- logs/p8/lua/        构建产物
- logs/p8/lua_live/   上次部署快照
- logs/p8_tweets.json / p8_zh.json / p8_ep_marks.json / p8_ep_calendar.json
- secrets.json（仓库根）LLM key 等在 "llm" 字段下（{"kimi": {...}, ...}）

各阶段以 `python -m nekoquote.<阶段>` 从仓库根运行（logs/ 相对路径依赖 CWD）。
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "logs"
