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
import subprocess
import uuid

from . import actions as actions_mod, assets, codes, decisions as decisions_mod, records
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


def save_run(root, run):
    """写回实例记录（调用方负责锁与绑定核验）。"""
    records.write_json(run_path(root, run.get("id")), run)
    return run


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
        # 机制稿 §7.1：`skip` 在必需项为 null，**可略项为 {condition, decision_point, downstream}**。
        # 两个方向都核：必需项不得带 skip；可略项不得缺声明——否则"可略"退化成"必需且无替代"，
        # 而人以为自己写的是可略（拼错 `required`/`skip` 时正是这种静默后果）。
        required_flag = step.get("required")
        skip_decl = step.get("skip")
        if required_flag is False and not isinstance(skip_decl, dict):
            problems.append(_problem(5, "skippable step must declare skip "
                                        "{condition, decision_point, downstream}", where,
                                     got=skip_decl))
        if isinstance(skip_decl, dict):
            if not isinstance(skip_decl.get("condition"), str) or \
                    not skip_decl.get("condition", "").strip():
                problems.append(_problem(5, "skip.condition must be non-empty text", where))
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
            else:
                declared_verifications = {item.get("id") for item in step.get("verifications") or []
                                          if isinstance(item, dict)}
                for entry in acceptance:
                    # 条目可以是给人看的文本，也可以是任务侧同形的 {id, statement, verification_ids}；
                    # 后者一旦出现就必须指回本步骤声明的验证（机制稿 §7.2「引用来源与顺序」）。
                    if not isinstance(entry, dict):
                        continue
                    refs = entry.get("verification_ids")
                    if refs is None:
                        continue
                    if not isinstance(refs, list):
                        problems.append(_problem(3, "acceptance verification_ids must be an array",
                                                 where, got=type(refs).__name__))
                        continue
                    unknown = [ref for ref in refs if ref not in declared_verifications]
                    if unknown:
                        problems.append(_problem(
                            3, "acceptance references undeclared verification",
                            where, got=unknown, declared=sorted(declared_verifications)))
        if step.get("type") == "human":
            if not isinstance(step.get("question"), str) or not step.get("question", "").strip():
                problems.append(_problem(3, "human step requires non-empty question", where))
            choices = step.get("choices")
            if not isinstance(choices, list) or not choices:
                problems.append(_problem(3, "human step requires non-empty choices", where))
    return problems


DEFINITION_KEYS = {
    "root": {"format_version", "workflow_id", "content_version", "purpose", "applicability",
             "inputs", "steps", "completion"},
    "step": {"id", "type", "title", "inputs", "outputs", "required", "skip", "human_points",
             "task_kind", "goal", "acceptance", "actions", "verifications", "question", "choices"},
    "action": {"id", "text", "inputs", "outputs", "required", "skip", "human_points"},
    "output": {"id", "kind", "path", "description", "required"},
    "verification": {"id", "source", "established_by", "stored_in", "consume_at"},
    "human_point": {"id", "question"},
    "input": {"type", "required", "description"},
}


def _unknown_key_problems(doc):
    """未登记键一律拒绝（机制稿 §7.1 的字段表是闭集；§1.1 要求每个键有消费者与失败出口）。

    静默忽略的后果是**行为静默变化**：`required` 拼错 → 该步骤变成必需；`skip` 拼错 → 可略声明整块丢失。
    说明文本写进 Markdown 正文，机读块只放机读字段。
    """
    problems = []

    def check(where, mapping, kind, path):
        if not isinstance(mapping, dict):
            return
        extra = sorted(set(mapping) - DEFINITION_KEYS[kind])
        if extra:
            problems.append(_problem(1, f"unknown {kind} key(s) not defined by the format",
                                     path, got=extra, defined=sorted(DEFINITION_KEYS[kind])))

    check("root", doc, "root", "")
    for step in doc.get("steps") or []:
        if not isinstance(step, dict):
            continue
        where = f"steps[{step.get('id')}]"
        check(where, step, "step", where)
        for action in step.get("actions") or []:
            if isinstance(action, dict):
                check(f"{where}.actions[{action.get('id')}]", action, "action",
                      f"{where}.actions[{action.get('id')}]")
        for output in step.get("outputs") or []:
            if isinstance(output, dict):
                check(f"{where}.outputs[{output.get('id')}]", output, "output",
                      f"{where}.outputs[{output.get('id')}]")
        for verification in step.get("verifications") or []:
            if isinstance(verification, dict):
                check(f"{where}.verifications[{verification.get('id')}]", verification,
                      "verification", f"{where}.verifications[{verification.get('id')}]")
        for point in step.get("human_points") or []:
            if isinstance(point, dict):
                check(f"{where}.human_points[{point.get('id')}]", point, "human_point",
                      f"{where}.human_points[{point.get('id')}]")
    for name, declaration in (doc.get("inputs") or {}).items():
        if isinstance(declaration, dict):
            check(f"inputs[{name}]", declaration, "input", f"inputs[{name}]")
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
    completion = doc.get("completion") or []
    if not any(isinstance(item, str) and item.strip() for item in completion):
        problems.append(_problem(6, "completion must state the finish condition", "completion"))
    # 定义级「必要验证」由**任务步骤**的 verifications 共同承载，因此只在存在任务步骤时要求；
    # 纯 human 步骤的流程没有交付物，硬要一条验证只会逼人写个假任务步骤（下面对每条任务步骤逐条核）。
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
    problems.extend(_unknown_key_problems(doc))   # 未登记键：字段表是闭集（机制稿 §7.1）
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
    doc, problems, text, path = load_definition(ctx.root, workflow_id)
    if text is None:
        raise DefinitionError("WF_PATH_INVALID",
                              {"reason": "definition file missing", "path": _rel(ctx.root, path),
                               "expected": f"{USER_WORKFLOWS_REL}/{workflow_id}.md"})
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


def _prepare_action_done(action, ok):
    """准备动作的结案：步骤状态按事实标，结果摘要区分「通过」与「只留草稿」。"""
    from . import actions as actions_mod

    action = actions_mod.complete(
        action, summary=("definition.prepare ok" if ok else "definition.prepare draft-only"))
    action = dict(action)
    action["steps"] = [{"id": "static_check", "state": "done"},
                       {"id": "write_preparation", "state": "done"}]
    return action


def prepare_scope_digest(scope_paths):
    """准备范围的身份（唯一定义）：决定里的 `object_digest` 就是它。"""
    return records.H("wf-prepare-scope-v1",
                     {"paths": sorted(str(item) for item in scope_paths or [])})


def _prepare_authorization(ctx, args, workflow_id, definition_rel):
    """`definition prepare --authorization <决定>` 的核验（设计稿 §5.7）。

    决定必须是人给出的（`_load_decision` 六键与 TODO 预检）、取值在 `prepare_definition` 域内，
    并且 `scope_paths` **可证覆盖**本次定义路径；`object_digest` 必须等于按 `scope_paths`
    重算的范围摘要（防止"答复后改范围"）。通过返回准备记录里的 authorization 对象。
    """
    from . import cli, decisions as decisions_mod

    path = args.value("--authorization")
    if not path:
        return None
    decisions = cli._load_decision(path)
    entry = None
    for item in decisions:
        if isinstance(item, dict) and decisions_mod.accepts("prepare_definition", item.get("choice")):
            entry = item
            break
    if entry is None:
        raise DefinitionError("WF_SEMANTIC_DECISION", {
            "reason": "authorization file has no choice=准备定义",
            "choices": [item.get("choice") for item in decisions if isinstance(item, dict)],
            "accepted": list(decisions_mod.domain("prepare_definition")),
        })
    raw = entry.get("scope_paths")
    if not isinstance(raw, list) or not raw or any(not isinstance(item, str) for item in raw):
        raise DefinitionError("WF_SEMANTIC_DECISION", {
            "reason": "authorization must list scope_paths (non-empty string array)",
            "got": raw,
            "exits": [f"用 --authorization-draft 取骨架（scope_paths 预填 {definition_rel}）后请人确认"]})
    from . import paths as paths_mod

    scope_paths = []
    for item in raw:
        try:
            scope_paths.append(paths_mod.normalize(item))
        except paths_mod.InvalidPath as exc:
            raise DefinitionError("WF_PATH_INVALID",
                                  {"reason": f"scope path is not a safe project-relative path: {exc}",
                                   "path": item})
    if definition_rel not in scope_paths:
        raise DefinitionError("WF_SEMANTIC_DECISION", {
            "reason": "authorization scope does not cover this definition",
            "scope_paths": scope_paths, "definition": definition_rel})
    expected = prepare_scope_digest(scope_paths)
    if entry.get("object_digest") != expected:
        raise DefinitionError("WF_SEMANTIC_DECISION", {
            "reason": "authorization scope digest mismatch",
            "recorded": entry.get("object_digest"), "expected": expected,
            "exits": ["按当前 scope_paths 重出决定（--authorization-draft 预填该摘要）",
                      "把 scope_paths 改回已确认的范围"]})
    return {"source": "decision", "by": entry.get("source"), "at": entry.get("at"),
            "subject": entry.get("subject"), "scope_paths": scope_paths,
            "scope_digest": expected}


def _resolve_preparation_authorization(authorization_entries, previous, workflow_id, definition_rel):
    """准备授权**只来自人给出的决定**：同范围重跑复用既有授权，范围变化必须新签。

    在取写权**之前**调用：缺授权是"请求不成立"，不该先占住写权再拒绝。
    """
    previous_authorization = (previous.get("authorization") or {})
    if authorization_entries is not None:
        return authorization_entries
    if (previous_authorization.get("source") == "decision"
            and definition_rel in (previous_authorization.get("scope_paths") or [])):
        return previous_authorization
    raise DefinitionError("WF_SEMANTIC_DECISION", {
        "reason": "准备定义需要人先授予准备范围（--authorization <决定>）",
        "definition": definition_rel,
        "exits": ["由人出具 choice=准备定义 的决定（scope_paths 覆盖该定义路径）后重跑",
                  f"拿不准结构先跑 `definition prepare --id {workflow_id} --authorization-draft`"],
    })


def _retention_drift(root, entries):
    """关闭保留时核对：记录里的路径现在还是不是那个内容（变了就是"离开准备通道期间被改过"）。"""
    import os as os_mod

    drifted = []
    for entry in entries or []:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            continue
        absolute = os.path.join(str(root), entry["path"])
        exists = os_mod.path.isfile(absolute)
        digest = _file_digest(absolute) if exists else None
        if not exists or digest != entry.get("content_digest"):
            drifted.append({"path": entry["path"], "recorded": entry.get("content_digest"),
                            "current": digest, "exists": exists})
    return drifted


def _file_digest(absolute):
    with open(absolute, "rb") as handle:
        return "sha256:" + records.sha256_hex(handle.read())


def retained_preparation_wip(root):
    """未关闭的**准备通道保留草稿**（消费点）：只把"仍占着工作区"的条目算作占用。

    记录里的摘要不是装饰：仍属未提交的条目按摘要核，内容变了标 `stale`（要人重新出处置）；
    已提交或已移走的条目算**已解除**（`cleared`），不再阻挡别的对象取写权——否则人把草稿
    处理掉了，记录却还在挡路，等于逼人删准备记录。
    """
    import os as os_mod

    from . import scope as scope_mod

    directory = os.path.join(str(root), PREPARATIONS_REL)
    if not os.path.isdir(directory):
        return []
    dirty = set(scope_mod.uncommitted_paths(root))
    found = []
    for name in sorted(os_mod.listdir(directory)):
        if not name.endswith(".json"):
            continue
        record = records.load_json(os.path.join(directory, name), {}) or {}
        entries = record.get("retained_wip") or []
        if not isinstance(entries, list) or not entries:
            continue
        blocking, stale, cleared = [], [], []
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
                continue
            absolute = os.path.join(str(root), entry["path"])
            exists = os_mod.path.isfile(absolute)
            digest = _file_digest(absolute) if exists else None
            item = {"path": entry["path"], "recorded": entry.get("content_digest"),
                    "current": digest, "exists": exists}
            if entry["path"] not in dirty:
                cleared.append(item)          # 已提交或已移走：保留条件已落实
                continue
            blocking.append(item)
            if not exists or digest != entry.get("content_digest"):
                stale.append(item)
        if not blocking:
            continue
        found.append({"preparation": record.get("id") or name[:-5],
                      "record": f"{PREPARATIONS_REL}/{name}",
                      "paths": [item["path"] for item in blocking],
                      "verified": [item for item in blocking if item not in stale],
                      "stale": stale, "cleared": cleared,
                      "risk": [entry.get("risk") for entry in entries
                               if isinstance(entry, dict) and entry.get("risk")],
                      "pending": [text for entry in entries if isinstance(entry, dict)
                                  for text in (entry.get("pending") or [])]})
    return found


def _staged_paths(root):
    """索引里已暂存的路径（`git diff --cached --name-only`）；无 git 时为空。"""
    from . import scope as scope_mod

    if not scope_mod.has_git(root):
        return set()
    code, out = scope_mod.git(root, "diff", "--cached", "--name-only", "-z")
    if code != 0:
        return set()
    return {item for item in out.split("\0") if item}


