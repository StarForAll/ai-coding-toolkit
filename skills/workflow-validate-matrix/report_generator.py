"""Report generator for workflow-validate-matrix."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from constants import DOCUMENT_TYPE, PROTOCOL_VERSION


REPAIR_CLASSIFICATIONS = ("confirmed-defect", "design-debt", "evidence-gap")
SEVERITIES = ("P0", "P1", "P2")
REQUIRED_FINDING_FIELDS = (
    "Category",
    "Severity Estimate",
    "Repair Classification",
    "Origin",
    "Evidence Layer",
    "Evidence",
    "Temp Project Location",
    "Description",
    "Suggested Investigation",
)


def _matrix_root(scenario_results: list[dict[str, Any]]) -> Path:
    if not scenario_results:
        return Path("/tmp/unknown").resolve()
    return Path(str(scenario_results[0].get("temp_dir", "/tmp/unknown"))).resolve().parent


def _relative_location(matrix_root: Path, finding: dict[str, Any]) -> str:
    temp_dir = Path(str(finding.get("temp_dir", matrix_root))).resolve()
    location = str(finding.get("location", ".") or ".")
    raw_path = Path(location)
    if raw_path.is_absolute():
        try:
            return raw_path.resolve().relative_to(matrix_root).as_posix()
        except ValueError:
            return raw_path.as_posix()

    try:
        scenario_root = temp_dir.relative_to(matrix_root).as_posix()
    except ValueError:
        scenario_root = str(finding.get("scenario", temp_dir.name))

    if location in ("", "."):
        return scenario_root
    return f"{scenario_root}/{location}".replace("//", "/")


def _flatten_findings(scenario_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for result in scenario_results:
        scenario_name = str(result.get("scenario", "unknown"))
        temp_dir = str(result.get("temp_dir", ""))
        result_findings = result.get("findings", [])
        if isinstance(result_findings, list):
            for finding in result_findings:
                if isinstance(finding, dict):
                    normalized = dict(finding)
                    normalized.setdefault("scenario", scenario_name)
                    normalized.setdefault("temp_dir", temp_dir)
                    findings.append(normalized)
        if result.get("status") == "failed" and not result_findings:
            findings.append(
                {
                    "title": f"Scenario validation failed - {scenario_name}",
                    "scenario": scenario_name,
                    "temp_dir": temp_dir,
                    "category": "script-behavior",
                    "severity": "P0",
                    "repair_classification": "confirmed-defect",
                    "origin": "workflow-source",
                    "evidence_layer": "generated-target-runtime",
                    "evidence": [
                        f"Scenario: {scenario_name}",
                        f"Error: {result.get('error', 'Unknown error')}",
                        f"Details: {result.get('error_details', 'N/A')}",
                    ],
                    "location": ".",
                    "description": (
                        f"Validation failed for scenario '{scenario_name}', indicating a critical issue "
                        "in the workflow installation or validation chain."
                    ),
                    "investigation": "Review the scenario error details and fix the underlying workflow source issue.",
                }
            )

    for index, finding in enumerate(findings, start=1):
        finding["id"] = f"WS-{index:03d}"
    return findings


def _count_by_severity(findings: list[dict[str, Any]]) -> dict[str, int]:
    return {severity: sum(1 for finding in findings if finding.get("severity") == severity) for severity in SEVERITIES}


def _group_by_repair_classification(findings: list[dict[str, Any]]) -> dict[str, list[str]]:
    groups = {classification: [] for classification in REPAIR_CLASSIFICATIONS}
    for finding in findings:
        classification = str(finding.get("repair_classification", "evidence-gap"))
        if classification in groups:
            groups[classification].append(str(finding["id"]))
    return groups


def _as_evidence_lines(value: Any) -> list[str]:
    if isinstance(value, list):
        lines = [str(item).strip() for item in value if str(item).strip()]
    else:
        lines = [line.strip() for line in str(value or "N/A").splitlines() if line.strip()]
    return lines or ["N/A"]


def _render_evidence(value: Any, scenario: str) -> str:
    lines = [f"  - Scenario: {scenario}"]
    for item in _as_evidence_lines(value):
        lines.append(f"  - {item}")
    return "\n".join(lines)


def generate_report(
    scenario_results: list[dict[str, Any]],
    output_path: Path,
    workflow_version: str,
    workflow_schema_version: str,
    trellis_version: str,
) -> None:
    """Generate WORKFLOW_QUESTIONS.md report."""
    findings = _flatten_findings(scenario_results)
    total_findings = len(findings)
    severity_counts = _count_by_severity(findings)
    repair_groups = _group_by_repair_classification(findings)

    timestamp = datetime.now(timezone.utc).isoformat()
    scenarios_tested = len(scenario_results)
    scenario_names = [result["scenario"] for result in scenario_results]
    matrix_root = _matrix_root(scenario_results)
    temp_project_root = str(matrix_root)

    frontmatter = f"""---
