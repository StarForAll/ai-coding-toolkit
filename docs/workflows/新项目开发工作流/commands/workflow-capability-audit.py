#!/usr/bin/env python3
"""Run the workflow-capability-audit execution skeleton."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def _load_module(module_name: str, filename: str):
    module_path = Path(__file__).resolve().with_name(filename)
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


ASSETS = _load_module("workflow_capability_assets", "workflow_assets.py")
INSTALL = _load_module("workflow_install_workflow", "install-workflow.py")

SCRIPT_DIR = Path(__file__).resolve().parent
WORKFLOW_ROOT = SCRIPT_DIR.parent
REPO_ROOT = SCRIPT_DIR.parents[3]
PYTHON = sys.executable
ALLOWED_CURRENT_CLIS = set(ASSETS.ALL_CLI_TYPES)

TRELLIS_SCRIPTS_DIR = REPO_ROOT / ".trellis" / "scripts"
if str(TRELLIS_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(TRELLIS_SCRIPTS_DIR))

from common.active_task import (  # type: ignore[import-not-found]
    ActiveTask,
    resolve_active_task,
    set_active_task,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a Trellis compatibility audit skeleton for 新项目开发工作流."
    )
    parser.add_argument(
        "--workflow-path",
        default="docs/workflows/新项目开发工作流/",
        help="Workflow root to audit. First version only supports docs/workflows/新项目开发工作流/.",
    )
    parser.add_argument(
        "--current-cli",
        default="",
        help="Current CLI label for the report. Pass this value (claude|opencode|codex) whenever the run may continue past the version gate into the full audit path. The script does not auto-detect the CLI.",
    )
    parser.add_argument(
        "--allow-equal-version-continue",
        action="store_true",
        help="Allow the full audit path when the current Trellis version exactly matches the compatible anchor.",
    )
    parser.add_argument(
        "--compatible-trellis-version",
        default="",
        help="When COMPATIBLE_TRELLIS_VERSION is missing, write this supplied value first.",
    )
    parser.add_argument(
        "--task-title",
        default="workflow-capability-audit: 新项目开发工作流",
        help="Task title used after the version gate passes.",
    )
    parser.add_argument("--task-dir", default="", help="Existing audit task dir for in-round supplemental validation.")
    parser.add_argument("--supplemental-capability", default="", help="Supplemental capability to validate within the same audit round.")
    parser.add_argument(
        "--surface",
        default="workflow-dependent-native",
        choices=["workflow-managed", "workflow-dependent-native"],
        help="Surface for supplemental capability validation.",
    )
    parser.add_argument("--mechanism", default="", help="Mechanism/benefit text for a supplemental capability.")
    parser.add_argument("--claude-path", action="append", default=[], help="Relative path used as Claude evidence for supplemental validation.")
    parser.add_argument("--opencode-path", action="append", default=[], help="Relative path used as OpenCode evidence for supplemental validation.")
    parser.add_argument("--codex-path", action="append", default=[], help="Relative path used as Codex evidence for supplemental validation.")
    parser.add_argument("--confirm-fix-scope", action="append", default=[], help="Confirmed fix-scope item to append to capability-report.md.")
    parser.add_argument("--record-correction", action="append", default=[], help="Applied correction note to append to capability-report.md.")
    parser.add_argument("--record-revalidation", action="append", default=[], help="Post-fix revalidation note to append to capability-report.md.")
    parser.add_argument("--finalize-fixture-destruction", action="store_true", help="Mark A/B fixture destruction as finally confirmed by the user.")
    parser.add_argument("--continue-after-human-shell", action="store_true", help="Continue the audit after a human operator has executed the manual shell embed command chain for B.")
    parser.add_argument("--manual-shell-evidence", action="append", default=[], help="Evidence bullet to record when continuing after the manual human-shell embed command chain.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable output")
    return parser


def print_stop(result: str, current_version: str | None, compatible_anchor: str | None, reason: str) -> dict[str, object]:
    payload = {
        "gate_result": result,
        "current_trellis_version": current_version,
        "compatible_anchor": compatible_anchor,
        "reason": reason,
        "task_created": False,
        "capability_report_created": False,
    }
    return payload


def _next_action_for_gate(result: str) -> str:
    actions = {
        "equal-version-stop": "Re-run with --allow-equal-version-continue when the user explicitly wants a same-version full audit.",
        "missing-compatible-anchor": "Supply a compatible Trellis version via --compatible-trellis-version and re-run.",
        "environment-error": "Verify Trellis CLI installation and ensure trellis -v returns a valid version.",
        "version-parse-error": "Check that both the current version and compatible anchor are valid semver strings.",
    }
    return actions.get(result, "Resolve the version gate condition and re-run the audit.")


def print_stop_human(payload: dict[str, object]) -> None:
    result = str(payload["gate_result"])
    current_version = payload["current_trellis_version"]
    compatible_anchor = payload["compatible_anchor"]
    reason = str(payload["reason"])
    print("## Version Gate Stop")
    print()
    print(f"- Gate Result: `{result}`")
    print(f"- Workflow Root: `docs/workflows/新项目开发工作流/`")
    print(f"- Current Trellis Version: `{current_version or 'unavailable'}`")
    print(f"- Compatible Anchor: `{compatible_anchor or 'missing'}`")
    print()
    print("### Why Execution Stops Here")
    print(f"- {reason}")
    print()
    print("### Task Creation")
    print("- Skipped: Yes")
    print("- Reason: version gate happens before task creation and audit artifact creation")
    print()
    print("### Next Action")
    print(f"- {_next_action_for_gate(result)}")


def print_structural_possible_human(signals: list[str]) -> None:
    print("## Structural-Break Judgment — Possible")
    print()
    print("### Why Judgment Is Not Yet Definitive")
    print("- Initial A/B evidence shows structural-risk signals, but the script cannot confirm a definitive structural break yet.")
    print()
    print("### Structural-Break Signals Observed")
    if signals:
        for signal in signals:
            print(f"- {signal}")
    else:
        print("- none recorded")
    print()
    print("### Why Normal Adaptation Cannot Be Safely Recommended Yet")
    print("- The current audit round found high-action compatibility signals that should be confirmed before normal adaptation proceeds.")
    print()
    print("### What Additional Confirmation Or Analysis Is Needed")
    print("- Explicit user confirmation to continue from capability audit into deeper structural-break analysis or confirmed compatibility-fix planning.")
    print()
    print("### Decision Required")
    print("- Confirm whether to continue into deeper structural-break analysis before any normal adaptation recommendation proceeds.")


def _find_section_bounds(text: str, heading: str) -> tuple[int, int]:
    start = text.find(heading)
    if start == -1:
        raise RuntimeError(f"Missing required section heading: {heading}")
    next_section = text.find("\n## ", start + len(heading))
    if next_section == -1:
        next_section = len(text)
    return start, next_section


def replace_section(text: str, heading: str, replacement_lines: list[str]) -> str:
    start, next_section = _find_section_bounds(text, heading)
    section = heading + "\n" + "\n".join(replacement_lines).rstrip() + "\n"
    return text[:start] + section + text[next_section:]


def update_compatible_anchor(new_value: str) -> None:
    target = SCRIPT_DIR / "workflow_assets.py"
    content = target.read_text(encoding="utf-8")
    marker = 'COMPATIBLE_TRELLIS_VERSION = "'
    if marker in content:
        start = content.index(marker) + len(marker)
        end = content.index('"', start)
        content = content[:start] + new_value + content[end:]
    else:
        insertion = f'COMPATIBLE_TRELLIS_VERSION = "{new_value}"\n'
        prefix = 'WORKFLOW_SCHEMA_VERSION = "'
        if prefix not in content:
            raise RuntimeError("Could not locate workflow version anchor insertion point.")
        start = content.index(prefix)
        end = content.index("\n", start)
        anchor_line = content[start:end + 1]
        content = content.replace(anchor_line, anchor_line + insertion, 1)
    target.write_text(content, encoding="utf-8")


def resolve_repo_developer_name() -> str:
    developer_file = REPO_ROOT / ".trellis" / ".developer"
    if developer_file.is_file():
        content = developer_file.read_text(encoding="utf-8")
        for line in content.splitlines():
            if line.startswith("name="):
                value = line.split("=", 1)[1].strip()
                if value:
                    return value
    raise RuntimeError("Developer not initialized in .trellis/.developer; cannot create fresh audit fixtures.")


def remove_child_link(parent_ref: str, child_ref: str) -> None:
    parent_task_json = resolve_task_json(parent_ref)
    if parent_task_json is None:
        return
    try:
        parent_data = json.loads(parent_task_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    child_name = Path(child_ref).name
    parent_children = parent_data.get("children", [])
    if child_name not in parent_children:
        return
    parent_data["children"] = [item for item in parent_children if item != child_name]
    parent_task_json.write_text(json.dumps(parent_data, ensure_ascii=False, indent=2), encoding="utf-8")


def restore_active_task(previous: ActiveTask) -> str | None:
    if not previous.task_path:
        return None
    restored = set_active_task(previous.task_path, REPO_ROOT)
    if restored is None:
        return (
            "Could not restore the previous session-scoped active task after audit rollback "
            "because no session identity was available in the current executor context."
        )
    return None


def resolve_audit_task_dir(task_dir_arg: str) -> Path:
    tasks_root = (REPO_ROOT / ".trellis" / "tasks").resolve()
    task_dir = (REPO_ROOT / task_dir_arg).resolve()
    try:
        task_dir.relative_to(tasks_root)
    except ValueError as exc:
        raise RuntimeError(f"--task-dir must stay under .trellis/tasks: {task_dir_arg}") from exc

    task_json = task_dir / "task.json"
    if not is_audit_task(task_json):
        raise RuntimeError(f"--task-dir must point to a workflow-capability-audit task: {task_dir_arg}")
    return task_dir


def parse_fixture_roots_from_report(report_path: Path) -> tuple[Path, Path]:
    text = report_path.read_text(encoding="utf-8")
    a_match = re.search(r"^- A Root: (.+)$", text, flags=re.MULTILINE)
    b_match = re.search(r"^- B Root: (.+)$", text, flags=re.MULTILINE)
    if not a_match or not b_match:
        raise RuntimeError("capability-report.md is missing A/B fixture paths.")
    return Path(a_match.group(1).strip()), Path(b_match.group(1).strip())


def validate_fixture_root(path: Path, prefix: str, label: str) -> Path:
    resolved = path.resolve()
    tmp_root = Path(tempfile.gettempdir()).resolve()
    try:
        resolved.relative_to(tmp_root)
    except ValueError as exc:
        raise RuntimeError(f"{label} root must stay under the system temp directory: {resolved}") from exc
    if not resolved.name.startswith(prefix):
        raise RuntimeError(f"{label} root does not match the expected audit fixture prefix: {resolved}")
    if not resolved.is_dir():
        raise RuntimeError(f"{label} root is missing or is not a directory: {resolved}")
    return resolved


def next_capability_id(report_text: str, prefix: str) -> str:
    matches = re.findall(rf"\b{re.escape(prefix)}-(\d+)\b", report_text)
    next_number = max((int(item) for item in matches), default=0) + 1
    return f"{prefix}-{next_number:03d}"


def _evidence_and_classification(
    a_root: Path,
    b_root: Path,
    rel_paths: list[str],
    surface: str,
) -> tuple[str, str, bool]:
    if not rel_paths:
        return "not-applicable", "not-applicable", False
    baseline_hits = [path for path in rel_paths if _exists(a_root / path)]
    expected_hits = [path for path in rel_paths if _exists(b_root / path)]
    evidence_bits = []
    if baseline_hits:
        evidence_bits.append(f"A={','.join(baseline_hits)}")
    if expected_hits:
        evidence_bits.append(f"B={','.join(expected_hits)}")
    evidence = _format_evidence(evidence_bits)

    if surface == "workflow-managed":
        if expected_hits:
            return evidence, "adopted-compatible", True
        if baseline_hits:
            return evidence, "missing-but-valuable", True
        return evidence, "not-applicable", False

    if baseline_hits and expected_hits:
        return evidence, "adopted-compatible", True
    if baseline_hits and not expected_hits:
        return evidence, "missing-but-valuable", True
    if not baseline_hits and expected_hits:
        return evidence, "unclear", True
    return evidence, "not-applicable", False


def _matrix_section_heading(surface: str) -> str:
    return (
        "## Workflow-Managed Surface Matrix"
        if surface == "workflow-managed"
        else "## Workflow-Dependent Trellis-Native Surface Matrix"
    )


def _parse_row_capability(row_line: str) -> str:
    cells = [cell.strip() for cell in row_line.strip().strip("|").split("|")]
    return cells[1].lower() if len(cells) > 1 else ""


def _parse_matrix_row_line(row_line: str) -> dict[str, str]:
    cells = [cell.strip() for cell in row_line.strip().strip("|").split("|")]
    return {
        "capability_id": cells[0] if len(cells) > 0 else "",
        "capability": cells[1] if len(cells) > 1 else "",
        "discovery_source": cells[3] if len(cells) > 3 else "",
    }


def _matrix_insert_sort_key(section_heading: str, row_line: str) -> tuple[int, str, str]:
    parsed = _parse_matrix_row_line(row_line)
    discovery_rank = 1 if parsed["discovery_source"] == "supplemental-confirmed" else 0
    capability = parsed["capability"]
    if section_heading == "## Workflow-Managed Surface Matrix":
        capability_family, _, capability_name = capability.partition(":")
        return (discovery_rank, capability_family.lower(), (capability_name or capability).lower())
    return (discovery_rank, capability.lower(), parsed["capability_id"].lower())


def insert_matrix_row(text: str, section_heading: str, row_line: str, capability_name: str) -> str:
    start, next_section = _find_section_bounds(text, section_heading)
    header_start = text.find("| Capability ID |", start, next_section)
    if header_start == -1:
        raise RuntimeError(f"Missing required matrix header row in section: {section_heading}")
    separator_start = text.find("|---|", header_start, next_section)
    if separator_start == -1:
        raise RuntimeError(f"Missing required matrix separator row in section: {section_heading}")
    data_start = text.find("\n", separator_start)
    if data_start == -1:
        raise RuntimeError(f"Malformed matrix separator row in section: {section_heading}")
    data_start += 1
    section_body = text[data_start:next_section]
    lines = [line for line in section_body.splitlines() if line.strip()]
    lines.append(row_line)
    lines.sort(key=lambda line: _matrix_insert_sort_key(section_heading, line))
    new_body = "\n".join(lines)
    return text[:data_start] + new_body + text[next_section:]


def append_rejected_supplemental_point(text: str, capability: str, reason: str, evidence: str) -> str:
    heading = "## Rejected / Unconfirmed Supplemental Points"
    start, next_section = _find_section_bounds(text, heading)
    entry = (
        f"- Point:\n"
        f"  - Capability: {capability}\n"
        f"  - Status: unconfirmed\n"
        f"  - Evidence checked: {evidence}\n"
        f"  - Reason: {reason}\n"
    )
    section = text[start:next_section]
    if "- none yet" in section:
        section = section.replace("- none yet", entry.rstrip())
    else:
        section = section.rstrip() + "\n" + entry
    return text[:start] + section + text[next_section:]


def replace_single_line_value(text: str, label: str, value: str) -> str:
    pattern = re.compile(rf"^(- {re.escape(label)}: ).*$", flags=re.MULTILINE)
    replacement = rf"\1{value}"
    if pattern.search(text):
        return pattern.sub(replacement, text, count=1)
    return text


def append_bullets_to_section(text: str, heading: str, bullets: list[str], placeholder: str) -> str:
    if not bullets:
        return text
    start, next_section = _find_section_bounds(text, heading)
    section = text[start:next_section]
    bullet_lines = "\n".join(f"- {item}" for item in bullets)
    if placeholder in section:
        section = section.replace(placeholder, bullet_lines)
    else:
        section = section.rstrip() + "\n" + bullet_lines + "\n"
    return text[:start] + section + text[next_section:]


def manual_shell_status(report_text: str) -> str | None:
    try:
        section = _read_section(report_text, "## Manual Shell Continuation Required")
    except RuntimeError:
        return None
    match = re.search(r"^- Status: (.+)$", section, flags=re.MULTILINE)
    return match.group(1).strip() if match else None


def refresh_manual_shell_section(
    report_text: str,
    *,
    status: str,
    command_block: str,
    evidence: list[str],
) -> str:
    evidence_lines = [f"  - {item}" for item in evidence] if evidence else ["  - none recorded yet"]
    replacement_lines = [
        f"- Status: {status}",
        "- Evidence:",
        *evidence_lines,
        "",
        "- Command Chain:",
        command_block,
    ]
    return replace_section(report_text, "## Manual Shell Continuation Required", replacement_lines)


def _section_has_recorded_items(text: str, heading: str) -> bool:
    return "- none yet" not in _read_section(text, heading)


def refresh_stop_point_section(report_text: str) -> str:
    destroyed = re.search(r"^- Destroyed: yes$", report_text, flags=re.MULTILINE) is not None
    final_confirmed = re.search(r"^- Final destruction confirmed by user: yes$", report_text, flags=re.MULTILINE) is not None
    confirmed_fix_scope_recorded = _section_has_recorded_items(report_text, "## Confirmed Fix Scope")
    manual_shell = manual_shell_status(report_text)

    if manual_shell == "pending":
        replacement_lines = [
            "- Auto-continue allowed: No",
            "- User confirmation required for:",
            "  - whether to run the manual shell embed command chain for B and return the terminal transcript/evidence",
        ]
    elif destroyed and final_confirmed:
        replacement_lines = [
            "- Auto-continue allowed: No",
            "- User confirmation required for:",
            "  - none pending; A/B fixture destruction already finalized for this audit round.",
        ]
    elif confirmed_fix_scope_recorded:
        replacement_lines = [
            "- Auto-continue allowed: No",
            "- User confirmation required for:",
            "  - whether to finalize A/B fixture destruction after post-fix revalidation is complete",
        ]
    else:
        replacement_lines = [
            "- Auto-continue allowed: No",
            "- User confirmation required for:",
            "  - whether to proceed from audit into confirmed compatibility-fix work",
        ]
    return replace_section(report_text, "## Stop Point and Pending Confirmations", replacement_lines)


def validate_supplemental_capability(
    task_dir: Path,
    capability: str,
    surface: str,
    mechanism: str,
    claude_paths: list[str],
    opencode_paths: list[str],
    codex_paths: list[str],
) -> dict[str, object]:
    report_path = task_dir / "capability-report.md"
    report_text = report_path.read_text(encoding="utf-8")
    a_root, b_root = parse_fixture_roots_from_report(report_path)

    claude_evidence, claude_classification, claude_confirmed = _evidence_and_classification(a_root, b_root, claude_paths, surface)
    opencode_evidence, opencode_classification, opencode_confirmed = _evidence_and_classification(a_root, b_root, opencode_paths, surface)
    codex_evidence, codex_classification, codex_confirmed = _evidence_and_classification(a_root, b_root, codex_paths, surface)

    confirmed = any([claude_confirmed, opencode_confirmed, codex_confirmed])
    if not confirmed:
        updated = append_rejected_supplemental_point(
            report_text,
            capability,
            "No baseline evidence confirmed the supplemental capability in the current A/B round.",
            "; ".join(filter(None, [claude_evidence, opencode_evidence, codex_evidence])) or "not-applicable",
        )
        updated = refresh_structural_break_section(updated)
        report_path.write_text(updated, encoding="utf-8")
        return {
            "mode": "supplemental-unconfirmed",
            "capability": capability,
            "capability_report": str(report_path),
            "report_path": str(report_path),
        }

    prefix = "WM" if surface == "workflow-managed" else "TN"
    capability_id = next_capability_id(report_text, prefix)
    overall = _normalize_overall(
        [claude_classification, opencode_classification, codex_classification]
    )
    structural_signal = "none detected from supplemental validation"
    adaptation_decision = "No action required unless later confirmed compatibility analysis changes this."
    if overall in {
        "present-but-incompatible",
        "missing-but-valuable",
        "unclear",
        "present-but-gated-unexpected",
        "present-but-gated-expected",
    }:
        structural_signal = "supplemental capability indicates additional compatibility attention may be required"
        adaptation_decision = "Review the supplemental capability in the next confirmed compatibility decision."
    row_line = (
        "| "
        + " | ".join(
            [
                capability_id,
                capability,
                mechanism or "User-supplemented capability confirmed in the current A/B round.",
                "supplemental-confirmed",
                claude_evidence,
                claude_classification,
                opencode_evidence,
                opencode_classification,
                codex_evidence,
                codex_classification,
                overall,
                structural_signal,
                adaptation_decision,
            ]
        )
        + " |"
    )
    updated = insert_matrix_row(report_text, _matrix_section_heading(surface), row_line, capability)
    updated = refresh_structural_break_section(updated)
    report_path.write_text(updated, encoding="utf-8")
    return {
        "mode": "supplemental-confirmed",
        "capability": capability,
        "capability_id": capability_id,
        "capability_report": str(report_path),
        "report_path": str(report_path),
    }


def update_fix_lifecycle(
    task_dir: Path,
    confirmed_fix_scope: list[str],
    applied_corrections: list[str],
    post_fix_revalidation: list[str],
    finalize_fixture_destruction: bool,
    compatible_anchor_value: str | None = None,
    allow_anchor_promotion: bool = False,
) -> dict[str, object]:
    report_path = task_dir / "capability-report.md"
    report_text = report_path.read_text(encoding="utf-8")
    updated = report_text
    updated = append_bullets_to_section(updated, "## Confirmed Fix Scope", confirmed_fix_scope, "- none yet")
    updated = append_bullets_to_section(updated, "## Applied Corrections", applied_corrections, "- none yet")
    updated = append_bullets_to_section(updated, "## Post-Fix Revalidation", post_fix_revalidation, "- none yet")
    if finalize_fixture_destruction:
        applied_section = _read_section(updated, "## Applied Corrections")
        revalidation_section = _read_section(updated, "## Post-Fix Revalidation")
        no_fix_path = (
            "- none yet" in applied_section
            and _section_has_recorded_items(updated, "## Confirmed Fix Scope")
            and _section_has_recorded_items(updated, "## Post-Fix Revalidation")
        )
        if not no_fix_path and ("- none yet" in applied_section or "- none yet" in revalidation_section):
            raise RuntimeError(
                "Cannot finalize fixture destruction before applied corrections and post-fix revalidation are recorded."
            )
        a_root, b_root = parse_fixture_roots_from_report(report_path)
        a_root = validate_fixture_root(a_root, "workflow-capability-audit-a-", "A")
        b_root = validate_fixture_root(b_root, "workflow-capability-audit-b-", "B")
        updated = replace_single_line_value(updated, "Destroyed", "yes")
        updated = replace_single_line_value(updated, "Final destruction confirmed by user", "yes")
        shutil.rmtree(a_root, ignore_errors=True)
        shutil.rmtree(b_root, ignore_errors=True)
    updated = refresh_stop_point_section(updated)
    report_path.write_text(updated, encoding="utf-8")
    if compatible_anchor_value and allow_anchor_promotion:
        report_after = report_path.read_text(encoding="utf-8")
        if _section_has_recorded_items(report_after, "## Post-Fix Revalidation"):
            update_compatible_anchor(compatible_anchor_value)
    return {
        "mode": "fix-lifecycle-updated",
        "capability_report": str(report_path),
        "report_path": str(report_path),
        "confirmed_fix_scope_items": len(confirmed_fix_scope),
        "applied_corrections_items": len(applied_corrections),
        "post_fix_revalidation_items": len(post_fix_revalidation),
        "fixture_destruction_finalized": finalize_fixture_destruction,
    }


def derive_structural_break(managed_rows: list[dict[str, Any]], dependent_rows: list[dict[str, Any]]) -> tuple[str, list[str], str]:
    rows = [*managed_rows, *dependent_rows]
    blocking = []
    for row in rows:
        if row["overall_summary"] in {
            "present-but-incompatible",
            "missing-but-valuable",
            "unclear",
            "present-but-gated-unexpected",
        }:
            blocking.append(f"{row['capability_id']}: {row['structural_signal']} ({row['overall_summary']})")
    if blocking:
        return (
            "possible",
            blocking,
            "High-action compatibility findings exist in the current A/B audit. Continue only after explicit user confirmation.",
        )
    return "no", [], "Current report state does not show structural-break signals that require escalation."


def parse_matrix_rows(section_text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in section_text.splitlines():
        if not line.startswith("| ") or line.startswith("| Capability ID |") or line.startswith("|---|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 13:
            continue
        rows.append(
            {
                "capability_id": cells[0],
                "capability": cells[1],
                "mechanism": cells[2],
                "discovery_source": cells[3],
                "claude_evidence": cells[4],
                "claude_classification": cells[5],
                "opencode_evidence": cells[6],
                "opencode_classification": cells[7],
                "codex_evidence": cells[8],
                "codex_classification": cells[9],
                "overall_summary": cells[10],
                "structural_signal": cells[11],
                "adaptation_decision": cells[12],
            }
        )
    return rows


def _read_section(text: str, heading: str) -> str:
    start, next_section = _find_section_bounds(text, heading)
    return text[start:next_section]


def refresh_structural_break_section(report_text: str) -> str:
    managed_rows = parse_matrix_rows(_read_section(report_text, "## Workflow-Managed Surface Matrix"))
    dependent_rows = parse_matrix_rows(_read_section(report_text, "## Workflow-Dependent Trellis-Native Surface Matrix"))
    result, signals, why = derive_structural_break(managed_rows, dependent_rows)
    signal_lines = [f"- {signal}" for signal in signals] or ["- none detected from current report state"]
    replacement_lines = [
        f"- Result: {result}",
        "- Signals:",
        *signal_lines,
        f"- Why: {why}",
        f"- Required next action: {'Stop and wait for explicit user confirmation before any normal adaptation path proceeds.' if result == 'possible' else 'Continue with the current confirmation boundary.'}",
    ]
    return replace_section(report_text, "## Structural-Break Judgment", replacement_lines)


def validate_current_cli(current_cli: str) -> str | None:
    normalized = current_cli.strip()
    if not normalized:
        return "--current-cli is required for the full upgrade audit. Pass claude, opencode, or codex."
    if normalized not in ALLOWED_CURRENT_CLIS:
        return "--current-cli must be one of: claude, opencode, codex."
    return None


def resolve_task_json(task_ref: str) -> Path | None:
    if not task_ref:
        return None
    normalized = task_ref.strip()
    if normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized.startswith("tasks/"):
        normalized = f".trellis/{normalized}"
    task_dir = REPO_ROOT / normalized
    task_json = task_dir / "task.json"
    if task_json.is_file():
        return task_json
    return None


def task_parent_ref(task_ref: str) -> str | None:
    task_json = resolve_task_json(task_ref)
    if task_json is None:
        return None
    try:
        data = json.loads(task_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    parent = data.get("parent")
    if not isinstance(parent, str) or not parent.strip():
        return None
    return f".trellis/tasks/{parent.strip()}"


def is_audit_task(task_json: Path | None) -> bool:
    if task_json is None:
        return False
    try:
        data = json.loads(task_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    title = str(data.get("title", ""))
    return title.startswith("workflow-capability-audit:")


def run_task_create(title: str, parent: str | None) -> str:
    command = [PYTHON, str(REPO_ROOT / ".trellis" / "scripts" / "task.py"), "create", title, "--slug", "workflow-capability-audit"]
    if parent:
        command.extend(["--parent", parent])
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "task create failed")
    task_dir = result.stdout.strip().splitlines()[-1].strip()
    if not task_dir:
        raise RuntimeError("task create did not return a task directory")
    return task_dir


def run_task_start(task_dir: str) -> None:
    command = [PYTHON, str(REPO_ROOT / ".trellis" / "scripts" / "task.py"), "start", task_dir]
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "task start failed")


def create_fixture_root(prefix: str, developer_name: str) -> Path:
    root = Path(tempfile.mkdtemp(prefix=prefix))
    try:
        subprocess.run(["git", "init", "-b", "main"], cwd=root, text=True, capture_output=True, check=True)
        subprocess.run(["git", "remote", "add", "origin", "git@example.com:first/repo.git"], cwd=root, text=True, capture_output=True, check=True)
        subprocess.run(["git", "remote", "set-url", "--add", "--push", "origin", "git@example.com:first/repo.git"], cwd=root, text=True, capture_output=True, check=True)
        subprocess.run(["git", "remote", "set-url", "--add", "--push", "origin", "git@example.com:second/repo.git"], cwd=root, text=True, capture_output=True, check=True)
        subprocess.run(
            ["trellis", "init", "--claude", "--opencode", "--codex", "-u", developer_name, "-y"],
            cwd=root,
            text=True,
            capture_output=True,
            check=True,
        )
        return root
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        raise


def _is_likely_codex_python_probe_false_negative(detail: str, current_cli: str) -> bool:
    if current_cli != "codex":
        return False
    lowered = detail.lower()
    return (
        'python command "python3" not found' in lowered
        and "trellis init requires python" in lowered
    )


def _codex_runtime_boundary_message(detail: str) -> str:
    return (
        "Codex runtime boundary: fresh `trellis init` failed inside the current Codex runtime, "
        "so this result is not yet sufficient proof that the user's actual machine environment is broken.\n"
        "Recheck the same `trellis init --claude --opencode --codex -u <name> -y` step in a real shell, "
        "Claude Code, or OpenCode on the same machine before concluding `Blocked / Environment Error`.\n"
        "If the non-Codex recheck succeeds, treat that result as the environment truth source.\n"
        f"Original Codex-local failure:\n{detail}"
    )


class HumanShellRequiredError(RuntimeError):
    def __init__(self, root: Path, project_id: str, command_block: str) -> None:
        super().__init__("Human shell execution required for workflow embed continuation.")
        self.root = root
        self.project_id = project_id
        self.command_block = command_block


def build_manual_embed_project_id(root: Path) -> str:
    base = re.sub(r"[^a-zA-Z0-9_-]+", "", root.name)
    if not base or not base[0].isalpha():
        base = f"workflowcapability{base}"
    if not base[-1].isalpha():
        base = f"{base}b"
    return base[:48]


def build_manual_embed_command_block(root: Path, project_id: str, profile: str = "<profile>") -> str:
    return "\n".join(
        [
            "```bash",
            "# Replace `<profile>` with `personal` or `outsourcing` before running the install commands below.",
            f'/ops/softwares/python/bin/python3 "{SCRIPT_DIR / "detect-embed-state.py"}" --project-root "{root}"',
            f'/ops/softwares/python/bin/python3 "{SCRIPT_DIR / "install-workflow.py"}" --project-root "{root}" --project-id "{project_id}" --profile {profile} --dry-run',
            f'WORKFLOW_EMBED_HUMAN_CONFIRMED=1 /ops/softwares/python/bin/python3 "{SCRIPT_DIR / "install-workflow.py"}" --project-root "{root}" --project-id "{project_id}" --profile {profile}',
            f'/ops/softwares/python/bin/python3 "{SCRIPT_DIR / "upgrade-compat.py"}" --project-root "{root}" --check',
            "# During formal install, complete the terminal confirmation prompt: EMBED <project-id>",
            "```",
        ]
    )


def install_workflow_into(root: Path) -> None:
    project_id = build_manual_embed_project_id(root)
    raise HumanShellRequiredError(root, project_id, build_manual_embed_command_block(root, project_id))


def initialize_prd(task_dir: Path, current_version: str, compatible_anchor: str) -> None:
    prd_path = task_dir / "prd.md"
    prd_path.write_text(
        f"""# workflow-capability-audit: 新项目开发工作流