def _end_preparation(ctx, args, workflow_id, definition_rel, record, holder, mine, held_scope,
                     previous):
    """`definition prepare --end [--disposition <文件>]`：定义定稿/暂停后释放准备写权。

    设计稿 §5.7/§1.3 给两条合法出路，本入口都认，但都按**事实**核：
    - 未提交路径已处置（提交或移走）——事实成立即可结束；
    - **保留**未提交的定义草稿：仅限本次授权准备范围，且必须在 `retained_wip` 里记人选择、
      准备范围、具体路径、存在/删除、内容哈希、暂存事实、未验证风险与待处置项
      （缺风险或待处置项就不是"明确处置"，只是自述）。
    顺序：**先落记录、后释放写权**，并让"已结束但写权仍在"的分支自愈补释放。两个方向都能
    恢复：写完记录中断 → 重入补释放（幂等分支）；释放完中断 → 重入补记录（事实仍成立）。
    反过来（先释放后落记录）在中断时会把保留事实丢掉，草稿就成了无交接记录的无主内容。
    """
    import os as os_mod

    from . import cli as cli_mod, scope as scope_mod

    path = preparation_path(ctx.root, workflow_id)

    def _release_if_mine():
        if mine and held_scope.get("kind") == "preparation" and held_scope.get("id") == workflow_id:
            cli_mod._release_writer_locked(ctx, holder)
            return True
        return False

    if not isinstance(previous, dict) or not previous:
        raise DefinitionError("WF_SEMANTIC_DECISION",
                              {"reason": "no preparation record to end", "workflow_id": workflow_id,
                               "exits": ["先跑 definition prepare --id <id> --authorization <决定>"]})
    if previous.get("ended_at"):
        # 自愈：上一次可能写完 ended_at 却在释放前中断
        healed = _release_if_mine()
        return codes.result("WF_OK", object={"id": workflow_id},
                            position_=codes.position(scope="maintenance"),
                            next_=("准备已结束（幂等）；本次补做了写权释放"
                                   if healed else "准备已结束（幂等）；下一步 run create 或重新 prepare"),
                            facts={"workflow_id": workflow_id, "ended_at": previous["ended_at"],
                                   "released": healed,
                                   "held_scope": (None if healed or not mine else held_scope)})

    scope_paths = list(previous.get("scope_paths") or [definition_rel])
    dirty = [item for item in scope_mod.uncommitted_paths(ctx.root) if item in scope_paths]
    staged = _staged_paths(ctx.root)
    disposition_path = args.value("--disposition")
    declared = []
    if disposition_path:
        loaded = records.load_json(disposition_path)
        entries = (loaded or {}).get("changes") if isinstance(loaded, dict) else loaded
        for item in entries or []:
            if isinstance(item, dict) and isinstance(item.get("object"), str):
                declared.append({"path": item["object"], "action": item.get("action"),
                                 "risk": item.get("risk"), "pending": item.get("pending")})
    by_path = {item["path"]: item for item in declared}

    problems, mismatched, retained = [], [], []
    for item in dirty:
        entry = by_path.get(item)
        if entry is None:
            problems.append({"path": item, "reason": "no disposition entry"})
            continue
        if entry.get("action") == "retain":
            pending = [text for text in (entry.get("pending") or []) if isinstance(text, str) and text.strip()]
            if not isinstance(entry.get("risk"), str) or not entry["risk"].strip() or not pending:
                problems.append({"path": item,
                                 "reason": "retain requires risk and pending（保留未验证风险与待处置项）"})
                continue
            absolute = os.path.join(ctx.root, item)
            exists = os_mod.path.isfile(absolute)
            retained.append({
                "path": item,
                "preparation_scope": scope_paths,
                "exists": exists,
                "content_digest": _file_digest(absolute) if exists else None,
                "staged": item in staged,
                "uncommitted": item in dirty,
                "risk": entry["risk"].strip(),
                "pending": pending,
                "recorded_at": records.now_str(),
            })
        elif entry.get("action") in ("commit", "delete"):
            mismatched.append(dict(entry, fact="path still uncommitted; commit/delete did not happen"))
        else:
            mismatched.append(dict(entry, fact="action must be commit|delete|retain"))
    unresolved = [item for item in dirty if item not in by_path]
    # 声明了但工作区里根本没这条未提交路径：声明与事实不符，不能静默丢弃
    for item in declared:
        if item["path"] in dirty:
            continue
        if item.get("action") == "retain":
            mismatched.append(dict(item, fact="path is not uncommitted at end（保留的是已提交/已移走的内容）"))
        elif item.get("action") in ("commit", "delete"):
            continue      # 已落实：无需处置，声明与事实一致
        else:
            mismatched.append(dict(item, fact="action must be commit|delete|retain"))
    if problems or mismatched or unresolved:
        raise DefinitionError("WF_WORKSPACE_UNRESOLVED",
                              {"reason": "preparation scope still has un-disposed edits",
                               "uncommitted": dirty,
                               "undisposed": [entry["path"] for entry in problems] or unresolved,
                               "mismatched": mismatched, "declared": declared, "staged": sorted(staged),
                               "exits": ["由人提交该定义或移走它，然后重跑 definition prepare --end",
                                         "要继续起草就保留：写一份 disposition（action=retain + "
                                         "risk + pending）记录保留条件后重跑",
                                         "不要结束准备也可以：写权继续由本会话持有"]})

    # 先释放、后落记录（见 docstring 的崩溃顺序）
    released = _release_if_mine()
    cross_scope = None if released or not mine else held_scope
    ended = dict(records.load_json(path) or dict(previous),
                 ended_at=records.now_str(), updated_at=records.now_str(),
                 # 只留**事实**：处置声明、结束时仍未提交的路径、真正保留的条目。
                 # 不写 `verified: true` 这类恒真自报——它没有消费点，等于给记录加装饰。
                 end_disposition={"declared": declared, "uncommitted_at_end": dirty},
                 retained_wip=retained)
    records.write_json(path, ended)
    return codes.result("WF_OK", object={"id": workflow_id},
                        position_=codes.position(scope="maintenance"),
                        next_=("准备已结束：写权已释放" if released or not mine
                               else "准备已结束，但本会话持有的是其他对象的写权（未释放）"),
                        facts={"workflow_id": workflow_id, "ended_at": ended["ended_at"],
                               "released": released, "held_scope": cross_scope,
                               "retained": retained,
                               "exits": (["本会话还持着别的准备写权：结束那一份定义，或用新会话继续"]
                                         if cross_scope else [])})


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
    definition_rel = f"{USER_WORKFLOWS_REL}/{workflow_id}.md"
    text, path = _definition_text(ctx.root, workflow_id)
    if args.flag("--authorization-draft"):
        scope_paths = [definition_rel]
        skeleton = {"source": "TODO human:<来源>（例如 human terminal）",
                    "at": records.now_str(),
                    "subject": f"准备定义 {workflow_id}",
                    "object_digest": prepare_scope_digest(scope_paths),
                    "choice": "准备定义",
                    "scope_paths": scope_paths,
                    "reason": "TODO（人填写：为什么允许准备这份定义、范围是什么）"}
        return codes.result("WF_OK", object={"id": workflow_id},
                            position_=codes.position(scope="maintenance"),
                            next_="把 TODO 换成人的答复后，用 definition prepare --authorization <文件> 重跑",
                            facts={"draft": skeleton, "definition": definition_rel,
                                   "note": "草稿只读；object_digest 随 scope_paths 变化，改范围须重出草稿"})
    authorization_entries = _prepare_authorization(ctx, args, workflow_id, definition_rel)
    existing_binding = session_mod.load_binding(ctx.root, key)
    if existing_binding:
        raise DefinitionError("WF_BINDING_MISMATCH", {
            "reason": "准备通道只给未绑定会话；本会话已绑定对象",
            "bound": existing_binding.get("object"),
            "exits": ["已绑定会话要改定义：走其已批准任务范围（回 Plan 重新批准）",
                      "确需准备另一份定义：在新会话里选择准备通道"],
        })
    with lock.acquire(ctx.root, holder_hint=f"definition prepare {workflow_id}"):
        record = writer_mod.load(ctx.root) or {}
        holder = record.get("holder") or {}
        held_scope = (holder.get("scope") or {}).get("object") or {}
        mine = record.get("state") == "held" and holder.get("id") == key
        state = record.get("state")
        if not mine and state != "idle":
            # 准备不例外于写权：held 是别人在写；recovering 是交接中间态（双方都没写权）。
            # 两种都不能写准备记录——否则入口会回 WF_OK，让 AI 误以为已取得准备写权
            # （六轮审查 b-4：recovering 下确实跳过取权分支照写了记录）。
            raise DefinitionError("WF_WRITER_BUSY",
                                  {"reason": "writer is not available for preparation",
                                   "state": state, "holder": holder,
                                   "exits": ["等对方释放或走已确认的交接/恢复出口",
                                             "交接中断（recovering）时先按恢复流程确认写者归属"]},
                                  next_="写权未就绪：先让写权回到空闲，再准备定义")

        previous = records.load_json(preparation_path(ctx.root, workflow_id), {}) or {}
        if args.flag("--end"):
            # 准备收口（设计稿 §5.7）：事实（未提交路径）先核，再按作用域释放准备写权。
            return _end_preparation(ctx, args, workflow_id, definition_rel, record, holder, mine,
                                    held_scope, previous)

        # 授权先定，再动写权：缺授权时绝不能先取得写权再拒绝——那会把写权留在会话手里，
        # 其他会话被"无主的准备写权"挡住，而准备记录根本没建立（四轮审查 a-P1）。
        authorization = _resolve_preparation_authorization(
            authorization_entries, previous, workflow_id, definition_rel)

        # 准备通道持有的是**限定到本次定义路径**的准备写权（`scope.object=preparation`）：
        # 这样准备期间的编辑仍是"单写者"，其他会话拿不到写权（此前只拒绝他人持权、自己不持权，
        # 等于准备期的编辑与其他写入并发——三轮审查 a-P1）。
        if mine:
            if held_scope.get("kind") != "preparation" or held_scope.get("id") != workflow_id:
                raise DefinitionError("WF_WRITER_BUSY", {
                    "reason": "本会话持有其他对象的写权，不能同时准备定义",
                    "scope": held_scope,
                    "exits": ["先结束该对象的收工/归档（写权随之释放）", "或在新会话里走准备通道"]})
        elif record.get("state") == "idle":
            owner_scope = {"object": {"kind": "preparation", "id": workflow_id},
                           "preparation": {"id": workflow_id,
                                           "scope_paths": [definition_rel]}}
            record = writer_mod.acquire(record, kind="session", ident=key, scope=owner_scope,
                                        checkpoint={"step": "definition-prepare",
                                                    "at": records.now_str()})
            writer_mod.save(ctx.root, record)
            holder = record.get("holder") or {}
        if text is None:
            validation = {"ok": False, "checked_at": records.now_str(),
                          "problems": [_problem(0, "definition file missing",
                                                expected=f"{USER_WORKFLOWS_REL}/{workflow_id}.md")]}
            digest = None
        else:
            doc, problems, _text, _path = load_definition(ctx.root, workflow_id)
            if doc is not None:
                problems = validate_definition(doc, ctx.root, workflow_id=workflow_id)
            validation = {"ok": not problems, "checked_at": records.now_str(),
                          "problems": problems}
            digest = "sha256:" + records.sha256_hex(text.encode("utf-8"))
        # 机制稿 §5.1：具名动作先在**主记录**登记意图——准备动作的主记录是准备记录本身。
        # 未通过校验时同样登记（草稿也是准备动作的结果），steps 按事实标 applied 与否。
        action = actions_mod.new_action(
            "definition.prepare",
            {"kind": "session", "id": key,
             "scope": {"object": {"kind": "preparation", "id": workflow_id},
                       "preparation": None}},
            int(previous.get("revision", 0)),
            {"workflow_id": workflow_id,
             "definition": f"{USER_WORKFLOWS_REL}/{workflow_id}.md",
             "digest": digest, "problems": len(validation.get("problems") or [])},
            steps=["static_check", "write_preparation"],
            head_before=actions_mod.head_of(ctx.root),
            targets=[{"kind": "preparation", "id": workflow_id}])
        preparation = {
            "schema_version": 1,
            "id": workflow_id,
            "session_key": key,
            "scope_paths": list(authorization.get("scope_paths") or [definition_rel]),
            # 重新准备＝重新取得写权、继续占有这份草稿：上次的保留在这里**关闭**并留下审计
            # （含当时摘要与本次进入时的实际摘要差异），而不是原样复制成一条永不过期的声明。
            "retained_wip": None,
            "retention_closed": ({"at": records.now_str(),
                                  "previous": previous.get("retained_wip"),
                                  "drifted": _retention_drift(ctx.root,
                                                              previous.get("retained_wip"))}
                                 if (isinstance(previous, dict)
                                     and previous.get("retained_wip")) else
                                 previous.get("retention_closed")),
            "authorization": authorization,
            "definition_refs": ([{"path": f"{USER_WORKFLOWS_REL}/{workflow_id}.md",
                                  "digest": digest}] if digest else []),
            "validation": validation,
            "progress": {"attempts": int((previous.get("progress") or {}).get("attempts") or 0) + 1,
                         "last_ok": validation["ok"]},
            "end_disposition": previous.get("end_disposition"),
            "ended_at": None,
            "updated_at": records.now_str(),
            "action": _prepare_action_done(action, validation["ok"]),
        }
        records.write_json(preparation_path(ctx.root, workflow_id), preparation)
    facts = {"workflow_id": workflow_id, "preparation": _rel(ctx.root, preparation_path(ctx.root, workflow_id)),
             "validation": validation, "progress": preparation["progress"],
             # 上次结束保留的草稿在这里**关闭**；离开准备通道期间被改过的路径在 drifted 里如实列出
             "retention_closed": ((preparation.get("retention_closed") or {}).get("drifted") or None),
             "action": {"id": preparation["action"]["id"],
                        "state": preparation["action"]["state"]}}
    if not validation["ok"]:
        raise DefinitionError("WF_DEFINITION_INVALID",
                              dict(facts, reason="preparation kept as draft; static validation failed"),
                              next_="按 validation.problems 修正后重跑 validate/prepare")
    return codes.result("WF_OK", object={"id": workflow_id},
                        position_=codes.position(scope="maintenance"),
                        next_="准备代次已固定：下一步 run create",
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
        # 逐步骤表态（机制稿 §7.2）：未出现的步骤不推断为 applicable——
        # 「人确认它适用」与「人没看它」在事后追责上不是一回事。
        missing = sorted(declared - set(steps))
        if missing:
            problems.append({"reason": "steps must declare every step of the definition",
                             "missing": missing})
        # 略过资格由定义给：必需步骤（skip=null）不能在这一层被声明成 skipped，
        # 否则 advance/finish 都会把创建输入当成"人已批准略过"（必需步骤被绕过）。
        by_id = {step.get("id"): step for step in doc.get("steps") or []
                 if isinstance(step, dict) and step.get("id")}
        for step_id, value in steps.items():
            if value == "skipped" and step_id in by_id and not step_skippable(by_id[step_id]):
                problems.append({"reason": "required step cannot be declared skipped"
                                           "（定义里该步骤 skip=null）",
                                 "step": step_id})
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


CREATION_FIELDS_FOR_DIGEST = ("definition_id", "definition_digest", "inputs", "steps", "expansion")


def creation_digest(creation):
    """创建输入的规范身份（唯一定义）：人签授权里的 `object_digest` 就是它。

    覆盖 `definition_id`/`definition_digest`/`inputs`/`steps`/`expansion` 五域——授权之后
    任何一域被改（换定义版本、改输入、改某步适用性）都不再匹配。
    """
    payload = {key: (creation or {}).get(key) for key in CREATION_FIELDS_FOR_DIGEST}
    return records.H("wf-creation-v1", payload)


def _creation_decision(authorization, creation):
    """实例记录里的 `creation_decision`：只记**可核的授权事实**，不自报 `source=human`。"""
    if not isinstance(authorization, dict) or authorization.get("source") != "decision":
        # 不该发生：`create` 已在入口拒绝无授权的创建；这里兜住"续做意图里丢了授权"的旧记录
        raise DefinitionError("WF_SEMANTIC_DECISION",
                              {"reason": "run.create intent has no human authorization",
                               "creation": (creation or {}).get("definition_id"),
                               "exits": ["由人重新出具 choice=创建实例 的决定后重跑 run create"]})
    return {"source": "decision",
            "by": authorization.get("by"),
            "at": authorization.get("at"),
            "subject": authorization.get("subject"),
            "creation_digest": authorization.get("creation_digest"),
            "steps": (creation or {}).get("steps") or {},
            "expansion": (creation or {}).get("expansion")}


def _creation_authorization(ctx, args, creation):
    """`run create --authorization <决定>` 的核验（设计稿 §5.7「实例创建授权」）。

    此前创建记录的 `creation_decision.source` 一律写 `human`——那是自报值，机制没有消费任何
    人的输入（六轮复核 A3 / 外部报告 b-P1）。现在必须交一份人给出的决定：取值在
    `create_instance` 域内，且 `object_digest` 等于**按创建文件当前内容**重算的摘要。
    """
    from . import cli, decisions as decisions_mod

    path = args.value("--authorization")
    if not path:
        return None
    entries = cli._load_decision(path)
    entry = next((item for item in entries
                  if isinstance(item, dict)
                  and decisions_mod.accepts("create_instance", item.get("choice"))), None)
    if entry is None:
        raise DefinitionError("WF_SEMANTIC_DECISION", {
            "reason": "authorization file has no choice=创建实例",
            "choices": [item.get("choice") for item in entries if isinstance(item, dict)],
            "accepted": list(decisions_mod.domain("create_instance")),
        })
    expected = creation_digest(creation)
    if entry.get("object_digest") != expected:
        raise DefinitionError("WF_SEMANTIC_DECISION", {
            "reason": "authorization does not bind the current creation input",
            "recorded": entry.get("object_digest"), "expected": expected,
            "exits": ["按当前 creation 文件重出决定（run create --authorization-draft --creation <文件> 预填摘要）",
                      "把 creation 改回已确认的内容"]})
    return {"source": "decision", "by": entry.get("source"), "at": entry.get("at"),
            "subject": entry.get("subject"), "creation_digest": expected}


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
    # 已结束（`--end`）的准备记录仍可用于创建：结束只表示"准备写权释放 + 未提交编辑已处置"，
    # 定义内容由 `validation`/`digest`（创建时按当前字节重核）保证，不因结束而失效。
    if definition_rel not in (record.get("scope_paths") or []):
        problems.append({"reason": "preparation scope does not cover this definition",
                         "scope_paths": record.get("scope_paths")})
    authorization = record.get("authorization") or {}
    if authorization.get("source") != "decision":
        problems.append({"reason": "preparation record has no human authorization",
                         "authorization": authorization.get("source"),
                         "exit": f"由人出具 choice=准备定义 的决定后重跑 definition prepare --id {workflow_id}"})
    elif definition_rel not in (authorization.get("scope_paths") or []):
        problems.append({"reason": "preparation authorization does not cover this definition",
                         "authorization_scope": authorization.get("scope_paths")})
    elif authorization.get("scope_digest") != prepare_scope_digest(authorization.get("scope_paths")):
        # 记录里的范围被改过（或旧记录缺摘要）：摘要与范围必须自洽，消费点重算一遍
        problems.append({"reason": "preparation authorization scope digest mismatch",
                         "recorded": authorization.get("scope_digest"),
                         "expected": prepare_scope_digest(authorization.get("scope_paths")),
                         "exit": "由人重新出具准备范围授权后重跑 definition prepare"})
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


def fixed_snapshot(ctx, run):
    """实例的**固定快照**（唯一定义）：存在性 + 摘要复核 + 解析一次，返回 `(doc, bytes)`。

    固定快照在实例生命周期内不可变（摘要随记录保存），所以"单读"与"重读"语义等价；
    但**读取时点**不是等价的：`run terminate` 曾在逐任务处置之后才读快照，快照缺失就留下
    半写状态。所有消费方（advance/finish/terminate/preview）都在业务写入之前调这里。
    """
    run_id = (run or {}).get("id")
    definition = (run or {}).get("definition") or {}
    snapshot_rel = definition.get("snapshot_path")
    snapshot_abs = join(ctx.root, snapshot_rel or "")
    if not snapshot_rel or not os.path.isfile(snapshot_abs):
        raise DefinitionError("WF_HISTORY_UNRESOLVED",
                              {"reason": "definition snapshot missing", "path": snapshot_rel,
                               "run": run_id})
    with open(snapshot_abs, "rb") as handle:
        snapshot_bytes = handle.read()
    digest = "sha256:" + records.sha256_hex(snapshot_bytes)
    if digest != definition.get("digest"):
        raise DefinitionError("WF_HISTORY_UNRESOLVED",
                              {"reason": "snapshot digest mismatch",
                               "recorded": definition.get("digest"), "current": digest,
                               "run": run_id})
    doc, problems = parse_definition(snapshot_bytes.decode("utf-8"))
    if doc is None or problems:
        raise DefinitionError("WF_DEFINITION_INVALID",
                              {"reason": "fixed snapshot is not statically valid",
                               "problems": problems, "run": run_id})
    return doc, snapshot_bytes


def create(ctx, args):
    """`run create --creation <path>`：建立实例、固定定义快照、首次绑定（机制稿 §7.2）。

    writer 上的**单一 `run.create` 父动作**承载：意图与写权授予同一次写入，中断按原意图续做
    （目标一次固定，不从当前请求重建）。实例创建只取得「规划权限」——不代批准业务、不建任务。
    """
    from . import actions as actions_mod, cli, codes as codes_mod, lock, session as session_mod, writer as writer_mod

    if args.flag("--creation-draft"):
        # 创建输入的只读骨架（与 `definition validate` 同一事实源）：摘要与步骤清单由机制预填，
        # 人只确认输入值与步骤适用性（设计稿 §5.7「人明确选择确切版本/哈希、输入与展开规则」）。
        workflow_id = args.value("--id")
        if not workflow_id or not ID_RE.match(workflow_id):
            raise DefinitionError("WF_PATH_INVALID",
                                  {"reason": "--creation-draft requires --id <workflow-id>"})
        doc, problems, text, path = load_definition(ctx.root, workflow_id)
        if text is None:
            raise DefinitionError("WF_PATH_INVALID",
                                  {"reason": "definition file missing",
                                   "expected": f"{USER_WORKFLOWS_REL}/{workflow_id}.md"})
        if doc is not None:
            problems = validate_definition(doc, ctx.root, workflow_id=workflow_id)
        digest = "sha256:" + records.sha256_hex(text.encode("utf-8"))
        steps = {step.get("id"): "applicable" for step in doc.get("steps") or []
                 if isinstance(step, dict) and step.get("id")} if doc else {}
        skeleton = {"definition_id": workflow_id, "definition_digest": digest,
                    "inputs": {name: "TODO" for name in ((doc or {}).get("inputs") or {})},
                    "steps": steps}
        return codes_mod.result(
            "WF_OK", object={"id": workflow_id},
            position_=codes_mod.position(scope="maintenance"),
            next_=("确认输入值与每个步骤的适用性（skipped 须同步写 creation）后，"
                   "人确认创建：run create --creation <文件>"
                   if not problems else "先按 validation.problems 修定义，再取创建骨架"),
            facts={"draft": skeleton, "definition": _rel(ctx.root, path), "digest": digest,
                   "validation": {"ok": not problems, "problems": problems},
                   "note": "草稿只读；摘要随定义内容变化，改定义后须重出草稿"})

    if args.flag("--authorization-draft"):
        # 创建授权骨架：`object_digest` 按**当前 creation 文件**预填，人只确认/写 quote 与理由。
        creation = _creation_file(args)
        skeleton = {"source": "TODO human:<来源>（例如 human terminal）",
                    "at": records.now_str(),
                    "subject": f"创建实例 {(creation or {}).get('definition_id')}",
                    "object_digest": creation_digest(creation),
                    "choice": "创建实例",
                    "reason": "TODO（人填写：为什么按这些输入与步骤适用性创建实例）"}
        return codes_mod.result(
            "WF_OK", object={"id": (creation or {}).get("definition_id")},
            position_=codes_mod.position(scope="maintenance"),
            next_="把 TODO 换成人的答复后，用 run create --creation <文件> --authorization <该文件> 重跑",
            facts={"draft": skeleton,
                   "note": "草稿只读；creation 的版本/输入/步骤任一变动都会让摘要失配，须重出草稿"})

    creation = _creation_file(args)
    session = ctx.session()
    key = ctx.key()
    code, profile_facts = session_mod.check_platforms(ctx.platforms(), session)
    if code:
        raise cli.CliError(code, profile_facts, next_="install（已装齐全部平台）后重试")
    if not isinstance(creation, dict):
        raise DefinitionError("WF_SEMANTIC_DECISION",
                              {"problems": creation_problems(creation)})
    workflow_id = creation.get("definition_id")
    doc, problems, text, definition_abs = load_definition(ctx.root, workflow_id or "")
    if text is None:
        raise DefinitionError("WF_PATH_INVALID",
                              {"reason": "definition file missing",
                               "expected": f"{USER_WORKFLOWS_REL}/{workflow_id}.md"})
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
    authorization = _creation_authorization(ctx, args, creation)
    if authorization is None:
        raise DefinitionError("WF_SEMANTIC_DECISION", {
            "reason": "实例创建需要人确认确切定义版本、输入与步骤适用性（--authorization <决定>）",
            "definition": definition_rel, "creation_digest": creation_digest(creation),
            "exits": ["由人出具 choice=创建实例 的决定（object_digest 取创建输入摘要）后重跑",
                      "拿不准结构先跑 `run create --authorization-draft --creation <文件>` 取骨架"]})
    problems = _preparation_problems(ctx.root, workflow_id, key, definition_rel)
    if problems:
        raise DefinitionError("WF_SEMANTIC_DECISION",
                              {"reason": "preparation scope does not authorise this creation",
                               "problems": problems},
                              next_=f"先跑 definition prepare --id {workflow_id}（校验通过后重试）")

    with lock.acquire(ctx.root, holder_hint="run create"):
        record = ctx.writer() or {}
        holder = record.get("holder") or {}
        scoped = (holder.get("scope") or {}).get("object") or {}
        if (record.get("state") == "held" and holder.get("id") == key
                and scoped.get("kind") == "preparation" and scoped.get("id") == workflow_id):
            # 创建实例是准备的天然收口：释放限定准备写权，随后由本入口取得实例写权。
            # （显式 `definition prepare --end` 仍用于"只备定义、不建实例"的路径。）
            from . import cli as _cli_mod

            _cli_mod._release_writer_locked(ctx, holder)
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
        for candidate in (join(ctx.root, record_rel), join(ctx.root, f"{RUNS_REL}/{run_id}")):
            if os.path.exists(candidate):
                raise cli.CliError("WF_TARGET_COLLISION", {"path": _rel(ctx.root, candidate)})
        instance_id = session.get("instance_id") or session_mod.new_instance_id()
        inputs = {"run": run_id, "definition": definition_rel, "digest": digest,
                  "inputs_digest": records.plain_digest(creation.get("inputs") or {}),
                  # 意图里固定完整创建输入与**人给出的创建授权**：续做时不必再读文件
                  "creation": creation, "authorization": authorization}
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
        updated = dict(updated)
        updated["action"] = action
        writer_mod.save(ctx.root, updated)
        return _advance_run_create(ctx, key, session, updated, action, text, creation,
                                   workflow_id, digest, instance_id, authorization)


def _advance_run_create(ctx, key, session, record, action, text, creation,
                        workflow_id, digest, instance_id, authorization=None):
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
        "creation_decision": _creation_decision(authorization, creation),
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
    session_mod.update_runtime(
        ctx.root, key,
        binding_digest=records.plain_digest(binding),
        instance_id=instance_id,
        object={"kind": "run", "id": run_id},
        current_task=None,
        cursor=None,
    )
    # ③ 步骤后置逐个核（手工标 done 不能代替产物）
    action = dict(action)
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
        next_="下一步 run advance 推进首个适用步骤",
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
    creation = (action.get("inputs") or {}).get("creation")
    if not isinstance(creation, dict):
        # 旧动作（本批之前落盘的意图）没有固定 creation 本体：只能按最小事实续做，
        # 并把这一点如实报告（不假装恢复到了完整输入）
        creation = {"inputs": {}, "steps": {}, "definition_id": workflow_id,
                    "degraded": True}
    # 续做分支：授权取证在原始意图里（`inputs.creation` 是固定输入，授权另存 inputs.authorization）
    resumed_authorization = (action.get("inputs") or {}).get("authorization")
    return _advance_run_create(ctx, key, session, record, action, text, creation,
                               workflow_id, digest, targets.get("instance"),
                               resumed_authorization)


ADVANCE_STEPS = ("resolve_step", "create_or_reuse_task", "record_cursor")


def _step_outputs(doc, step_id, instance_inputs, root=None):
    """步骤产物的引用（机制稿 §7.3：`step_results` 保存本次消费摘要）。

    字面路径直接用；`{input: name}` 按实例输入解析；解不出的保留声明并标 `resolved: false`
    ——**不猜路径**（猜出来的路径会让后续"复用"判断建立在假事实上）。
    """
    for step in _ordered_steps(doc):
        if step.get("id") != step_id:
            continue
        found = []
        for output in step.get("outputs") or []:
            if not isinstance(output, dict):
                continue
            declared = output.get("path")
            entry = {"id": output.get("id"), "kind": output.get("kind")}
            if isinstance(declared, str):
                entry.update({"path": declared, "resolved": True})
            elif isinstance(declared, dict) and declared.get("input"):
                value = instance_inputs.get(declared["input"])
                if isinstance(value, str):
                    entry.update({"path": value, "resolved": True,
                                  "from_input": declared["input"]})
                else:
                    entry.update({"path": declared, "resolved": False,
                                  "from_input": declared["input"]})
            else:
                entry.update({"path": None, "resolved": False})
            # `resolved` 只表示"路径能解出来"，不等于产物存在：两者分开记，
            # 下游据此判断"声明的产物是否真的落地"（六轮审查 b-2）。
            path = entry.get("path") if entry.get("resolved") and isinstance(entry.get("path"), str) else None
            absolute = join(str(root), path) if (path and root) else None
            found.append(dict(entry, exists=bool(absolute) and os.path.isfile(absolute)))
        return found
    return []


def step_skippable(step):
    """该步骤**是否允许**略过（唯一判据）：静态校验保证 `required=false ⇔ skip 声明存在`，
    所以 `skip` 是对象即可略；必需步骤的 `skip` 必然是 null。

    创建校验、推进与收尾都消费这一个函数——把"可略"当纪律判断，会让 `creation.steps` 里
    一句 `skipped` 变成绕过必需步骤的许可。
    """
    return isinstance((step or {}).get("skip"), dict)


def _applicability(creation, doc):
    """步骤适用性：`creation.steps` 的声明优先；未声明的按定义默认（required 即适用）。"""
    declared = (creation or {}).get("steps") or {}
    result = {}
    for step in doc.get("steps") or []:
        if not isinstance(step, dict) or not step.get("id"):
            continue
        step_id = step["id"]
        if step_id in declared:
            result[step_id] = declared[step_id]
        else:
            # 未在 creation 里声明的步骤：`required: false` 只说明"可略"，**不等于**已声明略过；
            # 略过必须由人在创建时逐步骤表态（`creation_problems` 要求全覆盖），这里只给默认适用。
            result[step_id] = "applicable"
    return result


def _ordered_steps(doc):
    return [step for step in doc.get("steps") or [] if isinstance(step, dict) and step.get("id")]


def _step_by_id(doc, step_id):
    """按 id 取步骤（唯一定义：只有 `_ordered_steps` 里的条目才是可执行步骤）。"""
    for step in _ordered_steps(doc):
        if step.get("id") == step_id:
            return step
    return None


def _next_step(doc, step_id, step_results=None):
    """下一个**尚无结果**的步骤；到头返回 None。

    跳过 `step_results` 里已记结果的步骤（含人判答复与 `skipped`），这样「返工返回定位后
    重入」与「重入同一条命令」都不会把已经结案的步骤再走一遍。游标不在定义里时报
    `WF_HISTORY_UNRESOLVED`——那是记录损坏，不按"从头开始"放行。
    """
    ordered = _ordered_steps(doc)
    ids = [step["id"] for step in ordered]
    if step_id and step_id not in ids:
        raise DefinitionError("WF_HISTORY_UNRESOLVED",
                              {"reason": "cursor step is not declared by the snapshot",
                               "step": step_id})
    start = 0 if not step_id else ids.index(step_id) + 1
    for step in ordered[start:]:
        if (step_results or {}).get(step["id"]):
            continue
        return step
    return None


def _require_upstream_outputs(ctx, doc, step, step_results):
    """`from: step` 的引用必须落在**已落地**的产物上（机制稿 §7.3）。

    只核事实：引用声明本身在静态校验里已核过（更早步骤、已声明产物）；这里核上游结果存在、
    路径解出、文件真的在。缺任何一项就不建下游任务——此前下游照常创建，
    AI 拿到的是"可以继续"的假信号（六轮审查 b-2）。
    """
    missing = []
    for entry in step.get("inputs") or []:
        if not isinstance(entry, dict) or entry.get("from") != "step":
            continue
        source, output_id = entry.get("step"), entry.get("output")
        upstream = step_results.get(source) or {}
        outputs = upstream.get("outputs") or []
        found = next((item for item in outputs
                      if isinstance(item, dict) and item.get("id") == output_id), None)
        if upstream.get("kind") != "satisfied":
            missing.append({"input": entry.get("id"), "step": source, "output": output_id,
                            "reason": "upstream step has no satisfied result",
                            "kind": upstream.get("kind")})
        elif found is None:
            missing.append({"input": entry.get("id"), "step": source, "output": output_id,
                            "reason": "upstream result does not list this output",
                            "declared": [item.get("id") for item in outputs
                                         if isinstance(item, dict)]})
        elif not found.get("resolved") or not found.get("exists"):
            missing.append({"input": entry.get("id"), "step": source, "output": output_id,
                            "path": found.get("path"), "resolved": found.get("resolved"),
                            "exists": found.get("exists"),
                            "reason": "declared artifact is missing on disk"})
    if missing:
        raise DefinitionError("WF_DEPENDENCY_UNMET",
                              {"reason": "upstream artifacts required by this step are missing",
                               "step": step.get("id"), "missing": missing,
                               "exits": ["回到上游步骤产出该产物（或改定义里的引用）",
                                         "确要跳过该步骤：改定义声明 skip 后由人重新确认创建输入"]},
                              next_="下游需要上游产物：先让上游真正产出，再推进本步骤")


def _previous_task_step(doc, step_id, applicability=None, step_results=None):
    """上一个**未略过**的 task 步骤（机制稿 §7.3：顺序前置只直接引用它；human 步骤不生成任务边）。

    「未略过」有两个来源：创建时声明 `skipped`、以及实例里已记 `skipped` 的结果。
    漏掉这层过滤会让"前一任务步骤被略过"变成致命错误（`WF_DEPENDENCY_UNMET` 找不到任务），
    而机制要求的是**跳过它、直接引用更前面那个未略过的任务步骤**。
    """
    ordered = _ordered_steps(doc)
    previous = None
    for step in ordered:
        if step.get("id") == step_id:
            return previous
        if step.get("type") != "task":
            continue
        declared = (applicability or {}).get(step["id"], "applicable")
        recorded = ((step_results or {}).get(step["id"]) or {}).get("kind")
        if declared == "skipped" or recorded == "skipped":
            continue
        previous = step
    return previous


def _return_from_rework(ctx, run, sequence, cursor, task_map):
    """游标停在受控返工 R 上时的处置（机制稿 §6.2、§7.3）。

    规则：R 未归档 → 报告等待（推进不动）；R 已归档但 T 仍挂起 → 报告等待复评；
    R 已归档且 T 已复评（挂起已清）→ 把游标按 `resume_task` 返回 T 并报告，之后正常推进。
    返回 None 表示游标不在 R 上，调用方继续常规推进。
    """
    from . import actions as actions_mod, cli, lock, tasks as tasks_mod, writer as writer_mod

    task_id = (cursor or {}).get("task_id")
    if not task_id:
        return None
    entry = next((item for item in sequence or []
                  if isinstance(item, dict) and item.get("task_id") == task_id), None)
    if entry is None:
        return None                      # 不是受控返工作务，按平常任务处理
    run_id = run.get("id")
    step_id = entry.get("step_id") or (cursor or {}).get("step_id")
    resume_task = entry.get("resume_task")
    rework = tasks_mod.load_task(ctx.root, task_id)
    if not isinstance(rework, dict):
        raise DefinitionError("WF_HISTORY_UNRESOLVED",
                              {"reason": "controlled rework record missing", "task": task_id})
    if rework.get("status") != "archived":
        return codes.result(
            "WF_OK", object={"id": run_id},
            position_=codes.position(scope="run", step_id=step_id),
            next_="游标在受控返工 R 上：先完成 R（独立批准/开工/检查/归档）并 task-reassess，再回来推进",
            facts={"run": run_id, "controlled_rework": task_id, "resume_task": resume_task,
                   "step": step_id, "rework_status": rework.get("status"),
                   "note": "R 的归档不算原定义步骤完成（机制稿 §7.3）"})
    target = tasks_mod.load_task(ctx.root, resume_task) if resume_task else None
    if not isinstance(target, dict):
        raise DefinitionError("WF_HISTORY_UNRESOLVED",
                              {"reason": "resume target missing", "task": resume_task})
    if target.get("suspended"):
        return codes.result(
            "WF_OK", object={"id": run_id},
            position_=codes.position(scope="run", step_id=step_id),
            next_="R 已归档但 T 仍挂起：先 task-reassess 清挂起，游标随后按登记返回 T",
            facts={"run": run_id, "controlled_rework": task_id, "resume_task": resume_task,
                   "rework_status": "archived", "resume_suspended": True, "step": step_id})
    # 返回定位：写回 run.advance 动作（游标是状态，须在动作里留痕）
    key = ctx.key()
    holder = ctx.require_held(run=run_id)[1]
    action = actions_mod.new_action(
        "run.advance", writer_mod.owner_ref("session", key, holder.get("scope")),
        int(run.get("revision", 0)),
        {"run": run_id, "restore_cursor": {"from": task_id, "to": resume_task}},
        steps=["restore_cursor"], head_before=actions_mod.head_of(ctx.root),
        targets=[{"kind": "run", "id": run_id}, {"kind": "task", "id": resume_task}])
    restored = dict(run, cursor={"step_id": step_id, "task_id": resume_task},
                    action=actions_mod.complete(
                        action, summary="run.advance restore cursor after rework",
                        control_assertion=cli._control_assertion(
                            ctx, "run.advance", writer_mod.owner_ref("session", key, holder.get("scope")),
                            action, [f"run:{run_id}", f"task:{resume_task}"])))
    records.write_json(run_path(ctx.root, run_id), restored)
    return codes.result(
        "WF_OK", object={"id": run_id},
        position_=codes.position(scope="run", step_id=step_id,
                                 action_id=restored["action"]["id"],
                                 action_state=restored["action"]["state"]),
        next_="已按登记的 resume_task 返回 T；继续推进该步骤（游标不再停在 R 上）",
        facts={"run": run_id, "controlled_rework": task_id, "resume_task": resume_task,
               "step": step_id, "cursor": restored["cursor"],
               "sequence_change": entry})


def _human_answer(decisions, step):
    """人判答复：`subject` 里**整词**出现该步骤 id；`skip` 表示按 skip 处置（仅可略步骤）。

    整词匹配（与 `plan-q` 同一口径）：定义同时有 `api` 与 `api-docs` 时，子串匹配会让
    给 `api-docs` 的答复被 `api` 抢走（六轮复核 b.4）。
    """
    import re

    for decision in decisions or []:
        if not isinstance(decision, dict):
            continue
        subject = decision.get("subject")
        text = " ".join(str(item) for item in subject) if isinstance(subject, list) else str(subject or "")
        pattern = r"(?<![A-Za-z0-9_-])" + re.escape(str(step["id"])) + r"(?![A-Za-z0-9_-])"
        if not re.search(pattern, text):
            continue
        return decision
    return None


def advance(ctx, args):
    """`run advance --run <id> [--decision <path>]`：推进实例游标（机制稿 §7.3）。

    本批覆盖**最小闭环**：首达任务步骤建任务并写顺序边（重入不建第二份）、
    human 步骤记答复、可略步骤按 skip 记结果、前一任务归档持久化可核后记 satisfied 并推进。
    实例记录上的 `run.advance` 动作固定目标（新任务/顺序边/游标），中断按原意图续做。
    """
    from . import actions as actions_mod, cli, lock, session as session_mod, tasks as tasks_mod, writer as writer_mod

    run_id = args.value("--run")
    decision_path = args.value("--decision")
    if not run_id:
        raise DefinitionError("WF_PATH_INVALID", {"reason": "run advance requires --run <id>"})
    decisions = cli._load_decision(decision_path) if decision_path else []
    key = ctx.key()
    with lock.acquire(ctx.root, holder_hint="run advance"):
        record = ctx.writer() or {}
        holder = record.get("holder") or {}
        if record.get("state") != "held" or holder.get("id") != key:
            raise cli.CliError("WF_WRITER_BUSY", {"holder": holder},
                               next_="由绑定该实例的会话推进；他人持有写权时先走交接/恢复出口")
        scope = (holder.get("scope") or {}).get("object") or {}
        if scope.get("kind") != "run" or scope.get("id") != run_id:
            raise DefinitionError("WF_BINDING_MISMATCH",
                                  {"reason": "writer scope is not this run", "scope": scope,
                                   "run": run_id})
        binding = session_mod.load_binding(ctx.root, key) or {}
        if ((binding.get("object") or {}).get("kind") != "run"
                or (binding.get("object") or {}).get("id") != run_id):
            raise DefinitionError("WF_BINDING_MISMATCH",
                                  {"reason": "session is not bound to this run",
                                   "binding": binding.get("object")})
        run = load_run(ctx.root, run_id)
        if not isinstance(run, dict):
            raise DefinitionError("WF_HISTORY_UNRESOLVED", {"reason": "run record missing",
                                                           "run": run_id})
        if run.get("terminal"):
            raise DefinitionError("WF_BINDING_MISMATCH",
                                  {"reason": "run already ended", "terminal": run.get("terminal")})
        if run.get("paused"):
            raise DefinitionError("WF_SEMANTIC_DECISION",
                                  {"reason": "run is paused", "exit": "先 run resume 或终止实例"})
        # 固定快照：记录里的摘要必须仍等于快照文件本身（源定义改了不影响已固定实例）
        doc, _snapshot_bytes = fixed_snapshot(ctx, run)
        creation = run.get("creation_decision") or {}
        cursor = run.get("cursor") or {}
        step_results = dict(run.get("step_results") or {})
        task_map = dict(run.get("task_map") or {})
        sequence = list(run.get("sequence_changes") or [])

        # ⓪ 受控返工 R：游标临时定位在 R 时只执行 R 与既定返回定位，
        #    **不把 R 归档当作原定义步骤完成**（机制稿 §7.3、§6.2「按已登记返回目标恢复 T」）。
        returned = _return_from_rework(ctx, run, sequence, cursor, task_map)
        if returned is not None:
            return returned
        run = load_run(ctx.root, run_id) or run
        cursor = run.get("cursor") or {}
        step_results = dict(run.get("step_results") or {})

        # ① 先把「已完成的步骤」结掉。**按步骤类型与已落盘结果判**，不把「游标上有 step_id」
        #    当成「必然有任务」：人判步骤与可略步骤合法地没有任务映射（`task_id: null`），
        #    它们的结果就在 `step_results` 里，重入时直接结案推进下一步。
        current = cursor.get("step_id")
        settled = None
        if current:
            mapping = task_map.get(current) or {}
            task_id = mapping.get("task_id")
            recorded = step_results.get(current) or {}
            if task_id:
                task = tasks_mod.load_task(ctx.root, task_id)
                if task is None:
                    raise DefinitionError("WF_HISTORY_UNRESOLVED",
                                          {"reason": "mapped task missing", "step": current,
                                           "task": task_id})
                persisted = tasks_mod.archive_persisted(ctx.root, task)
                if task.get("terminal") == "normal" and persisted.get("persisted"):
                    settled = current
                    step_results[current] = {"kind": "satisfied", "task_id": task_id,
                                             "at": records.now_str(),
                                             "terminal": task.get("terminal"),
                                             "outputs": _step_outputs(
                                                 doc, current, run.get("inputs") or {},
                                                 root=ctx.root)}
                elif task.get("terminal"):
                    # 任务已异常归档：本步骤不会再被满足，实例层只剩「终止或替换」两条路
                    raise DefinitionError(
                        "WF_SEMANTIC_DECISION",
                        {"reason": "task ended abnormally; step is not satisfied",
                         "step": current, "task": task_id,
                         "terminal": task.get("terminal"),
                         "exits": ["run terminate：按逐任务处置计划（放弃/保留）异常终止实例",
                                   "由人裁定替换该步骤的任务（task-replace）后重建推进",
                                   "若目标是继续做这件事：回 Plan 重新规划，不在旧步骤上推进"]},
                        next_="该步骤任务已异常归档：实例不再推进本步骤；用 run terminate 逐任务处置，或由人裁定替换")
            elif recorded.get("kind") in ("satisfied", "skipped"):
                # 人判答复、或按 creation 声明略过的步骤：结果已在盘上，重入即结案
                settled = current
            else:
                raise DefinitionError("WF_HISTORY_UNRESOLVED",
                                      {"reason": "cursor step has neither a task nor a result",
                                       "step": current,
                                       "step_type": (_step_by_id(doc, current) or {}).get("type"),
                                       "recorded": recorded or None},
                                      next_="只读核对实例记录与快照；不按猜测补建任务")

        # ①' 当前步骤已有任务但还没正常归档：**停在原地等它**，不跳到下一步
        #    （机制稿 §7.3：任务四阶段完成且归档持久化可核后才记 satisfied 并推进 cursor）
        if current and settled is None:
            mapping = task_map.get(current) or {}
            if mapping.get("task_id"):
                return codes.result(
                    "WF_OK", object={"id": run_id},
                    position_=codes.position(scope="run", step_id=current,
                                             task_id=mapping["task_id"]),
                    next_="当前步骤的任务尚未正常归档：在该任务上完成四阶段后重入 advance",
                    facts={"run": run_id, "step": current, "task": mapping["task_id"],
                           "waiting": True, "cursor": cursor,
                           "step_results": step_results})

        # ② 找下一个要处理的步骤
        step = _next_step(doc, settled or current, step_results)
        if step is None:
            # 末步结案必须落盘：此前只回显 facts，`run finish` 重读磁盘仍看到该步骤未完成
            # （六轮审查 b-1：末步 advance 返回 WF_OK、写盘 0 次）。
            if settled:
                # 只补结果，**不动 cursor**：游标上的 task_id 还被写权释放前置与 current-task
                # 投影消费，置空会顺手改掉那两处的行为（自查：状态字段不做"顺手归一"）。
                run = dict(run, step_results=step_results)
                records.write_json(run_path(ctx.root, run_id), run)
            return codes.result("WF_OK", object={"id": run_id},
                                position_=codes.position(scope="run", step_id=settled),
                                next_="所有步骤已记录结果：run finish 正常结束，或 run terminate 异常终止",
                                facts={"run": run_id, "cursor": cursor,
                                       "step_results": step_results, "settled": settled})
        step_id = step["id"]
        applicability = _applicability(creation, doc)
        decided = _human_answer(decisions, step)

        if applicability.get(step_id) == "skipped":
            if not step_skippable(step):
                raise DefinitionError(
                    "WF_SEMANTIC_DECISION",
                    {"reason": "step is required (skip=null); it cannot be skipped",
                     "step": step_id, "creation_steps": applicability,
                     "exits": ["按定义执行该步骤（建任务或回答人判点）",
                               "确要略过：改定义声明 skip 后由人重新确认创建输入（新实例）"]},
                    next_="必需步骤不能略过：回到该步骤执行，不要用创建输入绕过")
            # 可略步骤：不为保存答复强建任务；下游替代链已在静态校验里核过
            if decided is None:
                raise DefinitionError("WF_SEMANTIC_DECISION",
                                      {"reason": "skippable step needs a decision",
                                       "step": step_id,
                                       "decision_point": ((step.get("skip") or {}).get("decision_point"))},
                                      next_="用 --decision 记录略过决定（subject 含该步骤 id）")
            step_results[step_id] = {"kind": "skipped", "at": records.now_str(),
                                     "decision": decided.get("choice"),
                                     "decision_detail": decided,
                                     # 机制稿 §7.1：答复保存实际决定**及适用快照哈希**
                                     "definition_digest": (run.get("definition") or {}).get("digest")}
            run = dict(run, step_results=step_results,
                       cursor={"step_id": step_id, "task_id": None})
            records.write_json(run_path(ctx.root, run_id), run)
            return codes.result("WF_OK", object={"id": run_id},
                                position_=codes.position(scope="run", step_id=step_id),
                                next_="该步骤已记 skipped；继续 advance 推进下一步",
                                facts={"run": run_id, "step": step_id, "skipped": True,
                                       "cursor": run["cursor"], "step_results": step_results})

        if step.get("type") == "human":
            if decided is None:
                raise DefinitionError("WF_SEMANTIC_DECISION",
                                      {"reason": "human step needs an answer", "step": step_id,
                                       "question": step.get("question"),
                                       "choices": step.get("choices")},
                                      next_="用 --decision 记录答复（subject 含该步骤 id）")
            if decided.get("choice") not in (step.get("choices") or []):
                raise DefinitionError("WF_SEMANTIC_DECISION",
                                      {"reason": "answer is not one of the declared choices",
                                       "step": step_id, "got": decided.get("choice"),
                                       "choices": step.get("choices")})
            step_results[step_id] = {"kind": "satisfied", "at": records.now_str(),
                                     "decision": decided.get("choice"),
                                     "definition_digest": (run.get("definition") or {}).get("digest")}
            run = dict(run, step_results=step_results,
                       cursor={"step_id": step_id, "task_id": None})
            records.write_json(run_path(ctx.root, run_id), run)
            return codes.result("WF_OK", object={"id": run_id},
                                position_=codes.position(scope="run", step_id=step_id),
                                next_="人判步骤已记录；继续 advance 推进下一步",
                                facts={"run": run_id, "step": step_id, "answer": decided.get("choice"),
                                       "cursor": run["cursor"]})

        # ③ task 步骤：已映射就复用（重入不建第二份），否则按**预生成 id + 意图固定**创建
        mapping = task_map.get(step_id) or {}
        if mapping.get("task_id"):
            task_id = mapping["task_id"]
            task = tasks_mod.load_task(ctx.root, task_id)
            if task is None:
                raise DefinitionError("WF_HISTORY_UNRESOLVED",
                                      {"reason": "mapped task missing", "task": task_id})
            return codes.result("WF_OK", object={"id": run_id},
                                position_=codes.position(scope="run", step_id=step_id,
                                                         task_id=task_id),
                                next_="该步骤的任务已生成：在其上完成四阶段后重入 advance 记 satisfied",
                                facts={"run": run_id, "step": step_id, "task": task_id,
                                       "reused": True, "cursor": cursor})
        _require_upstream_outputs(ctx, doc, step, step_results)
        previous = _previous_task_step(doc, step_id, applicability, step_results)
        predecessors = []
        if previous is not None:
            prior_task = (task_map.get(previous["id"]) or {}).get("task_id")
            if not prior_task:
                raise DefinitionError("WF_DEPENDENCY_UNMET",
                                      {"reason": "previous task step has no task yet",
                                       "step": previous["id"]})
            prior_record = tasks_mod.load_task(ctx.root, prior_task) or {}
            if prior_record.get("terminal") != "normal":
                raise DefinitionError("WF_DEPENDENCY_UNMET",
                                      {"reason": "previous step's task is not normally archived",
                                       "step": previous["id"], "task": prior_task,
                                       "terminal": prior_record.get("terminal")},
                                      next_="先完成并正常归档上一个任务，再推进")
            predecessors = [prior_task]
        # 续做而不是重建：锁内中断（例如"任务目录已发布、映射还没写"）后重入时，
        # 已登记的 `run.advance` 动作里固定着这次的 task id——沿用它，绝不再生成第二个。
        pending = run.get("action") or {}
        resume_task = None
        if (pending.get("kind") == "run.advance" and pending.get("state") != "done"
                and (pending.get("inputs") or {}).get("step") == step_id
                and (pending.get("inputs") or {}).get("run") == run_id):
            resume_task = (pending.get("inputs") or {}).get("task")
        task = tasks_mod.new_task_record(step.get("task_kind") or "ordinary",
                                         step.get("title") or step_id)
        if resume_task:
            task["id"] = resume_task
        task["run_id"] = run_id
        task["prerequisites"] = list(predecessors)
        inputs = {"run": run_id, "step": step_id, "task": task["id"],
                  "predecessors": sorted(predecessors)}
        action = (pending if resume_task else
                  actions_mod.new_action("run.advance",
                                         writer_mod.owner_ref("session", key, scope),
                                         int(run.get("revision", 0)), inputs,
                                         steps=list(ADVANCE_STEPS),
                                         head_before=actions_mod.head_of(ctx.root),
                                         targets=[{"kind": "run", "id": run_id},
                                                  {"kind": "task", "id": task["id"]},
                                                  {"kind": "step", "id": step_id}]))
        run = dict(run, action=action)
        records.write_json(run_path(ctx.root, run_id), run)
        template = join(ctx.root, ".wf/templates/task")
        directory = join(ctx.root, f"{tasks_mod.TASKS_REL}/{tasks_mod.dir_name(task['id'], task['title'])}")
        staging = join(ctx.root, f"{tasks_mod.TASKS_REL}/.staging-{task['id']}")
        if os.path.exists(staging):
            raise cli.CliError("WF_TARGET_COLLISION", {"path": _rel(ctx.root, staging)})
        if not os.path.exists(directory):
            tasks_mod._publish_task_tree(ctx, directory, staging, template, task)
        elif not resume_task:
            # 不是本次中断留下的目录：真冲突（别把别人的任务认成自己的）
            raise cli.CliError("WF_TARGET_COLLISION", {"path": _rel(ctx.root, directory)})
        task_map[step_id] = {"task_id": task["id"], "predecessors": sorted(predecessors),
                             "superseded_ids": []}
        run = dict(run, task_map=task_map, step_results=step_results,
                   cursor={"step_id": step_id, "task_id": task["id"]},
                   action=actions_mod.complete(
                       action, summary="run.advance",
                       control_assertion=cli._control_assertion(
                           ctx, "run.advance", writer_mod.owner_ref("session", key, scope),
                           action, [f"task:{task['id']}"])))
        records.write_json(run_path(ctx.root, run_id), run)
        # 合并写：游标变了不等于"整份侧车重建"，写权代次（`writer_generation`）由写权入口写入，
        # 这里必须原样保留，否则下一步写操作取不到代次（dogfood 实录）。
        session_mod.update_runtime(
            ctx.root, key,
            binding_digest=records.plain_digest(binding),
            instance_id=binding.get("instance_id"),
            object={"kind": "run", "id": run_id},
            current_task=task["id"],
            cursor=run["cursor"],
        )
    stale = [step for step in ADVANCE_STEPS if not _advance_step_done(ctx, run_id, run, step)]
    if stale:
        raise DefinitionError("WF_PERSISTENCE_FAILED",
                              {"reason": "run.advance step postcondition missing", "steps": stale},
                              next_="重入 run advance 续做（按已固定的任务 id，不新建第二份）")
    return codes.result(
        "WF_OK",
        object={"id": run_id},
        position_=codes.position(scope="run", step_id=step_id, task_id=task["id"],
                                 action_id=run["action"]["id"],
                                 action_state=run["action"]["state"]),
        next_="在该任务上完成四阶段（Plan/Execute/Check/Finish）后重入 advance 记 satisfied",
        facts={"run": run_id, "step": step_id, "task": task["id"],
               "directory": _rel(ctx.root, directory),
               "predecessors": predecessors, "cursor": run["cursor"],
               "terminated": sequence},
    )


def _advance_step_done(ctx, run_id, run, step):
    """`run.advance` 各步的真实后置（不看步骤字段）。"""
    from . import tasks as tasks_mod

    cursor = run.get("cursor") or {}
    step_id = cursor.get("step_id")
    mapping = (run.get("task_map") or {}).get(step_id) or {}
    task_id = mapping.get("task_id")
    if step == "resolve_step":
        return bool(step_id)
    if step == "create_or_reuse_task":
        if not task_id:
            return False
        record = tasks_mod.load_task(ctx.root, task_id)
        return isinstance(record, dict) and record.get("run_id") == run_id
    if step == "record_cursor":
        return cursor.get("task_id") == task_id and bool(task_id)
    return False


PAUSE_STEPS = ("record_reason", "pause_task", "write_run")


def _reassert_current_task_pause(ctx, run, reason):
    """实例处于暂停态时，确保当前任务也暂停（幂等修复，不改 phase/status/游标）。"""
    from . import tasks as tasks_mod

    task_id = (run.get("cursor") or {}).get("task_id")
    if not task_id:
        return False
    task = tasks_mod.load_task(ctx.root, task_id)
    if not isinstance(task, dict) or task.get("paused"):
        return False
    directory = tasks_mod.task_dir(ctx.root, task_id)
    task = dict(task, paused=True,
                pause_reason={"reason": reason or "instance paused",
                              "at": records.now_str(), "by": "run.pause", "run": run.get("id")})
    tasks_mod.save_task(ctx.root, directory, task)
    return True


def pause(ctx, args):
    """`run pause --run <id> --reason <text>`：受控暂停（机制稿 §7.3、§1.5 的 `paused`）。

    保存**暂停原因与当前步骤**，并把当前步骤的任务一并暂停（清掉它的执行候选）——
    机制稿 §7.3 明确「实例暂停须保存当前任务的暂停或等待原因及当前步骤，
    不能只移动游标绕过任务门禁」，所以这里不动 `cursor`。

    **解除路径是 `run resume`**：它只清 `paused`、记录谁/何时/依据，不恢复任务、不动游标。
    是否恢复当前步骤的任务是第二个决定（`task-resume`），异常收场走 `run terminate`。
    """
    from . import actions as actions_mod, cli, lock, session as session_mod, tasks as tasks_mod, writer as writer_mod

    run_id = args.value("--run")
    reason = args.value("--reason")
    if not run_id or not isinstance(reason, str) or not reason.strip():
        raise DefinitionError("WF_PATH_INVALID",
                              {"reason": "run pause requires --run <id> --reason <text>"})
    key = ctx.key()
    with lock.acquire(ctx.root, holder_hint="run pause"):
        record = ctx.writer() or {}
        holder = record.get("holder") or {}
        if record.get("state") != "held" or holder.get("id") != key:
            raise cli.CliError("WF_WRITER_BUSY", {"holder": holder},
                               next_="由绑定该实例的会话暂停；他人持有写权时先走交接/恢复出口")
        scope = (holder.get("scope") or {}).get("object") or {}
        if scope.get("kind") != "run" or scope.get("id") != run_id:
            raise DefinitionError("WF_BINDING_MISMATCH",
                                  {"reason": "writer scope is not this run", "scope": scope})
        binding = session_mod.load_binding(ctx.root, key) or {}
        if ((binding.get("object") or {}).get("kind") != "run"
                or (binding.get("object") or {}).get("id") != run_id):
            raise DefinitionError("WF_BINDING_MISMATCH",
                                  {"reason": "session is not bound to this run",
                                   "binding": binding.get("object")})
        run = load_run(ctx.root, run_id)
        if not isinstance(run, dict):
            raise DefinitionError("WF_HISTORY_UNRESOLVED", {"reason": "run record missing",
                                                           "run": run_id})
        if run.get("terminal"):
            raise DefinitionError("WF_BINDING_MISMATCH",
                                  {"reason": "run already ended", "terminal": run.get("terminal")})
        if run.get("paused"):
            # 幂等之外还要**修复不变量**：实例暂停 ⇒ 当前任务也暂停。此前这里直接返回，
            # 于是"实例暂停、任务被 task-resume 解冻"的矛盾状态没人收拾（六轮审查 b-6）。
            repaired = _reassert_current_task_pause(ctx, run, reason)
            return codes.result("WF_OK", object={"id": run_id},
                                position_=codes.position(scope="run"),
                                next_=("实例已在暂停态（幂等）；已补上当前任务的暂停"
                                       if repaired else "实例已在暂停态（幂等，不重复写入）"),
                                facts={"run": run_id, "paused": True,
                                       "paused_reason": run.get("paused_reason"),
                                       "task_pause_repaired": repaired})
        cursor = run.get("cursor") or {}
        task_id = cursor.get("task_id")
        action = actions_mod.new_action("run.pause",
                                        writer_mod.owner_ref("session", key, scope),
                                        int(run.get("revision", 0)),
                                        {"run": run_id, "reason": reason,
                                         "step": cursor.get("step_id"), "task": task_id},
                                        steps=list(PAUSE_STEPS),
                                        head_before=actions_mod.head_of(ctx.root),
                                        targets=[{"kind": "run", "id": run_id},
                                                 {"kind": "step", "id": cursor.get("step_id")},
                                                 {"kind": "task", "id": task_id}])
        run = dict(run, action=action)
        records.write_json(run_path(ctx.root, run_id), run)
        # 当前任务一并暂停（只清执行候选，不改 phase/status、不动游标）
        paused_task = None
        if task_id:
            directory = tasks_mod.task_dir(ctx.root, task_id)
            task = tasks_mod.load_task(ctx.root, task_id) if directory else None
            if task is None:
                raise DefinitionError("WF_HISTORY_UNRESOLVED",
                                      {"reason": "current task missing", "task": task_id})
            if not task.get("paused"):
                task = dict(task, paused=True,
                            pause_reason={"reason": reason, "at": records.now_str(),
                                          "by": "run.pause", "run": run_id})
                tasks_mod.save_task(ctx.root, directory, task)
            paused_task = task_id
        run = dict(run, paused=True,
                   paused_reason={"reason": reason, "at": records.now_str(),
                                  "session_key": key, "step": cursor.get("step_id")},
                   action=actions_mod.complete(
                       action, summary="run.pause",
                       control_assertion=cli._control_assertion(
                           ctx, "run.pause", writer_mod.owner_ref("session", key, scope),
                           action, [f"run:{run_id}"])))
        records.write_json(run_path(ctx.root, run_id), run)
    stale = []
    if not run.get("paused"):
        stale.append("write_run")
    if paused_task and not (tasks_mod.load_task(ctx.root, paused_task) or {}).get("paused"):
        stale.append("pause_task")
    if not stale and not run.get("paused_reason", {}).get("reason"):
        stale.append("record_reason")
    if stale:
        raise DefinitionError("WF_PERSISTENCE_FAILED",
                              {"reason": "run.pause step postcondition missing", "steps": stale},
                              next_="重入 run pause（幂等）")
    return codes.result(
        "WF_OK",
        object={"id": run_id},
        position_=codes.position(scope="run", step_id=cursor.get("step_id"), task_id=paused_task,
                                 action_id=run["action"]["id"],
                                 action_state=run["action"]["state"]),
        next_=("人确认后 run resume 解除实例暂停（只清 paused、不恢复任务、不动游标）；"
               "是否恢复当前任务另跑 task-resume；要异常收场用 run terminate"),
        facts={"run": run_id, "paused": True, "paused_reason": run["paused_reason"],
               "paused_task": paused_task, "cursor": cursor,
               "control_assertion": run["action"]["result"]["control_assertion"]},
    )


RESUME_STEPS = ("clear_paused", "record_resume")


TERMINATE_DISPOSITIONS = {"放弃": "abandon", "abandon": "abandon",
                          "保留": "keep", "keep": "keep"}


FINISH_STEPS = ("check_steps", "write_normal", "persist_record")


def _persist_run_records(ctx, run, run_id, decisions, op, key, scope):
    """固定提交步骤（唯一实现）：**先把"完成态"写盘，再提交，然后从 Git 读回核对**。

    原先的顺序是"先提交、后把动作标 done"：成功后磁盘上留下的是 `persist_pending`，
    下一次写入才变成 `done`——于是回显 `persisted=true` 时 Git 里的记录还停在待提交
    （六轮审查 b-5）。改成先写后提交后，提交的内容就是我们声称的那个终态；
    核对失败则回退到 `persist_pending` 并如实报 `persisted=false`。
    提交清单同时带上定义快照：实例记录引用了它，分开提交会留下半份记录组。
    """
    from . import actions as actions_mod, cli, paths as paths_mod, tasks as tasks_mod, writer as writer_mod

    record_rel = f"{RUNS_REL}/{run_id}.json"
    snapshot_rel = ((run.get("definition") or {}).get("snapshot_path"))
    grants = [item for item in decisions if isinstance(item, dict)
              and decisions_mod.accepts("commit_grant", item.get("choice"))]
    covered = any(path in (record_rel, snapshot_rel) or paths_mod.match_path(path, record_rel)
                  for grant in grants for path in _grant_paths(grant.get("subject")))
    result = {"persisted": False, "commit": None, "record": record_rel,
              "records": [item for item in (record_rel, snapshot_rel) if item]}
    if not covered:
        return result

    pending_run = dict(run)
    action = dict(run["action"])
    done_run = dict(run, action=actions_mod.complete(
        action, summary=f"run.{op}",
        control_assertion=cli._control_assertion(
            ctx, f"run.{op}", writer_mod.owner_ref("session", key, scope),
            action, [f"run:{run_id}"])))
    records.write_json(run_path(ctx.root, run_id), done_run)
    paths = [item for item in (record_rel, snapshot_rel)
             if item and os.path.exists(join(ctx.root, item))]
    result["commit"] = tasks_mod._commit_paths(
        ctx.root, paths, f"wf: run {op} {run_id}\n\nwf-task: {run_id}")
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", record_rel],
                             cwd=str(ctx.root), capture_output=True, text=True, check=False)
    dirty = subprocess.run(["git", "status", "--porcelain", "--", record_rel],
                           cwd=str(ctx.root), capture_output=True, text=True,
                           check=False).stdout.strip()
    committed = subprocess.run(["git", "show", f"HEAD:{record_rel}"], cwd=str(ctx.root),
                               capture_output=True, text=True, check=False)
    from_git = None
    if committed.returncode == 0:
        try:
            from_git = json.loads(committed.stdout)
        except ValueError:
            from_git = None
    result["persisted"] = (tracked.returncode == 0 and dirty == ""
                           and isinstance(from_git, dict)
                           and (from_git.get("action") or {}).get("state") == "done")
    if not result["persisted"]:
        # 提交没落地：把记录退回"目标已成立、提交未完成"，别让磁盘上留下假的完成态
        records.write_json(run_path(ctx.root, run_id), pending_run)
        result["head_state"] = ((from_git or {}).get("action") or {}).get("state")
    return result


