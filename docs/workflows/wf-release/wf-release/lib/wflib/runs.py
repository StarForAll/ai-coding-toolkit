"""runs.py — 用户工作流定义与实例（机制稿 §7）。

已交付：**定义静态校验**（§7.2，`definition validate`）与**准备记录**（§1.4 的准备记录字段，
`definition prepare`）。实例的创建/推进/终止仍报告能力不可用，登记见实现稿「已知边界」节。

静态校验只做**可机械判定**的部分：格式与 schema、局部 id 与保留前缀、引用来源与顺序、
路径边界、required/skip 与替代映射、完成/验证/人判声明。定义写得够不够清楚、某个 skip
条件该不该被认可，是人的判断，不在这里。
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import uuid

from . import assets, codes, records
from .paths import join

ROUND = 2

DEFINITION_MARKER = "<!-- wf-definition:v1 -->"
USER_WORKFLOWS_REL = ".wf/user-workflows"
PREPARATIONS_REL = ".wf/preparations"
ID_RE = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
# 这两个前缀由机制稿 §1.3 保留给人判点来源识别（定义里的人判点不得占用）
RESERVED_HUMAN_POINT_PREFIXES = ("plan-q-", "debug-ruling-")
INPUT_TYPES = ("text", "path", "artifact_ref", "secret_ref")
STEP_TYPES = ("task", "human")
TASK_KINDS = ("ordinary", "initialize", "bootstrap")
OUTPUT_KINDS = ("delivery", "step_artifact")
REFERENCE_SOURCES = ("existing_project", "current_plan", "prior_step")
CONSUME_POINTS = ("start", "check", "finish")
# 输入/产物的 `from` 取值域（机制稿 §7.1 的表；消费者只接受这五个）
FROM_KINDS = ("input", "project", "secret_ref", "step", "action")


class DefinitionError(Exception):
    def __init__(self, code, facts=None, next_=None):
        super().__init__(code)
        self.code = code
        self.facts = facts or {}
        self.next = next_


def _problem(stage, reason, location="definition", **extra):
    return dict({"stage": stage, "location": location, "reason": reason}, **extra)


RUNS_REL = ".wf/workflow-runs"


def run_path(root, run_id):
    return join(root, f".wf/workflow-runs/{run_id}.json")


def load_run(root, run_id):
    if not run_id:
        return None
    return records.load_json(run_path(root, run_id))


def iter_runs(root):
    """枚举实例记录（只读）。

    读不出的记录**不当作不存在**：调用方拿到 `(None, path)` 时必须报 unknown，
    否则「悬空 run_id」会被当成「不是实例任务」而错误放行（机制稿 §6.1 独立接续资格）。
    """
    import os

    directory = join(root, RUNS_REL)
    if not os.path.isdir(directory):
        return []
    found = []
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(directory, name)
        found.append((records.load_json(path), path))
    return found


# 独立接续资格（机制稿 §6.1）的绑定面判定结果。**唯一实现**：
# `cli._eligible_task_bind` 用它决定放行/拒绝，`cli.cmd_ready` 用它归组与给阻断项。
BINDING_NONE = "no_run"
BINDING_IN_FLIGHT = "in_flight"
BINDING_NORMAL = "run_ended_normal"
BINDING_ABNORMAL_LICENSED = "run_abnormal_licensed"
BINDING_ABNORMAL_UNLICENSED = "run_abnormal_unlicensed"
BINDING_MISSING = "run_record_missing"


def binding_state(root, task):
    """任务在实例轴上的可接续状态：`{state, run_id, run, permission}`。"""
    run_id = (task or {}).get("run_id")
    if not run_id:
        return {"state": BINDING_NONE, "run_id": None, "run": None, "permission": None}
    run = load_run(root, run_id)
    if run is None:
        return {"state": BINDING_MISSING, "run_id": run_id, "run": None, "permission": None}
    terminal = run.get("terminal")
    if terminal == "normal":
        return {"state": BINDING_NORMAL, "run_id": run_id, "run": run, "permission": None}
    if terminal == "abnormal":
        permission = task.get("independent_resume") or {}
        licensed = bool(permission.get("decision") and permission.get("termination_action"))
        return {"state": BINDING_ABNORMAL_LICENSED if licensed else BINDING_ABNORMAL_UNLICENSED,
                "run_id": run_id, "run": run, "permission": permission or None}
    return {"state": BINDING_IN_FLIGHT, "run_id": run_id, "run": run, "permission": None}


def definition_path(root, workflow_id):
    return join(root, f"{USER_WORKFLOWS_REL}/{workflow_id}.md")


def preparation_path(root, workflow_id):
    return join(root, f"{PREPARATIONS_REL}/{workflow_id}.json")


def _definition_text(root, workflow_id):
    path = definition_path(root, workflow_id)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read(), path
    except OSError:
        return None, path


def parse_definition(text):
    """解析 `<!-- wf-definition:v1 -->` 与其**紧邻**的 `json` 围栏（机制稿 §7.1）。

    只解析那一个机读块，不对 Markdown 求值；标记重复、围栏不紧邻、JSON 不可解析都是结构问题。
    """
    problems = []
    if not isinstance(text, str) or not text.strip():
        return None, [_problem(1, "definition file is empty")]
    count = text.count(DEFINITION_MARKER)
    if count == 0:
        return None, [_problem(1, "definition marker missing", marker=DEFINITION_MARKER)]
    if count > 1:
        return None, [_problem(1, "definition marker must be unique", count=count)]
    after = text.split(DEFINITION_MARKER, 1)[1]
    lines = after.splitlines()
    index = 0
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index >= len(lines) or not lines[index].strip().startswith("```"):
        return None, [_problem(1, "machine-readable block must directly follow the marker")]
    fence = lines[index].strip()
    if fence not in ("```json", "```"):
        return None, [_problem(1, "block right after the marker must be a json fence", fence=fence)]
    body = []
    closed = False
    for line in lines[index + 1:]:
        if line.strip().startswith("```"):
            closed = True
            break
        body.append(line)
    if not closed:
        return None, [_problem(1, "json fence is not closed")]
    try:
        doc = json.loads("\n".join(body))
    except ValueError as exc:
        return None, [_problem(1, f"machine-readable block is not valid JSON: {exc}")]
    if not isinstance(doc, dict):
        return None, [_problem(1, "definition root must be an object")]
    problems.extend(_schema_problems(doc))
    return doc, problems


def _schema_problems(doc):
    """第 1 阶段：格式与 schema（含局部 id 的字符集）。"""
    problems = []
    if doc.get("format_version") != 1:
        problems.append(_problem(1, "format_version must be 1", "format_version",
                                 got=doc.get("format_version")))
    workflow_id = doc.get("workflow_id")
    if not isinstance(workflow_id, str) or not ID_RE.match(workflow_id):
        problems.append(_problem(1, "workflow_id must match [a-z][a-z0-9-]{0,63}", "workflow_id",
                                 got=workflow_id))
    version = doc.get("content_version")
    if not isinstance(version, int) or isinstance(version, bool) or version <= 0:
        problems.append(_problem(1, "content_version must be a positive integer", "content_version",
                                 got=version))
    for field in ("purpose", "applicability"):
        value = doc.get(field)
        if not isinstance(value, str) or not value.strip():
            problems.append(_problem(1, f"{field} must be non-empty text", field))
    inputs = doc.get("inputs", {})
    if not isinstance(inputs, dict):
        problems.append(_problem(1, "inputs must be an object", "inputs"))
        inputs = {}
    for name, spec in inputs.items():
        where = f"inputs.{name}"
        if not isinstance(spec, dict):
            problems.append(_problem(1, "input declaration must be an object", where))
            continue
        if spec.get("type") not in INPUT_TYPES:
            problems.append(_problem(1, f"input type must be one of {list(INPUT_TYPES)}", where,
                                     got=spec.get("type")))
        if not isinstance(spec.get("required"), bool):
            problems.append(_problem(1, "input required must be a boolean", where))
        if not isinstance(spec.get("description"), str) or not spec.get("description").strip():
            problems.append(_problem(1, "input description must be non-empty text", where))
    steps = doc.get("steps")
    if not isinstance(steps, list) or not steps:
        problems.append(_problem(1, "steps must be a non-empty ordered array", "steps"))
        steps = []
    completion = doc.get("completion")
    if not isinstance(completion, list) or not completion or any(
            not isinstance(item, str) or not item.strip() for item in completion):
        problems.append(_problem(1, "completion must be a non-empty array of non-empty text",
                                 "completion"))
    return problems


def _local_id_problems(doc):
    """第 2 阶段：id 唯一（步骤、动作、人判点、产物、验证）。"""
    problems = []
    seen_steps = set()
    for index, step in enumerate(doc.get("steps") or []):
        where = f"steps[{index}]"
        if not isinstance(step, dict):
            problems.append(_problem(2, "step must be an object", where))
            continue
        step_id = step.get("id")
        if not isinstance(step_id, str) or not ID_RE.match(step_id):
            problems.append(_problem(2, "step id must match [a-z][a-z0-9-]{0,63}", where,
                                     got=step_id))
        elif step_id in seen_steps:
            problems.append(_problem(2, "step id must be unique", where, id=step_id))
        else:
            seen_steps.add(step_id)
        if step.get("type") not in STEP_TYPES:
            problems.append(_problem(2, f"step type must be one of {list(STEP_TYPES)}", where,
                                     got=step.get("type")))
        if not isinstance(step.get("title"), str) or not step.get("title", "").strip():
            problems.append(_problem(2, "step title must be non-empty text", where))
        if not isinstance(step.get("required", True), bool):
            problems.append(_problem(2, "step required must be a boolean", where))
        seen_points = set()
        for point in step.get("human_points") or []:
            point_where = f"{where}.human_points"
            if not isinstance(point, dict):
                problems.append(_problem(2, "human point must be an object", point_where))
                continue
            point_id = point.get("id")
            if not isinstance(point_id, str) or not ID_RE.match(point_id):
                problems.append(_problem(2, "human point id must match [a-z][a-z0-9-]{0,63}",
                                         point_where, got=point_id))
                continue
            if point_id.startswith(RESERVED_HUMAN_POINT_PREFIXES):
                problems.append(_problem(2, "human point id uses a reserved prefix", point_where,
                                         id=point_id, reserved=list(RESERVED_HUMAN_POINT_PREFIXES)))
            if point_id in seen_points:
                problems.append(_problem(2, "human point id must be unique within the step",
                                         point_where, id=point_id))
            seen_points.add(point_id)
            if not isinstance(point.get("question"), str) or not point.get("question", "").strip():
                problems.append(_problem(2, "human point question must be non-empty text",
                                         point_where, id=point_id))
        seen_outputs = set()
        for output in step.get("outputs") or []:
            output_where = f"{where}.outputs"
            if not isinstance(output, dict):
                problems.append(_problem(2, "output must be an object", output_where))
                continue
            output_id = output.get("id")
            if not isinstance(output_id, str) or not ID_RE.match(output_id):
                problems.append(_problem(2, "output id must match [a-z][a-z0-9-]{0,63}",
                                         output_where, got=output_id))
            elif output_id in seen_outputs:
                problems.append(_problem(2, "output id must be unique within the step",
                                         output_where, id=output_id))
            else:
                seen_outputs.add(output_id)
            if output.get("kind") not in OUTPUT_KINDS:
                problems.append(_problem(2, f"output kind must be one of {list(OUTPUT_KINDS)}",
                                         output_where, got=output.get("kind")))
        seen_actions = set()
        for action in step.get("actions") or []:
            action_where = f"{where}.actions"
            if not isinstance(action, dict):
                problems.append(_problem(2, "action must be an object", action_where))
                continue
            action_id = action.get("id")
            if not isinstance(action_id, str) or not ID_RE.match(action_id):
                problems.append(_problem(2, "action id must match [a-z][a-z0-9-]{0,63}",
                                         action_where, got=action_id))
            elif action_id in seen_actions:
                problems.append(_problem(2, "action id must be unique within the step",
                                         action_where, id=action_id))
            else:
                seen_actions.add(action_id)
            if not isinstance(action.get("text"), str) or not action.get("text", "").strip():
                problems.append(_problem(2, "action text must be non-empty text", action_where,
                                         id=action_id))
        seen_verifications = set()
        for verification in step.get("verifications") or []:
            verification_where = f"{where}.verifications"
            if not isinstance(verification, dict):
                problems.append(_problem(2, "verification must be an object", verification_where))
                continue
            verification_id = verification.get("id")
            if not isinstance(verification_id, str) or not ID_RE.match(verification_id):
                problems.append(_problem(2, "verification id must match [a-z][a-z0-9-]{0,63}",
                                         verification_where, got=verification_id))
            elif verification_id in seen_verifications:
                problems.append(_problem(2, "verification id must be unique within the step",
                                         verification_where, id=verification_id))
            else:
                seen_verifications.add(verification_id)
    return problems


def _step_index(doc):
    """`{step_id: 序号}`：顺序边界（`from: step` 只能引用更早的步骤）靠它判。"""
    return {step.get("id"): index for index, step in enumerate(doc.get("steps") or [])
            if isinstance(step, dict) and isinstance(step.get("id"), str)}


def _reference_problems(doc):
    """第 3 阶段：引用来源与顺序（机制稿 §7.1 的 `from`/验证声明两张表）。"""
    problems = []
    inputs = doc.get("inputs") or {}
    order = _step_index(doc)
    for index, step in enumerate(doc.get("steps") or []):
        if not isinstance(step, dict):
            continue
        step_id = step.get("id")
        where = f"steps[{index}]"
        action_order = {action.get("id"): position
                        for position, action in enumerate(step.get("actions") or [])
                        if isinstance(action, dict)}
        for entry in step.get("inputs") or []:
            problems.extend(_from_problems(entry, where, inputs, step_id, order, action_order,
                                           doc=doc))
        for position, action in enumerate(step.get("actions") or []):
            if not isinstance(action, dict):
                continue
            for entry in action.get("inputs") or []:
                problems.extend(_from_problems(entry, f"{where}.actions[{position}]", inputs,
                                               step_id, order, action_order, doc=doc,
                                               consumer_position=position))
        for position, verification in enumerate(step.get("verifications") or []):
            if not isinstance(verification, dict):
                continue
            problems.extend(_verification_problems(verification,
                                                   f"{where}.verifications[{position}]",
                                                   step_id, order, action_order))
        if step.get("type") == "task" and step.get("task_kind") not in TASK_KINDS:
            problems.append(_problem(3, f"task step requires task_kind in {list(TASK_KINDS)}",
                                     where, got=step.get("task_kind")))
        if step.get("type") == "task":
            goal = step.get("goal")
            if not isinstance(goal, str) or not goal.strip():
                problems.append(_problem(3, "task step requires non-empty goal", where))
            acceptance = step.get("acceptance")
            if not isinstance(acceptance, list) or not acceptance:
                problems.append(_problem(3, "task step requires non-empty acceptance", where))
        if step.get("type") == "human":
            if not isinstance(step.get("question"), str) or not step.get("question", "").strip():
                problems.append(_problem(3, "human step requires non-empty question", where))
            choices = step.get("choices")
            if not isinstance(choices, list) or not choices:
                problems.append(_problem(3, "human step requires non-empty choices", where))
    return problems


def _declared_outputs_of(doc, step_id):
    for step in doc.get("steps") or []:
        if isinstance(step, dict) and step.get("id") == step_id:
            return {item.get("id") for item in step.get("outputs") or []
                    if isinstance(item, dict) and isinstance(item.get("id"), str)}
    return set()


def _declared_actions_of(doc, step_id):
    for step in doc.get("steps") or []:
        if isinstance(step, dict) and step.get("id") == step_id:
            return [item for item in step.get("actions") or [] if isinstance(item, dict)]
    return []


def _from_problems(entry, where, inputs, step_id, order, action_order,
                   doc=None, consumer_position=None):
    """一张表判一个引用（机制稿 §7.1 的 `from` 取值域）。

    三类来源都要落在**已声明**的对象上：`input` 指本实例输入、`step` 指更早步骤的已声明产物、
    `action` 指同一步骤内更早动作的已声明产物。存在性与顺序都是纯事实，不涉及判断。
    """
    problems = []
    if not isinstance(entry, dict):
        return [_problem(3, "reference must be an object", where)]
    kind = entry.get("from")
    if kind not in FROM_KINDS:
        return [_problem(3, f"from must be one of {list(FROM_KINDS)}", where, got=kind)]
    if kind == "input":
        name = entry.get("name")
        if not isinstance(name, str) or name not in inputs:
            problems.append(_problem(3, "from: input must reference a declared input", where,
                                     name=name, declared=sorted(inputs)))
    elif kind == "project":
        if not isinstance(entry.get("path"), str) or not entry["path"]:
            problems.append(_problem(3, "from: project requires a path", where))
    elif kind == "secret_ref":
        if entry.get("provider") not in ("env", "host_store"):
            problems.append(_problem(3, "secret_ref provider must be env or host_store", where,
                                     got=entry.get("provider")))
        if not isinstance(entry.get("name"), str) or not entry.get("name"):
            problems.append(_problem(3, "secret_ref requires a name", where))
    elif kind == "step":
        source = entry.get("step")
        if not isinstance(source, str) or source not in order:
            problems.append(_problem(3, "from: step must reference a declared step", where,
                                     step=source))
        elif source == step_id or order[source] >= order.get(step_id, 0):
            problems.append(_problem(3, "from: step must reference an earlier step", where,
                                     step=source))
        elif doc is not None:
            outputs = _declared_outputs_of(doc, source)
            if entry.get("output") not in outputs:
                problems.append(_problem(3, "from: step must reference a declared output", where,
                                         step=source, output=entry.get("output"),
                                         declared=sorted(outputs)))
    else:      # action
        source = entry.get("action")
        if not isinstance(source, str) or source not in action_order:
            problems.append(_problem(3, "from: action must reference a declared action of this step",
                                     where, action=source))
        elif consumer_position is not None and action_order[source] >= consumer_position:
            problems.append(_problem(3, "from: action must reference an earlier action", where,
                                     action=source))
        elif doc is not None:
            declared = set()
            for action in _declared_actions_of(doc, step_id):
                if action.get("id") == source:
                    for output in action.get("outputs") or []:
                        if isinstance(output, dict) and isinstance(output.get("id"), str):
                            declared.add(output["id"])
            if entry.get("output") not in declared:
                problems.append(_problem(3, "from: action must reference a declared output", where,
                                         action=source, output=entry.get("output"),
                                         declared=sorted(declared)))
    return problems


def _verification_problems(verification, where, step_id, order, action_order):
    problems = []
    source = verification.get("source")
    if source not in REFERENCE_SOURCES:
        return [_problem(3, f"verification source must be one of {list(REFERENCE_SOURCES)}", where,
                         got=source)]
    if verification.get("consume_at") not in CONSUME_POINTS:
        problems.append(_problem(3, f"consume_at must be one of {list(CONSUME_POINTS)}", where,
                                 got=verification.get("consume_at")))
    established = verification.get("established_by") or {}
    stored = verification.get("stored_in") or {}
    if not isinstance(established, dict) or not isinstance(stored, dict):
        return problems + [_problem(3, "established_by/stored_in must be objects", where)]
    if source == "existing_project":
        if established.get("kind") != "project":
            problems.append(_problem(3, "existing_project requires established_by.kind=project",
                                     where, got=established.get("kind")))
        if stored.get("kind") != "project_file" or not isinstance(stored.get("path"), str):
            problems.append(_problem(3, "existing_project requires stored_in.project_file.path",
                                     where))
    elif source == "current_plan":
        if established.get("kind") != "current_task":
            problems.append(_problem(3, "current_plan requires established_by.kind=current_task",
                                     where, got=established.get("kind")))
        if stored.get("kind") != "task_plan" or not isinstance(stored.get("verification_id"), str):
            problems.append(_problem(3, "current_plan requires stored_in.task_plan.verification_id",
                                     where))
    else:      # prior_step
        if established.get("kind") != "step":
            problems.append(_problem(3, "prior_step requires established_by.kind=step", where,
                                     got=established.get("kind")))
        source_step = established.get("step_id")
        if not isinstance(source_step, str) or source_step not in order:
            problems.append(_problem(3, "prior_step requires a declared earlier step", where,
                                     step=source_step))
        elif order[source_step] >= order.get(step_id, 0):
            problems.append(_problem(3, "prior_step must be an earlier step", where,
                                     step=source_step))
        action_id = established.get("action_id")
        if action_id is not None and action_order is not None and action_id not in action_order:
            problems.append(_problem(3, "prior_step action_id must hit a declared action", where,
                                     action=action_id))
        if stored.get("kind") != "step_output" or stored.get("step_id") != source_step:
            problems.append(_problem(3, "prior_step requires stored_in.step_output of that step",
                                     where, stored=stored))
    return problems


def _path_problems(doc, root):
    """第 4 阶段：产物路径（机制稿 §7.1）。delivery 相对项目根，step_artifact 相对实例产物根。"""
    from . import paths as paths_mod

    problems = []
    inputs = doc.get("inputs") or {}
    for index, step in enumerate(doc.get("steps") or []):
        if not isinstance(step, dict):
            continue
        where = f"steps[{index}]"
        for output in step.get("outputs") or []:
            if not isinstance(output, dict):
                continue
            kind = output.get("kind")
            declared = output.get("path")
            if isinstance(declared, dict):
                # `{input: name}` 只能指向 path 类型输入，不拼接任意模板表达式
                name = declared.get("input")
                spec = inputs.get(name) if isinstance(name, str) else None
                if not isinstance(spec, dict) or spec.get("type") != "path":
                    problems.append(_problem(4, "output path {input: ...} must point to a path input",
                                             where, input=name, output=output.get("id")))
                continue
            if not isinstance(declared, str) or not declared.strip():
                problems.append(_problem(4, "output requires a path or an input reference", where,
                                         output=output.get("id")))
                continue
            try:
                normalized = paths_mod.normalize(declared)
            except paths_mod.InvalidPath as exc:
                problems.append(_problem(4, f"output path invalid: {exc}", where,
                                         path=declared))
                continue
            if normalized.startswith("../") or os.path.isabs(normalized):
                problems.append(_problem(4, "output path must stay inside the project", where,
                                         path=declared))
                continue
            if kind == "delivery" and root is not None:
                violation = paths_mod.boundary_violation(root, normalized)
                if violation:
                    problems.append(_problem(4, violation, where, path=normalized))
            if kind == "step_artifact" and not normalized.startswith(USER_WORKFLOWS_REL):
                # 产物根由实现方案固定：实例专属产物一律落在 `.wf/user-workflows/` 之下，
                # 不同实例的同名 step_artifact 因此不会解析到同一路径
                problems.append(_problem(4, "step_artifact must live under the instance artifact root",
                                         where, path=normalized, root=USER_WORKFLOWS_REL))
    return problems


def _skip_problems(doc):
    """第 5 阶段：required/skip 与替代映射（机制稿 §7.1、§7.2 下游一致性）。"""
    problems = []
    for index, step in enumerate(doc.get("steps") or []):
        if not isinstance(step, dict):
            continue
        where = f"steps[{index}]"
        required = step.get("required", True)
        skip = step.get("skip")
        if required and skip not in (None, {}):
            problems.append(_problem(5, "required step must declare skip=null", where))
        if skip not in (None, {}) and not isinstance(skip, dict):
            problems.append(_problem(5, "skip must be null or an object", where))
            continue
        if not isinstance(skip, dict):
            continue
        point = skip.get("decision_point")
        declared_points = {item.get("id") for item in step.get("human_points") or []
                          if isinstance(item, dict)}
        if not isinstance(point, str) or point not in declared_points:
            problems.append(_problem(5, "skip.decision_point must reference a declared human point",
                                     where, decision_point=point, declared=sorted(declared_points)))
        if not isinstance(skip.get("condition"), str) or not skip.get("condition", "").strip():
            problems.append(_problem(5, "skip.condition must be non-empty text (a human judgement)",
                                     where))
        downstream = skip.get("downstream")
        if downstream is None:
            continue
        if not isinstance(downstream, list):
            problems.append(_problem(5, "skip.downstream must be an array", where))
            continue
        consumers = _consumer_index(doc)
        for position, item in enumerate(downstream):
            item_where = f"{where}.skip.downstream[{position}]"
            if not isinstance(item, dict):
                problems.append(_problem(5, "downstream entry must be an object", item_where))
                continue
            consumer = item.get("consumer")
            if consumer not in consumers:
                problems.append(_problem(5, "downstream.consumer must exist in the definition",
                                         item_where, consumer=consumer))
            mode = item.get("mode")
            if mode not in ("unused", "replacement"):
                problems.append(_problem(5, "downstream.mode must be unused or replacement",
                                         item_where, got=mode))
            if mode == "replacement":
                source = item.get("replacement")
                problems.extend(_from_problems(source, item_where, doc.get("inputs") or {},
                                               step.get("id"), _step_index(doc), {}, doc=doc))
    return problems


def _consumer_index(doc):
    """所有可能的消费方 id：步骤 id、动作 id、验证声明的 id（机制稿 §7.2 的 consumer 定义）。"""
    found = set()
    for step in doc.get("steps") or []:
        if not isinstance(step, dict):
            continue
        if isinstance(step.get("id"), str):
            found.add(step["id"])
        for action in step.get("actions") or []:
            if isinstance(action, dict) and isinstance(action.get("id"), str):
                found.add(action["id"])
        for verification in step.get("verifications") or []:
            if isinstance(verification, dict) and isinstance(verification.get("id"), str):
                found.add(verification["id"])
    return found


def _completion_problems(doc):
    """第 6 阶段：完成/验证/人判声明（机制稿 §7.2 末段）。"""
    problems = []
    total_verifications = sum(len(step.get("verifications") or [])
                              for step in doc.get("steps") or [] if isinstance(step, dict))
    completion = doc.get("completion") or []
    if not any(isinstance(item, str) and item.strip() for item in completion):
        problems.append(_problem(6, "completion must state the finish condition", "completion"))
    if total_verifications == 0:
        # 定义级「必要验证」由任务步骤的 verifications 共同承载；一条都没有即空壳声明
        problems.append(_problem(6, "definition declares no verification; the necessary checks "
                                    "must be carried by task steps", "verifications"))
    for index, step in enumerate(doc.get("steps") or []):
        if not isinstance(step, dict) or step.get("type") != "task":
            continue
        if not step.get("verifications"):
            problems.append(_problem(6, "task step declares no verification",
                                     f"steps[{index}]", id=step.get("id")))
    return problems


def validate_definition(doc, root=None, workflow_id=None):
    """静态校验（机制稿 §7.2 的固定顺序）：返回按阶段排序的问题清单。"""
    problems = list(_schema_problems(doc))
    problems.extend(_local_id_problems(doc))
    problems.extend(_reference_problems(doc))
    problems.extend(_path_problems(doc, root))
    problems.extend(_skip_problems(doc))
    problems.extend(_completion_problems(doc))
    if workflow_id and doc.get("workflow_id") and doc["workflow_id"] != workflow_id:
        problems.append(_problem(1, "workflow_id must equal the definition file name",
                                 "workflow_id", expected=workflow_id, got=doc["workflow_id"]))
    return sorted(problems, key=lambda item: item.get("stage", 0))


def _require_workflow_id(args):
    workflow_id = args.value("--id")
    if not workflow_id or not ID_RE.match(workflow_id):
        raise DefinitionError("WF_PATH_INVALID",
                              {"reason": "definition requires --id <workflow-id> matching "
                                         "[a-z][a-z0-9-]{0,63}", "got": workflow_id})
    return workflow_id


def validate(ctx, args):
    """`definition validate --id <workflow-id>`：只读静态校验（机制稿 §7.2 的固定顺序）。

    只读：不写任何记录；问题清单按阶段排序返回，`ok=false` 时给 `WF_DEFINITION_INVALID`。
    """
    from . import codes

    workflow_id = _require_workflow_id(args)
    text, path = _definition_text(ctx.root, workflow_id)
    if text is None:
        raise DefinitionError("WF_PATH_INVALID",
                              {"reason": "definition file missing", "path": _rel(ctx.root, path),
                               "expected": f"{USER_WORKFLOWS_REL}/{workflow_id}.md"})
    doc, problems = parse_definition(text)
    if doc is not None:
        problems = validate_definition(doc, ctx.root, workflow_id=workflow_id)
    stages = sorted({item.get("stage") for item in problems})
    facts = {"workflow_id": workflow_id, "path": _rel(ctx.root, path),
             "digest": "sha256:" + records.sha256_hex(text.encode("utf-8")),
             "problems": problems, "stages_with_problems": stages}
    if problems:
        raise DefinitionError("WF_DEFINITION_INVALID",
                              dict(facts, reason="static validation failed"),
                              next_="按 problems 逐条修正定义；不猜承载步骤，不用自由文本占位")
    return codes.result("WF_OK", object={"id": workflow_id},
                        position_=codes.position(scope="maintenance"),
                        next_="静态校验通过：下一步 prepare 固定准备代次，再 run create",
                        facts=dict(facts, ok=True))


def _rel(root, path):
    return os.path.relpath(path, str(root)).replace(os.sep, "/")


def prepare(ctx, args):
    """`definition prepare --id <workflow-id>`：建立/更新准备记录（机制稿 §1.4、§7.2）。

    准备记录落 `.wf/preparations/<id>.json`（控制记录，见 `scope._is_control_record`）：
    `{session_key, scope_paths, authorization, definition_refs, validation, progress, wip, ended_at}`。
    未通过校验的草稿**照常保留**（机制稿 §7.2：「准备结束或取消可以保留未通过草稿」），
    失败出口是 `WF_DEFINITION_INVALID` + 问题清单。
    """
    from . import codes, lock, scope, session as session_mod, writer as writer_mod

    workflow_id = _require_workflow_id(args)
    key = ctx.key()
    text, path = _definition_text(ctx.root, workflow_id)
    with lock.acquire(ctx.root, holder_hint=f"definition prepare {workflow_id}"):
        record = writer_mod.load(ctx.root) or {}
        holder = record.get("holder") or {}
        if isinstance(record, dict) and record.get("state") == "held" and holder.get("id") != key:
            # 准备不例外于写权：别的会话正在写这个项目时先让人处理（机制稿 §1.4）
            raise DefinitionError("WF_WRITER_BUSY",
                                  {"reason": "writer held by another session", "holder": holder},
                                  next_="等待对方释放或走已确认的交接/恢复出口")
        if text is None:
            validation = {"ok": False, "checked_at": records.now_str(),
                          "problems": [_problem(0, "definition file missing",
                                                expected=f"{USER_WORKFLOWS_REL}/{workflow_id}.md")]}
            digest = None
        else:
            doc, problems = parse_definition(text)
            if doc is not None:
                problems = validate_definition(doc, ctx.root, workflow_id=workflow_id)
            validation = {"ok": not problems, "checked_at": records.now_str(),
                          "problems": problems}
            digest = "sha256:" + records.sha256_hex(text.encode("utf-8"))
        previous = records.load_json(preparation_path(ctx.root, workflow_id), {}) or {}
        preparation = {
            "schema_version": 1,
            "id": workflow_id,
            "session_key": key,
            "scope_paths": [f"{USER_WORKFLOWS_REL}/{workflow_id}.md"],
            # 准备授权不复用任务批准（机制稿 §1.4）：这里只记「谁在什么时候以此会话发起」，
            # 实例创建时另核人的确认引用
            "authorization": {"source": "human", "at": records.now_str(),
                              "session_key": key},
            "definition_refs": ([{"path": f"{USER_WORKFLOWS_REL}/{workflow_id}.md",
                                  "digest": digest}] if digest else []),
            "validation": validation,
            "progress": {"attempts": int((previous.get("progress") or {}).get("attempts") or 0) + 1,
                         "last_ok": validation["ok"]},
            "wip": previous.get("wip"),
            "ended_at": None,
            "updated_at": records.now_str(),
        }
        records.write_json(preparation_path(ctx.root, workflow_id), preparation)
    facts = {"workflow_id": workflow_id, "preparation": _rel(ctx.root, preparation_path(ctx.root, workflow_id)),
             "validation": validation, "progress": preparation["progress"]}
    if not validation["ok"]:
        raise DefinitionError("WF_DEFINITION_INVALID",
                              dict(facts, reason="preparation kept as draft; static validation failed"),
                              next_="按 validation.problems 修正后重跑 validate/prepare")
    return codes.result("WF_OK", object={"id": workflow_id},
                        position_=codes.position(scope="maintenance"),
                        next_="准备代次已固定：下一步 run create（实例创建仍属未交付能力）",
                        facts=dict(facts, ok=True))


CREATION_FIELDS = ("definition_id", "definition_digest", "inputs", "steps")
APPLICABILITY = ("applicable", "skipped")


def creation_problems(creation, doc=None):
    """创建输入的结构校验（只做机械判定：缺字段、未知键、取值域）。

    「这个展开规则合不合理」「这步该不该略过」是人的判断，命令只要求它们**被明确声明**。
    """
    problems = []
    if not isinstance(creation, dict):
        return [{"reason": "creation file must be a JSON object"}]
    for field in CREATION_FIELDS:
        if field not in creation:
            problems.append({"reason": f"creation requires `{field}`", "field": field})
    workflow_id = creation.get("definition_id")
    if not isinstance(workflow_id, str) or not ID_RE.match(workflow_id):
        problems.append({"reason": "definition_id must match [a-z][a-z0-9-]{0,63}",
                         "field": "definition_id", "got": workflow_id})
    digest = creation.get("definition_digest")
    if not isinstance(digest, str) or not digest.startswith("sha256:"):
        problems.append({"reason": "definition_digest must be a sha256 Digest",
                         "field": "definition_digest", "got": digest})
    inputs = creation.get("inputs")
    if not isinstance(inputs, dict):
        problems.append({"reason": "inputs must be an object", "field": "inputs"})
    steps = creation.get("steps")
    if not isinstance(steps, dict) or not steps:
        problems.append({"reason": "steps must be a non-empty object of step id -> applicability",
                         "field": "steps"})
    elif doc is not None:
        declared = {step.get("id") for step in doc.get("steps") or []
                    if isinstance(step, dict) and step.get("id")}
        for step_id, value in steps.items():
            if step_id not in declared:
                problems.append({"reason": "steps names an undeclared step", "step": step_id,
                                 "declared": sorted(declared)})
            if value not in APPLICABILITY:
                problems.append({"reason": f"steps value must be one of {list(APPLICABILITY)}",
                                 "step": step_id, "got": value})
    expansion = creation.get("expansion")
    if expansion is not None and not isinstance(expansion, dict):
        problems.append({"reason": "expansion must be an object when present", "field": "expansion"})
    return problems


def input_value_problems(doc, values):
    """按定义的 `inputs` 声明核实际取值（机制稿 §7.2 的「绑定后的实际输入」）。"""
    problems = []
    declared = doc.get("inputs") or {}
    for name, spec in declared.items():
        required = isinstance(spec, dict) and spec.get("required")
        if name not in values:
            if required:
                problems.append({"reason": "required input missing", "input": name})
            continue
        value = values[name]
        kind = spec.get("type") if isinstance(spec, dict) else None
        if kind == "text":
            if not isinstance(value, str):
                problems.append({"reason": "text input must be a string", "input": name})
        elif kind == "path":
            if not isinstance(value, str) or not value.strip():
                problems.append({"reason": "path input must be a non-empty string", "input": name})
            else:
                from . import paths as paths_mod

                try:
                    paths_mod.normalize(value)
                except paths_mod.InvalidPath as exc:
                    problems.append({"reason": f"path input invalid: {exc}", "input": name})
        elif kind in ("artifact_ref",):
            if not isinstance(value, dict) or value.get("from") not in ("project", "step"):
                problems.append({"reason": "artifact_ref must be a project/step reference",
                                 "input": name, "got": value})
        elif kind == "secret_ref":
            if not isinstance(value, dict) or value.get("from") != "secret_ref":
                problems.append({"reason": "secret_ref input must be a secret reference object "
                                            "(never a plaintext value)", "input": name,
                                 "got": type(value).__name__})
            elif value.get("provider") not in ("env", "host_store"):
                problems.append({"reason": "secret_ref provider must be env or host_store",
                                 "input": name, "got": value.get("provider")})
    unknown = sorted(set(values) - set(declared))
    if unknown:
        problems.append({"reason": "inputs not declared by the definition", "inputs": unknown,
                         "declared": sorted(declared)})
    return problems


def _creation_file(args):
    from . import records as records_mod

    path = args.value("--creation")
    if not path:
        raise DefinitionError("WF_PATH_INVALID", {"reason": "run create requires --creation <path>"})
    loaded = records_mod.load_json(path)
    if loaded is None:
        raise DefinitionError("WF_PATH_INVALID", {"reason": "creation file missing", "path": path})
    return loaded


def _preparation_problems(root, workflow_id, key, definition_rel):
    """准备范围重核（机制稿 §1.4、§7.2）：本会话确有该定义的有效准备记录。"""
    problems = []
    record = records.load_json(preparation_path(root, workflow_id), None)
    if not isinstance(record, dict):
        problems.append({"reason": "no preparation record for this definition",
                         "exit": f"先跑 definition prepare --id {workflow_id}"})
        return problems
    if record.get("session_key") != key:
        problems.append({"reason": "preparation belongs to another session",
                         "exit": "由原会话创建实例，或在新会话重跑 definition prepare"})
    if record.get("ended_at"):
        problems.append({"reason": "preparation already ended",
                         "exit": f"重新跑 definition prepare --id {workflow_id}"})
    if definition_rel not in (record.get("scope_paths") or []):
        problems.append({"reason": "preparation scope does not cover this definition",
                         "scope_paths": record.get("scope_paths")})
    if not (record.get("validation") or {}).get("ok"):
        problems.append({"reason": "preparation validation did not pass",
                         "problems": (record.get("validation") or {}).get("problems")})
    return problems


RUN_STEPS = ("write_snapshot", "write_run", "acquire_writer", "bind")


def _run_step_done(ctx, key, targets, step):
    """各步的真实后置（不看步骤字段）：文件/记录存在且内容对得上。"""
    run_id = targets.get("run")
    if not run_id:
        return False
    if step == "write_snapshot":
        snapshot = join(ctx.root, f"{RUNS_REL}/{run_id}/definition.md")
        digest = targets.get("definition-digest")
        return os.path.isfile(snapshot) and (
            "sha256:" + records.sha256_hex(open(snapshot, "rb").read()) == digest)
    if step == "write_run":
        record = load_run(ctx.root, run_id)
        return isinstance(record, dict) and record.get("terminal", "missing") is None
    if step == "acquire_writer":
        record = ctx.writer() or {}
        holder = record.get("holder") or {}
        scope = (holder.get("scope") or {}).get("object") or {}
        return (record.get("state") == "held" and holder.get("id") == key
                and scope.get("kind") == "run" and scope.get("id") == run_id)
    if step == "bind":
        from . import session as session_mod

        binding = session_mod.load_binding(ctx.root, key) or {}
        return ((binding.get("object") or {}).get("kind") == "run"
                and (binding.get("object") or {}).get("id") == run_id)
    return False


def _write_run_snapshot(ctx, run_id, text):
    """完整快照：原字节落 `definition.md`（机制稿 §1.5 的 `snapshot_path`）。"""
    directory = join(ctx.root, f"{RUNS_REL}/{run_id}")
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, "definition.md")
    records.atomic_write(path, text)
    return path


def create(ctx, args):
    """`run create --creation <path>`：建立实例、固定定义快照、首次绑定（机制稿 §7.2）。

    writer 上的**单一 `run.create` 父动作**承载：意图与写权授予同一次写入，中断按原意图续做
    （目标一次固定，不从当前请求重建）。实例创建只取得「规划权限」——不代批准业务、不建任务。
    """
    from . import actions as actions_mod, cli, lock, session as session_mod, writer as writer_mod

    creation = _creation_file(args)
    session = ctx.session()
    key = ctx.key()
    code, profile_facts = session_mod.check_platforms(ctx.platforms(), session)
    if code:
        raise cli.CliError(code, profile_facts, next_="install --platform <当前宿主> 后重试")
    if not isinstance(creation, dict):
        raise DefinitionError("WF_SEMANTIC_DECISION",
                              {"problems": creation_problems(creation)})
    workflow_id = creation.get("definition_id")
    text, definition_abs = _definition_text(ctx.root, workflow_id or "")
    if text is None:
        raise DefinitionError("WF_PATH_INVALID",
                              {"reason": "definition file missing",
                               "expected": f"{USER_WORKFLOWS_REL}/{workflow_id}.md"})
    doc, problems = parse_definition(text)
    if doc is not None:
        problems = validate_definition(doc, ctx.root, workflow_id=workflow_id)
    problems = problems + creation_problems(creation, doc)
    if problems:
        raise DefinitionError("WF_DEFINITION_INVALID",
                              {"problems": problems, "reason": "creation or definition invalid"})
    digest = "sha256:" + records.sha256_hex(text.encode("utf-8"))
    if creation.get("definition_digest") != digest:
        raise DefinitionError("WF_SEMANTIC_DECISION",
                              {"reason": "definition content changed since it was confirmed",
                               "confirmed": creation.get("definition_digest"), "current": digest,
                               "exits": ["按当前内容重新确认后重试", "把定义改回已确认的版本"]})
    value_problems = input_value_problems(doc, creation.get("inputs") or {})
    if value_problems:
        raise DefinitionError("WF_SEMANTIC_DECISION",
                              {"reason": "bound inputs do not satisfy the definition",
                               "problems": value_problems})
    definition_rel = f"{USER_WORKFLOWS_REL}/{workflow_id}.md"
    problems = _preparation_problems(ctx.root, workflow_id, key, definition_rel)
    if problems:
        raise DefinitionError("WF_SEMANTIC_DECISION",
                              {"reason": "preparation scope does not authorise this creation",
                               "problems": problems},
                              next_=f"先跑 definition prepare --id {workflow_id}（校验通过后重试）")

    with lock.acquire(ctx.root, holder_hint="run create"):
        record = ctx.writer() or {}
        pending = record.get("action") or {}
        if pending.get("kind") == "run.create" and pending.get("state") != "done":
            if (record.get("holder") or {}).get("id") != key:
                raise cli.CliError("WF_WRITER_BUSY",
                                   {"reason": "unfinished run.create intent owned by another session"},
                                   next_="由原会话重入续做，或走受控恢复")
            return _resume_run_create(ctx, key, session, record, pending, text)
        if session_mod.load_binding(ctx.root, key):
            raise DefinitionError("WF_BINDING_MISMATCH",
                                  {"reason": "session already bound",
                                   "object": (session_mod.load_binding(ctx.root, key) or {}).get("object")},
                                  next_="继续当前对象用 continue/bind；要开新实例请在新会话里选")
        cli.assert_no_foreign_wip(ctx, exclude_id=None)
        if record.get("state") != "idle":
            raise cli.CliError("WF_WRITER_BUSY", {"holder": record.get("holder")})

        run_id = uuid.uuid4().hex
        record_rel = f"{RUNS_REL}/{run_id}.json"
        snapshot_rel = f"{RUNS_REL}/{run_id}/definition.md"
        for candidate in (join(ctx.root, record_rel), join(ctx.root, f"{RUNS_REL}/{run_id}")):
            if os.path.exists(candidate):
                raise cli.CliError("WF_TARGET_COLLISION", {"path": _rel(ctx.root, candidate)})
        instance_id = session.get("instance_id") or session_mod.new_instance_id()
        inputs = {"run": run_id, "definition": definition_rel, "digest": digest,
                  "inputs_digest": records.plain_digest(creation.get("inputs") or {})}
        owner_scope = {"object": {"kind": "run", "id": run_id},
                       "preparation": {"id": workflow_id, "scope_paths": [definition_rel]}}
        updated = writer_mod.acquire(record, kind="session", ident=key, scope=owner_scope,
                                     checkpoint={"step": "run-create", "at": records.now_str()})
        action = actions_mod.new_action("run.create", writer_mod.owner_ref(
            "session", key, owner_scope), int(updated.get("revision", 0)), inputs,
            steps=list(RUN_STEPS), head_before=actions_mod.head_of(ctx.root),
            targets=[{"kind": "writer", "id": "writer"},
                     {"kind": "run", "id": run_id},
                     {"kind": "binding", "id": key},
                     {"kind": "instance", "id": instance_id},
                     {"kind": "definition", "id": workflow_id},
                     {"kind": "definition-digest", "id": digest}])
        action["steps"] = [{"id": step, "state": "pending"} for step in RUN_STEPS]
        updated = dict(updated)
        updated["action"] = action
        writer_mod.save(ctx.root, updated)
        return _advance_run_create(ctx, key, session, updated, action, text, creation,
                                   workflow_id, digest, instance_id)


def _advance_run_create(ctx, key, session, record, action, text, creation,
                        workflow_id, digest, instance_id):
    from . import actions as actions_mod, cli, session as session_mod, writer as writer_mod

    targets = {item.get("kind"): item.get("id") for item in action.get("targets") or []
               if isinstance(item, dict)}
    run_id = targets.get("run")
    # ① 快照与记录：内容来自**本次确认的定义字节**（digest 已在锁外核过，这里再核一次防漂移）
    current = "sha256:" + records.sha256_hex(text.encode("utf-8"))
    if current != digest:
        raise DefinitionError("WF_SEMANTIC_DECISION",
                              {"reason": "definition changed between confirmation and creation",
                               "confirmed": digest, "current": current})
    _write_run_snapshot(ctx, run_id, text)
    run_record = {
        "schema_version": 1,
        "id": run_id,
        "workflow_id": workflow_id,
        "definition": {"workflow_id": workflow_id,
                       "content_version": (parse_definition(text)[0] or {}).get("content_version"),
                       "format_version": 1,
                       "snapshot_path": f"{RUNS_REL}/{run_id}/definition.md",
                       "digest": digest},
        "inputs": creation.get("inputs") or {},
        "creation_decision": {"source": "human", "at": records.now_str(),
                              "steps": creation.get("steps") or {},
                              "expansion": creation.get("expansion")},
        "cursor": None,
        "step_results": {},
        "task_map": {},
        "sequence_changes": [],
        "pending": None,
        "paused": False,
        "closing": None,
        "terminal": None,
        "ended_at": None,
    }
    records.write_json(run_path(ctx.root, run_id), run_record)
    # ② 绑定（首次绑定；`bind` 不承担首次创建，这里由 run.create 父动作承载）
    binding = {
        "schema_version": 1,
        "id": key,
        "revision": 0,
        "created_at": records.now_str(),
        "updated_at": records.now_str(),
        "write_mark": None,
        "action": None,
        "identity": {"provider": session["provider"], "value": session["identity"]},
        "instance_id": instance_id,
        "object": {"kind": "run", "id": run_id},
        "bound_at": records.now_str(),
    }
    session_mod.save_binding(ctx.root, key, binding)
    cli._sync_attachment_instance(ctx, key, instance_id)
    session_mod.write_runtime(ctx.root, key, {
        "binding_digest": records.plain_digest(binding),
        "instance_id": instance_id,
        "object": {"kind": "run", "id": run_id},
        "current_task": None,
        "cursor": None,
    })
    # ③ 步骤后置逐个核（手工标 done 不能代替产物）
    action = dict(action)
    action["steps"] = [{"id": step, "state": "done"} for step in RUN_STEPS]
    action = dict(action, state="applying", next_step=None)
    record = dict(record)
    record["action"] = action
    writer_mod.save(ctx.root, record)
    stale = [step for step in RUN_STEPS if not _run_step_done(ctx, key, targets, step)]
    if stale:
        raise DefinitionError("WF_PERSISTENCE_FAILED",
                              {"reason": "run.create step postcondition missing", "steps": stale},
                              next_="重入 run create 续做缺失后置（不按当前参数重建）")
    assertion = cli._control_assertion(
        ctx, "run.create", writer_mod.owner_ref("session", key, (record.get("holder") or {}).get("scope")),
        action, [f"run:{run_id}"])
    action = actions_mod.complete(action, summary="run.create", control_assertion=assertion)
    record["action"] = action
    record["write_mark"] = cli._write_mark(
        ctx, "run.create", writer_mod.owner_ref("session", key, (record.get("holder") or {}).get("scope")),
        (record.get("holder") or {}).get("generation"), action.get("head_before"),
        ["run"], action)
    writer_mod.save(ctx.root, record)
    return codes.result(
        "WF_OK",
        object={"id": run_id},
        position_=codes.position(scope="run", step_id=None, action_id=action.get("id"),
                                 action_state=action.get("state")),
        next_="下一步 run advance 推进首个适用步骤（当前仍是未交付能力）",
        facts={"run": {"id": run_id, "workflow_id": workflow_id, "digest": digest,
                       "snapshot": f"{RUNS_REL}/{run_id}/definition.md"},
               "generation": record.get("generation"),
               "instance_id": instance_id,
               "binding": {"kind": "run", "id": run_id},
               "steps": [step for step in RUN_STEPS],
               "control_assertion": assertion},
    )


def _resume_run_create(ctx, key, session, record, action, text):
    """按**原意图**续做：目标取自 action.targets，定义字节若已变则拒（快照不可重建）。"""
    targets = {item.get("kind"): item.get("id") for item in action.get("targets") or []
               if isinstance(item, dict)}
    digest = targets.get("definition-digest")
    current = "sha256:" + records.sha256_hex(text.encode("utf-8"))
    if current != digest:
        raise DefinitionError("WF_SEMANTIC_DECISION",
                              {"reason": "definition changed after the interrupted creation",
                               "intent": digest, "current": current,
                               "exits": ["把定义改回原版本后重入", "放弃该意图后重新 create"]})
    workflow_id = targets.get("definition")
    creation = records.load_json(join(ctx.root, f"{RUNS_REL}/{targets.get('run')}.creation.json"), {}) or {}
    if not creation:
        # 意图里的输入摘要与步骤适用性取自本次动作固定值；不再要求 creation 文件仍在
        creation = {"inputs": {}, "steps": {}, "definition_id": workflow_id}
    return _advance_run_create(ctx, key, session, record, action, text, creation,
                               workflow_id, digest, targets.get("instance"))


def locate(ctx, args):
    """`run locate --run <id>`：只读定位（机制稿 §2.1 的绑定内定位）。"""
    from . import codes, tasks as tasks_mod

    run_id = args.value("--run")
    if not run_id:
        raise DefinitionError("WF_PATH_INVALID", {"reason": "run locate requires --run <id>"})
    run = load_run(ctx.root, run_id)
    if not isinstance(run, dict):
        raise DefinitionError("WF_HISTORY_UNRESOLVED",
                              {"reason": "run record missing or unreadable", "run": run_id})
    tasks = []
    for step_id, mapping in sorted((run.get("task_map") or {}).items()):
        task_id = (mapping or {}).get("task_id")
        record = tasks_mod.load_task(ctx.root, task_id) if task_id else None
        tasks.append({"step_id": step_id, "task_id": task_id,
                      "status": (record or {}).get("status"),
                      "phase": (record or {}).get("phase"),
                      "unknown": record is None})
    return codes.result("WF_OK", object={"id": run_id},
                        position_=codes.position(scope="run"),
                        next_="按 cursor 与 step_results 判断下一步",
                        facts={"run": {key: run.get(key) for key in
                                       ("id", "workflow_id", "terminal", "paused", "ended_at")},
                               "definition": run.get("definition"),
                               "cursor": run.get("cursor"),
                               "step_results": run.get("step_results") or {},
                               "task_map": run.get("task_map") or {},
                               "sequence_changes": run.get("sequence_changes") or [],
                               "tasks": tasks})


def advance(*_args, **_kwargs):
    raise assets.CapabilityUnavailable("run advance (D12)", ROUND)


def pause(*_args, **_kwargs):
    raise assets.CapabilityUnavailable("run pause (D13)", ROUND)


def terminate(*_args, **_kwargs):
    raise assets.CapabilityUnavailable("run terminate (D13)", ROUND)


def load_definition(*_args, **_kwargs):
    raise assets.CapabilityUnavailable("workflow definition loading (D11)", ROUND)


def finish(*_args, **_kwargs):
    raise assets.CapabilityUnavailable("run finish (D13)", ROUND)
