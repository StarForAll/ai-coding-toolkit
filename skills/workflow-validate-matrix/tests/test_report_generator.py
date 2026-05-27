#!/usr/bin/env python3
"""Unit tests for workflow-validate-matrix report generation."""

from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

from report_generator import generate_report, parse_validation_output_to_findings, verify_report
from validation_runner import ValidationResult


class ReportGeneratorTests(unittest.TestCase):
    def test_mixed_failed_and_success_findings_keep_summary_ids_aligned(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wvm-report-") as tmp:
            root = Path(tmp)
            failed_dir = root / "failed"
            success_dir = root / "success"
            failed_dir.mkdir()
            success_dir.mkdir()
            report = root / "WORKFLOW_QUESTIONS.md"

            generate_report(
                [
                    {
                        "scenario": "failed",
                        "status": "failed",
                        "temp_dir": str(failed_dir),
                        "findings": [
                            {
                                "title": "Failed scenario finding",
                                "scenario": "failed",
                                "temp_dir": str(failed_dir),
                                "category": "script-behavior",
                                "severity": "P0",
                                "repair_classification": "confirmed-defect",
                                "origin": "workflow-source",
                                "evidence_layer": "generated-target-runtime",
                                "evidence": ["failed evidence"],
                                "location": ".",
                                "description": "failed",
                                "investigation": "check failed",
                            }
                        ],
                    },
                    {
                        "scenario": "success",
                        "status": "success",
                        "temp_dir": str(success_dir),
                        "findings": [
                            {
                                "title": "Design debt finding",
                                "scenario": "success",
                                "temp_dir": str(success_dir),
                                "category": "cli-adaptation",
                                "severity": "P1",
                                "repair_classification": "design-debt",
                                "origin": "trellis-native",
                                "evidence_layer": "generated-target-runtime",
                                "evidence": ["design evidence"],
                                "location": ".agents/skills",
                                "description": "design",
                                "investigation": "check design",
                            },
                            {
                                "title": "Evidence gap finding",
                                "scenario": "success",
                                "temp_dir": str(success_dir),
                                "category": "document-reference",
                                "severity": "P2",
                                "repair_classification": "evidence-gap",
                                "origin": "workflow-source",
                                "evidence_layer": "generated-target-installed",
                                "evidence": ["gap evidence"],
                                "location": ".trellis/workflow.md",
                                "description": "gap",
                                "investigation": "check gap",
                            },
                        ],
                    },
                ],
                report,
                workflow_version="0.test",
                workflow_schema_version="3",
                trellis_version="0.test",
            )

            content = report.read_text(encoding="utf-8")
            self.assertIn("- Confirmed Defects: WS-001", content)
            self.assertIn("- Design-Debt Items: WS-002", content)
            self.assertIn("- Evidence-Gap Items: WS-003", content)
            self.assertEqual(re.findall(r"^### (WS-\d{3}):", content, re.M), ["WS-001", "WS-002", "WS-003"])
            self.assertIn("- **Temp Project Location**: success/.agents/skills", content)

    def test_verify_report_rejects_summary_classification_drift(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wvm-report-") as tmp:
            root = Path(tmp)
            scenario_dir = root / "scenario"
            scenario_dir.mkdir()
            report = root / "WORKFLOW_QUESTIONS.md"
            generate_report(
                [
                    {
                        "scenario": "scenario",
                        "status": "success",
                        "temp_dir": str(scenario_dir),
                        "findings": [
                            {
                                "title": "Design debt finding",
                                "scenario": "scenario",
                                "temp_dir": str(scenario_dir),
                                "category": "cli-adaptation",
                                "severity": "P1",
                                "repair_classification": "design-debt",
                                "origin": "trellis-native",
                                "evidence_layer": "generated-target-runtime",
                                "evidence": ["design evidence"],
                                "location": ".agents/skills",
                                "description": "design",
                                "investigation": "check design",
                            }
                        ],
                    }
                ],
                report,
                workflow_version="0.test",
                workflow_schema_version="3",
                trellis_version="0.test",
            )
            content = report.read_text(encoding="utf-8").replace(
                "- Design-Debt Items: WS-001",
                "- Design-Debt Items: none",
            )
            report.write_text(content, encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "classification IDs"):
                verify_report(report)

    def test_parse_validation_output_to_findings_collects_structured_warning_findings(self) -> None:
        result = ValidationResult(
            step="upgrade-compat",
            success=True,
            findings=[
                {
                    "title": "upgrade-compat emitted warnings",
                    "step": "upgrade-compat",
                    "severity": "P2",
                    "repair_classification": "evidence-gap",
                }
            ],
        )

        findings = parse_validation_output_to_findings([result], "scenario")

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["scenario"], "scenario")
        self.assertEqual(findings[0]["repair_classification"], "evidence-gap")

    def test_verify_report_ignores_embedded_severity_label_inside_description_text(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wvm-report-") as tmp:
            root = Path(tmp)
            scenario_dir = root / "scenario"
            scenario_dir.mkdir()
            report = root / "WORKFLOW_QUESTIONS.md"
            generate_report(
                [
                    {
                        "scenario": "scenario",
                        "status": "success",
                        "temp_dir": str(scenario_dir),
                        "findings": [
                            {
                                "title": "Description mentions severity label",
                                "scenario": "scenario",
                                "temp_dir": str(scenario_dir),
                                "category": "script-behavior",
                                "severity": "P1",
                                "repair_classification": "design-debt",
                                "origin": "workflow-source",
                                "evidence_layer": "generated-target-runtime",
                                "evidence": ["normal evidence"],
                                "location": ".",
                                "description": "- **Severity Estimate**: P2 should stay inside the description payload",
                                "investigation": "check parser",
                            }
                        ],
                    }
                ],
                report,
                workflow_version="0.test",
                workflow_schema_version="3",
                trellis_version="0.test",
            )

            verify_report(report)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
