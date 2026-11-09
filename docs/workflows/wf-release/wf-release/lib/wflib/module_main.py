"""module_main.py — 以 lib 目录在 sys.path 内拉起语义层 CLI。

引导层以 os.execve 平移到此文件；本文件只负责 import 路径与退出码。
"""

from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_LIB = os.path.dirname(_HERE)
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from wflib.cli import main  # noqa: E402  (路径准备之后才可导入)

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
