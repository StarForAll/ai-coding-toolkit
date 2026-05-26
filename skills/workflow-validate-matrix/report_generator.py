"""Report generator for workflow-validate-matrix."""

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

from constants import PROTOCOL_VERSION, DOCUMENT_TYPE


def generate_report(
    scenario_results: List[Dict[str, Any]],
    output_path: Path,
    workflow_version: str,
    trellis_version: str,
) -> None:
    """Generate WORKFLOW_QUESTIONS.md report."""

    # Count findings and scenarios
    total_findings = 0
    p0_count = 0
    p1_count = 0
    p2_count = 0
    successful_scenarios = []
    failed_scenarios = []

    for result in scenario_results:
        if result["status"] == "success":
            successful_scenarios.append(result)
            total_findings += len(result.get("findings", []))
            # Count by severity (placeholder - real implementation would parse findings)
        else:
            failed_scenarios.append(result)

    # Generate frontmatter
    timestamp = datetime.now(timezone.utc).isoformat()
    scenarios_tested = len(scenario_results)
    scenario_names = [r["scenario"] for r in scenario_results]

    frontmatter = f"""---
document-type: {DOCUMENT_TYPE}
protocol: {PROTOCOL_VERSION}
matrix-validation: true
scenarios-tested: {scenarios_tested}
scenarios: {scenario_names}
trellis-version: {trellis_version}
workflow-version: {workflow_version}
workflow-schema-version: unknown
scan-timestamp: {timestamp}
temp-project-root: multiple
total-findings: {total_findings}
p0-count: {p0_count}
p1-count: {p1_count}
p2-count: {p2_count}
---

"""

    # Generate scan summary
    scan_summary = f"""## Scan Summary

Matrix validation across {scenarios_tested} scenarios.

**Scenarios Tested**:
"""

    for result in scenario_results:
        status_icon = "✅" if result["status"] == "success" else "❌"
        scan_summary += f"- {status_icon} **{result['scenario']}**: {result['status']}\n"

    scan_summary += f"""
**Results**:
- Total scenarios: {scenarios_tested}
- Successful: {len(successful_scenarios)}
- Failed: {len(failed_scenarios)}
- Total findings: {total_findings}

"""

    # Generate scenario results section
    scenario_section = """## Scenario Results

"""

    for result in scenario_results:
        scenario_section += f"""### Scenario: {result['scenario']}

**Status**: {result['status']}
"""

        if result["status"] == "success":
            findings_count = len(result.get("findings", []))
            scenario_section += f"""**Findings**: {findings_count} issues found
**Description**: {result.get('description', 'N/A')}

"""
        else:
            scenario_section += f"""**Error**: {result.get('error', 'Unknown error')}
**Details**: {result.get('error_details', 'N/A')}

"""

    # Generate analysis summary
    analysis_summary = f"""## Analysis Summary

### Overall Assessment

Matrix validation tested {scenarios_tested} scenarios. {len(successful_scenarios)} succeeded, {len(failed_scenarios)} failed.

### Confirmed Defects

{total_findings} issues found across successful scenarios.

### Design-Debt Items

None identified in this run.

### Evidence-Gap Items

Failed scenarios require investigation before repair.

"""

    # Generate findings section
    findings_section = """## Findings

"""

    if total_findings == 0 and len(failed_scenarios) == 0:
        findings_section += "No issues found. All scenarios passed validation.\n\n"
    elif total_findings == 0 and len(failed_scenarios) > 0:
        findings_section += "No findings from successful scenarios. See failed scenarios above.\n\n"
    else:
        # Aggregate findings from all successful scenarios
        finding_id = 1
        for result in successful_scenarios:
            for finding in result.get("findings", []):
                findings_section += f"""### WS-{finding_id:03d}

**Scenario**: {result['scenario']}
**Category**: {finding.get('category', 'Unknown')}
**Severity Estimate**: {finding.get('severity', 'P2')}
**Repair Classification**: {finding.get('repair_classification', 'evidence-gap')}
**Origin**: {finding.get('origin', 'workflow-source')}
**Evidence Layer**: {finding.get('evidence_layer', 'generated-target-installed')}

**Evidence**:
{finding.get('evidence', 'N/A')}

**Temp Project Location**: {finding.get('location', 'N/A')}

**Description**: {finding.get('description', 'N/A')}

**Suggested Investigation**: {finding.get('investigation', 'N/A')}

"""
                finding_id += 1

    # Combine all sections
    report = (
        frontmatter
        + scan_summary
        + scenario_section
        + analysis_summary
        + findings_section
    )

    # Write report
    output_path.write_text(report, encoding="utf-8")


def parse_validation_output_to_findings(
    validation_results: List[Any], scenario_name: str
) -> List[Dict[str, Any]]:
    """Parse validation command outputs into findings.

    This is a simplified version for MVP.
    Real implementation would parse actual command outputs.
    """
    findings = []

    for result in validation_results:
        if not result.success and result.error:
            # Convert errors to findings
            findings.append({
                "category": "Validation Failure",
                "severity": "P1",
                "repair_classification": "confirmed-defect",
                "origin": "workflow-source",
                "evidence_layer": "generated-target-runtime",
                "evidence": f"Step '{result.step}' failed with error: {result.error}",
                "location": f"Scenario: {scenario_name}",
                "description": f"Validation step '{result.step}' failed during matrix validation",
                "investigation": f"Review {result.step} output and fix the underlying issue",
            })

        # Parse output for specific issues (simplified for MVP)
        if "conflict" in result.output.lower() or "error" in result.output.lower():
            findings.append({
                "category": "Compatibility Issue",
                "severity": "P2",
                "repair_classification": "confirmed-defect",
                "origin": "workflow-source",
                "evidence_layer": "generated-target-installed",
                "evidence": result.output[:500],  # First 500 chars
                "location": f"Scenario: {scenario_name}, Step: {result.step}",
                "description": f"Potential issue detected in {result.step} output",
                "investigation": "Review the output and determine if this is a real issue",
            })

    return findings