document-type: {DOCUMENT_TYPE}
protocol: {PROTOCOL_VERSION}
matrix-validation: true
scenarios-tested: {scenarios_tested}
scenarios: {scenario_names}
trellis-version: {trellis_version}
workflow-version: {workflow_version}
workflow-schema-version: {workflow_schema_version}
scan-timestamp: {timestamp}
temp-project-root: {temp_project_root}
total-findings: {total_findings}
p0-count: {severity_counts['P0']}
p1-count: {severity_counts['P1']}
p2-count: {severity_counts['P2']}
---

"""

    scan_summary = f"""# Workflow Scan Report

## Scan Summary

- Trellis Version: {trellis_version}
- Workflow Version: {workflow_version}
- Workflow Schema Version: {workflow_schema_version}
- Scan Time: {timestamp}
- Temp Project Root: {temp_project_root}
- Total Findings: {total_findings} (P0: {severity_counts['P0']}, P1: {severity_counts['P1']}, P2: {severity_counts['P2']})

**Matrix Validation**: {scenarios_tested} scenarios tested

**Scenario Results**:
"""

    for result in scenario_results:
        status_icon = "✅" if result["status"] == "success" else "❌"
        findings_count = len(result.get("findings", []))
        scan_summary += f"- {status_icon} **{result['scenario']}**: {result['status']} ({findings_count} findings)\n"
    scan_summary += "\n"

    problem_analysis = "none"
    if total_findings:
        problem_analysis = f"Matrix validation found {total_findings} issue(s) across {scenarios_tested} scenario(s)"

    failed_scenarios = [result for result in scenario_results if result["status"] != "success"]
    gap_analysis = "none"
    if failed_scenarios:
        gap_analysis = (
            f"{len(failed_scenarios)} scenario(s) failed validation: "
            + ", ".join(str(result["scenario"]) for result in failed_scenarios)
        )

    analysis_summary = f"""## Analysis Summary

- Problem Analysis: {problem_analysis}
- Gap / Missing-Surface Analysis: {gap_analysis}
- Residual Issues: none
- New Issues: none
- Confirmed Defects: {', '.join(repair_groups['confirmed-defect']) if repair_groups['confirmed-defect'] else 'none'}
- Design-Debt Items: {', '.join(repair_groups['design-debt']) if repair_groups['design-debt'] else 'none'}
- Evidence-Gap Items: {', '.join(repair_groups['evidence-gap']) if repair_groups['evidence-gap'] else 'none'}

"""

    findings_section = "## Findings\n\n"
    if not findings:
        findings_section += "No issues found. All scenarios passed validation.\n\n"
    else:
        for finding in findings:
            scenario = str(finding.get("scenario", "unknown"))
            findings_section += f"""### {finding['id']}: {finding.get('title', 'Issue detected')}

- **Category**: {finding.get('category', 'script-behavior')}
- **Severity Estimate**: {finding.get('severity', 'P2')}
- **Repair Classification**: {finding.get('repair_classification', 'evidence-gap')}
- **Origin**: {finding.get('origin', 'workflow-source')}
- **Evidence Layer**: {finding.get('evidence_layer', 'generated-target-installed')}
- **Evidence**:
{_render_evidence(finding.get('evidence', 'N/A'), scenario)}
- **Temp Project Location**: {_relative_location(matrix_root, finding)}
- **Description**: {finding.get('description', 'N/A')}
- **Suggested Investigation**: {finding.get('investigation', 'N/A')}