def _pending_persist(ctx, run, run_id, decisions, op, key, scope):
    """`persist_pending` 的重入：只重做固定提交步骤，不重做业务。

    终态已落盘、只差分提交时，两个入口原来一律报 "run already ended"——入口自己给的
    "补授权后重入"于是变成死出口（六轮审查 b-2）。这里按**事实**续做：有覆盖该路径的
    commit 授权就提交并只读复核，然后把动作收尾；没有就仍停着并给同一个出口。
    """
    outcome = _persist_run_records(ctx, run, run_id, decisions, op, key, scope)
    persisted, commit_result = outcome["persisted"], outcome["commit"]
    record_rel = outcome["record"]
    return codes.result(
        "WF_OK",
        object={"id": run_id},
        position_=codes.position(scope="run", action_id=run["action"]["id"],
                                 action_state=run["action"]["state"]),
        next_=("实例已结束并持久化：可 writer release 结束会话"
               if persisted else
               f"实例已结束，但**记录组尚未提交**：给出覆盖该路径的 commit 授权后重入 run {op} 续做"),
        facts={"run": run_id, "terminal": run.get("terminal"), "ended_at": run.get("ended_at"),
               "closing": run.get("closing"), "persisted": persisted,
               "record": record_rel, "commit": commit_result, "resumed": True,
               "note": "重入只补做固定提交步骤，不重做结束/终止的业务判定"})


