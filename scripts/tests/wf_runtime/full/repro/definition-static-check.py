#!/usr/bin/env python3
"""P1-1：`definition validate/prepare` 必须可跑，且静态校验会挡住保留前缀（机制稿 §7.2）。

此前 `definition` 是 `_unavailable(2, ...)` 桩。现在：`validate` 只读跑六阶段静态校验
（问题清单按阶段排序），`prepare` 落准备记录（`{session_key, scope_paths, authorization,
definition_refs, validation, progress, wip, ended_at}`），未通过的草稿照常保留。

注入形态 = 去掉「人判点 id 不得占用保留前缀」这一检查 → 违例定义被放行，目标断言必须变红。
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H

SID = "sess-DEF"
MARKER = "<!-- wf-definition:v1 -->"

FROM = '''            if point_id.startswith(RESERVED_HUMAN_POINT_PREFIXES):\n'''
TO = '''            if False:  # 注入：不拦保留前缀\n'''

STEP = {
    "id": "change", "type": "task", "title": "实施变更", "task_kind": "ordinary",
    "inputs": [], "outputs": [], "required": True, "skip": None,
    "human_points": [{"id": "approve-plan", "question": "是否批准当前规划？"}],
    "goal": "完成获批变更", "acceptance": ["验收通过"],
    "actions": [{"id": "work", "text": "实现并验证", "inputs": [], "outputs": [],
                 "required": True, "skip": None, "human_points": []}],
    "verifications": [{"id": "task-check", "source": "current_plan",
                       "established_by": {"kind": "current_task"},
                       "stored_in": {"kind": "task_plan", "verification_id": "task-check"},
                       "consume_at": "check"}],
}


def _document(point_id):
    step = json.loads(json.dumps(STEP))
    step["human_points"][0]["id"] = point_id
    return {
        "format_version": 1, "workflow_id": "bounded-change", "content_version": 1,
        "purpose": "完成一个已限定范围的变更", "applicability": "已有项目基线与配置",
        "inputs": {}, "steps": [step], "completion": ["change 对应任务正常归档"],
    }


def _write(project, doc):
    directory = os.path.join(project, ".wf/user-workflows")
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, "bounded-change.md")
    body = json.dumps(doc, ensure_ascii=False, indent=2)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(f"{MARKER}\n```json\n{body}\n```\n\n# 说明\n")
    return path


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/runs.py"), FROM, TO)

    problems = []
    _write(project, _document("approve-plan"))
    rc, payload = H.cli(project, ["definition", "validate", "--id", "bounded-change", "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if rc != 0 or (payload or {}).get("code") != "WF_OK":
        problems.append(f"合法定义未通过：{(payload or {}).get('code')} "
                        f"{((payload or {}).get('facts') or {}).get('problems')}")

    rc, payload = H.cli(project, ["definition", "prepare", "--id", "bounded-change", "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    preparation = os.path.join(project, ".wf/preparations/bounded-change.json")
    if rc != 0 or (payload or {}).get("code") != "WF_OK":
        problems.append(f"prepare 失败：{(payload or {}).get('code')}")
    elif not os.path.isfile(preparation):
        problems.append("prepare 未落准备记录")
    else:
        record = json.load(open(preparation, encoding="utf-8"))
        for field in ("session_key", "scope_paths", "authorization", "definition_refs",
                      "validation", "progress", "ended_at"):
            if field not in record:
                problems.append(f"准备记录缺字段：{field}")
        if not (record.get("validation") or {}).get("ok"):
            problems.append("准备记录未记录校验结果")

    # 目标断言：保留前缀必须被拒
    _write(project, _document("plan-q-1"))
    rc, payload = H.cli(project, ["definition", "validate", "--id", "bounded-change", "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    code = (payload or {}).get("code") if rc != 0 else "WF_OK"
    if code != "WF_DEFINITION_INVALID":
        problems.append(f"保留前缀未被拒：rc={rc} code={code}")
    else:
        found = ((payload or {}).get("facts") or {}).get("problems") or []
        if not any("reserved prefix" in str(item.get("reason") or "") for item in found):
            problems.append(f"拒绝原因未点名保留前缀：{found[:2]}")

    # 草稿保留：未通过的 prepare 仍写记录，但 ok=false
    rc, payload = H.cli(project, ["definition", "prepare", "--id", "bounded-change", "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if rc == 0:
        problems.append("未通过的 prepare 报了成功")
    else:
        record = json.load(open(preparation, encoding="utf-8"))
        if (record.get("validation") or {}).get("ok") is not False:
            problems.append("未通过的草稿未被记录为 ok=false")

    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
