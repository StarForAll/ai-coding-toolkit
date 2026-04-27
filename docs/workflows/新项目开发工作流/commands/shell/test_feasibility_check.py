from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[5]
PYTHON = (
    "/ops/softwares/python/bin/python3"
    if Path("/ops/softwares/python/bin/python3").exists()
    else shutil.which("python3") or shutil.which("python")
)
SCRIPT = REPO_ROOT / "docs" / "workflows" / "新项目开发工作流" / "commands" / "shell" / "feasibility-check.py"


class FeasibilityCheckTests(unittest.TestCase):
    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [PYTHON, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    # ── compliance step ──

    def test_compliance_step_prints_checklist(self) -> None:
        result = self.run_script("--step", "compliance")
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("法律与合规风险初筛清单", result.stdout)

    # ── estimate step ──

    def test_estimate_creates_template_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            result = self.run_script("--step", "estimate", "--task-dir", td)
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            assessment = Path(td) / "assessment.md"
            self.assertTrue(assessment.exists())
            text = assessment.read_text(encoding="utf-8")
            self.assertIn("项目可行性评估", text)
            self.assertIn("project_engagement_type", text)
            self.assertIn("delivery_control_track", text)
            self.assertIn("source_watermark_level", text)
            self.assertIn("阶段出口快照", text)

    def test_estimate_prints_existing_assessment(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            assessment = Path(td) / "assessment.md"
            assessment.write_text("# existing\n", encoding="utf-8")
            result = self.run_script("--step", "estimate", "--task-dir", td)
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            self.assertIn("当前 assessment.md 内容", result.stdout)

    # ── risk-analysis step ──

    def test_risk_analysis_creates_assessment_from_requirement_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            req = Path(td) / "req.md"
            req.write_text("build a login page", encoding="utf-8")
            result = self.run_script(
                "--step", "risk-analysis",
                "--task-dir", td,
                "--requirement-file", str(req),
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            self.assertTrue((Path(td) / "assessment.md").exists())
            self.assertTrue((Path(td) / "risk-analysis-guide.md").exists())

    def test_risk_analysis_fails_on_empty_requirement(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            req = Path(td) / "req.md"
            req.write_text("   \n", encoding="utf-8")
            result = self.run_script(
                "--step", "risk-analysis",
                "--task-dir", td,
                "--requirement-file", str(req),
            )
            self.assertIn("需求文本为空", result.stdout)

    # ── validate step ──

    def test_validate_fails_when_assessment_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            result = self.run_script("--step", "validate", "--task-dir", td)
            self.assertEqual(result.returncode, 1)

    def test_validate_fails_when_missing_legal_gate(self) -> None:
        content = (
            "# 评估\n"
            "- 总体决策：接\n"
            "- 是否允许进入 brainstorm：是\n"
            "\n"
            "## 红线检查\n"
            "✅ 通过\n"
        )
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "assessment.md").write_text(content, encoding="utf-8")
            result = self.run_script("--step", "validate", "--task-dir", td)
            self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
            self.assertIn("法律/合规风险结论", result.stdout + result.stderr)

    def test_validate_passes_for_internal_project_with_generic_gate(self) -> None:
        content = (
            "# 评估\n"
            "- 总体决策：接\n"
            "- 法律/合规风险结论：通过\n"
            "- 是否允许进入 brainstorm：是\n"
            "- `project_engagement_type`: `non_outsourcing`\n"
            "\n"
            "## 红线检查\n"
            "✅ 通过\n"
        )
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "assessment.md").write_text(content, encoding="utf-8")
            result = self.run_script("--step", "validate", "--task-dir", td)
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            self.assertIn("内部项目", result.stdout)

    def test_validate_passes_for_internal_project_without_ownership_fields(self) -> None:
        content = (
            "# 评估\n"
            "- 总体决策：接\n"
            "- 法律/合规风险结论：通过\n"
            "- 是否允许进入 brainstorm：是\n"
            "- `project_engagement_type`: `non_outsourcing`\n"
            "\n"
            "## 红线检查\n"
            "✅ 通过\n"
        )
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "assessment.md").write_text(content, encoding="utf-8")
            result = self.run_script("--step", "validate", "--task-dir", td)
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_validate_fails_when_external_project_missing_ownership_fields(self) -> None:
        content = (
            "# 评估\n"
            "- 总体决策：接\n"
            "- 法律/合规风险结论：通过\n"
            "- 是否允许进入 brainstorm：是\n"
            "- `project_engagement_type`: `external_outsourcing`\n"
            "- `kickoff_payment_ratio`: `30%`\n"
            "- `kickoff_payment_received`: `yes`\n"
            "\n"
            "## 红线检查\n"
            "✅ 通过\n"
            "- `delivery_control_track`: `hosted_deployment`\n"
            "- `delivery_control_handover_trigger`: `final_payment_received`\n"
            "- `delivery_control_retained_scope`: source code and keys\n"
        )
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "assessment.md").write_text(content, encoding="utf-8")
            result = self.run_script("--step", "validate", "--task-dir", td)
            self.assertEqual(result.returncode, 1)
            self.assertIn("source_watermark_level", result.stdout + result.stderr)

    def test_validate_fails_when_channels_is_placeholder(self) -> None:
        content = (
            "# 评估\n"
            "- 总体决策：接\n"
            "- 法律/合规风险结论：通过\n"
            "- 是否允许进入 brainstorm：是\n"
            "- `project_engagement_type`: `external_outsourcing`\n"
            "- `kickoff_payment_ratio`: `30%`\n"
            "- `kickoff_payment_received`: `yes`\n"
            "\n"
            "## 红线检查\n"
            "✅ 通过\n"
            "- `delivery_control_track`: `hosted_deployment`\n"
            "- `delivery_control_handover_trigger`: `final_payment_received`\n"
            "- `delivery_control_retained_scope`: source code and keys\n"
            "- `source_watermark_level`: `basic`\n"
            "- `source_watermark_channels`: `...`\n"
            "- `zero_width_watermark_enabled`: `no`\n"
            "- `subtle_code_marker_enabled`: `no`\n"
            "- `ownership_proof_required`: `yes`\n"
        )
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "assessment.md").write_text(content, encoding="utf-8")
            result = self.run_script("--step", "validate", "--task-dir", td)
            self.assertEqual(result.returncode, 1)
            self.assertIn("source_watermark_channels", result.stdout + result.stderr)

    def test_validate_passes_for_complete_hosted_deployment(self) -> None:
        content = (
            "# 评估\n"
            "- 总体决策：接\n"
            "- 法律/合规风险结论：通过\n"
            "- 是否允许进入 brainstorm：是\n"
            "- `project_engagement_type`: `external_outsourcing`\n"
            "- `kickoff_payment_ratio`: `30%`\n"
            "- `kickoff_payment_received`: `yes`\n"
            "\n"
            "## 红线检查\n"
            "✅ 通过\n"
            "- `delivery_control_track`: `hosted_deployment`\n"
            "- `delivery_control_handover_trigger`: `final_payment_received`\n"
            "- `delivery_control_retained_scope`: source code and keys\n"
            "- `source_watermark_level`: `none`\n"
            "- `source_watermark_channels`: `none`\n"
            "- `zero_width_watermark_enabled`: `no`\n"
            "- `subtle_code_marker_enabled`: `no`\n"
            "- `ownership_proof_required`: `no`\n"
        )
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "assessment.md").write_text(content, encoding="utf-8")
            result = self.run_script("--step", "validate", "--task-dir", td)
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            self.assertIn("验证通过", result.stdout)

    def test_validate_fails_when_track_invalid(self) -> None:
        content = (
            "# 评估\n"
            "- 总体决策：接\n"
            "- 法律/合规风险结论：通过\n"
            "- 是否允许进入 brainstorm：是\n"
            "- `project_engagement_type`: `external_outsourcing`\n"
            "- `kickoff_payment_ratio`: `30%`\n"
            "- `kickoff_payment_received`: `yes`\n"
            "\n"
            "## 红线检查\n"
            "✅ 通过\n"
            "- `delivery_control_track`: `invalid_value`\n"
            "- `delivery_control_handover_trigger`: `final_payment_received`\n"
            "- `delivery_control_retained_scope`: none\n"
            "- `source_watermark_level`: `none`\n"
            "- `source_watermark_channels`: `none`\n"
            "- `zero_width_watermark_enabled`: `no`\n"
            "- `subtle_code_marker_enabled`: `no`\n"
            "- `ownership_proof_required`: `no`\n"
        )
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "assessment.md").write_text(content, encoding="utf-8")
            result = self.run_script("--step", "validate", "--task-dir", td)
            self.assertEqual(result.returncode, 1)

    def test_validate_checks_trial_authorization_terms(self) -> None:
        content = (
            "# 评估\n"
            "- 总体决策：接\n"
            "- 法律/合规风险结论：通过\n"
            "- 是否允许进入 brainstorm：是\n"
            "- `project_engagement_type`: `external_outsourcing`\n"
            "- `kickoff_payment_ratio`: `40%`\n"
            "- `kickoff_payment_received`: `yes`\n"
            "\n"
            "## 红线检查\n"
            "✅ 通过\n"
            "- `delivery_control_track`: `trial_authorization`\n"
            "- `delivery_control_handover_trigger`: `final_payment_received`\n"
            "- `delivery_control_retained_scope`: source code\n"
            "- `source_watermark_level`: `none`\n"
            "- `source_watermark_channels`: `none`\n"
            "- `zero_width_watermark_enabled`: `no`\n"
            "- `subtle_code_marker_enabled`: `no`\n"
            "- `ownership_proof_required`: `no`\n"
        )
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "assessment.md").write_text(content, encoding="utf-8")
            result = self.run_script("--step", "validate", "--task-dir", td)
            self.assertEqual(result.returncode, 1)
            self.assertIn("trial_authorization_terms", result.stdout + result.stderr)

    def test_validate_fails_when_project_engagement_type_missing(self) -> None:
        content = (
            "# 评估\n"
            "- 总体决策：接\n"
            "- 法律/合规风险结论：通过\n"
            "- 是否允许进入 brainstorm：是\n"
            "\n"
            "## 红线检查\n"
            "✅ 通过\n"
        )
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "assessment.md").write_text(content, encoding="utf-8")
            result = self.run_script("--step", "validate", "--task-dir", td)
            self.assertEqual(result.returncode, 1)
            self.assertIn("project_engagement_type", result.stdout + result.stderr)

    def test_validate_warns_when_external_project_kickoff_not_received(self) -> None:
        content = (
            "# 评估\n"
            "- 总体决策：谈判后接\n"
            "- 法律/合规风险结论：通过\n"
            "- 是否允许进入 brainstorm：是\n"
            "- `project_engagement_type`: `external_outsourcing`\n"
            "- `kickoff_payment_ratio`: `30%`\n"
            "- `kickoff_payment_received`: `no`\n"
            "\n"
            "## 红线检查\n"
            "✅ 通过\n"
            "- `delivery_control_track`: `hosted_deployment`\n"
            "- `delivery_control_handover_trigger`: `final_payment_received`\n"
            "- `delivery_control_retained_scope`: source code and keys\n"
            "- `source_watermark_level`: `none`\n"
            "- `source_watermark_channels`: `none`\n"
            "- `zero_width_watermark_enabled`: `no`\n"
            "- `subtle_code_marker_enabled`: `no`\n"
            "- `ownership_proof_required`: `no`\n"
        )
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "assessment.md").write_text(content, encoding="utf-8")
            result = self.run_script("--step", "validate", "--task-dir", td)
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            self.assertIn("启动款到账", result.stdout + result.stderr)

    def test_validate_fails_when_ownership_required_has_invalid_level(self) -> None:
        content = (
            "# 评估\n"
            "- 总体决策：接\n"
            "- 法律/合规风险结论：通过\n"
            "- 是否允许进入 brainstorm：是\n"
            "- `project_engagement_type`: `external_outsourcing`\n"
            "- `kickoff_payment_ratio`: `30%`\n"
            "- `kickoff_payment_received`: `yes`\n"
            "\n"
            "## 红线检查\n"
            "✅ 通过\n"
            "- `delivery_control_track`: `hosted_deployment`\n"
            "- `delivery_control_handover_trigger`: `final_payment_received`\n"
            "- `delivery_control_retained_scope`: source code and keys\n"
            "- `source_watermark_level`: `none`\n"
            "- `source_watermark_channels`: `visible`\n"
            "- `zero_width_watermark_enabled`: `no`\n"
            "- `subtle_code_marker_enabled`: `no`\n"
            "- `ownership_proof_required`: `yes`\n"
        )
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "assessment.md").write_text(content, encoding="utf-8")
            result = self.run_script("--step", "validate", "--task-dir", td)
            self.assertEqual(result.returncode, 1)
            self.assertIn("source_watermark_level", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