def finish(ctx, args):
    """`run finish --run <id> [--decision <path>]`：实例正常结束（机制稿 §7.4）。

    前置全是**事实核对**，不替人判断：所有**必需**步骤已 `satisfied`、可略步骤的 `skipped` 成立、
    `task_map` 里每个任务都正常归档且持久化可核、human 步骤有人判答复、工作区没有未处置的保留 WIP。
    任一不成立即 `WF_SEMANTIC_DECISION`/`WF_WORKSPACE_UNRESOLVED` 并列出缺什么——**不代调**
    任务的 `finish`（机制稿 §7.4：任务 finish 由人调用）。

    持久化：给了 `--decision` 且其中的 `commit` 授权覆盖实例记录路径时，按精确路径提交并只读复核；
    没给授权就停在 `persist_pending`，如实说明「记录组尚未提交」。
    """
    from . import actions as actions_mod, cli, lock, session as session_mod, tasks as tasks_mod, writer as writer_mod

    run_id = args.value("--run")
    decision_path = args.value("--decision")
    if not run_id:
        raise DefinitionError("WF_PATH_INVALID", {"reason": "run finish requires --run <id>"})
    decisions = cli._load_decision(decision_path) if decision_path else []
    key = ctx.key()
    with lock.acquire(ctx.root, holder_hint="run finish"):
        record = ctx.writer() or {}
        holder = record.get("holder") or {}
        if record.get("state") != "held" or holder.get("id") != key:
            raise cli.CliError("WF_WRITER_BUSY", {"holder": holder},
                               next_="由绑定该实例的会话结束实例；他人持有写权时先走交接/恢复出口")
        scope = (holder.get("scope") or {}).get("object") or {}
        if scope.get("kind") != "run" or scope.get("id") != run_id:
            raise DefinitionError("WF_BINDING_MISMATCH",
                                  {"reason": "writer scope is not this run", "scope": scope})
        binding = session_mod.load_binding(ctx.root, key) or {}
        if ((binding.get("object") or {}).get("kind") != "run"
                or (binding.get("object") or {}).get("id") != run_id):
            raise DefinitionError("WF_BINDING_MISMATCH",
                                  {"reason": "session is not bound to this run",
                                   "binding": binding.get("object")})
        run = load_run(ctx.root, run_id)
        if not isinstance(run, dict):
            raise DefinitionError("WF_HISTORY_UNRESOLVED", {"reason": "run record missing",
                                                           "run": run_id})
        if run.get("terminal"):
            if (run.get("action") or {}).get("state") != "persist_pending":
                raise DefinitionError("WF_BINDING_MISMATCH",
                                      {"reason": "run already ended",
                                       "terminal": run.get("terminal")})
            return _pending_persist(ctx, run, run_id, decisions, "finish", key, scope)
        if run.get("paused"):
            raise DefinitionError("WF_SEMANTIC_DECISION",
                                  {"reason": "run is paused", "exit": "先 run resume 再结束"})
        doc, _snapshot_bytes = fixed_snapshot(ctx, run)
        step_results = run.get("step_results") or {}
        task_map = run.get("task_map") or {}
        creation = run.get("creation_decision") or {}
        applicability = _applicability(creation, doc)

        # ① 步骤面：每个步骤都要有**本次适用性允许**的落盘结果。
        #    可略资格只看定义的 skip 声明（`step_skippable`），创建输入只能决定"本次是否要略"，
        #    不能把必需步骤变成可略；反过来，可略但本次标 applicable 的步骤也必须真做完。
        unsatisfied, illegal_skips = [], []
        for step in _ordered_steps(doc):
            step_id = step["id"]
            result = step_results.get(step_id) or {}
            kind = result.get("kind")
            declared_skipped = applicability.get(step_id) == "skipped"
            allowed_kinds = ("skipped", "satisfied") if (declared_skipped and step_skippable(step)) \
                else ("satisfied",)
            if kind is None:
                unsatisfied.append({"step": step_id, "kind": None})
            elif kind not in allowed_kinds:
                illegal_skips.append({"step": step_id, "kind": kind,
                                      "declared": applicability.get(step_id),
                                      "skippable": step_skippable(step)})
        # ② 任务面：每个已生成任务都正常归档且持久化可核
        bad_tasks = []
        for step_id, mapping in sorted(task_map.items()):
            task_id = (mapping or {}).get("task_id")
            task = tasks_mod.load_task(ctx.root, task_id) if task_id else None
            if not isinstance(task, dict):
                bad_tasks.append({"step": step_id, "task": task_id, "reason": "missing"})
                continue
            if task.get("terminal") != "normal":
                bad_tasks.append({"step": step_id, "task": task_id,
                                  "terminal": task.get("terminal")})
                continue
            persisted = tasks_mod.archive_persisted(ctx.root, task)
            if not persisted.get("persisted"):
                bad_tasks.append({"step": step_id, "task": task_id,
                                  "reason": persisted.get("reason") or "archive not persisted"})
        if unsatisfied or illegal_skips or bad_tasks:
            raise DefinitionError("WF_SEMANTIC_DECISION",
                                  {"reason": "instance is not ready to finish normally",
                                   "unsatisfied_steps": unsatisfied,
                                   "illegal_skips": illegal_skips,
                                   "tasks_not_normal": bad_tasks},
                                  next_="把缺口对应的步骤/任务做完（任务 finish 由人调用），或改用 run terminate")
        # ③ 真实工作区：本实例任务不得留下未处置的保留 WIP
        from . import scope as scope_mod

        dirty = set(scope_mod.uncommitted_paths(ctx.root))
        sticky = []
        for task_id in sorted({(m or {}).get("task_id") for m in task_map.values() if (m or {}).get("task_id")}):
            task = tasks_mod.load_task(ctx.root, task_id) or {}
            retained = [path for path in tasks_mod.wip_paths(task) if path in dirty]
            if retained:
                sticky.append({"task": task_id, "paths": retained})
        if sticky:
            raise DefinitionError("WF_WORKSPACE_UNRESOLVED",
                                  {"reason": "run tasks keep undisposed WIP", "blocked": sticky},
                                  next_="先处置这些路径（提交/反向修正/承接）后重入")

        record_rel = f"{RUNS_REL}/{run_id}.json"
        action = actions_mod.new_action("run.finish",
                                        writer_mod.owner_ref("session", key, scope),
                                        int(run.get("revision", 0)),
                                        {"run": run_id, "mode": "normal"},
                                        steps=list(FINISH_STEPS),
                                        head_before=actions_mod.head_of(ctx.root),
                                        targets=[{"kind": "run", "id": run_id}])
        run = dict(run, action=action,
                   closing={"mode": "normal", "at": records.now_str(),
                            "decision": decisions, "task_dispositions": {}, "next_step": None})
        records.write_json(run_path(ctx.root, run_id), run)
        run = dict(run, terminal="normal", ended_at=records.now_str(),
                   action=dict(action, state="persist_pending", next_step=None))
        records.write_json(run_path(ctx.root, run_id), run)

        # ④ 持久化：有覆盖该路径的提交授权才提交；否则停在 persist_pending 并如实说明
        outcome = _persist_run_records(ctx, run, run_id, decisions, "finish", key, scope)
        persisted = outcome["persisted"]
        commit_result = outcome["commit"]
        if persisted:
            run = records.load_json(run_path(ctx.root, run_id)) or run
    next_ = ("实例已正常结束并持久化：可 writer release 结束会话"
             if persisted else
             "实例已正常结束，但**记录组尚未提交**：给出覆盖该路径的 commit 授权后重入 run finish 续做")
    return codes.result(
        "WF_OK",
        object={"id": run_id},
        position_=codes.position(scope="run",
                                 action_id=run["action"]["id"],
                                 action_state=run["action"]["state"]),
        next_=next_,
        facts={"run": run_id, "terminal": "normal", "ended_at": run["ended_at"],
               "closing": run["closing"], "persisted": persisted,
               "record": record_rel, "commit": commit_result,
               "note": "任务 finish 由人实际调用；实例结束入口不代调"})