"""

    report = frontmatter + scan_summary + analysis_summary + findings_section
    output_path.write_text(report, encoding="utf-8")
    verify_report(output_path)


def _frontmatter_and_body(content: str) -> tuple[dict[str, str], str]:
    if not content.startswith("---\n"):
        raise ValueError("Report missing frontmatter")
    parts = content.split("---\n", 2)
    if len(parts) < 3:
        raise ValueError("Report frontmatter malformed")

    frontmatter: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        frontmatter[key.strip()] = value.strip()
    return frontmatter, parts[2]


def _parse_summary_ids(body: str, label: str) -> list[str]:
    prefix = f"- {label}:"
    for line in body.splitlines():
        if line.startswith(prefix):
            raw = line.split(":", 1)[1].strip()
            if raw == "none":
                return []
            return [item.strip() for item in raw.split(",") if item.strip()]
    raise ValueError(f"Analysis Summary missing {label}")


def _parse_finding_blocks(body: str) -> list[dict[str, str]]:
    blocks: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in body.splitlines():
        if line.startswith("### WS-"):
            if current is not None:
                blocks.append(current)
            ws_id = line.split(":", 1)[0].replace("### ", "").strip()
            current = {"id": ws_id, "heading": line}
            continue
        if current is None:
            continue
        if line.startswith("- **") and "**:" in line:
            key = line.split("**", 2)[1]
            value = line.split(":", 1)[1].strip()
            current[key] = value
    if current is not None:
        blocks.append(current)
    return blocks


def verify_report(report_path: Path) -> None:
    """Verify report frontmatter, body counts, summary IDs, and required fields."""
    try:
        content = report_path.read_text(encoding="utf-8")
        frontmatter, body = _frontmatter_and_body(content)

        required_frontmatter = {
            "document-type",
            "protocol",
            "trellis-version",
            "workflow-version",
            "workflow-schema-version",
            "scan-timestamp",
            "temp-project-root",
            "total-findings",
            "p0-count",
            "p1-count",
            "p2-count",
        }
        missing_frontmatter = sorted(required_frontmatter - set(frontmatter))
        if missing_frontmatter:
            raise ValueError(f"Missing frontmatter keys: {', '.join(missing_frontmatter)}")
        if frontmatter["document-type"] != DOCUMENT_TYPE:
            raise ValueError(f"document-type mismatch: {frontmatter['document-type']}")
        if frontmatter["protocol"] != PROTOCOL_VERSION:
            raise ValueError(f"protocol mismatch: {frontmatter['protocol']}")
        if not Path(frontmatter["temp-project-root"]).is_absolute():
            raise ValueError("temp-project-root must be absolute")
        for section in ("## Scan Summary", "## Analysis Summary", "## Findings"):
            if section not in body:
                raise ValueError(f"Missing section: {section}")

        findings = _parse_finding_blocks(body)
        expected_total = int(frontmatter["total-findings"])
        if len(findings) != expected_total:
            raise ValueError(f"Finding count mismatch: frontmatter says {expected_total}, body has {len(findings)}")

        expected_ids = [f"WS-{index:03d}" for index in range(1, expected_total + 1)]
        actual_ids = [finding["id"] for finding in findings]
        if actual_ids != expected_ids:
            raise ValueError(f"Finding IDs are not sequential: {actual_ids}")

        severity_counts = {
            severity: sum(1 for finding in findings if finding.get("Severity Estimate") == severity)
            for severity in SEVERITIES
        }
        for severity, frontmatter_key in (("P0", "p0-count"), ("P1", "p1-count"), ("P2", "p2-count")):
            if severity_counts[severity] != int(frontmatter[frontmatter_key]):
                raise ValueError(
                    f"{frontmatter_key} mismatch: frontmatter says {frontmatter[frontmatter_key]}, "
                    f"body has {severity_counts[severity]}"
                )

        for finding in findings:
            missing_fields = [field for field in REQUIRED_FINDING_FIELDS if field not in finding]
            if missing_fields:
                raise ValueError(f"{finding['id']} missing fields: {', '.join(missing_fields)}")
            classification = finding.get("Repair Classification", "")
            if classification not in REPAIR_CLASSIFICATIONS:
                raise ValueError(f"{finding['id']} has invalid Repair Classification: {classification}")

        body_groups = {classification: [] for classification in REPAIR_CLASSIFICATIONS}
        for finding in findings:
            body_groups[finding["Repair Classification"]].append(finding["id"])

        summary_groups = {
            "confirmed-defect": _parse_summary_ids(body, "Confirmed Defects"),
            "design-debt": _parse_summary_ids(body, "Design-Debt Items"),
            "evidence-gap": _parse_summary_ids(body, "Evidence-Gap Items"),
        }
        if summary_groups != body_groups:
            raise ValueError(f"Analysis Summary classification IDs do not match finding body: {summary_groups} != {body_groups}")
    except Exception as exc:
        raise RuntimeError(f"Report verification failed: {exc}") from exc


def parse_validation_output_to_findings(
    validation_results: list[Any],
    scenario_name: str,
) -> list[dict[str, Any]]:
    """Collect structured findings from validation results.

    Kept as a public helper for tests and compatibility with the original
    implementation. Findings now come from each validation step, including
    successful commands that emit warnings.
    """
    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for result in validation_results:
        result_findings = getattr(result, "findings", []) or []
        for finding in result_findings:
            key = (str(finding.get("step", getattr(result, "step", ""))), str(finding.get("title", "")))
            if key in seen:
                continue
            seen.add(key)
            normalized = dict(finding)
            normalized.setdefault("scenario", scenario_name)
            findings.append(normalized)
    return findings
