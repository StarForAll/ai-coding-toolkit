#!/usr/bin/env python3
"""P1-2：`run create` 建立实例、固定快照、首次绑定，且**重入不建第二个实例**（机制稿 §7.2）。

此前 `run` 是 `_unavailable(2, ...)` 桩。现在：
- 必须先在**同一会话**跑过 `definition prepare`（准备范围授权，机制稿 §1.4）；
- 创建时固定定义**原字节**到 `.wf/workflow-runs/<id>/definition.md`，摘要进实例记录；
- 同会话重入 `run create` 按**原意图**续做/幂等返回，不产生第二个实例；
- `run locate` 只读回读。

注入形态 = 把快照写成「非原字节」（模拟"重新序列化后落盘"）→ 目标断言（快照字节与确认的
定义一致）必须变红。重入幂等作为正向断言保留：它同时被未结案意图/已绑定/writer 非 idle
三层挡着，任一层单点注入都到不了"建出第二个实例"，那样的注入没有证明力。
"""

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H

SID = "sess-RUN"
MARKER = "<!-- wf-definition:v1 -->"

STEP = {
    "id": "change", "type": "task", "title": "实施变更", "task_kind": "ordinary",
    "inputs": [{"from": "input", "name": "request"}], "outputs": [], "required": True, "skip": None,
    "human_points": [{"id": "approve-plan", "question": "是否批准当前规划？"}],
    "goal": "完成获批变更", "acceptance": ["验收通过"],
    "actions": [{"id": "work", "text": "实现并验证", "inputs": [], "outputs": [],
                 "required": True, "skip": None, "human_points": []}],
    "verifications": [{"id": "task-check", "source": "current_plan",
                       "established_by": {"kind": "current_task"},
                       "stored_in": {"kind": "task_plan", "verification_id": "task-check"},
                       "consume_at": "check"}],
}

# 目标断言选在**快照必须等于确认的原字节**（机制稿 §7.1「快照哈希同时覆盖完整文件」）。
# 说明：也曾想把「重入建第二个实例」当目标，但那条路同时被三层保护挡着
# （未结案意图 / 已绑定 / writer 非 idle），任何单点注入都到不了"建出第二个实例"——
# 注入退化成不可达就没有意义（B3-1 的教训）。重入仍作**正向断言**留在本用例里。
FROM = '''    records.atomic_write(path, text)\n'''
TO = '''    records.atomic_write(path, text + "\\n# 注入：快照改写成非原字节\\n")\n'''


