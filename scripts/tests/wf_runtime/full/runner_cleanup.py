#!/usr/bin/env python3
"""runner_cleanup.py — 清理证据的唯一解释点与 run 最终收口。

三层职责分开记录（父任务 design §2.1/§3.1）：

1. `assess_execution(payload)`：把一次 `execution.run()` 的结果解释成
   `cleaned/unknown/failed`；结构缺失、类型不符、矛盾报告一律 unknown，禁止删除；
2. `assess_run(...)`：聚合 root 控制结果、`commands/` receipts、unit 证据与 gate 报告，
   给出 `cleanup_state`（进程/本地资源事实）、`evidence_state`（证据完整性）与原因；
   目标成败不推导清理许可，清理失败也不改写目标 rc；
3. `finalize(...)`：只有 `cleanup_state=cleaned` 才按固定角色序删除本 run owned 资源，
   逐项报告 removed/failed/not-attempted，首次失败即停、不重试、不重建已删项。

本模块不杀进程、不扫描缓存根、不发布摘要；CLI 只供人工排障与测试读取（root 入口不依赖
stdout 协议）。
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))  # scripts/tests：wf_test_release 等作者侧模块

import resource_lifecycle as lifecycle  # noqa: E402

FAULT_ENV = "WF_RUNNER_FINALIZE_FAULT"
FAULT_SWITCH = "WF_TEST_FAULT_INJECTION"
FAULT_VALUES = (
    "assess-exception", "assess-none", "assess-empty", "assess-malformed",
    "assess-contradictory", "delete-oserror", "delete-after-first",
    "control-write-oserror", "summary-exception", "summary-malformed",
    "state-finish-oserror", "metrics-write-oserror", "metrics-missing",
    "metrics-truncated", "metrics-old-run", "metrics-input-mismatch",
)
STATUSES = ("passed", "failed", "cancelled", "timeout")


class CleanupError(Exception):
    """可预期的清理/聚合拒绝。"""


def validate_fault_selector():
    """校验受限故障选择器；未开总开关时点名变量一律忽略。"""
    requested = os.environ.get(FAULT_ENV)
    if not requested:
        return None
    if os.environ.get(FAULT_SWITCH) != "1":
        raise CleanupError(f"{FAULT_ENV} 只在 {FAULT_SWITCH}=1 时生效")
    if requested not in FAULT_VALUES:
        raise CleanupError(f"未知故障点：{requested!r}（可选 {'|'.join(FAULT_VALUES)}）")
    import fixture_scope
    if fixture_scope.current_scope() is None:
        raise CleanupError("受限故障注入需要有效 owned test scope")
    return requested


def fault_active(*names):
    if not names:
        return False
    if os.environ.get(FAULT_SWITCH) != "1":
        return False
    return os.environ.get(FAULT_ENV) in names


def assess_execution(payload):
    """唯一解释 execution supervision 的函数（不对象/缺字段/矛盾 → unknown）。"""
    if not isinstance(payload, dict):
        return {"cleanup_state": "unknown", "reason": "execution result is not an object"}
    status = payload.get("status")
    if status not in STATUSES:
        return {"cleanup_state": "unknown", "reason": f"execution status invalid: {status!r}"}
    supervision = payload.get("supervision")
    if not isinstance(supervision, dict):
        return {"cleanup_state": "unknown", "reason": "supervision is missing"}
    state = supervision.get("cleanup_state")
    if state not in ("cleaned", "unknown", "failed"):
        return {"cleanup_state": "unknown", "reason": f"cleanup_state invalid: {state!r}"}
    infrastructure = supervision.get("infrastructure_error")
    if not isinstance(infrastructure, bool):
        return {"cleanup_state": "unknown", "reason": "infrastructure_error is missing"}
    if state == "cleaned":
        target_rc = supervision.get("target_rc")
        cancelled = status in ("cancelled", "timeout")
        if not isinstance(target_rc, int) or isinstance(target_rc, bool):
            if not cancelled:
                return {"cleanup_state": "unknown",
                        "reason": "clean result without target rc evidence"}
        if infrastructure:
            return {"cleanup_state": "unknown",
                    "reason": "clean result contradicts infrastructure_error"}
    return {"cleanup_state": state, "reason": str(supervision.get("termination_reason") or "")}


def read_children(results_root, run_id):
    """读取 `commands/` receipts（ledger）。未知/坏子记录报问题，不静默忽略。"""
    root = Path(results_root)
    commands_dir = root / lifecycle.COMMANDS_DIR
    commands, problems = [], []
    if not commands_dir.is_dir():
        if commands_dir.exists():
            problems.append({"kind": "malformed", "detail": f"commands is not a directory"})
        return {"commands": commands, "problems": problems}
    known = set()
    for path in sorted(commands_dir.iterdir()):
        if path.is_symlink() or not path.is_file() or not path.name.endswith(".json"):
            problems.append({"kind": "unexpected", "detail": str(path)})
            continue
        known.add(path.name)
        try:
            record = lifecycle.read_receipt(path)
        except lifecycle.LifecycleError as exc:
            problems.append({"kind": "unreadable", "detail": str(exc)})
            continue
        if record.get("evidence_scope") != "managed-child":
            problems.append({"kind": "wrong-domain", "detail": f"{path}: scope={record.get('evidence_scope')!r}"})
            continue
        if record.get("run_id") != run_id:
            problems.append({"kind": "wrong-run", "detail": f"{path}: run_id={record.get('run_id')!r}"})
            continue
        if record.get("state") != "finished":
            problems.append({"kind": "pending", "detail": f"{path}: state={record.get('state')!r}",
                             "retained": str(path)})
            continue
        local = record.get("local_cleanup")
        result = record.get("result")
        supervision = record.get("supervision")
        assessment = assess_execution({"status": (result or {}).get("status"),
                                       "supervision": supervision})
        if assessment["cleanup_state"] != "cleaned":
            problems.append({"kind": assessment["cleanup_state"], "detail": f"{path}: {assessment['reason']}",
                             "retained": record.get("log_path") or str(path)})
        elif local not in ("none", "removed", "retained-keep"):
            problems.append({"kind": "local-" + str(local), "detail": f"{path}: local_cleanup={local!r}",
                             "retained": record.get("log_path") or str(path)})
        commands.append({"path": str(path), "command_id": record["command_id"],
                         "argv": record.get("argv"), "rc": (result or {}).get("rc"),
                         "status": (result or {}).get("status"),
                         "cleanup_state": assessment["cleanup_state"],
                         "local_cleanup": local,
                         "retained_paths": record.get("retained_paths") or []})
    return {"commands": commands, "problems": problems}


def _unit_evidence(results_root, run_id, plan):
    """逐计划单元核 unit_execution（缺失/错 ID/旧 JSON/伪 prep 都报问题）。"""
    root = Path(results_root)
    units, problems = [], []
    for entry in (plan or {}).get("units") or []:
        name = entry["name"]
        path = root / f"{name}.test.log.json"
        if not path.exists():
            problems.append({"kind": "missing-unit", "detail": name})
            continue
        try:
            record = lifecycle.read_json_object(path, f"unit result {name}")
        except lifecycle.LifecycleError as exc:
            problems.append({"kind": "unreadable-unit", "detail": str(exc)})
            continue
        unit_execution = record.get("unit_execution")
        if not isinstance(unit_execution, dict):
            problems.append({"kind": "no-unit-execution", "detail": name})
            continue
        if unit_execution.get("schema_version") != lifecycle.UNIT_EXECUTION_SCHEMA or \
                isinstance(unit_execution.get("schema_version"), bool):
            problems.append({"kind": "unit-schema", "detail": name})
            continue
        if unit_execution.get("unit") != name:
            problems.append({"kind": "unit-name", "detail": name})
            continue
        if unit_execution.get("run_id") != run_id:
            problems.append({"kind": "unit-wrong-run",
                             "detail": f"{name}: run_id={unit_execution.get('run_id')!r}"})
            continue
        if unit_execution.get("state") not in ("passed", "prep-failed"):
            problems.append({"kind": "unit-state", "detail": name})
            continue
        row = unit_execution.get("result_row")
        if not isinstance(row, list) or len(row) != 5 or row[0] != name:
            problems.append({"kind": "unit-row", "detail": name})
            continue
        units.append({"unit": name, "state": unit_execution["state"],
                      "invocation_id": unit_execution.get("invocation_id"),
                      "command_count": len(unit_execution.get("command_evidence") or [])})
    return {"units": units, "problems": problems}


def validate_assessment(assessment):
    """核聚合结果的结构与内部一致性；矛盾（cleaned 但仍有保留/问题）按 unknown。"""
    if not isinstance(assessment, dict) or not assessment:
        raise CleanupError("assessment is not a non-empty object")
    state = assessment.get("cleanup_state")
    if state not in ("cleaned", "unknown", "failed"):
        raise CleanupError(f"assessment cleanup_state invalid: {state!r}")
    problems = assessment.get("problems")
    if not isinstance(problems, list):
        raise CleanupError("assessment problems is not a list")
    retained = assessment.get("retained_paths")
    if not isinstance(retained, list):
        raise CleanupError("assessment retained_paths is not a list")
    if state == "cleaned":
        if problems:
            raise CleanupError("assessment claims cleaned while problems remain")
        if retained:
            raise CleanupError("assessment claims cleaned while paths are retained")
        target = assessment.get("target")
        if not isinstance(target, dict) or target.get("cleanup_state") != "cleaned":
            raise CleanupError("assessment claims cleaned without a cleaned target")
    return assessment


def assess_run(results_root, run_id, plan, control, gate_report):
    """聚合 root 控制结果、child receipts、unit 证据与 gate 报告。

    `cleanup_state` 只回答“进程与本地资源是否确认释放”；unit/gate 证据缺失进入
    `evidence_state`，不会把“没跑完”误记成“没清理”，也不会反过来放宽清理许可。
    """
    reasons, cleanup_problems, evidence_problems, retained = [], [], [], []
    control_assessment = assess_execution(control)
    if control_assessment["cleanup_state"] != "cleaned":
        cleanup_problems.append({"kind": "root-" + control_assessment["cleanup_state"],
                                 "detail": control_assessment["reason"] or "root control not cleaned"})
    children = read_children(results_root, run_id)
    cleanup_problems.extend(children["problems"])
    for item in children["problems"]:
        if item.get("retained"):
            retained.append(item["retained"])
    units = _unit_evidence(results_root, run_id, plan)
    evidence_problems.extend(units["problems"])
    gate_state = "unknown" if not isinstance(gate_report, dict) else (
        "complete" if gate_report.get("ok") else "incomplete")
    if gate_state == "unknown":
        evidence_problems.append({"kind": "gate-report", "detail": "gate report is missing"})
    elif gate_state == "incomplete":
        evidence_problems.append({"kind": "gate-rows", "detail": "result rows do not match the frozen plan"})
    for item in cleanup_problems:
        reasons.append(f"cleanup: {item['kind']}: {item['detail']}")
    for item in evidence_problems:
        reasons.append(f"evidence: {item['kind']}: {item['detail']}")
    if any(item["kind"] in ("failed", "root-failed") or item["kind"].startswith("local-failed")
           for item in cleanup_problems):
        cleanup_state = "failed"
    elif cleanup_problems:
        cleanup_state = "unknown"
    else:
        cleanup_state = "cleaned"
    return {
        "schema_version": 1,
        "run_id": run_id,
        "cleanup_state": cleanup_state,
        "evidence_state": "incomplete" if evidence_problems else "complete",
        "reasons": reasons[:50],
        "problems": cleanup_problems,
        "evidence_problems": evidence_problems,
        "retained_paths": sorted(set(retained)),
        "target": {"cleanup_state": control_assessment["cleanup_state"],
                   "status": control.get("status"), "rc": control.get("rc")},
        "commands": children["commands"],
        "units": units["units"],
        "gate": gate_report,
        "repro": (gate_report or {}).get("repro") if isinstance(gate_report, dict) else None,
    }


def resource_plan(plan, results_root):
    """按固定角色序给出本次 run 实际存在的资源（路径只从已核 plan/固定位派生）。

    是否 owned 由 `fixture_scope.remove` 的真实 marker 校验决定：残留但无 marker 的目录
    必须如实报 failed（保留现场），不能因为“不归我”就静默跳过。
    """
    fix = (plan or {}).get("fix")
    roles = []
    if fix:
        roles.append(("FIX", fix))
        roles.append(("LEGACY_FIXTURE_ROOT", fix + ".legacy"))
    roles.append(("RUN_TEMPLATE", str(Path(results_root) / "template")))
    # 默认 dev 发行建在本代结果目录里，只有本代有归属；显式 --no-build 消费共享发行，
    # 共享根只释放消费租约（不由本 run 删除）。
    if (plan or {}).get("fixture_deploy") == "dev" and not int((plan or {}).get("no_build") or 0):
        private = (plan or {}).get("test_release_root")
        if private:
            roles.append(("PRIVATE_RELEASE", private))
    return [(role, path) for role, path in roles if os.path.lexists(path)]


def finalize(results_root, plan, assessment):
    """按角色序删除 owned 资源；返回严格报告（不打印 GATE-OK、不重试）。"""
    assessment = validate_assessment(assessment)
    report = {"cleanup_state": assessment["cleanup_state"], "removed": [], "failed": [],
              "not_attempted": [], "retained_paths": list(assessment["retained_paths"]),
              "reasons": list(assessment["reasons"])}
    resources = resource_plan(plan, results_root)
    if assessment["cleanup_state"] != "cleaned":
        report["not_attempted"] = [role for role, _ in resources]
        return report
    import fixture_scope
    import wf_test_release

    if fault_active("delete-oserror") and resources:
        report["failed"] = [resources[0][0]]
        report["not_attempted"] = [role for role, _ in resources[1:]]
        report["cleanup_state"] = "failed"
        report["reasons"].append("injected delete failure before first removal")
        report["retained_paths"].append(resources[0][1])
        return report
    for index, (role, path) in enumerate(resources):
        if fault_active("delete-after-first") and index == 1:
            report["failed"] = [role]
            report["cleanup_state"] = "failed"
            report["reasons"].append("injected delete failure after first removal")
            report["retained_paths"].append(path)
            report["not_attempted"] = [item[0] for item in resources[index + 1:]]
            return report
        try:
            if role == "PRIVATE_RELEASE":
                wf_test_release.cleanup_private_release(path)
            else:
                fixture_scope.remove(path)
        except (fixture_scope.FixtureError, wf_test_release.TestReleaseError, OSError) as exc:
            report["failed"] = [role]
            report["cleanup_state"] = "failed"
            report["reasons"].append(f"{role}: {exc}")
            report["retained_paths"].append(path)
            report["not_attempted"] = [item[0] for item in resources[index + 1:]]
            return report
        report["removed"].append(role)
    return report


def _load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def main(argv=None):
    parser = argparse.ArgumentParser(description="清理证据聚合与 finalize（只供排障/测试）")
    parser.add_argument("--results-dir")
    parser.add_argument("--run-id")
    parser.add_argument("--plan-file")
    parser.add_argument("--control-file")
    parser.add_argument("--gate-file", help="results_gate assess-run 的 JSON 报告")
    parser.add_argument("--format", choices=("sh", "json"), default="json")
    args = parser.parse_args(argv)
    if not args.results_dir:
        parser.error("--results-dir is required")
    try:
        plan = _load_json(args.plan_file) if args.plan_file else {}
        control = _load_json(args.control_file) if args.control_file else {}
        gate = _load_json(args.gate_file) if args.gate_file else {}
        assessment = assess_run(args.results_dir, args.run_id or "", plan, control, gate)
        assessment = validate_assessment(assessment) if assessment.get("cleanup_state") == "cleaned" else assessment
    except (CleanupError, OSError, ValueError) as exc:
        print(f"CLEANUP-REFUSED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(assessment, ensure_ascii=False, sort_keys=True))
    return 0 if assessment["cleanup_state"] == "cleaned" else 1


if __name__ == "__main__":
    raise SystemExit(main())