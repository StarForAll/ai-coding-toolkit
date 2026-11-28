#!/usr/bin/env python3
"""返工（普通任务绑定分支）：T 显式暂停 + **入口内 release**（机制稿 §6.2）。

与 `repro/task-rework.py`（同实例分支）互补：这里 T 不属于任何实例，
返工后 T 必须 paused 且写权已由入口释放，新会话才能直接绑定 R。

注入形态 = 不释放写权（模拟"暂停了但写权还握着"）→ 目标断言 3 变红。
"""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_flow as F

SID = "sess-RWH"

FROM = '''            updated = writer_mod.release(ctx.writer())'''
TO = '''            updated = ctx.writer()  # 注入：不释放写权'''


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/tasks.py"), FROM, TO)
    task_id, task_dir = F.build_task(project, root, title="要被返工的任务", sid=SID)

    decision = os.path.join(root, "rework.json")
    json.dump([{"source": "human", "at": "2026-11-12T00:00:00.000000Z",
                "subject": [task_id, "方案错"], "object_digest": "sha256:" + "a" * 64,
                "choice": "返工", "reason": "实施方向错"}],
              open(decision, "w"), ensure_ascii=False)

    def run(args, sid=SID):
        return H.cli(project, args + ["--json"], sid=sid,
                     inputs={"generation": H.generation(project)})

    problems = []
    rc, payload = run(["task-rework", "--task", task_id, "--decision", decision])
    facts = (payload or {}).get("facts") or {}
    if rc != 0:
        raise H.TargetFailure(f"rework 失败：{(payload or {}).get('code')} {facts}")
    rework_id = facts.get("rework")
    record = json.load(open(os.path.join(task_dir, "task.json"), encoding="utf-8"))
    # 1) 普通任务分支：T 显式暂停
    if record.get("paused") is not True:
        problems.append("普通任务分支未暂停 T")
    if rework_id not in (record.get("prerequisites") or []):
        problems.append("T 前置未增 R")
    # 2) 入口内 release：写权回到 idle
    writer = json.load(open(os.path.join(project, ".wf/writer.json"), encoding="utf-8"))
    if writer.get("state") != "idle":
        problems.append(f"写权未释放（目标断言）：{writer.get('state')}")
    if facts.get("released") is not True:
        problems.append(f"facts 未声明已释放：{facts.get('released')}")
    # 3) 交接材料：T 的 WIP 被记录（handoff.wip），不是只暂停
    handoff = (record.get("handoff") or {}).get("wip") or {}
    if handoff.get("task_id") != task_id or handoff.get("resolved") is not None:
        problems.append(f"未保存交接/工作区：{handoff}")
    # 3b) WIP 每项必须是 fingerprint.item（含 digest）：纯字符串会让恢复期的"有变化重核"
    #     与写权前置的按摘要豁免在这条来源上静默失效（R22 F3 / R23 F4）。
    for item in handoff.get("paths") or []:
        if not isinstance(item, dict) or not item.get("path") or not item.get("digest"):
            problems.append(f"交接 WIP 形状不符（应为 fingerprint.item）：{item}")
            break
    # 4) 新会话能直接绑定 R（写权已由入口释放，无需人工 release）；T 的交接 WIP 由 R 承接，
    #    不必先把被否的实现提交入库（2026-11-27 人裁方案①：返工谱系豁免）。
    rc, payload = run(["bind", "--task", rework_id], sid="sess-RWH2")
    if rc != 0:
        problems.append(f"新会话无法绑定 R：{(payload or {}).get('code')} {(payload or {}).get('facts')}")

    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
