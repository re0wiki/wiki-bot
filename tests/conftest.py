"""pytest 公共环境设置。

两个环境陷阱：
1. pywikibot 需要找到 user-config.py：设置 PYWIKIBOT_DIR 指向仓库根目录，
   使测试从任意 cwd 运行都能找到配置。
2. python -m pytest 会把 cwd（通常是仓库根）注入 sys.path，使仓库根的
   pywikibot/ 目录以 namespace package 遮蔽已安装的 pywikibot——移除之。
"""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("PYWIKIBOT_DIR", str(REPO_ROOT))

sys.path = [p for p in sys.path if Path(p or ".").resolve() != REPO_ROOT]