def _grant_paths(subject):
    if isinstance(subject, list):
        return [str(item) for item in subject if isinstance(item, str)]
    if isinstance(subject, str):
        return [subject]
    return []


def _terminate_decisions(entries):
    """批量计划里的全部内联决定（含每条任务附带的提交授权）。"""
    found = []
    for entry in entries.values():
        found.extend(item for item in entry.get("decisions") or [] if isinstance(item, dict))
    return found


def _record_stop_request(ctx, run_id, plan_path, holder):
    """把停止请求记进**本会话侧车**（机制稿 §7.4 的只读接收 + §4.4 的侧车窄例外）。

    侧车按会话隔离、可丢弃、不参与任何门禁；因此这里记的是"某人请求过停止"，
    **不是**终止事实。写失败只降级为可见提示（侧车不是判定字段）。
    """
    from . import session as session_mod

    key = ctx.key()
    request = {"run": run_id, "at": records.now_str(), "plan": plan_path,
               "session_key": key, "blocked_by": holder,
               "note": "只读接收：未执行任何项目写入；恢复写权后重入 run terminate 执行"}
    merged = session_mod.update_runtime(ctx.root, key, stop_request=request)
    return dict(request, sidecar_written=bool(merged),
                sidecar=os.path.relpath(session_mod.runtime_path(ctx.root, key),
                                        str(ctx.root)).replace(os.sep, "/"))


