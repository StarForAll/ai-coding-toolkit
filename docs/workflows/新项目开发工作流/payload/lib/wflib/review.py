"""review.py — 审查发起、导入与判定（机制稿 §9.1、§9.2）。"""

from __future__ import annotations

import json
import os
import tempfile

from . import check as check_mod, config, records, writer as writer_mod
from .paths import join

REPORT_MARKER = "<!-- wf-review-report:v1 -->"
PROTOCOL = "wf-review-v1"
REVIEW_FOCUS = "范围、验收、契约/spec、跨层回归、可测性"

REPORT_FIELDS = (
    "protocol",
    "task-id",
    "round",
    "reviewer-id",
    "source-cli",
    "review-time",
    "review-focus",
    "check-anchor",
    "read-scope",
    "excluded-scope",
    "scope-exceptions",
    "axes",
    "findings",
    "verdict",
)


BLOCKING_SEVERITIES = ("blocker", "blocking", "critical", "high")

# 外部审查的固定五轴（机制稿 §9.2、skill wf-review）；内部两轴属 Check 自审，不在此列
REVIEW_AXES = ("range", "acceptance", "contract", "regression", "testability")
AXIS_CONCLUSIONS = ("pass", "fail", "uncovered")


def _axis_conclusion(value):
    """轴结果既可能是 {conclusion, basis} 也可能是裸结论字符串。"""
    if isinstance(value, dict):
        return value.get("conclusion")
    return value


class ReviewError(Exception):
    def __init__(self, code, facts=None):
        super().__init__(code)
        self.code = code
        self.facts = facts or {}


def staging_root(ctx, task_id):
    project_config, _problems = config.load_project_config(ctx.root, allow_missing=True)
    project_id = (project_config or {}).get("project_id") or "unknown-project"
    return os.path.join(tempfile.gettempdir(), "wf-review", str(project_id), task_id)


def slot_dir(ctx, task_id, round_no, slot):
    return os.path.join(staging_root(ctx, task_id), f"round-{int(round_no)}", slot)


def parse_report(text):
    if REPORT_MARKER not in text:
        raise ReviewError("WF_REVIEW_INVALID", {"reason": "report protocol marker missing"})
    tail = text.split(REPORT_MARKER, 1)[1]
    fence = tail.find("```json")
    if fence < 0:
        raise ReviewError("WF_REVIEW_INVALID", {"reason": "report json block missing"})
    start = fence + len("```json")
    end = tail.find("```", start)
    if end < 0:
        raise ReviewError("WF_REVIEW_INVALID", {"reason": "report json block not closed"})
    try:
        payload = records.loads(tail[start:end])
    except records.RecordInvalid as exc:
        raise ReviewError("WF_REVIEW_INVALID", {"reason": f"report json invalid: {exc}"})
    if not isinstance(payload, dict):
        raise ReviewError("WF_REVIEW_INVALID", {"reason": "report payload must be an object"})
    missing = [field for field in REPORT_FIELDS if field not in payload]
    if missing:
        raise ReviewError("WF_REVIEW_INVALID", {"missing_fields": missing})
    if payload.get("protocol") != PROTOCOL:
        raise ReviewError("WF_REVIEW_INVALID", {"reason": "unsupported protocol", "protocol": payload.get("protocol")})
    return payload


def _current_anchor(ctx, task):
    try:
        anchor, parts = check_mod.current_anchor(ctx, task)
    except check_mod.CheckError as exc:
        raise ReviewError(exc.code, exc.facts)
    return anchor, parts


