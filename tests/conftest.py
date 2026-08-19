"""pytest 公共环境设置。

pywikibot 需要找到 user-config.py：设置 PYWIKIBOT_DIR 指向仓库根目录，
使测试从任意 cwd 运行都能找到配置。
"""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("PYWIKIBOT_DIR", str(REPO_ROOT))
