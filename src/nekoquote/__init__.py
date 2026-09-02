"""NekoQuote 语录管线包。

代码在仓库内（本包），运行期数据在 .cache/nekoquote/（gitignored；常驻状态，
删了有代价——logs/ 才是「跑完即删」的 scratch，勿混放）：
- .cache/nekoquote/lua_base/   月表基线（缺失时由 nekoquote.bootstrap 从 wiki 重建）
- .cache/nekoquote/lua/        构建产物
- .cache/nekoquote/lua_live/   上次部署快照
- .cache/nekoquote/sync_state.json / tweets.json / zh.json / ep_marks.json / ep_calendar.json
- secrets.json（仓库根）LLM key 等在 "llm" 字段下（{"kimi": {...}, ...}）

各阶段以 `python -m nekoquote.<阶段>` 运行（路径全部经 DATA 常量解析，不依赖 CWD）。
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / ".cache" / "nekoquote"
