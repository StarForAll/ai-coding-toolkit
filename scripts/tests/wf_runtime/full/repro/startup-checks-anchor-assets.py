#!/usr/bin/env python3
"""651 固定流转程序化：启动校验必须含「写者标记锚点」与「框架资产可用性」两步。

obligation（机制稿 §5.2 的启动固定顺序 ⑧⑨）：
- ⑧ 持有/恢复态下，`.wf-lock` 的标记行必须可识别；标记缺失/未知 → `WF_HISTORY_UNRESOLVED`；
- ⑨ 必需框架资产缺失 → 报对应入口不可用 `WF_CAPABILITY_UNAVAILABLE`。
「status 四步 ok」曾经不等于完整启动校验，本用例把后两步钉死。

注入形态：资产缺失也报 ok（不核资产）。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _snapshot as S

SID = "sess-STARTUP"
FROM = ('        missing = [rel for rel in required if not os.path.isfile(join(ctx.root, rel))]\n')
TO = ('        missing = []  # 注入：不核资产\n')


def startup(project):
    rc, payload = H.cli(project, ["status", "--json"], sid=SID,
                        inputs={"generation": H.generation(project)})
    findings = (payload or {}).get("facts", {}).get("startup") or []
    return {item.get("step"): item for item in findings}


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    os.makedirs(os.path.join(project, "pkg"), exist_ok=True)
    open(os.path.join(project, "pkg/a.py"), "w").write("a\n")
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/tasks.py"), FROM, TO)
    S.started_task(project, root, sid=SID)      # 写者持有 → ⑧ 生效
    problems = []

    steps = startup(project)
    for name in ("candidates", "marker", "assets"):
        if name not in steps:
            problems.append(f"启动校验缺步骤 {name}")
    if problems:
        raise H.TargetFailure("；".join(problems))

    # ⑧ 标记行被改成未知内容 → 必须报待核对
    with open(os.path.join(project, ".wf-lock"), "w", encoding="utf-8") as handle:
        handle.write("wf-lock-unknown\nholder pid=1 start=1\n")
    marker = startup(project).get("marker") or {}
    if marker.get("status") != "blocked" or marker.get("code") != "WF_HISTORY_UNRESOLVED":
        problems.append(f"⑧ 未按标记锚点阻断：{marker}")

    # ⑨ 删必需资产 → 必须报能力不可用
    os.remove(os.path.join(project, ".wf/bin/repair.py"))
    assets = startup(project).get("assets") or {}
    if assets.get("status") != "blocked" or assets.get("code") != "WF_CAPABILITY_UNAVAILABLE":
        problems.append(f"⑨ 未按资产缺失阻断：{assets}")
    elif ".wf/bin/repair.py" not in (assets.get("missing") or []):
        problems.append(f"⑨ 未点名缺失资产：{assets.get('missing')}")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
