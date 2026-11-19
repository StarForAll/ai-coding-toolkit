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
# 每个计划单元的 typed outcome：唯一由本模块产生，summary 只搬运不改判。
OUTCOMES = ("passed", "assertion_failed", "preparation_failed", "execution_failed",
            "cancelled", "unverified")
# 准备失败标签 → 必须存在的受监督阶段 receipt（run_one.sh 的 fail_prep 标签是唯一来源）。
PREP_PHASE_BY_LABEL = (("INSTALL-FAILED", "install"), ("FIXTURE-FAILED", "fixture"),
                       ("INIT-FAILED", "init"))


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


def _read_rows(results_root):
    """五列结果行的只读投影：同名重复行保留（归因阶段按矛盾处理）。"""
    rows = {}
    try:
        with open(Path(results_root) / "lines", encoding="utf-8", errors="replace") as handle:
            for line in handle.read().splitlines():
                parts = line.split("\t")
                if len(parts) == 5:
                    rows.setdefault(parts[0], []).append(parts)
    except OSError:
        pass
    return rows


def _unit_receipts(unit_execution, run_id):
    """逐阶段核 receipt：终态、命令身份、同一代 run；返回 (receipts, problems)。"""
    receipts, problems = [], []
    for item in unit_execution.get("command_evidence") or []:
        if not isinstance(item, dict):
            problems.append("command evidence is not an object")
            continue
        phase = item.get("phase")
        command_id = item.get("command_id")
        evidence_path = item.get("evidence_path")
        if not isinstance(phase, str) or not phase:
            problems.append("command evidence has no phase")
            continue
        if not isinstance(command_id, str) or not command_id:
            problems.append(f"{phase} evidence has no command id")
            continue
        if not isinstance(evidence_path, str) or not evidence_path:
            problems.append(f"{phase} evidence has no receipt path")
            continue
        try:
            receipt = lifecycle.read_receipt(evidence_path)
        except lifecycle.LifecycleError as exc:
            problems.append(f"{phase} receipt is unreadable: {exc}")
            continue
        if receipt.get("state") != "finished":
            problems.append(f"{phase} receipt is not finished")
            continue
        if receipt.get("command_id") != command_id:
            problems.append(f"{phase} receipt command id mismatch")
            continue
        if receipt.get("run_id") != run_id:
            problems.append(f"{phase} receipt belongs to another run")
            continue
        recorded = receipt.get("result")
        if not isinstance(recorded, dict) or recorded.get("status") not in STATUSES:
            problems.append(f"{phase} receipt result is unusable")
            continue
        receipts.append({"phase": phase, "command_id": command_id, "receipt": receipt,
                         "result": recorded, "result_path": item.get("result_path")})
    return receipts, problems


def _classify_preparation(unit_execution, receipts):
    """prep-failed → preparation_failed 或 unverified（不把准备失败记成断言失败）。"""
    label = unit_execution.get("failure_reason")
    if not isinstance(label, str) or not label:
        return "unverified", "preparation failure has no recorded reason"
    if not receipts and unit_execution.get("preflight_failed") is True:
        # 启动登记前就失败：没有（也不该有）受监督流程的 receipt。
        return "preparation_failed", "preflight failed before any supervised step"
    required = next((phase for prefix, phase in PREP_PHASE_BY_LABEL
                     if label.startswith(prefix)), None)
    by_phase = {item["phase"]: item for item in receipts}
    if required and required not in by_phase:
        return "unverified", f"preparation failed ({label}) without a {required} receipt"
    for item in receipts:
        if item["phase"] == required and item["result"].get("status") == "passed":
            return "unverified", f"{required} receipt claims success for a failed preparation"
    return "preparation_failed", label


def classify_unit(unit_execution, result, row, receipts, receipt_problems, result_path):
    """单单元唯一分类器：`row`×`unit_execution`×test result×receipts 交叉核对。

    `bad`（聚合行）只说明“该单元未通过”，不能单独证明断言失败；只有目标进程正常退出、
    显式 FAIL 与完整计数同时成立才归 assertion_failed。
    """
    if receipt_problems:
        return "unverified", "; ".join(receipt_problems)
    if not isinstance(result, dict):
        return "unverified", "unit result is not an object"
    try:
        row_rc = int(row[1])
    except (TypeError, ValueError):
        return "unverified", "unit row rc is not an integer"
    rc = result.get("rc")
    if isinstance(rc, bool) or not isinstance(rc, int) or rc != row_rc:
        return "unverified", "unit row contradicts the test result rc"
    if (row[3] == "ok") != (rc == 0):
        return "unverified", "unit row status contradicts the test result rc"
    state = unit_execution.get("state")
    if state == "prep-failed":
        # 准备失败没有 test 断言事实；分类只依赖准备阶段标签与同代 receipt。
        return _classify_preparation(unit_execution, receipts)
    assertion = result.get("assertion_result")
    supervision = result.get("supervision")
    if not isinstance(assertion, dict):
        return "unverified", "unit result has no assertion facts"
    if not isinstance(supervision, dict):
        return "unverified", "unit result has no supervision facts"
    phases = {item["phase"]: item for item in receipts}
    test = phases.get("test")
    if test is None:
        return "unverified", "unit evidence has no supervised test phase"
    recorded_path = test.get("result_path")
    if not isinstance(recorded_path, str) or \
            os.path.abspath(recorded_path) != os.path.abspath(result_path):
        return "unverified", "test receipt does not name this unit result"
    if (test["result"].get("rc") != result.get("rc")
            or test["result"].get("status") != result.get("status")):
        return "unverified", "test receipt result differs from the unit result"
    status = result.get("status")
    if status in ("cancelled", "timeout"):
        if test["result"].get("status") != status:
            return "unverified", "cancelled result contradicts its receipt"
        return "cancelled", status
    target_rc = supervision.get("target_rc")
    if isinstance(target_rc, bool) or not isinstance(target_rc, int):
        return "unverified", "test target exit status is missing"
    if target_rc != 0:
        if assertion.get("ok") is True:
            return "unverified", "target failed but assertion facts claim success"
        return "execution_failed", f"target rc={target_rc}"
    failures = assertion.get("failures")
    complete = assertion.get("counts_complete")
    if assertion.get("ok") is True and failures == 0 and complete is True:
        return "passed", "all expected assertions passed"
    if isinstance(failures, int) and not isinstance(failures, bool) and failures > 0:
        if complete is not True:
            return "unverified", "explicit failures without complete assertion counts"
        if row[3] != "bad":
            return "unverified", "assertion failure without a failing result row"
        return "assertion_failed", f"{failures} explicit failed assertion(s)"
    if failures == 0:
        return "unverified", "insufficient assertions without an explicit failure"
    return "unverified", "unit assertion facts are not classifiable"


