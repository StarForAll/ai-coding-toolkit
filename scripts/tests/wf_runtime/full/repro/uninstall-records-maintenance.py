#!/usr/bin/env python3
"""619 卸载登记维护写者并留可核回执（kind=uninstall）。

obligation（机制稿 §10.5、设计稿 §4.4/§7.3）：
- 卸载在写权合法时按维护写者处理：取得持有、递增代次；
- 结束后释放为空闲，并留下**可核回执**：`disposition.kind=uninstall`，
  事实是「登记要移除的资产当前都不存在」——因此回执必须派生为 `disposed`，
  而不是 `applied_pending_commit`/`pending_check`（后两者会挡住后续任务开工）。

注入形态：把处置类型写成 `commit`（卸载不是提交语义，事实核不过 → pending_check）。
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H

FROM = '                        "kind": "uninstall",\n'
TO = '                        "kind": "commit",  # 注入：用提交语义记卸载\n'


def uninstall(project, *args, feed=""):
    return subprocess.run([H.WF_PYTHON, os.path.join(project, ".wf/bin/uninstall.py"),
                           "--project", project, *args],
                          capture_output=True, text=True, input=feed)


def check():
    root, lib, _payload = H.stage()
    H.load(lib)
    project = H.deploy(root)
    H.ensure_project_config(project)
    before = json.load(open(os.path.join(project, ".wf/writer.json"), encoding="utf-8"))
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/bin/uninstall.py"), FROM, TO)

    preview = uninstall(project)
    token = re.search(r"令牌：([0-9a-f]{32})", preview.stdout or "")
    if not token:
        raise H.Precondition(f"预览未给令牌：{(preview.stdout or '')[-160:]}")
    applied = uninstall(project, "--apply", "--nonce", token.group(1), feed=token.group(1) + "\n")
    if applied.returncode != 0:
        raise H.Precondition(f"卸载应用失败：{(applied.stdout or applied.stderr)[-200:]}")

    record = json.load(open(os.path.join(project, ".wf/writer.json"), encoding="utf-8"))
    problems = []
    if record.get("state") != "idle" or record.get("holder"):
        problems.append(f"卸载后未释放维护持有：{record.get('state')}/{record.get('holder')}")
    if record.get("generation") != (before.get("generation") or 0) + 2:
        problems.append(f"代次不是 +2：{before.get('generation')} → {record.get('generation')}")

    # 卸载已删掉项目内的 .wf/lib，导入必须走**暂存 payload**，不能被项目的残路径抢先
    sys.path[:] = [item for item in sys.path if "/proj/.wf/lib" not in item]
    # 项目 lib 可能已被 H.ensure_project_config 先导入并缓存，必须清掉缓存再按暂存 payload 导入
    for name in [item for item in sys.modules if item == "wflib" or item.startswith("wflib.")]:
        del sys.modules[name]
    if lib not in sys.path:
        sys.path.insert(0, lib)
    from wflib import tasks as wf_tasks

    states = [item for item in wf_tasks.task_receipts(project) if item.get("operation") == "uninstall"]
    if not states:
        problems.append("没有卸载回执")
    else:
        state = states[-1].get("state")
        if state != "disposed":
            problems.append(f"卸载回执未派生 disposed：{state}（{states[-1].get('facts')}）")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
