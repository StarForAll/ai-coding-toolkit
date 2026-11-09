#!/usr/bin/env python3
"""F5-3：回执 `changes[].path` 必须是项目相对路径（运行期按相对路径匹配与查 Git 树）。

与代次、元数据分开注入，各自独立可证伪。"""
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
                'changes = [{"path": os.path.relpath(path, args.target).replace(os.sep, "/"),',
                'changes = [{"path": path,  # 注入：写绝对路径')
    import install as wf_install

    fixture = H.install_fixture(root, generation=2)
    rc, out = H.run_quietly(wf_install.add_platforms, fixture["args"], "c0", fixture["manifest"],
                            fixture["writes"], [fixture["skill_root"]])
    if rc != 0:
        raise H.Precondition(f"追加平台未成功：{out.strip()[:160]}")
    writer = json.load(open(os.path.join(fixture["target"], ".wf/writer.json"), encoding="utf-8"))
    paths = [item.get("path") for item in ((writer.get("maintenance_results") or [{}])[-1]).get("changes") or []]
    if not paths:
        raise H.TargetFailure("回执 changes 为空")
    absolute = [path for path in paths if path and os.path.isabs(path)]
    if absolute:
        raise H.TargetFailure(f"回执含绝对路径：{absolute}")


if __name__ == "__main__":
    sys.exit(H.main(check))