def _unit_evidence(results_root, run_id, plan):
    """每个计划单元恰好一个 typed outcome；缺失/错代/矛盾也占位为 unverified。"""
    root = Path(results_root)
    rows = _read_rows(results_root)
    units, problems = [], []

    def record_outcome(name, outcome, reason, unit_execution=None):
        if outcome == "unverified":
            problems.append({"kind": "unit-unverified", "detail": f"{name}: {reason}"})
        units.append({"unit": name,
                      "state": (unit_execution or {}).get("state"),
                      "invocation_id": (unit_execution or {}).get("invocation_id"),
                      "command_count": len((unit_execution or {}).get("command_evidence") or []),
                      "outcome": outcome, "outcome_reason": reason})

    for entry in (plan or {}).get("units") or []:
        name = entry["name"]
        path = root / f"{name}.test.log.json"
        if not path.exists():
            record_outcome(name, "unverified", "unit result is missing")
            continue
        try:
            record = lifecycle.read_json_object(path, f"unit result {name}")
        except lifecycle.LifecycleError as exc:
            record_outcome(name, "unverified", f"unit result is unreadable: {exc}")
            continue
        unit_execution = record.get("unit_execution")
        if not isinstance(unit_execution, dict):
            record_outcome(name, "unverified", "unit result has no unit_execution")
            continue
        if unit_execution.get("schema_version") != lifecycle.UNIT_EXECUTION_SCHEMA or \
                isinstance(unit_execution.get("schema_version"), bool):
            record_outcome(name, "unverified", "unit_execution schema is invalid",
                           unit_execution)
            continue
        if unit_execution.get("unit") != name:
            record_outcome(name, "unverified", "unit_execution names another unit",
                           unit_execution)
            continue
        if unit_execution.get("run_id") != run_id:
            record_outcome(name, "unverified",
                           f"unit_execution belongs to another run_id"
                           f" ({unit_execution.get('run_id')!r})", unit_execution)
            continue
        if unit_execution.get("state") not in ("passed", "prep-failed"):
            record_outcome(name, "unverified", "unit_execution state is invalid",
                           unit_execution)
            continue
        row = unit_execution.get("result_row")
        if not isinstance(row, list) or len(row) != 5 or row[0] != name:
            record_outcome(name, "unverified", "unit_execution result_row is malformed",
                           unit_execution)
            continue
        observed_rows = rows.get(name) or []
        if len(observed_rows) != 1 or observed_rows[0] != row:
            record_outcome(name, "unverified",
                           "unit row is missing, duplicated or differs", unit_execution)
            continue
        receipts, receipt_problems = _unit_receipts(unit_execution, run_id)
        outcome, reason = classify_unit(unit_execution, record, row, receipts,
                                        receipt_problems, str(path))
        record_outcome(name, outcome, reason, unit_execution)
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

    `cleanup_state` 只回答“进程与本地资源是否确认释放”；`evidence_state` 只回答“每个
    计划单元是否都有合法、同代、可分类的结果与必要 receipts”。行级失败不是证据缺口：
    结构完整的准备/执行/取消失败仍是 `evidence_state=complete`，但类别明确且绝不
    计为断言失败。gate 的聚合 bad 值只作兼容门禁，不参与单元分类。
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
    if not isinstance(gate_report, dict):
        evidence_problems.append({"kind": "gate-report", "detail": "gate report is missing"})
    else:
        gate_facts = gate_report.get("gate")
        if isinstance(gate_facts, dict):
            broken = (int(gate_facts.get("malformed") or 0) > 0
                      or bool(gate_facts.get("duplicate")) or bool(gate_facts.get("unexpected")))
            if broken:
                evidence_problems.append({
                    "kind": "gate-rows",
                    "detail": "result rows are malformed, duplicated or unexpected"})
        repro = gate_report.get("repro")
        if isinstance(repro, dict):
            unverified = 0
            for counts in (repro.get("phase_counts") or {}).values():
                if isinstance(counts, dict):
                    unverified += int(counts.get("unverified") or 0)
            if unverified:
                evidence_problems.append({
                    "kind": "repro-unverified",
                    "detail": f"{unverified} repro phase(s) lack this-generation evidence"})
    outcome_counts = {name: 0 for name in OUTCOMES}
    for item in units["units"]:
        outcome_counts[item["outcome"]] += 1
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
        "unit_outcomes": [{"unit": item["unit"], "outcome": item["outcome"]}
                          for item in units["units"]],
        "outcome_counts": outcome_counts,
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