## Goal

Audit whether the current Trellis version relationship to the workflow compatibility anchor requires compatibility adaptation for `docs/workflows/新项目开发工作流/`.

## What I already know

* Current Trellis version is `{current_version}`.
* Current compatibility anchor is `{compatible_anchor}`.
* This audit is limited to `docs/workflows/新项目开发工作流/`.

## Requirements

* Create fresh `A` and `B` fixtures after the version gate allows continuation.
* Discover current Trellis baseline capabilities dynamically.
* Compare workflow-managed and workflow-dependent Trellis-native surfaces.
* Produce `capability-report.md` and stop for user confirmation.
""",
        encoding="utf-8",
    )


def detect_cli_types_from_roots(*roots: Path) -> list[str]:
    return ASSETS.detect_cli_types(*roots)


def _exists(path: Path) -> bool:
    return path.exists()


def _format_evidence(items: list[str]) -> str:
    return "; ".join(items) if items else "not-applicable"


def _normalize_overall(summary_values: list[str]) -> str:
    severity_order = [
        "present-but-incompatible",
        "missing-but-valuable",
        "unclear",
        "present-but-gated-unexpected",
        "present-but-gated-expected",
        "intentionally-disabled",
        "patched-compatible",
        "adopted-compatible",
        "not-applicable",
    ]
    filtered = [value for value in summary_values if value]
    if not filtered:
        return "not-applicable"
    for candidate in severity_order:
        if candidate in filtered:
            return candidate
    return filtered[0]


def _managed_row_key(spec: Any) -> str:
    if spec.kind == "script":
        return f"script:{spec.name}"
    if spec.kind == "doc":
        return f"doc:{spec.name}"
    return spec.name


def _managed_row_label(spec: Any) -> str:
    if spec.kind == "script":
        return f"helper-script:{spec.name}"
    if spec.kind == "doc":
        return f"shared-doc:{spec.name}"
    return spec.name


def _managed_mechanism(spec: Any) -> str:
    if spec.category == "patch-baseline":
        return "Workflow preserves Trellis baseline content and injects workflow patch behavior."
    if spec.category == "overlay-baseline":
        return "Workflow replaces the live baseline copy with workflow-owned content."
    if spec.category == "added-command":
        return "Workflow adds a workflow-only capability beyond the Trellis baseline."
    if spec.category == "disabled-baseline":
        return "Workflow intentionally disables a baseline capability on the embedded surface."
    if spec.category == "shared-script":
        return "Workflow deploys a shared helper script used across CLI carriers."
    return "Workflow-managed compatibility surface."


def _locate_spec_presence(spec: Any, root: Path) -> list[str]:
    if spec.cli_type == "codex" and spec.kind == "skill" and spec.category == "disabled-baseline":
        locations = []
        for skills_dir in ASSETS.list_all_codex_skills_dirs(root):
            target = skills_dir / spec.name / "SKILL.md"
            if target.exists():
                locations.append(target.relative_to(root).as_posix())
        return locations
    path = spec.locate(root)
    if path is None or not path.exists():
        return []
    return [path.relative_to(root).as_posix()]


def _locate_extra_presence(root: Path, rel_paths: tuple[str, ...]) -> list[str]:
    return [path for path in rel_paths if _exists(root / path)]


def _locate_extra_confirmed_presence(
    root: Path,
    rel_paths: tuple[str, ...],
    required_substrings: tuple[str, ...],
) -> list[str]:
    locations = _locate_extra_presence(root, rel_paths)
    if not required_substrings:
        return locations
    confirmed: list[str] = []
    for rel_path in locations:
        try:
            content = (root / rel_path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if all(marker in content for marker in required_substrings):
            confirmed.append(rel_path)
    return confirmed


def _managed_sort_key(row: dict[str, Any]) -> tuple[int, str, str]:
    discovery_rank = 1 if row.get("discovery_source") == "supplemental-confirmed" else 0
    capability = str(row.get("capability", ""))
    capability_family, _, capability_name = capability.partition(":")
    return (discovery_rank, capability_family, capability_name or capability)


def build_workflow_managed_rows(a_root: Path, b_root: Path, cli_types: list[str]) -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    specs = ASSETS.build_managed_asset_specs(cli_types)
    for spec in specs:
        key = _managed_row_key(spec)
        row = rows.setdefault(
            key,
            {
                "capability": _managed_row_label(spec),
                "mechanism": _managed_mechanism(spec),
                "discovery_source": "ai-discovered",
                "claude_evidence": "not-applicable",
                "claude_classification": "not-applicable",
                "opencode_evidence": "not-applicable",
                "opencode_classification": "not-applicable",
                "codex_evidence": "not-applicable",
                "codex_classification": "not-applicable",
                "structural_signal": "none detected from A/B surface shape",
                "adaptation_decision": "No action required in fresh B unless later compatibility analysis changes this.",
            },
        )
        baseline_locations = _locate_spec_presence(spec, a_root)
        expected_locations = _locate_spec_presence(spec, b_root)
        evidence_bits = []
        if baseline_locations:
            evidence_bits.append(f"A={','.join(baseline_locations)}")
        if expected_locations:
            evidence_bits.append(f"B={','.join(expected_locations)}")
        if not baseline_locations and not expected_locations:
            evidence_bits.append("absent in A/B")
        evidence = _format_evidence(evidence_bits)

        if spec.category == "disabled-baseline":
            classification = "intentionally-disabled"
        elif expected_locations:
            classification = "patched-compatible" if spec.category == "patch-baseline" else "adopted-compatible"
        elif baseline_locations:
            classification = "missing-but-valuable"
            row["structural_signal"] = "managed surface missing from fresh embedded B"
            row["adaptation_decision"] = "Investigate why the expected workflow-managed asset is absent from fresh B."
        else:
            classification = "not-applicable"

        if spec.cli_type == "claude":
            row["claude_evidence"] = evidence
            row["claude_classification"] = classification
        elif spec.cli_type == "opencode":
            row["opencode_evidence"] = evidence
            row["opencode_classification"] = classification
        elif spec.cli_type == "codex":
            row["codex_evidence"] = evidence
            row["codex_classification"] = classification
        else:
            for prefix in ("claude", "opencode", "codex"):
                row[f"{prefix}_evidence"] = evidence
                if row[f"{prefix}_classification"] == "not-applicable":
                    row[f"{prefix}_classification"] = classification

    for extra in ASSETS.build_managed_audit_extra_specs(cli_types):
        row = {
            "capability": extra.capability,
            "mechanism": extra.mechanism,
            "discovery_source": "ai-discovered",
            "claude_evidence": "not-applicable",
            "claude_classification": "not-applicable",
            "opencode_evidence": "not-applicable",
            "opencode_classification": "not-applicable",
            "codex_evidence": "not-applicable",
            "codex_classification": "not-applicable",
            "structural_signal": "none detected from A/B surface shape",
            "adaptation_decision": "No action required in fresh B unless later compatibility analysis changes this.",
        }
        per_cli_values = {
            "claude": extra.claude_paths,
            "opencode": extra.opencode_paths,
            "codex": extra.codex_paths,
        }
        for prefix, rel_paths in per_cli_values.items():
            baseline_locations = _locate_extra_confirmed_presence(a_root, rel_paths, extra.required_substrings)
            expected_locations = _locate_extra_confirmed_presence(b_root, rel_paths, extra.required_substrings)
            evidence_bits = []
            if baseline_locations:
                evidence_bits.append(f"A={','.join(baseline_locations)}")
            if expected_locations:
                evidence_bits.append(f"B={','.join(expected_locations)}")
            if not baseline_locations and not expected_locations:
                evidence_bits.append("absent in A/B")
            row[f"{prefix}_evidence"] = _format_evidence(evidence_bits)
            if expected_locations:
                classification = "adopted-compatible"
            elif baseline_locations:
                classification = "missing-but-valuable"
                row["structural_signal"] = "managed surface missing from fresh embedded B"
                row["adaptation_decision"] = "Investigate why the expected workflow-managed asset is absent from fresh B."
            else:
                classification = "not-applicable"
            row[f"{prefix}_classification"] = classification
        rows[extra.capability] = row

    sorted_rows: list[dict[str, Any]] = []
    for index, row in enumerate(sorted(rows.values(), key=_managed_sort_key), start=1):
        row["capability_id"] = f"WM-{index:03d}"
        row["overall_summary"] = _normalize_overall(
            [
                row["claude_classification"],
                row["opencode_classification"],
                row["codex_classification"],
            ]
        )
        sorted_rows.append(row)
    return sorted_rows


def build_workflow_dependent_rows(a_root: Path, b_root: Path) -> list[dict[str, Any]]:
    definitions = [
        {
            "capability": "project-rules-and-routing-carrier",
            "mechanism": "Workflow depends on AGENTS-style project rules/routing as a shared long-lived carrier.",
            "claude": ["AGENTS.md"],
            "opencode": ["AGENTS.md"],
            "codex": ["AGENTS.md"],
        },
        {
            "capability": "claude-hooks-and-settings-carrier",
            "mechanism": "Workflow may rely on Claude runtime hooks/settings that are Trellis-native or manually maintained rather than installer-managed.",
            "claude": [".claude/settings.json", ".claude/hooks", ".claude/hooks/inject-workflow-state.py", ".claude/hooks/session-start.py", ".claude/hooks/inject-subagent-context.py"],
            "opencode": [],
            "codex": [],
        },
        {
            "capability": "opencode-plugin-and-instructions-carrier",
            "mechanism": "Workflow may rely on OpenCode plugin/instruction carrier surfaces outside installer-managed workflow commands.",
            "claude": [],
            "opencode": [".opencode/plugins", ".opencode/package.json"],
            "codex": [],
        },
        {
            "capability": "codex-hooks-and-config-carrier",
            "mechanism": "Workflow may rely on Codex hook/config surfaces outside installer-managed shared skills, and these surfaces can remain file-present while runtime activation is still gated by project trust plus higher-precedence hook/config decisions outside the embedded workflow files.",
            "claude": [],
            "opencode": [],
            "codex": [".codex/hooks.json", ".codex/config.toml", ".codex/hooks/inject-workflow-state.py"],
            "gated_cli": "codex",
            "gated_expectation": "expected",
            "gated_reason": "carrier exists in A/B, but Codex runtime activation still depends on feature gates or user approval outside the embedded workflow files",
            "gated_decision": "Treat file presence and runtime activation as separate checks when judging Codex compatibility.",
        },
        {
            "capability": "implementation-agent-carrier",
            "mechanism": "Workflow depends on per-CLI implementation agent carrier directories even beyond installer ownership boundaries.",
            "claude": [
                ".claude/agents/trellis-research.md",
                ".claude/agents/trellis-implement.md",
                ".claude/agents/trellis-check.md",
            ],
            "opencode": [
                ".opencode/agents/trellis-research.md",
                ".opencode/agents/trellis-implement.md",
                ".opencode/agents/trellis-check.md",
            ],
            "codex": [
                ".codex/agents/trellis-research.toml",
                ".codex/agents/trellis-implement.toml",
                ".codex/agents/trellis-check.toml",
            ],
        },
        {
            "capability": "trellis-runtime-workflow-guide",
            "mechanism": "Workflow depends on Trellis runtime workflow guide and project runtime script surfaces.",
            "claude": [".trellis/workflow.md", ".trellis/scripts/task.py"],
            "opencode": [".trellis/workflow.md", ".trellis/scripts/task.py"],
            "codex": [".trellis/workflow.md", ".trellis/scripts/task.py"],
        },
        {
            "capability": "shared-skills-deployment-carrier",
            "mechanism": "Workflow depends on .agents/skills/ as a shared deployment layer for shared skills consumed by OpenCode and Codex.",
            "claude": [],
            "opencode": [".agents/skills"],
            "codex": [".agents/skills"],
        },
        {
            "capability": "claude-native-skills-carrier",
            "mechanism": "Workflow depends on .claude/skills/ as the Claude-native skills carrier for workflow-installed or workflow-maintained skills.",
            "claude": [".claude/skills"],
            "opencode": [],
            "codex": [],
        },
        {
            "capability": "opencode-native-skills-carrier",
            "mechanism": "Workflow depends on .opencode/skills/ as the OpenCode-native skills carrier for workflow-installed or workflow-maintained skills.",
            "claude": [],
            "opencode": [".opencode/skills"],
            "codex": [],
        },
        {
            "capability": "opencode-lib-carrier",
            "mechanism": "Workflow depends on .opencode/lib/ as the OpenCode helper libraries carrier (e.g., trellis-context.js, session-utils.js).",
            "claude": [],
            "opencode": [".opencode/lib"],
            "codex": [],
        },
        {
            "capability": "trellis-hooks-script-carrier",
            "mechanism": "Workflow depends on Trellis-side lifecycle hook scripts under .trellis/scripts/hooks/ rather than an older .trellis/hooks directory model.",
            "claude": [".trellis/scripts/hooks", ".trellis/scripts/hooks/linear_sync.py"],
            "opencode": [".trellis/scripts/hooks", ".trellis/scripts/hooks/linear_sync.py"],
            "codex": [".trellis/scripts/hooks", ".trellis/scripts/hooks/linear_sync.py"],
        },
        {
            "capability": "codex-secondary-skills-carrier",
            "mechanism": "Workflow must account for .codex/skills/ as a Codex-local/secondary skills carrier that may appear after trellis init, may hold Codex-only or project-local skills, and can affect duplicate shared-skill cleanup plus Codex-side runtime behavior.",
            "claude": [],
            "opencode": [],
            "codex": [".codex/skills"],
        },
    ]

    rows: list[dict[str, Any]] = []
    for index, definition in enumerate(definitions, start=1):
        row: dict[str, Any] = {
            "capability_id": f"TN-{index:03d}",
            "capability": definition["capability"],
            "mechanism": definition["mechanism"],
            "discovery_source": "ai-discovered",
            "structural_signal": "none detected from A/B dependency surface shape",
            "adaptation_decision": "No action required in fresh B unless later compatibility analysis changes this.",
        }
        per_cli_classifications: list[str] = []
        for prefix in ("claude", "opencode", "codex"):
            rel_paths = definition[prefix]
            if not rel_paths:
                row[f"{prefix}_evidence"] = "not-applicable"
                row[f"{prefix}_classification"] = "not-applicable"
                per_cli_classifications.append("not-applicable")
                continue
            baseline_hits = [path for path in rel_paths if _exists(a_root / path)]
            expected_hits = [path for path in rel_paths if _exists(b_root / path)]
            evidence_bits = []
            if baseline_hits:
                evidence_bits.append(f"A={','.join(baseline_hits)}")
            if expected_hits:
                evidence_bits.append(f"B={','.join(expected_hits)}")
            row[f"{prefix}_evidence"] = _format_evidence(evidence_bits)
            if baseline_hits and expected_hits:
                if definition.get("gated_cli") == prefix:
                    gated_expectation = str(definition.get("gated_expectation", "unexpected"))
                    classification = (
                        "present-but-gated-expected"
                        if gated_expectation == "expected"
                        else "present-but-gated-unexpected"
                    )
                    row["structural_signal"] = str(definition.get("gated_reason", "carrier presence is conditional at runtime"))
                    row["adaptation_decision"] = str(definition.get("gated_decision", "Review runtime gating before concluding compatibility."))
                else:
                    classification = "adopted-compatible"
            elif baseline_hits and not expected_hits:
                classification = "missing-but-valuable"
                row["structural_signal"] = "workflow depends on Trellis-native surface not preserved in fresh B"
                row["adaptation_decision"] = "Inspect whether the workflow still relies on this Trellis-native surface after upgrade."
            elif not baseline_hits and not expected_hits:
                classification = "not-applicable"
            else:
                classification = "unclear"
                row["structural_signal"] = "surface presence differs unexpectedly between A and B"
                row["adaptation_decision"] = "Inspect the surface-presence mismatch before concluding compatibility."
            row[f"{prefix}_classification"] = classification
            per_cli_classifications.append(classification)
        row["overall_summary"] = _normalize_overall(per_cli_classifications)
        rows.append(row)
    return rows


def summarize_baseline_capabilities(a_root: Path) -> list[str]:
    bullets: list[str] = []
    if (a_root / ".claude" / "commands" / "trellis").is_dir():
        bullets.append("Claude baseline command carrier discovered under `.claude/commands/trellis/`.")
    if (a_root / ".opencode" / "commands" / "trellis").is_dir():
        bullets.append("OpenCode baseline command carrier discovered under `.opencode/commands/trellis/`.")
    if (a_root / ".agents" / "skills").is_dir():
        bullets.append("Shared skills carrier discovered under `.agents/skills/`.")
    if (a_root / ".codex" / "agents").is_dir():
        bullets.append("Codex implementation agent carrier discovered under `.codex/agents/`.")
    if (a_root / ".codex" / "hooks.json").exists():
        bullets.append("Codex hook/config carrier discovered under `.codex/`.")
    if (a_root / "AGENTS.md").exists():
        bullets.append("Shared project rules carrier discovered in `AGENTS.md`.")
    return bullets or ["No baseline capability summary could be derived from fresh A."]


def _render_matrix(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| Capability ID | Capability | Latest Trellis Mechanism / Benefit | Discovery Source | Claude Evidence | Claude Classification | OpenCode Evidence | OpenCode Classification | Codex Evidence | Codex Classification | Overall Summary | Structural Signal | Adaptation Decision |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["capability_id"]),
                    str(row["capability"]),
                    str(row["mechanism"]),
                    str(row["discovery_source"]),
                    str(row["claude_evidence"]),
                    str(row["claude_classification"]),
                    str(row["opencode_evidence"]),
                    str(row["opencode_classification"]),
                    str(row["codex_evidence"]),
                    str(row["codex_classification"]),
                    str(row["overall_summary"]),
                    str(row["structural_signal"]),
                    str(row["adaptation_decision"]),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def initialize_capability_report(
    task_dir: Path,
    current_cli: str,
    current_version: str,
    compatible_anchor: str,
    gate_result: str,
    reason: str,
    a_root: Path,
    b_root: Path,
    managed_rows: list[dict[str, Any]],
    dependent_rows: list[dict[str, Any]],
    manual_shell_command_block: str | None = None,
) -> None:
    report_path = task_dir / "capability-report.md"
    structural_result, structural_signals, structural_why = derive_structural_break(managed_rows, dependent_rows)
    signal_lines = [f"- {signal}" for signal in structural_signals] or ["- none detected from initial A/B pass"]
    content = f"""# workflow-capability-audit: 新项目开发工作流