def _terminate_preview(ctx, run_id):
    """异常终止的只读预览（机制稿 §7.4：逐个列出已生成任务、返工/继任者、未生成步骤、已有改动、外部依赖）。

    只读：不写任何记录。人据此填 `--plan`（每个已生成任务一条 `{object, decision_ref, reason}`）。
    """
    from . import codes, scope as scope_mod, tasks as tasks_mod

    run = load_run(ctx.root, run_id)
    if not isinstance(run, dict):
        raise DefinitionError("WF_HISTORY_UNRESOLVED", {"reason": "run record missing", "run": run_id})
    if run.get("terminal"):
        raise DefinitionError("WF_BINDING_MISMATCH",
                              {"reason": "run already ended", "terminal": run.get("terminal")})
    doc, _snapshot_bytes = fixed_snapshot(ctx, run)
    task_map = run.get("task_map") or {}
    tasks = []
    for step_id, mapping in sorted(task_map.items()):
        task_id = (mapping or {}).get("task_id")
        task = tasks_mod.load_task(ctx.root, task_id) if task_id else None
        if not isinstance(task, dict):
            tasks.append({"step_id": step_id, "task_id": task_id, "unknown": True})
            continue
        preview = tasks_mod._abandon_preview(ctx, task)
        tasks.append({"step_id": step_id, "task_id": task_id,
                      "status": task.get("status"), "terminal": task.get("terminal"),
                      "paused": bool(task.get("paused")), "suspended": bool(task.get("suspended")),
                      "uncommitted": preview.get("uncommitted") or [],
                      "existing_commits": (preview.get("existing_commits") or [])[:5],
                      "downstream": preview.get("downstream") or [],
                      "unfinished_rework": preview.get("unfinished_rework") or []})
    generated = set(task_map)
    not_executed = [step["id"] for step in _ordered_steps(doc or {}) if step["id"] not in generated]
    from . import session as session_mod

    runtime = session_mod.load_runtime(ctx.root, ctx.key()) or {}
    return codes.result(
        "WF_OK",
        object={"id": run_id},
        position_=codes.position(scope="run", step_id=(run.get("cursor") or {}).get("step_id")),
        next_="按本预览为每个已生成任务填一条 {object, decision_ref, reason} 后带 --plan 重入；"
              "有未提交改动的任务需在决定里给 disposition（逐路径去向），否则会被拒且零写入",
        facts={"run": run_id, "mode": "abnormal", "preview": True,
               "tasks": tasks, "not_executed_steps": not_executed,
               "sequence_changes": run.get("sequence_changes") or [],
               "cursor": run.get("cursor"), "task_map": task_map,
               "external_dependencies": [{"step": step, "task": (mapping or {}).get("task_id")}
                                         for step, mapping in sorted(task_map.items())],
               # 上次写权不可核时记在本会话侧车的停止请求（机制稿 §7.4）；不是终止事实
               "pending_stop_request": runtime.get("stop_request")})