def launch(ctx, task, request_path):
    from . import cli, lock

    request = records.load_json(request_path)
    if not isinstance(request, dict):
        raise ReviewError("WF_PATH_INVALID", {"reason": "launch request missing or not an object"})
    check = task.get("check") or {}
    if check.get("result") != "pass":
        raise ReviewError("WF_CHECK_FAILED", {"reason": "launch requires a valid Check pass"})
    implementation = request.get("implementation_clis") or []
    slots = request.get("slots") or []
    if not isinstance(implementation, list) or not implementation:
        raise ReviewError("WF_REVIEW_INVALID", {"reason": "implementation_clis required"})
    if not isinstance(slots, list) or not slots:
        raise ReviewError("WF_REVIEW_INVALID", {"reason": "at least one slot required"})
    for slot in slots:
        if not isinstance(slot, dict) or not slot.get("slot") or not slot.get("reviewer_cli"):
            raise ReviewError("WF_REVIEW_INVALID", {"reason": "slot requires slot id and reviewer_cli"})
        if slot["reviewer_cli"] in implementation:
            raise ReviewError("WF_REVIEW_INVALID", {"reason": "reviewer CLI must differ from implementation CLIs",
                                                    "slot": slot})
    if not request.get("export_decision"):
        raise ReviewError("WF_REVIEW_INVALID", {"reason": "export authorization decision required"})
    submitted = request.get("submitted_scope") or {}
    slots_material = (("diff",), ("requirement", "requirements"), ("test_results", "tests"))
    missing_material = [names[0] for names in slots_material
                        if not any(submitted.get(name) for name in names)]
    if missing_material:
        # 三类材料是审查输入的最小集，缺一即无法覆盖必要检查面（机制稿 §9.2）
        raise ReviewError("WF_REVIEW_INVALID",
                          {"reason": "submitted_scope lacks required material",
                           "missing": missing_material, "submitted": sorted(submitted)})
    anchor, _parts = _current_anchor(ctx, task)
    with lock.acquire(ctx.root, holder_hint="review-launch"):
        _record, holder = ctx.require_held(task=task.get("id"))
        path = _task_dir(ctx, task)
        from . import tasks as tasks_mod

        task = records.load_json(os.path.join(path, "task.json"))
        reviews = task.setdefault("reviews", {})
        round_no = int(reviews.get("last_round") or 0) + 1
        attempts = list(reviews.get("attempts") or [])
        if not attempts:
            attempts = [{"number": 1, "rework_ref": None, "round_ids": [], "outcome": None}]
        current_attempt = attempts[-1]
        used = list(current_attempt.get("round_ids") or [])
        if len(used) >= 2:
            raise ReviewError("WF_SEMANTIC_DECISION",
                              {"reason": "同一实施尝试最多两轮；两轮用尽须由人发起返工",
                               "attempt": current_attempt.get("number"), "rounds": used})
        attempt = current_attempt.get("number") or 1
        temp_paths = []
        for slot in slots:
            directory = slot_dir(ctx, task.get("id"), round_no, slot["slot"])
            os.makedirs(directory, exist_ok=True)
            request_payload = {
                "task-id": task.get("id"),
                "round": round_no,
                "reviewer-id": slot["slot"],
                "review-focus": REVIEW_FOCUS,
                "check-anchor": {"check_id": check.get("id"), "check_anchor": anchor},
                "submitted_scope": request.get("submitted_scope") or {},
                "readable_scope": request.get("readable_scope") or {},
                "exclusions": request.get("exclusions") or [],
            }
            records.write_json(os.path.join(directory, "request.json"), request_payload)
            temp_paths.append(directory)
        entry = {
            "round": round_no,
            "attempt": attempt,
            "decision": request.get("export_decision"),
            "implementation_clis": implementation,
            "slots": slots,
            "anchor": {"check_id": check.get("id"), "check_anchor": anchor},
            "submitted_scope": request.get("submitted_scope") or {},
            "readable_scope": request.get("readable_scope") or {},
            "exclusions": request.get("exclusions") or [],
            "export_decision": request.get("export_decision"),
            "temp_paths": temp_paths,
        }
        if len(slots) < 2:
            entry["degraded"] = "single-provider"
        launches = list(reviews.get("launches") or [])
        launches.append(entry)
        reviews["launches"] = launches
        reviews["last_round"] = round_no
        current_attempt["round_ids"] = sorted(set(used) | {round_no})
        reviews["attempts"] = attempts
        inputs = {"task": task.get("id"), "round": round_no}
        task, action = tasks_mod._start_task_action(
            ctx, path, task, "review.launch", holder, inputs, ["declare", "stage_requests"]
        )
        task, assertion = tasks_mod._finish_task_action(
            ctx, path, task, "review.launch", holder, inputs, action, evidence_refs=temp_paths
        )
    commands = [
        f"/wf-review --task-id {task.get('id')} --round {round_no} --reviewer-id {slot['slot']} "
        f"--review-focus {REVIEW_FOCUS} --request {os.path.join(directory, 'request.json')}"
        for slot, directory in zip(slots, temp_paths)
    ]
    from . import codes

    return codes.result(
        "WF_OK",
        object={"id": task.get("id"), "name": task.get("title")},
        position_=codes.position(scope="task", phase=task.get("phase"), task_id=task.get("id"),
                                 action_id=task["action"]["id"], action_state=task["action"]["state"]),
        next_="由人在 reviewer CLI 会话中调用上述 skill 文本；报告写入各自暂存目录",
        facts={
            "round": round_no,
            "attempt": attempt,
            "anchor": {"check_id": check.get("id"), "check_anchor": anchor},
            "temp_paths": temp_paths,
            "degraded": entry.get("degraded"),
            "paste_text": commands,
            "control_assertion": assertion,
        },
    )