## Audit Target and Boundary
- Workflow Root: `docs/workflows/新项目开发工作流/`
- Current CLI: {current_cli or 'not specified (pass --current-cli)'}
- Current Trellis Version: {current_version}
- Compatible Anchor: {compatible_anchor}
- Audit Scope: task-based compatibility audit

## Version Gate Outcome
- Result: {gate_result}
- Reason: {reason}

## Evidence-Gathering Actions Executed In This Round
- Step 0 version gate passed — Layer: runtime command output
- Fresh A fixture created — Layer: generated target project
- Fresh B fixture created — Layer: generated target project
{"- Workflow embed into B has NOT been executed by this audit run; human shell continuation is required — Layer: source repo" if manual_shell_command_block else ""}

## Native CLI Adaptation Evidence
<!-- Fill this section during Step B AI review unless the execution engine already prefilled it. -->
- Claude Code:
  - Official docs source:
  - Workflow-source / A/B evidence:
  - Agreement / discrepancy:
- OpenCode:
  - Official docs source:
  - Workflow-source / A/B evidence:
  - Agreement / discrepancy:
- Codex:
  - Official docs source:
  - Workflow-source / A/B evidence:
  - Agreement / discrepancy:
- Discrepancy resolution:

## Discovered Baseline Capabilities
{chr(10).join(f"- {item}" for item in summarize_baseline_capabilities(a_root))}