def _definition_text():
    doc = {
        "format_version": 1, "workflow_id": "bounded-change", "content_version": 1,
        "purpose": "完成一个已限定范围的变更", "applicability": "已有项目基线与配置",
        "inputs": {"request": {"type": "text", "required": True, "description": "人的变更要求"}},
        "steps": [STEP], "completion": ["change 对应任务正常归档"],
    }
    body = json.dumps(doc, ensure_ascii=False, indent=2)
    return f"{MARKER}\n```json\n{body}\n```\n\n# 说明\n", doc


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/runs.py"), FROM, TO)

    text, _doc = _definition_text()
    definition_rel = ".wf/user-workflows/bounded-change.md"
    os.makedirs(os.path.join(project, ".wf/user-workflows"), exist_ok=True)
    with open(os.path.join(project, definition_rel), "w", encoding="utf-8") as handle:
        handle.write(text)
    digest = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()

    problems = []
    # ① 没有准备记录时不得创建（准备范围授权）
    creation = {"definition_id": "bounded-change", "definition_digest": digest,
                "inputs": {"request": "改 X"}, "steps": {"change": "applicable"}}
    creation_path = os.path.join(root, "creation.json")
    json.dump(creation, open(creation_path, "w"), ensure_ascii=False)
    rc, payload = H.cli(project, ["run", "create", "--creation", creation_path, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if rc == 0 or (payload or {}).get("code") != "WF_SEMANTIC_DECISION":
        problems.append(f"无准备记录仍创建成功：{(payload or {}).get('code')}")
    if os.path.isdir(os.path.join(project, ".wf/workflow-runs")):
        problems.append("被拒的创建仍然写了实例目录")

    # ② 准备后创建成功，快照与记录就位
    rc, payload = H.cli(project, ["definition", "prepare", "--id", "bounded-change", "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"definition prepare 失败：{(payload or {}).get('code')}")
    rc, payload = H.cli(project, ["run", "create", "--creation", creation_path, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    facts = (payload or {}).get("facts") or {}
    run_id = ((facts.get("run") or {}).get("id"))
    if rc != 0 or (payload or {}).get("code") != "WF_OK" or not run_id:
        # 目标断言就在这一步：快照必须等于确认的原字节，否则创建失败（注入即走这里）
        raise H.TargetFailure(f"创建失败：{(payload or {}).get('code')} {facts}")
    else:
        snapshot = os.path.join(project, ".wf/workflow-runs", run_id, "definition.md")
        if not os.path.isfile(snapshot):
            problems.append("未落定义快照")
        else:
            with open(snapshot, encoding="utf-8") as handle:
                if "sha256:" + hashlib.sha256(handle.read().encode("utf-8")).hexdigest() != digest:
                    problems.append("快照字节与确认的定义不一致")
        record = json.load(open(os.path.join(project, ".wf/workflow-runs", f"{run_id}.json")))
        if (record.get("definition") or {}).get("digest") != digest:
            problems.append("实例记录未固定定义摘要")
        if record.get("terminal") is not None or record.get("ended_at") is not None:
            problems.append("新实例不应带终态")
        # 首次绑定：会话绑定到 run，且写权 scope 指向同一实例
        bindings = [json.load(open(os.path.join(project, ".wf/session-bindings", name)))
                    for name in os.listdir(os.path.join(project, ".wf/session-bindings"))
                    if name.endswith(".json")]
        if not any((item.get("object") or {}).get("kind") == "run"
                   and (item.get("object") or {}).get("id") == run_id for item in bindings):
            problems.append(f"未建立 run 绑定：{[(i.get('object') or {}) for i in bindings]}")
        holder = (json.load(open(os.path.join(project, ".wf/writer.json"))) or {}).get("holder") or {}
        scope = (holder.get("scope") or {}).get("object") or {}
        if scope.get("kind") != "run" or scope.get("id") != run_id:
            problems.append(f"写权 scope 未指向实例：{scope}")
        if not ((holder.get("scope") or {}).get("preparation") or {}).get("id"):
            problems.append("写权 scope 未记录准备范围（机制稿 §1.4）")

    # ③ 目标断言：重入不建第二个实例
    os.makedirs(os.path.join(project, ".wf/workflow-runs"), exist_ok=True)
    before = sorted(name for name in os.listdir(os.path.join(project, ".wf/workflow-runs"))
                    if name.endswith(".json"))
    rc, payload = H.cli(project, ["run", "create", "--creation", creation_path, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    after = sorted(name for name in os.listdir(os.path.join(project, ".wf/workflow-runs"))
                   if name.endswith(".json"))
    if after != before:
        problems.append(f"重入建了第二个实例：{before} → {after}")
    if len(after) != 1:
        problems.append(f"实例记录数量不是 1：{after}")

    # ④ locate 只读回读
    rc, payload = H.cli(project, ["run", "locate", "--run", run_id, "--json"], sid=SID)
    facts = (payload or {}).get("facts") or {}
    if rc != 0 or (payload or {}).get("code") != "WF_OK":
        problems.append(f"locate 失败：{(payload or {}).get('code')}")
    elif (facts.get("definition") or {}).get("digest") != digest:
        problems.append(f"locate 未回报定义摘要：{facts.get('definition')}")
    elif facts.get("tasks") != []:
        problems.append(f"新实例不应有任务映射：{facts.get('tasks')}")

    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
