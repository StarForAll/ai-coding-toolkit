#!/usr/bin/env python3
"""D4.3 锚点探针（一次性证据采集，不进仓库源树）。

双配置对比 SUT 驱动解释器对 `wflib.session.l2_anchor()` 锚点拓扑的影响：
- 配置①（现状）：子解释器 = /usr/bin/python3（≠ 父，模拟今天的 SUT/驱动异解释器）；
- 配置②（假设统一）：子解释器 = 父进程同一解释器。

证据效力限定为"差异存在性"（design D4.3）：配置②的具体锚点值取决于探针调用方
环境、不可跨终端复现，不作为"具体锚点值"证据。

用法（在 unshare + 两级 python 祖先下运行，贴近 worker 链层级深度）：
  unshare -Urm bash -c '<PY> probe_anchor.py parent <child-interpreter> <label>'
"""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
LIB = REPO / "docs/workflows/wf/payload/lib"

CHILD_CODE = (
    "import json, sys; sys.path.insert(0, sys.argv[1]);\n"
    "import wflib.session as s\n"
    "anchor = s.l2_anchor()\n"
    "print(json.dumps({'anchor': anchor, 'key': s.anchor_key(anchor)},\n"
    "                 ensure_ascii=False, sort_keys=True))\n"
)


def main() -> int:
    if len(sys.argv) != 4 or sys.argv[1] != "parent":
        print(__doc__)
        return 2
    child_interpreter, label = sys.argv[2], sys.argv[3]
    proc = subprocess.run([child_interpreter, "-c", CHILD_CODE, str(LIB)],
                          capture_output=True, text=True)
    print(f"[{label}] child={child_interpreter} parent={sys.executable}")
    print(f"[{label}] stdout: {proc.stdout.strip() or '(空)'}")
    if proc.stderr.strip():
        print(f"[{label}] stderr: {proc.stderr.strip()[-400:]}")
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
