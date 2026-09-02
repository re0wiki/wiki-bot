"""按文件路径加载仓库内模块的辅助。

src/scripts/ 没有 __init__.py（pywikibot 按文件名加载脚本，不走 import），
因此测试用 importlib 按路径加载，不走 sys.path。
"""

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_module(name: str, rel_path: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / rel_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
