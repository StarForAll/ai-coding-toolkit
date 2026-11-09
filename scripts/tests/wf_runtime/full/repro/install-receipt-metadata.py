#!/usr/bin/env python3
"""F5-8：安装记录（元数据）变化必须进回执，不能只报投放的文件。

与代次、路径分开注入，各自独立可证伪。"""
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
                'changed = deployed + [installation_path]',
                'changed = deployed  # 注入：元数据不计入变更')
    import install as wf_install

    fixture = H.install_fixture(root, generation=2)
    rc, out = H.run_quietly(wf_install.add_platforms, fixture["args"], "c0", fixture["manifest"],
                            fixture["writes"], [fixture["skill_root"]])
    if rc != 0:
        raise H.Precondition(f"追加平台未成功：{out.strip()[:160]}")
    writer = json.load(open(os.path.join(fixture["target"], ".wf/writer.json"), encoding="utf-8"))
    paths = [item.get("path") for item in ((writer.get("maintenance_results") or [{}])[-1]).get("changes") or []]
    if ".wf/install/installation.json" not in paths:
        raise H.TargetFailure(f"元数据变更未进回执：{paths}")


if __name__ == "__main__":
    sys.exit(H.main(check))
