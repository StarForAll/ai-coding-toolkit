#!/usr/bin/env python3
"""660 判定物与原因码：码表本身是可核的判定物。

obligation（设计稿 §8.2「判定物与原因码」）：每一枚码都必须带**档位**与**出口**，
阻断类必须带「禁止的错误修复」；档位只取自三档。码表错了，所有门禁判定都会跟着错。

注入形态：把一枚码的档位改成非法值（档位是判定物的一部分，不是注释）。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H

TIERS = {"pass", "blocked", "needs_decision"}


def check():
    root, lib, payload = H.stage()
    H.load(lib)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        # 码表已改为 protocol 投影（codes.py 不再持有枚举字面量），注入点随之改变：
        # 覆盖一枚码的档位为非法值，判定物一旦错就必须红。
        H.patch(os.path.join(payload, "lib", "wflib", "codes.py"),
                "CODES = _protocol_codes()",
                'CODES = _protocol_codes()\nCODES["WF_OK"] = ("ok", CODES["WF_OK"][1])')
    from wflib import codes as C

    problems = []
    expected = len(json.load(open(os.path.join(H.PAYLOAD, "protocol", "codes.json"), encoding="utf-8"))["codes"])
    if len(C.CODES) != expected:
        problems.append(f"码表与 protocol 不一致：{len(C.CODES)} vs {expected}")
    for code, spec in C.CODES.items():
        if not isinstance(code, str) or not code.startswith("WF_"):
            problems.append(f"码名不合规：{code!r}")
            continue
        if not isinstance(spec, (tuple, list)) or len(spec) < 2:
            problems.append(f"{code}：元组不足（tier, exit）")
            continue
        tier, exit_hint = spec[0], spec[1]
        if tier not in TIERS:
            problems.append(f"{code}：档位非法 {tier!r}")
        if not str(exit_hint or "").strip():
            problems.append(f"{code}：缺出口")
        if tier in ("blocked", "needs_decision") and len(spec) < 3:
            problems.append(f"{code}：阻断/待决档缺「禁止的错误修复」")
        if problems:
            break
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