def terminate(ctx, args):
    """`run terminate --run <id> --plan <path>`：实例异常终止 + 逐任务处置（机制稿 §7.4）。

    人的批量计划一次确认：每个已生成任务给一条 `{object, decision_ref, reason}`，
    `decision_ref` 是内联 `Decision`，其 `choice` 声明处置（`放弃/abandon` 或 `保留/keep`）。
    **先整批预检、再逐个应用**——任何一项不成立就零写入（含"放弃的任务还有未处置 WIP"）。
    放弃复用 `tasks._apply_abandon()`（与 `task-abandon` 同一实现）；保留写 `independent_resume`，
    执行中的先 `paused`；未生成的步骤记 `not_executed`，不建空壳任务。
    """
    from . import actions as actions_mod, cli, lock, session as session_mod, tasks as tasks_mod, writer as writer_mod

    run_id = args.value("--run")
    plan_path = args.value("--plan")
    preview_only = args.flag("--preview")
    if not run_id:
        raise DefinitionError("WF_PATH_INVALID", {"reason": "run terminate requires --run <id>"})
    if preview_only:
        return _terminate_preview(ctx, run_id)
    # 计划只覆盖**已生成的任务**：实例刚建好、一步还没展开时，合法计划就是空数组
    # （此前空数组与"没有任务条目"同时被拒 → 新实例无路可终止，六轮审查 b-4）。
    plan = []
    if plan_path:
        loaded = records.load_json(plan_path)
        if loaded is None:
            raise DefinitionError("WF_PATH_INVALID", {"reason": "plan file missing", "path": plan_path})
        plan = [loaded] if isinstance(loaded, dict) else loaded
        if not isinstance(plan, list):
            raise DefinitionError("WF_SEMANTIC_DECISION",
                                  {"reason": "plan must be an array of {object, decision_ref, reason}"})
    key = ctx.key()
    with lock.acquire(ctx.root, holder_hint="run terminate"):
        record = ctx.writer() or {}
        holder = record.get("holder") or {}
        if record.get("state") != "held" or holder.get("id") != key:
            # 机制稿 §7.4：**写权无法核实时只读接收停止请求**，待恢复后再写。
            # 落点是 §4.4 允许的窄例外——本会话侧车（不进项目记录、不写判定字段、可丢弃）。
            receipt = _record_stop_request(ctx, run_id, plan_path, holder)
            raise cli.CliError(
                "WF_WRITER_BUSY",
                {"holder": holder, "stop_request": receipt,
                 "reason": "stop request received; no project write was performed"},
                next_=("停止请求已记在本会话侧车（**未执行任何项目写入**）：先恢复写权"
                       "（repair / 交接），再重入 run terminate；预览会把该请求带出来"))
        scope = (holder.get("scope") or {}).get("object") or {}
        if scope.get("kind") != "run" or scope.get("id") != run_id:
            raise DefinitionError("WF_BINDING_MISMATCH",
                                  {"reason": "writer scope is not this run", "scope": scope})
        binding = session_mod.load_binding(ctx.root, key) or {}
        if ((binding.get("object") or {}).get("kind") != "run"
                or (binding.get("object") or {}).get("id") != run_id):
            raise DefinitionError("WF_BINDING_MISMATCH",
                                  {"reason": "session is not bound to this run",
                                   "binding": binding.get("object")})
        run = load_run(ctx.root, run_id)
        if not isinstance(run, dict):
            raise DefinitionError("WF_HISTORY_UNRESOLVED", {"reason": "run record missing",
                                                           "run": run_id})
        generated_now = [(mapping or {}).get("task_id")
                         for mapping in (run.get("task_map") or {}).values()
                         if (mapping or {}).get("task_id")]
        if not plan_path and generated_now and not run.get("terminal"):
            raise DefinitionError("WF_PATH_INVALID",
                                  {"reason": "run terminate requires --plan when tasks were generated",
                                   "generated": generated_now,
                                   "exits": ["按 run terminate --preview 的清单逐任务给处置后带 --plan 重入"]})
        if run.get("terminal"):
            if (run.get("action") or {}).get("state") != "persist_pending":
                raise DefinitionError("WF_BINDING_MISMATCH",
                                      {"reason": "run already ended",
                                       "terminal": run.get("terminal")})
            # `decision_ref` 与主路径同形：单个 Decision 或 Decision 数组（后者才带提交授权）。
            entries = {}
            for item in plan:
                if not isinstance(item, dict) or not isinstance(item.get("object"), str):
                    continue
                raw = item.get("decision_ref")
                entries[item["object"]] = {"decisions": [entry for entry in raw
                                                         if isinstance(entry, dict)] if isinstance(raw, list)
                                            else ([raw] if isinstance(raw, dict) else [])}
            return _pending_persist(ctx, run, run_id, _terminate_decisions(entries),
                                    "terminate", key, scope)
        # 快照在任何业务写入之前读一次：缺失/失配即零写入退出（不再留半写状态）
        doc, _snapshot_bytes = fixed_snapshot(ctx, run)

        # ① 计划归一与覆盖核对（未知任务/漏项/重复一律拒，零写入）
        entries, problems = {}, []
        for position, item in enumerate(plan):
            where = f"plan[{position}]"
            if not isinstance(item, dict):
                problems.append({"entry": where, "reason": "entry must be an object"})
                continue
            task_id = item.get("object")
            if not isinstance(task_id, str) or not task_id:
                problems.append({"entry": where, "reason": "object must be a task id"})
                continue
            if task_id in entries:
                problems.append({"entry": where, "reason": "duplicate task in plan", "task": task_id})
                continue
            # `decision_ref` 可以是单个 Decision，也可以是 Decision 数组：
            # 与 `task-abandon` 的 `--decision` 同形——首项是处置决定，其余可带提交授权
            raw = item.get("decision_ref")
            candidates = raw if isinstance(raw, list) else [raw]
            decision = next((entry for entry in candidates
                             if isinstance(entry, dict)
                             and TERMINATE_DISPOSITIONS.get(str(entry.get("choice")))), None)
            if decision is None:
                problems.append({"entry": where,
                                 "reason": "decision_ref must contain an inline Decision whose "
                                           "choice is 放弃/abandon or 保留/keep",
                                 "task": task_id})
                continue
            disposition = TERMINATE_DISPOSITIONS.get(str(decision.get("choice")))
            if disposition is None:
                problems.append({"entry": where, "reason": "choice must be 放弃/abandon or 保留/keep",
                                 "task": task_id, "got": decision.get("choice")})
                continue
            if not isinstance(item.get("reason"), str) or not item["reason"].strip():
                problems.append({"entry": where, "reason": "reason must be non-empty", "task": task_id})
                continue
            entries[task_id] = {"decision": decision, "disposition": disposition,
                                "reason": item["reason"],
                                "wip": item.get("disposition"),
                                "decisions": [entry for entry in candidates if isinstance(entry, dict)]}
        generated = sorted({(mapping or {}).get("task_id")
                            for mapping in (run.get("task_map") or {}).values()
                            if (mapping or {}).get("task_id")})
        missing = [task_id for task_id in generated if task_id not in entries]
        unknown = sorted(set(entries) - set(generated))
        if missing:
            problems.append({"reason": "every generated task needs a disposition", "missing": missing})
        if unknown:
            problems.append({"reason": "plan names tasks that are not part of this run",
                             "unknown": unknown, "generated": generated})
        if problems:
            raise DefinitionError("WF_SEMANTIC_DECISION",
                                  {"reason": "termination plan is incomplete or invalid",
                                   "problems": problems},
                                  next_="按 problems 补齐计划后重入；本次未写入任何记录")

        # ② 整批预检：放弃项的 WIP 去向必须覆盖，否则零写入（机制稿 §7.4「先校改动处置」）
        preflight = []
        for task_id, entry in entries.items():
            task = tasks_mod.load_task(ctx.root, task_id)
            if not isinstance(task, dict):
                raise DefinitionError("WF_HISTORY_UNRESOLVED",
                                      {"reason": "task record missing", "task": task_id})
            if task.get("status") == "archived":
                # 中断后已归档的任务不再次放弃（机制稿 §7.4）
                preflight.append({"task": task_id, "status": "already_archived",
                                  "terminal": task.get("terminal")})
                continue
            if entry["disposition"] == "abandon":
                preview = tasks_mod._abandon_preview(ctx, task)
                uncovered = tasks_mod._uncovered_paths(preview["uncommitted"], entry["wip"])
                if uncovered:
                    raise DefinitionError("WF_WORKSPACE_UNRESOLVED",
                                          {"reason": "abandoned task has un-disposed WIP",
                                           "task": task_id, "uncovered": uncovered,
                                           "preview": preview},
                                          next_="给该任务补 disposition（逐路径去向）后重入；本次未写入任何记录")
        # ③ 固定关闭意图（closing.mode=abnormal）与动作
        action = actions_mod.new_action("run.terminate",
                                        writer_mod.owner_ref("session", key, scope),
                                        int(run.get("revision", 0)),
                                        {"run": run_id, "mode": "abnormal",
                                         "tasks": sorted(entries)},
                                        steps=["save_closing", "apply_tasks", "write_terminal",
                                               "persist_record"],
                                        head_before=actions_mod.head_of(ctx.root),
                                        targets=[{"kind": "run", "id": run_id}]
                                                + [{"kind": "task", "id": task_id}
                                                   for task_id in sorted(entries)])
        run = dict(run, action=action,
                   closing={"mode": "abnormal", "at": records.now_str(),
                            "decision": [entry["decision"] for entry in entries.values()],
                            "task_dispositions": {task_id: entry["disposition"]
                                                   for task_id, entry in entries.items()},
                            "next_step": None})
        records.write_json(run_path(ctx.root, run_id), run)

        # ④ 逐 task 应用（放弃复用 `_apply_abandon`；保留写 independent_resume）
        applied = {}
        for task_id in sorted(entries):
            entry = entries[task_id]
            task = tasks_mod.load_task(ctx.root, task_id)
            if task.get("status") == "archived":
                applied[task_id] = {"disposition": entry["disposition"],
                                    "status": "already_archived", "terminal": task.get("terminal")}
                continue
            if entry["disposition"] == "abandon":
                path = tasks_mod.task_dir(ctx.root, task_id)
                pass_through = [entry["decision"]] + [item for item in entry["decisions"]
                                                       if item is not entry["decision"]]
                payload = tasks_mod._apply_abandon(ctx, task_id, task, path,
                                                   pass_through, entry["wip"], holder)
                if isinstance(payload, dict) and payload.get("code") not in (None, "WF_OK"):
                    # `_apply_abandon` 的软停（缺去向/缺授权）原样上抛；实例保持 closing 待决
                    run = dict(run, closing=dict(run["closing"],
                                                 pending={"task": task_id,
                                                          "code": payload.get("code"),
                                                          "facts": payload.get("facts")}))
                    records.write_json(run_path(ctx.root, run_id), run)
                    return payload
                applied[task_id] = {"disposition": "abandon", "terminal": "abnormal"}
            else:
                directory = tasks_mod.task_dir(ctx.root, task_id)
                task = dict(task,
                            independent_resume={"decision": entry["decision"],
                                                "termination_action": action["id"],
                                                "reason": entry["reason"]})
                if task.get("status") == "in_progress" and not task.get("paused"):
                    task["paused"] = True
                    task["pause_reason"] = {"reason": "instance terminated; task kept",
                                            "at": records.now_str(),
                                            "by": "run.terminate", "run": run_id}
                tasks_mod.save_task(ctx.root, directory, task)
                applied[task_id] = {"disposition": "keep", "paused": bool(task.get("paused"))}

        # ⑤ 未生成的步骤记 not_executed（不建空壳任务）；`doc` 来自 ③ 之前的单次读取
        step_results = dict(run.get("step_results") or {})
        for step in _ordered_steps(doc or {}):
            if step["id"] in (run.get("task_map") or {}):
                continue
            if step["id"] in step_results:
                continue
            step_results[step["id"]] = {"kind": "not_executed", "at": records.now_str()}
        # 终态先落盘：`persist_pending` 表达"目标已成立、固定提交步骤未完成"（机制稿 §5.1）
        run = dict(run, step_results=step_results, terminal="abnormal",
                   ended_at=records.now_str(),
                   action=dict(action, state="persist_pending", next_step="persist_record"))
        records.write_json(run_path(ctx.root, run_id), run)
        # ④ 固定提交步骤：与 finish 共用同一实现（先写完成态、再提交、从 Git 读回核对）
        outcome = _persist_run_records(ctx, run, run_id, _terminate_decisions(entries),
                                       "terminate", key, scope)
        persisted = outcome["persisted"]
        commit_result = outcome["commit"]
        record_rel = outcome["record"]
    stale = [step for step in ("save_closing", "apply_tasks", "write_terminal")
             if not _terminate_step_done(ctx, run_id, step, entries)]
    if not persisted:
        stale = [step for step in stale if step != "persist_record"]
    if stale:
        raise DefinitionError("WF_PERSISTENCE_FAILED",
                              {"reason": "run.terminate step postcondition missing", "steps": stale},
                              next_="持写权重入 run terminate（已归档任务不重复放弃）")
    return codes.result(
        "WF_OK",
        object={"id": run_id},
        position_=codes.position(scope="run", action_id=run["action"]["id"],
                                 action_state=run["action"]["state"]),
        next_=("实例已异常终止并持久化：保留任务在新会话按 independent_resume 独立接续；"
               "**只报告退出完成与保留风险，不报告业务验收通过**"
               if persisted else
               "实例已异常终止，但**记录组尚未提交**：给出覆盖该路径的 commit 授权后重入续做"),
        facts={"run": run_id, "terminal": "abnormal", "ended_at": run["ended_at"],
               "closing": run["closing"], "applied": applied,
               "step_results": run["step_results"], "persisted": persisted,
               "record": record_rel, "commit": commit_result,
               "control_assertion": (run["action"].get("result") or {}).get("control_assertion")},
    )