def _task_dir(ctx, task):
    from . import tasks as tasks_mod

    directory = tasks_mod.task_dir(ctx.root, task.get("id"))
    if not directory:
        raise ReviewError("WF_RECORD_INVALID", {"missing_task": task.get("id")})
    return directory


def import_report(ctx, task, round_no, slot, report_path):
    from . import cli, lock

    if not os.path.isabs(report_path):
        raise ReviewError("WF_PATH_INVALID", {"reason": "report path must be absolute", "path": report_path})
    try:
        with open(report_path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except OSError as exc:
        raise ReviewError("WF_PATH_INVALID", {"reason": f"report unreadable: {exc}", "path": report_path})
    payload = parse_report(text)
    if str(payload.get("task-id")) != str(task.get("id")):
        raise ReviewError("WF_REVIEW_INVALID", {"reason": "task-id mismatch", "report": payload.get("task-id")})
    if int(payload.get("round") or 0) != int(round_no):
        raise ReviewError("WF_REVIEW_INVALID", {"reason": "round mismatch", "report": payload.get("round")})
    if str(payload.get("reviewer-id")) != str(slot):
        raise ReviewError("WF_REVIEW_INVALID", {"reason": "reviewer-id mismatch", "report": payload.get("reviewer-id")})
    with lock.acquire(ctx.root, holder_hint="review-import"):
        _record, holder = ctx.require_held(task=task.get("id"))
        path = _task_dir(ctx, task)
        from . import tasks as tasks_mod

        task = records.load_json(os.path.join(path, "task.json"))
        reviews = task.get("reviews") or {}
        launch = None
        for entry in reviews.get("launches") or []:
            if int(entry.get("round") or 0) == int(round_no):
                launch = entry
                break
        if not launch:
            raise ReviewError("WF_SEMANTIC_DECISION", {"reason": "round was not launched", "round": round_no})
        slot_paths = [directory for directory in launch.get("temp_paths") or []
                      if os.path.basename(directory.rstrip(os.sep)) == slot]
        if not slot_paths:
            raise ReviewError("WF_REVIEW_INVALID", {"reason": "slot not declared in launch", "slot": slot})
        staging = os.path.realpath(slot_paths[0])
        real_report = os.path.realpath(report_path)
        if not real_report.startswith(staging + os.sep):
            raise ReviewError("WF_PATH_INVALID", {"reason": "report must come from its staging directory",
                                                  "expected": staging, "actual": real_report})
        anchor, _parts = _current_anchor(ctx, task)
        if payload.get("check-anchor", {}).get("check_anchor") != anchor:
            raise ReviewError("WF_REVIEW_INVALID", {"reason": "check-anchor mismatch", "report": payload.get("check-anchor")})
        target_dir = os.path.join(path, "review", f"review-round-{int(round_no)}")
        os.makedirs(target_dir, exist_ok=True)
        target = os.path.join(target_dir, f"{slot}.md")
        existing_digest = records.file_digest(target)
        incoming_digest = "sha256:" + records.sha256_hex(text.encode("utf-8"))
        if existing_digest and existing_digest != incoming_digest:
            # 同路径不同摘要即冲突：不覆盖、不留旧结论（机制稿 §9.2）
            raise ReviewError("WF_REVIEW_INVALID",
                              {"reason": "report digest differs from the imported one",
                               "slot": slot, "existing": existing_digest, "incoming": incoming_digest},
                              )
        if existing_digest:
            # 同摘要重入：幂等，不重复写
            pass
        else:
            records.atomic_write(target, text)
        digest = records.file_digest(target)
        imported = [entry for entry in reviews.get("imported") or []
                    if not (int(entry.get("round") or 0) == int(round_no) and entry.get("slot") == slot)]
        imported.append({"round": int(round_no), "slot": slot,
                         "report_path": os.path.relpath(target, str(ctx.root)).replace(os.sep, "/"),
                         "report_digest": digest, "anchor": {"check_id": (task.get("check") or {}).get("id"),
                                                             "check_anchor": anchor}})
        reviews["imported"] = imported
        task["reviews"] = reviews
        inputs = {"task": task.get("id"), "round": int(round_no), "slot": slot}
        task, action = tasks_mod._start_task_action(
            ctx, path, task, "review.import", holder, inputs, ["verify_metadata", "verify_anchor", "publish"]
        )
        task, assertion = tasks_mod._finish_task_action(
            ctx, path, task, "review.import", holder, inputs, action, evidence_refs=[digest]
        )
    from . import codes

    return codes.result(
        "WF_OK",
        object={"id": task.get("id"), "name": task.get("title")},
        position_=codes.position(scope="task", phase=task.get("phase"), task_id=task.get("id")),
        next_="导入另一槽位报告后 review-decide",
        facts={"round": int(round_no), "slot": slot, "report_digest": digest,
               "verdict": payload.get("verdict"), "findings": payload.get("findings"),
               "control_assertion": assertion},
    )


def decide(ctx, task, round_no, plan_path, unavailable_path):
    from . import cli, lock

    dispositions = []
    if plan_path:
        loaded = records.load_json(plan_path)
        if loaded is None:
            raise ReviewError("WF_PATH_INVALID", {"reason": "plan file missing", "path": plan_path})
        dispositions = loaded if isinstance(loaded, list) else [loaded]
    unavailable = None
    if unavailable_path:
        unavailable = records.load_json(unavailable_path)
        if not isinstance(unavailable, dict) or not unavailable.get("evidence"):
            raise ReviewError("WF_SEMANTIC_DECISION", {"reason": "unavailable declaration requires evidence"})
    with lock.acquire(ctx.root, holder_hint="review-decide"):
        _record, holder = ctx.require_held(task=task.get("id"))
        path = _task_dir(ctx, task)
        from . import tasks as tasks_mod

        task = records.load_json(os.path.join(path, "task.json"))
        reviews = task.get("reviews") or {}
        launch = None
        for entry in reviews.get("launches") or []:
            if int(entry.get("round") or 0) == int(round_no):
                launch = entry
                break
        imported = [entry for entry in reviews.get("imported") or [] if int(entry.get("round") or 0) == int(round_no)]
        anchor, _parts = _current_anchor(ctx, task)
        if unavailable:
            verdict = "unavailable"
            facts = {"unavailable": unavailable}
        else:
            if not imported:
                raise ReviewError("WF_REVIEW_INVALID", {"reason": "no imported report for this round"})
            declared_slot_ids = [slot.get("slot") for slot in (launch or {}).get("slots") or []
                                 if isinstance(slot, dict) and slot.get("slot")]
            if len(declared_slot_ids) < 2:
                raise ReviewError("WF_REVIEW_INVALID",
                                  {"reason": "launch must declare at least two reviewer slots",
                                   "declared": declared_slot_ids})
            imported_slots = [entry.get("slot") for entry in imported]
            missing_slots = [slot for slot in declared_slot_ids if slot not in imported_slots]
            if missing_slots:
                # 声明的槽位都要有报告：缺一即输入不完整，不能按已导入的部分判 pass
                raise ReviewError("WF_REVIEW_INVALID",
                                  {"reason": "declared slots missing reports", "missing": missing_slots,
                                   "imported": imported_slots})
            source_clis = []
            declared_slots = {slot.get("slot"): slot.get("reviewer_cli")
                              for slot in (launch or {}).get("slots") or []
                              if isinstance(slot, dict) and slot.get("slot")}
            problems = []       # 输入不成立：报告/身份/锚点/材料不合规 → 拒绝，不写结论
            failures = []       # 有效审查给出的未通过结论 → 记 fail，成为复盘触发事实
            for entry in imported:
                rel = entry.get("report_path")
                if not rel:
                    problems.append({"slot": entry.get("slot"), "reason": "imported entry lacks report_path"})
                    continue
                report_abs = join(ctx.root, rel)
                # 导入端防住"同路径换内容"，判定端必须同样重核摘要：否则报告文件可被事后改写
                current_digest = records.file_digest(report_abs)
                if entry.get("report_digest") != current_digest:
                    problems.append({"slot": entry.get("slot"), "reason": "report file changed after import",
                                     "recorded": entry.get("report_digest"), "current": current_digest,
                                     "path": rel})
                    continue
                try:
                    with open(report_abs, "r", encoding="utf-8") as handle:
                        payload = parse_report(handle.read())
                except OSError as exc:
                    problems.append({"slot": entry.get("slot"), "reason": "report file unreadable",
                                     "path": rel, "error": str(exc)})
                    continue
                source_clis.append(payload.get("source-cli"))
                report_anchor = payload.get("check-anchor")
                if not isinstance(report_anchor, dict) or report_anchor.get("check_anchor") != anchor:
                    # 失效锚点一律重审，不能因旧文件仍在而复用（机制稿 §9.2）
                    problems.append({"slot": entry.get("slot"), "reason": "report anchor does not match current check",
                                     "report_anchor": report_anchor, "current_anchor": anchor})
                declared_cli = declared_slots.get(entry.get("slot"))
                if declared_cli and payload.get("source-cli") != declared_cli:
                    problems.append({"slot": entry.get("slot"), "reason": "report source-cli not declared for slot",
                                     "source_cli": payload.get("source-cli"), "declared": declared_cli})
                for field in ("read-scope", "excluded-scope"):
                    if not payload.get(field):
                        problems.append({"slot": entry.get("slot"), "reason": f"report lacks {field}"})
                # 报告自身声明的未覆盖/例外项即未决事实，不能只看总 verdict（机制稿 §9.2）
                for item in payload.get("scope-exceptions") or []:
                    failures.append({"slot": entry.get("slot"), "reason": "report declares an uncovered exception",
                                     "exception": item})
                axes = payload.get("axes") or {}
                if not isinstance(axes, dict):
                    problems.append({"slot": entry.get("slot"), "reason": "report axes must be an object"})
                    axes = {}
                missing_axes = [axis for axis in REVIEW_AXES if axis not in axes]
                if missing_axes:
                    # 报告未覆盖必要检查面：属输入不成立，不能当通过（机制稿 §9.2 五轴）
                    problems.append({"slot": entry.get("slot"), "reason": "report does not cover all review axes",
                                     "missing": missing_axes, "expected": list(REVIEW_AXES)})
                for axis, result in sorted(axes.items()):
                    if axis not in REVIEW_AXES:
                        problems.append({"slot": entry.get("slot"), "reason": "unknown review axis", "axis": axis})
                        continue
                    conclusion = _axis_conclusion(result)
                    if conclusion not in AXIS_CONCLUSIONS:
                        problems.append({"slot": entry.get("slot"), "reason": "review axis conclusion invalid",
                                         "axis": axis, "conclusion": conclusion})
                    elif conclusion != "pass":
                        failures.append({"slot": entry.get("slot"), "reason": "review axis is not pass",
                                         "axis": axis, "conclusion": conclusion})
                need = payload.get("material-gaps") or payload.get("missing-materials")
                if need:
                    failures.append({"slot": entry.get("slot"), "reason": "report declares required material gaps",
                                     "gaps": need})
                blocking = [item for item in payload.get("findings") or []
                            if isinstance(item, dict) and item.get("severity") in BLOCKING_SEVERITIES]
                if blocking:
                    failures.append({"slot": entry.get("slot"), "reason": "report carries blocking findings",
                                     "findings": blocking})
                if payload.get("verdict") != "pass":
                    failures.append({"slot": entry.get("slot"), "reason": "report verdict is not pass",
                                     "verdict": payload.get("verdict")})
            if problems:
                raise ReviewError("WF_REVIEW_INVALID", {"problems": problems})
            distinct = sorted(set(source_clis))
            implementation = set((launch or {}).get("implementation_clis") or [])
            verdict = "pass"
            facts = {"reviewer_clis": distinct}
            reasons = []
            if len(distinct) < 2:
                reasons.append({"reason": "人数不合格：需要两个彼此不同的审查 CLI", "reviewer_clis": distinct})
            if implementation & set(distinct):
                reasons.append({"reason": "审查 CLI 与实施 CLI 重叠", "reviewer_clis": distinct,
                                "implementation": sorted(implementation)})
            if failures:
                reasons.append({"reason": "审查未通过", "failures": failures})
            if reasons:
                verdict = "fail"
                facts = dict(facts, reasons=reasons)
                if len(reasons) == 1:
                    facts.update({key: value for key, value in reasons[0].items() if key != "reason"})
                    facts["reason"] = reasons[0]["reason"]
        result = {
            "verdict": verdict,
            "round": int(round_no),
            "check_id": (task.get("check") or {}).get("id"),
            "anchor": {"check_id": (task.get("check") or {}).get("id"), "check_anchor": anchor},
            "imported": [{"slot": entry.get("slot"), "report_digest": entry.get("report_digest")} for entry in imported],
            "facts": facts,
            "degraded": (launch or {}).get("degraded"),
        }
        reviews["result"] = result
        # 历史 fail 事实须能重建：把本轮结论落到所在尝试的 outcome（机制稿 §9.2、§11.2）
        attempts = list(reviews.get("attempts") or [])
        for entry in attempts:
            if int(round_no) in (entry.get("round_ids") or []):
                # 尝试级 outcome 单调保留历史失败：同一尝试内前轮 fail 不被后轮 pass 覆盖，
                # 否则 retrospective_triggers 重建不出 review_fail（机制稿 §11.2 的「历史 result=fail」）
                if entry.get("outcome") != "fail":
                    entry["outcome"] = verdict
                break
        if attempts:
            reviews["attempts"] = attempts
        reviews["dispositions"] = list(reviews.get("dispositions") or []) + dispositions
        task["reviews"] = reviews
        inputs = {"task": task.get("id"), "round": int(round_no), "verdict": verdict}
        task, action = tasks_mod._start_task_action(
            ctx, path, task, "review.decide", holder, inputs, ["derive_verdict", "record_dispositions"]
        )
        task, assertion = tasks_mod._finish_task_action(
            ctx, path, task, "review.decide", holder, inputs, action,
            evidence_refs=[entry.get("report_path") for entry in imported if entry.get("report_path")],
        )
    from . import codes

    code = "WF_OK" if verdict == "pass" else ("WF_REVIEW_UNAVAILABLE" if verdict == "unavailable" else "WF_REVIEW_INVALID")
    return codes.result(
        code,
        object={"id": task.get("id"), "name": task.get("title")},
        position_=codes.position(scope="task", phase=task.get("phase"), task_id=task.get("id")),
        next_="verdict=pass 后由人调用 finish" if verdict == "pass" else "补真实审查或按异常退出处置",
        facts={"result": result, "control_assertion": assertion},
    )
