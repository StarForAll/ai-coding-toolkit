#!/usr/bin/env python3
"""F5-7：追加平台成功时，授予与释放各递增一次代次（2 → 4）。

单独一条用例、单独一个注入点：只有「释放不增代次」会把它打红，
避免与回执类断言混在一个脚本里互相掩盖（第八轮复审 F8-6）。"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H


def check():
    root, _lib, payload = H.stage()
    sys.path.insert(0, payload)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(payload, "install.py"),
                'released_generation = held_generation + 1',
                'released_generation = held_generation  # 注入：释放不增代次')
    import install as wf_install

    fixture = H.install_fixture(root, generation=2)
    rc, out = H.run_quietly(wf_install.add_platforms, fixture["args"], "c0", fixture["manifest"],
                            fixture["writes"], [fixture["skill_root"]])
    if rc != 0:
        raise H.Precondition(f"追加平台未成功：{out.strip()[:160]}")
    writer = json.load(open(os.path.join(fixture["target"], ".wf/writer.json"), encoding="utf-8"))
    if writer.get("generation") != 4:
        raise H.TargetFailure(f"代次不是 2→4：{writer.get('generation')}")


if __name__ == "__main__":
    sys.exit(H.main(check))