{"## Manual Shell Continuation Required\n- Status: pending\n- Evidence:\n  - none recorded yet\n\n- Command Chain:\n" + manual_shell_command_block + "\n" if manual_shell_command_block else ""}

## Workflow-Managed Surface Matrix

{_render_matrix(managed_rows)}

## Workflow-Dependent Trellis-Native Surface Matrix

{_render_matrix(dependent_rows)}

## Rejected / Unconfirmed Supplemental Points
- none yet

## Structural-Break Judgment
- Result: {structural_result}
- Signals:
{chr(10).join(signal_lines)}
- Why: {structural_why}
- Required next action: {"Stop and wait for explicit user confirmation before any normal adaptation path proceeds." if structural_result == "possible" else "Continue with the current confirmation boundary."}

## Confirmed Fix Scope
- none yet

## Applied Corrections
- none yet

## Post-Fix Revalidation
- none yet

## A/B Fixture Status
- A Root: {a_root}
- B Root: {b_root}
- Destroyed: no
- Final destruction confirmed by user: no

## Stop Point and Pending Confirmations
- Auto-continue allowed: No
- User confirmation required for:
  - whether to proceed from audit into confirmed compatibility-fix work
{"  - whether to run the manual shell embed command chain for B and return the terminal transcript" if manual_shell_command_block else ""}
"""
    report_path.write_text(content, encoding="utf-8")


def continue_after_human_shell(
    task_dir: Path,
    manual_shell_evidence: list[str],
) -> dict[str, object]:
    report_path = task_dir / "capability-report.md"
    report_text = report_path.read_text(encoding="utf-8")
    a_root, b_root = parse_fixture_roots_from_report(report_path)
    a_root = validate_fixture_root(a_root, "workflow-capability-audit-a-", "A")
    b_root = validate_fixture_root(b_root, "workflow-capability-audit-b-", "B")
    install_record = b_root / ".trellis" / "workflow-installed.json"
    if not install_record.is_file():
        raise RuntimeError(
            "B fixture does not yet show a completed workflow embed. Run the manual shell command chain first, then continue."
        )
    if (b_root / ".trellis" / "workflow-embed-attempt.json").exists():
        raise RuntimeError(
            "B fixture still contains workflow-embed-attempt.json, which indicates the manual shell embed chain did not finish cleanly."
        )
    cli_types = detect_cli_types_from_roots(a_root, b_root)
    managed_rows = build_workflow_managed_rows(a_root, b_root, cli_types)
    dependent_rows = build_workflow_dependent_rows(a_root, b_root)
    updated = report_text
    updated = replace_section(
        updated,
        "## Evidence-Gathering Actions Executed In This Round",
        [
            "- Step 0 version gate passed — Layer: runtime command output",
            "- Fresh A fixture created — Layer: generated target project",
            "- Fresh B fixture created — Layer: generated target project",
            "- Human operator completed the manual shell embed command chain for B — Layer: runtime command output",
            *[f"- {item} — Layer: runtime command output" for item in manual_shell_evidence],
        ],
    )
    command_block = build_manual_embed_command_block(b_root, build_manual_embed_project_id(b_root))
    updated = refresh_manual_shell_section(
        updated,
        status="completed",
        command_block=command_block,
        evidence=manual_shell_evidence,
    )
    updated = replace_section(
        updated,
        "## Workflow-Managed Surface Matrix",
        ["", *_render_matrix(managed_rows).splitlines()],
    )
    updated = replace_section(
        updated,
        "## Workflow-Dependent Trellis-Native Surface Matrix",
        ["", *_render_matrix(dependent_rows).splitlines()],
    )
    updated = refresh_structural_break_section(updated)
    updated = refresh_stop_point_section(updated)
    report_path.write_text(updated, encoding="utf-8")
    return {
        "mode": "continued-after-human-shell",
        "task_dir": str(task_dir.relative_to(REPO_ROOT)),
        "capability_report": str(report_path),
        "report_path": str(report_path),
        "a_root": str(a_root),
        "b_root": str(b_root),
        "managed_rows": len(managed_rows),
        "dependent_rows": len(dependent_rows),
        "manual_shell_evidence_items": len(manual_shell_evidence),
    }


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    assets = ASSETS

    if args.continue_after_human_shell:
        if not args.task_dir:
            print("--task-dir is required for --continue-after-human-shell.", file=sys.stderr)
            return 1
        try:
            task_dir = resolve_audit_task_dir(args.task_dir)
            payload = continue_after_human_shell(task_dir, args.manual_shell_evidence)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.supplemental_capability:
        if not args.task_dir:
            print("--task-dir is required for supplemental capability validation.", file=sys.stderr)
            return 1
        try:
            task_dir = resolve_audit_task_dir(args.task_dir)
            payload = validate_supplemental_capability(
                task_dir=task_dir,
                capability=args.supplemental_capability,
                surface=args.surface,
                mechanism=args.mechanism,
                claude_paths=args.claude_path,
                opencode_paths=args.opencode_path,
                codex_paths=args.codex_path,
            )
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.confirm_fix_scope or args.record_correction or args.record_revalidation or args.finalize_fixture_destruction:
        if not args.task_dir:
            print("--task-dir is required for fix lifecycle updates.", file=sys.stderr)
            return 1
        try:
            task_dir = resolve_audit_task_dir(args.task_dir)
            compatible_anchor_value: str | None = None
            current_version, _source = assets.resolve_current_trellis_version()
            if current_version is None:
                raise RuntimeError(
                    "Cannot promote COMPATIBLE_TRELLIS_VERSION during fix lifecycle because trellis -v failed or returned empty output."
                )
            if assets.parse_trellis_version(current_version) is None:
                raise RuntimeError(
                    "Cannot promote COMPATIBLE_TRELLIS_VERSION during fix lifecycle because the current Trellis version is not parseable semver."
                )
            compatible_anchor_value = current_version
            allow_anchor_promotion = args.finalize_fixture_destruction
            payload = update_fix_lifecycle(
                task_dir=task_dir,
                confirmed_fix_scope=args.confirm_fix_scope,
                applied_corrections=args.record_correction,
                post_fix_revalidation=args.record_revalidation,
                finalize_fixture_destruction=args.finalize_fixture_destruction,
                compatible_anchor_value=compatible_anchor_value,
                allow_anchor_promotion=allow_anchor_promotion,
            )
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.workflow_path.rstrip("/") != "docs/workflows/新项目开发工作流":
        print("Only docs/workflows/新项目开发工作流/ is supported in first version.", file=sys.stderr)
        return 1

    compatible_anchor = getattr(assets, "COMPATIBLE_TRELLIS_VERSION", None)
    if not compatible_anchor:
        if not args.compatible_trellis_version:
            payload = print_stop(
                "missing-compatible-anchor",
                None,
                None,
                "COMPATIBLE_TRELLIS_VERSION is missing. Supply a value first.",
            )
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print_stop_human(payload)
            return 0
        supplied_version = args.compatible_trellis_version.strip()
        if assets.parse_trellis_version(supplied_version) is None:
            payload = print_stop(
                "version-parse-error",
                None,
                supplied_version,
                "Supplied compatible Trellis version could not be parsed using semantic-version comparison.",
            )
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print_stop_human(payload)
            return 0
        update_compatible_anchor(supplied_version)
        assets = _load_module("workflow_capability_assets_reloaded", "workflow_assets.py")
        compatible_anchor = getattr(assets, "COMPATIBLE_TRELLIS_VERSION", None)

    current_version, _source = assets.resolve_current_trellis_version()
    if current_version is None:
        payload = print_stop(
            "environment-error",
            None,
            compatible_anchor,
            "trellis -v failed or returned empty output.",
        )
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print_stop_human(payload)
        return 0

    comparison = assets.compare_trellis_versions(current_version, compatible_anchor)
    if comparison is None:
        payload = print_stop(
            "version-parse-error",
            current_version,
            compatible_anchor,
            "Version strings could not be parsed using semantic-version comparison.",
        )
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print_stop_human(payload)
        return 0
    if comparison == 0 and not args.allow_equal_version_continue:
        payload = print_stop(
            "equal-version-stop",
            current_version,
            compatible_anchor,
            "Current Trellis version already matches the workflow compatibility anchor, and no explicit same-version continuation was requested.",
        )
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print_stop_human(payload)
        return 0
    if comparison < 0:
        raise RuntimeError(
            "Workflow contract violation: COMPATIBLE_TRELLIS_VERSION must not exceed trellis -v."
        )

    gate_result = "equal-version-continue" if comparison == 0 else "newer-version-continue"
    reason = (
        "Current Trellis version matches the workflow compatibility anchor and explicit continuation was requested."
        if comparison == 0
        else "Current Trellis version is newer than the workflow compatibility anchor."
    )

    current_cli_error = validate_current_cli(args.current_cli)
    if current_cli_error:
        print(current_cli_error, file=sys.stderr)
        return 1

    current_active = resolve_active_task(REPO_ROOT)
    current_ref = current_active.task_path or ""
    current_task_json = resolve_task_json(current_ref)
    if current_ref and is_audit_task(current_task_json):
        print(
            f"An existing workflow-capability-audit task is already active: {current_ref}. "
            "Resume or complete the existing audit before starting a new full audit.",
            file=sys.stderr,
        )
        return 1
    parent = current_ref if current_ref and not is_audit_task(current_task_json) else None
    task_dir_ref = ""
    task_dir_preexisted = False
    existing_task_dir_names = {
        entry.name
        for entry in (REPO_ROOT / ".trellis" / "tasks").iterdir()
        if entry.is_dir() and entry.name != "archive"
    }
    a_root: Path | None = None
    b_root: Path | None = None
    manual_shell_required: HumanShellRequiredError | None = None
    try:
        task_dir_ref = run_task_create(args.task_title, parent)
        task_dir_preexisted = Path(task_dir_ref).name in existing_task_dir_names
        if task_dir_preexisted:
            raise RuntimeError(
                f"workflow-capability-audit task directory already exists: {task_dir_ref}. "
                "Resume or complete the existing audit instead of creating a fresh full audit in the same directory."
            )
        run_task_start(task_dir_ref)
        task_dir = REPO_ROOT / task_dir_ref
        developer_name = resolve_repo_developer_name()

        a_root = create_fixture_root("workflow-capability-audit-a-", developer_name)
        b_root = create_fixture_root("workflow-capability-audit-b-", developer_name)
        initialize_prd(task_dir, current_version, compatible_anchor)
        try:
            install_workflow_into(b_root)
        except HumanShellRequiredError as exc:
            manual_shell_required = exc
            initialize_capability_report(
                task_dir,
                args.current_cli,
                current_version,
                compatible_anchor,
                gate_result,
                reason,
                a_root,
                b_root,
                [],
                [],
                manual_shell_command_block=exc.command_block,
            )
            payload = {
                "gate_result": gate_result,
                "reason": reason,
                "current_trellis_version": current_version,
                "compatible_anchor": compatible_anchor,
                "task_dir": task_dir_ref,
                "a_root": str(a_root),
                "b_root": str(b_root),
                "capability_report": f"{task_dir_ref}/capability-report.md",
                "requires_user_confirmation": True,
                "requires_human_shell_embed": True,
                "human_shell_commands": exc.command_block,
                "next_action": "Run the manual shell embed command chain for B and return the terminal transcript.",
            }
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print("## Human Shell Required")
                print()
                print("The capability audit reached the workflow-embed boundary for fixture B.")
                print("This audit must stop here and wait for a human operator to run the following shell commands manually:")
                print()
                print(exc.command_block)
                print()
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        cli_types = detect_cli_types_from_roots(a_root, b_root)
        managed_rows = build_workflow_managed_rows(a_root, b_root, cli_types)
        dependent_rows = build_workflow_dependent_rows(a_root, b_root)
        initialize_capability_report(
            task_dir,
            args.current_cli,
            current_version,
            compatible_anchor,
            gate_result,
            reason,
            a_root,
            b_root,
            managed_rows,
            dependent_rows,
        )
        structural_result, structural_signals, _structural_why = derive_structural_break(managed_rows, dependent_rows)
    except RuntimeError as exc:
        if a_root is not None:
            shutil.rmtree(a_root, ignore_errors=True)
        if b_root is not None:
            shutil.rmtree(b_root, ignore_errors=True)
        rollback_parent = (task_parent_ref(task_dir_ref) if task_dir_ref else None) or parent
        if rollback_parent and task_dir_ref:
            remove_child_link(rollback_parent, task_dir_ref)
        if task_dir_ref and not task_dir_preexisted:
            shutil.rmtree(REPO_ROOT / task_dir_ref, ignore_errors=True)
        restore_warning = restore_active_task(current_active)
        if restore_warning:
            print(f"WARN: {restore_warning}", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        if a_root is not None:
            shutil.rmtree(a_root, ignore_errors=True)
        if b_root is not None:
            shutil.rmtree(b_root, ignore_errors=True)
        rollback_parent = (task_parent_ref(task_dir_ref) if task_dir_ref else None) or parent
        if rollback_parent and task_dir_ref:
            remove_child_link(rollback_parent, task_dir_ref)
        if task_dir_ref and not task_dir_preexisted:
            shutil.rmtree(REPO_ROOT / task_dir_ref, ignore_errors=True)
        restore_warning = restore_active_task(current_active)
        if restore_warning:
            print(f"WARN: {restore_warning}", file=sys.stderr)
        detail = exc.stderr or exc.stdout or str(exc)
        if _is_likely_codex_python_probe_false_negative(detail.strip(), args.current_cli):
            print(_codex_runtime_boundary_message(detail.strip()), file=sys.stderr)
            return 1
        print(detail.strip(), file=sys.stderr)
        return 1

    payload = {
        "gate_result": gate_result,
        "reason": reason,
        "current_trellis_version": current_version,
        "compatible_anchor": compatible_anchor,
        "task_dir": task_dir_ref,
        "a_root": str(a_root),
        "b_root": str(b_root),
        "capability_report": f"{task_dir_ref}/capability-report.md",
        "managed_rows": len(managed_rows),
        "dependent_rows": len(dependent_rows),
        "structural_break_judgment": structural_result,
        "requires_user_confirmation": True,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if structural_result == "possible":
            print_structural_possible_human(structural_signals)
            print()
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