def _terminate_step_done(ctx, run_id, step, entries):
    from . import tasks as tasks_mod

    run = load_run(ctx.root, run_id) or {}
    if step == "save_closing":
        return (run.get("closing") or {}).get("mode") == "abnormal"
    if step == "apply_tasks":
        for task_id, entry in entries.items():
            task = tasks_mod.load_task(ctx.root, task_id)
            if not isinstance(task, dict):
                return False
            if entry["disposition"] == "abandon" and task.get("status") != "archived":
                return False
            if entry["disposition"] == "keep" and not task.get("independent_resume"):
                return False
        return True
    if step == "write_terminal":
        return run.get("terminal") == "abnormal" and bool(run.get("ended_at"))
    return False


def resume(ctx, args):
    """`run resume --run <id> [--decision <path>]`：解除**实例**暂停（机制稿 §2.2、§7.3）。

    只做三件机制该做的事：核事实（绑定/写权/确实处于暂停）、**清 `paused`**、**记录依据**
    （谁、何时、可选的决定引用）。明确不做：**不恢复当前任务**（那是 `task-resume` 的另一个决定，
    它自核 WIP 指纹/身份/前置）、**不动 `cursor`**、**不推进**、不判断"是否该恢复"。

    `--decision` 是可选的：单纯解除不必写决定文件（恢复不属机制稿 §2 授权边界里的五类不可逆动作）；
    给了就存进 `resumed.decision`，并核 `subject` 含本实例 id 与**当前暂停时点**
    （拿上一次的决定来清这一次的暂停会被拒）。
    """
    from . import actions as actions_mod, cli, lock, session as session_mod, writer as writer_mod

    run_id = args.value("--run")
    decision_path = args.value("--decision")
    if not run_id:
        raise DefinitionError("WF_PATH_INVALID", {"reason": "run resume requires --run <id>"})
    decisions = cli._load_decision(decision_path) if decision_path else []
    key = ctx.key()
    with lock.acquire(ctx.root, holder_hint="run resume"):
        record = ctx.writer() or {}
        holder = record.get("holder") or {}
        if record.get("state") != "held" or holder.get("id") != key:
            raise cli.CliError("WF_WRITER_BUSY", {"holder": holder},
                               next_="由绑定该实例的会话解除暂停；他人持有写权时先走交接/恢复出口")
        scope = (holder.get("scope") or {}).get("object") or {}
        if scope.get("kind") != "run" or scope.get("id") != run_id:
            raise DefinitionError("WF_BINDING_MISMATCH",
                                  {"reason": "writer scope is not this run", "scope": scope})
        binding = session_mod.load_binding(ctx.root, key) or {}
        if ((binding.get("object") or {}).get("kind") != "run"
                or (binding.get("object") or {}).get("id") != run_id):
            raise DefinitionError("WF_BINDING_MISMATCH",
                                  {"reason": "session is not bound to this run",
                                   "binding": binding.get("object")})
        run = load_run(ctx.root, run_id)
        if not isinstance(run, dict):
            raise DefinitionError("WF_HISTORY_UNRESOLVED", {"reason": "run record missing",
                                                           "run": run_id})
        if run.get("terminal"):
            raise DefinitionError("WF_BINDING_MISMATCH",
                                  {"reason": "run already ended", "terminal": run.get("terminal")})
        paused_reason = run.get("paused_reason") or {}
        if not run.get("paused"):
            return codes.result("WF_OK", object={"id": run_id},
                                position_=codes.position(scope="run"),
                                next_="实例本不在暂停态（幂等，不写记录）",
                                facts={"run": run_id, "paused": False,
                                       "resumed": run.get("resumed")})
        # 可选决定：给了就核「这份决定是不是针对**当前这次**暂停」
        decision = None
        if decisions:
            decision = decisions[0]
            subject = decision.get("subject")
            text = " ".join(str(item) for item in subject) if isinstance(subject, list) else str(subject or "")
            problems = []
            if run_id not in text:
                problems.append({"reason": "decision subject must name this run", "run": run_id})
            if paused_reason.get("at") and paused_reason["at"] not in text:
                problems.append({"reason": "decision must bind the pause it lifts (subject must "
                                           "contain paused_reason.at)", "paused_at": paused_reason.get("at")})
            if not str(decision.get("choice") or "").strip():
                problems.append({"reason": "decision requires a non-empty choice"})
            if problems:
                raise DefinitionError("WF_SEMANTIC_DECISION",
                                      {"reason": "resume decision does not match the current pause",
                                       "problems": problems},
                                      next_="用针对本次暂停（含 paused_reason.at）的新决定重试，或不传 --decision")
        action = actions_mod.new_action("run.resume",
                                        writer_mod.owner_ref("session", key, scope),
                                        int(run.get("revision", 0)),
                                        {"run": run_id, "paused_at": paused_reason.get("at"),
                                         "decision": bool(decision)},
                                        steps=list(RESUME_STEPS),
                                        head_before=actions_mod.head_of(ctx.root),
                                        targets=[{"kind": "run", "id": run_id},
                                                 {"kind": "step", "id": (run.get("cursor") or {}).get("step_id")}])
        run = dict(run, action=action)
        records.write_json(run_path(ctx.root, run_id), run)
        resumed = {"at": records.now_str(), "session_key": key,
                   "lifted_paused_at": paused_reason.get("at")}
        if decision is not None:
            resumed["decision"] = {"choice": decision.get("choice"),
                                   "subject": decision.get("subject"),
                                   "reason": decision.get("reason"),
                                   "source": decision.get("source"),
                                   "at": decision.get("at")}
        # `paused_reason` 留作历史（历史事实不抹）；`paused=false` 是权威
        run = dict(run, paused=False, resumed=resumed,
                   action=actions_mod.complete(
                       action, summary="run.resume",
                       control_assertion=cli._control_assertion(
                           ctx, "run.resume", writer_mod.owner_ref("session", key, scope),
                           action, [f"run:{run_id}"])))
        records.write_json(run_path(ctx.root, run_id), run)
    stale = [step for step in RESUME_STEPS if not _resume_step_done(ctx, run_id, step)]
    if stale:
        raise DefinitionError("WF_PERSISTENCE_FAILED",
                              {"reason": "run.resume step postcondition missing", "steps": stale},
                              next_="重入 run resume（幂等）")
    return codes.result(
        "WF_OK",
        object={"id": run_id},
        position_=codes.position(scope="run", step_id=(run.get("cursor") or {}).get("step_id"),
                                 action_id=run["action"]["id"],
                                 action_state=run["action"]["state"]),
        next_="实例已解除暂停。**当前任务仍是暂停态**：要不要恢复它另跑 task-resume（那是另一个决定）；"
              "继续推进用 run advance，从 cursor 走",
        facts={"run": run_id, "paused": False, "resumed": run["resumed"],
               "cursor": run.get("cursor"),
               "current_task_paused": _current_task_paused(ctx, run),
               "control_assertion": run["action"]["result"]["control_assertion"]},
    )


def _resume_step_done(ctx, run_id, step):
    run = load_run(ctx.root, run_id) or {}
    if step == "clear_paused":
        return run.get("paused") is False
    if step == "record_resume":
        return bool((run.get("resumed") or {}).get("at"))
    return False


def _current_task_paused(ctx, run):
    """当前步骤的任务是否仍暂停（解除实例暂停**不会**动它）。"""
    from . import tasks as tasks_mod

    task_id = (run.get("cursor") or {}).get("task_id")
    if not task_id:
        return None
    record = tasks_mod.load_task(ctx.root, task_id)
    return None if record is None else bool(record.get("paused"))


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


def load_definition(root, workflow_id):
    """定位并解析定义：返回 `(doc, problems, text, path)`（机制稿 §7.2 的唯一定义加载入口）。

    `doc` 为 None 表示**不可解析**（文件缺失/无标记/非 JSON），`problems` 给出结构问题；
    两者都为 None/空表示可解析且结构成立。只读：不写任何记录。
    """
    text, path = _definition_text(root, workflow_id or "")
    if text is None:
        return None, [_problem(0, "definition file missing",
                               expected=f"{USER_WORKFLOWS_REL}/{workflow_id}.md")], None, path
    doc, problems = parse_definition(text)
    return doc, problems, text, path


