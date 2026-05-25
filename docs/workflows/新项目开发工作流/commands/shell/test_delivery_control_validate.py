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
SCRIPT = REPO_ROOT / "docs" / "workflows" / "新项目开发工作流" / "commands" / "shell" / "delivery-control-validate.py"

COMPLETE_HOSTED_ASSESSMENT = """\
# 评估
- 总体决策：接
- 是否允许进入 brainstorm：是
- `project_engagement_type`: `external_outsourcing`
- `kickoff_payment_ratio`: `30%`
- `kickoff_payment_received`: `yes`
- `delivery_control_track`: `hosted_deployment`
- `delivery_control_handover_trigger`: `final_payment_received`
- `delivery_control_retained_scope`: source code and keys
- `milestone_payment_schedule`: `M1:40%,M2:30%,Final:30%`
- `non_payment_remedy_path`: `written_notice -> retained_control_delivery_only -> suspend_final_handover`
- `dispute_escalation_path`: `technical_review -> project_negotiation -> third_party_arbitration`
"""

COMPLETE_TRIAL_ASSESSMENT = """\
# 评估
- 总体决策：接
- 是否允许进入 brainstorm：是
- `project_engagement_type`: `external_outsourcing`
- `kickoff_payment_ratio`: `40%`
- `kickoff_payment_received`: `yes`
- `delivery_control_track`: `trial_authorization`
- `delivery_control_handover_trigger`: `final_payment_received`
- `delivery_control_retained_scope`: source code
- `milestone_payment_schedule`: `M1:40%,M2:30%,Final:30%`
- `non_payment_remedy_path`: `written_notice -> trial_expiration_read_only -> suspend_permanent_authorization`
- `dispute_escalation_path`: `technical_review -> project_negotiation -> third_party_arbitration`
- `trial_authorization_terms.validity`: 90天
- `trial_authorization_terms.clock_source_or_usage_basis`: 首次部署日
- `trial_authorization_terms.expiration_behavior`: 只读模式
- `trial_authorization_terms.renewal_policy`: 续费延长
- `trial_authorization_terms.permanent_authorization_trigger`: 尾款到账
"""

PLAN_WITH_DELIVERY = """\
# Task Plan

## 外部项目交付控制

### 交付控制任务
- 开工授权确认任务
- 托管部署任务
- 源码移交任务
- 控制权移交任务

### 开工触发条件
- 首款到账后才允许 implementation（kickoff_payment_received: yes）
- 里程碑付款按 `milestone_payment_schedule` 执行

### 交付触发条件
- 尾款到账后触发控制权移交（handover_trigger: final_payment_received）
- 若客户拒付，按 `non_payment_remedy_path` 执行
- 若出现验收争议，按 `dispute_escalation_path` 升级

## Trellis Task 清单

| 任务路径 | 类型 | 项目域 | 说明 |
|---------|------|--------|------|
| .trellis/tasks/04-14-hosted-deploy | implementation | delivery | 托管部署任务 |
| .trellis/tasks/04-14-source-handover | delivery | delivery | 源码移交任务 |
| .trellis/tasks/04-14-control-handover | delivery | delivery | 控制权移交任务 |
"""

DELIVERY_DIR_CONTENT = {
    "transfer-checklist.md": "# Transfer Checklist\n\n"
    "## 当前事件允许移交什么\n"
    "- docs\n\n"
    "## 当前事件禁止标记为已移交什么\n"
    "- production keys\n\n"
    "## 触发条件 / 付款 / 权限 / 证明材料是否齐备\n"
    "- retained-control delivery\n"
    "- milestone_payment_schedule\n"
    "- non_payment_remedy_path\n"
    "- dispute_escalation_path\n",
    "deliverables.md": "# Deliverables\n\n"
    "## Closeout Assets\n"
    "- docs\n\n"
    "## Verification Evidence\n"
    "- lint: pass\n\n"
    "## Current Status\n"
    "- pass\n\n"
    "## Residual Risks\n"
    "- none\n",
    "acceptance.md": "# Acceptance\n\n"
    "## Acceptance Criteria Status\n"
    "- sample: pass\n\n"
    "## Blocking Findings\n"
    "- none\n\n"
    "## Acceptance Gate\n"
    "- pass\n\n"
    "## 当前交付状态\n"
    "- pass\n",
}


class DeliveryControlValidateTests(unittest.TestCase):
    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [PYTHON, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def _make_task_dir(self) -> Path:
        d = Path(tempfile.mkdtemp(prefix="dcv-test-"))
        self.addCleanup(shutil.rmtree, d)
        return d

    # ── feasibility phase ──

    def test_feasibility_fails_when_assessment_missing(self) -> None:
        d = self._make_task_dir()
        result = self.run_script("--phase", "feasibility", "--task-dir", str(d))
        self.assertEqual(result.returncode, 1)

    def test_feasibility_passes_for_internal_project(self) -> None:
        d = self._make_task_dir()
        (d / "assessment.md").write_text(
            "# 评估\n- `project_engagement_type`: `non_outsourcing`\n",
            encoding="utf-8",
        )
        result = self.run_script("--phase", "feasibility", "--task-dir", str(d))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_feasibility_passes_for_complete_hosted_deployment(self) -> None:
        d = self._make_task_dir()
        (d / "assessment.md").write_text(COMPLETE_HOSTED_ASSESSMENT, encoding="utf-8")
        result = self.run_script("--phase", "feasibility", "--task-dir", str(d))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_feasibility_fails_when_milestone_payment_schedule_missing(self) -> None:
        d = self._make_task_dir()
        content = COMPLETE_HOSTED_ASSESSMENT.replace(
            "- `milestone_payment_schedule`: `M1:40%,M2:30%,Final:30%`\n",
            "",
        )
        (d / "assessment.md").write_text(content, encoding="utf-8")
        result = self.run_script("--phase", "feasibility", "--task-dir", str(d))
        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("milestone_payment_schedule", result.stdout + result.stderr)

    def test_feasibility_fails_when_non_payment_or_dispute_path_missing(self) -> None:
        d = self._make_task_dir()
        content = COMPLETE_HOSTED_ASSESSMENT.replace(
            "- `non_payment_remedy_path`: `written_notice -> retained_control_delivery_only -> suspend_final_handover`\n",
            "",
        ).replace(
            "- `dispute_escalation_path`: `technical_review -> project_negotiation -> third_party_arbitration`\n",
            "",
        )
        (d / "assessment.md").write_text(content, encoding="utf-8")
        result = self.run_script("--phase", "feasibility", "--task-dir", str(d))
        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("non_payment_remedy_path", result.stdout + result.stderr)
        self.assertIn("dispute_escalation_path", result.stdout + result.stderr)

    def test_feasibility_checks_trial_terms(self) -> None:
        d = self._make_task_dir()
        # trial track but no terms
        content = (
            "# 评估\n"
            "- 总体决策：接\n"
            "- 是否允许进入 brainstorm：是\n"
            "- `project_engagement_type`: `external_outsourcing`\n"
            "- `kickoff_payment_ratio`: `30%`\n"
            "- `kickoff_payment_received`: `yes`\n"
            "- `delivery_control_track`: `trial_authorization`\n"
            "- `delivery_control_handover_trigger`: `final_payment_received`\n"
            "- `delivery_control_retained_scope`: source code\n"
        )
        (d / "assessment.md").write_text(content, encoding="utf-8")
        result = self.run_script("--phase", "feasibility", "--task-dir", str(d))
        self.assertEqual(result.returncode, 1)
        self.assertIn("trial_authorization_terms", result.stdout + result.stderr)

    def test_feasibility_passes_for_complete_trial(self) -> None:
        d = self._make_task_dir()
        (d / "assessment.md").write_text(COMPLETE_TRIAL_ASSESSMENT, encoding="utf-8")
        result = self.run_script("--phase", "feasibility", "--task-dir", str(d))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    # ── plan phase ──

    def test_plan_fails_when_plan_missing(self) -> None:
        d = self._make_task_dir()
        (d / "assessment.md").write_text(COMPLETE_HOSTED_ASSESSMENT, encoding="utf-8")
        result = self.run_script("--phase", "plan", "--task-dir", str(d))
        self.assertEqual(result.returncode, 1)

    def test_plan_passes_with_delivery_tasks(self) -> None:
        d = self._make_task_dir()
        (d / "assessment.md").write_text(COMPLETE_HOSTED_ASSESSMENT, encoding="utf-8")
        task_root = d / ".trellis" / "tasks"
        task_root.mkdir(parents=True)
        for name in ("04-14-hosted-deploy", "04-14-source-handover", "04-14-control-handover"):
            (task_root / name).mkdir(parents=True)
        (d / "task_plan.md").write_text(PLAN_WITH_DELIVERY, encoding="utf-8")
        result = self.run_script("--phase", "plan", "--task-dir", str(d))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_plan_fails_when_remedy_or_dispute_flow_missing(self) -> None:
        d = self._make_task_dir()
        (d / "assessment.md").write_text(COMPLETE_HOSTED_ASSESSMENT, encoding="utf-8")
        task_root = d / ".trellis" / "tasks"
        task_root.mkdir(parents=True)
        for name in ("04-14-hosted-deploy", "04-14-source-handover", "04-14-control-handover"):
            (task_root / name).mkdir(parents=True)
        content = PLAN_WITH_DELIVERY.replace(
            "- 若客户拒付，按 `non_payment_remedy_path` 执行\n",
            "",
        ).replace(
            "- 若出现验收争议，按 `dispute_escalation_path` 升级\n",
            "",
        )
        (d / "task_plan.md").write_text(content, encoding="utf-8")
        result = self.run_script("--phase", "plan", "--task-dir", str(d))
        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("non_payment_remedy_path", result.stdout + result.stderr)
        self.assertIn("dispute_escalation_path", result.stdout + result.stderr)

    def test_plan_passes_for_internal_project(self) -> None:
        d = self._make_task_dir()
        (d / "assessment.md").write_text(
            "# 评估\n- `project_engagement_type`: `non_outsourcing`\n",
            encoding="utf-8",
        )
        result = self.run_script("--phase", "plan", "--task-dir", str(d))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    # ── delivery phase ──

    def test_delivery_fails_when_dir_missing(self) -> None:
        d = self._make_task_dir()
        (d / "assessment.md").write_text(COMPLETE_HOSTED_ASSESSMENT, encoding="utf-8")
        result = self.run_script("--phase", "delivery", "--task-dir", str(d))
        self.assertEqual(result.returncode, 1)

    def test_feasibility_fails_when_project_type_missing(self) -> None:
        d = self._make_task_dir()
        (d / "assessment.md").write_text("# 评估\n", encoding="utf-8")
        result = self.run_script("--phase", "feasibility", "--task-dir", str(d))
        self.assertEqual(result.returncode, 1)
        self.assertIn("project_engagement_type", result.stdout + result.stderr)

    def test_delivery_passes_with_complete_docs(self) -> None:
        d = self._make_task_dir()
        (d / "assessment.md").write_text(COMPLETE_HOSTED_ASSESSMENT, encoding="utf-8")
        delivery = d / "delivery"
        delivery.mkdir()
        for name, content in DELIVERY_DIR_CONTENT.items():
            (delivery / name).write_text(content, encoding="utf-8")
        result = self.run_script("--phase", "delivery", "--task-dir", str(d))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_delivery_fails_when_acceptance_contract_is_placeholder_only(self) -> None:
        d = self._make_task_dir()
        (d / "assessment.md").write_text(COMPLETE_HOSTED_ASSESSMENT, encoding="utf-8")
        delivery = d / "delivery"
        delivery.mkdir()
        for name, content in DELIVERY_DIR_CONTENT.items():
            (delivery / name).write_text(content, encoding="utf-8")
        (delivery / "acceptance.md").write_text("# acceptance\n", encoding="utf-8")
        result = self.run_script("--phase", "delivery", "--task-dir", str(d))
        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("Acceptance Criteria Status", result.stdout + result.stderr)

    def test_delivery_fails_when_deliverables_contract_is_placeholder_only(self) -> None:
        d = self._make_task_dir()
        (d / "assessment.md").write_text(COMPLETE_HOSTED_ASSESSMENT, encoding="utf-8")
        delivery = d / "delivery"
        delivery.mkdir()
        for name, content in DELIVERY_DIR_CONTENT.items():
            (delivery / name).write_text(content, encoding="utf-8")
        (delivery / "deliverables.md").write_text("# deliverables\n", encoding="utf-8")
        result = self.run_script("--phase", "delivery", "--task-dir", str(d))
        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("Closeout Assets", result.stdout + result.stderr)

    def test_delivery_fails_when_transfer_checklist_missing_new_remedy_fields(self) -> None:
        d = self._make_task_dir()
        (d / "assessment.md").write_text(COMPLETE_HOSTED_ASSESSMENT, encoding="utf-8")
        delivery = d / "delivery"
        delivery.mkdir()
        incomplete = dict(DELIVERY_DIR_CONTENT)
        incomplete["transfer-checklist.md"] = "# Transfer Checklist\n\nretained-control delivery\n"
        for name, content in incomplete.items():
            (delivery / name).write_text(content, encoding="utf-8")
        result = self.run_script("--phase", "delivery", "--task-dir", str(d))
        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("milestone_payment_schedule", result.stdout + result.stderr)

    def test_delivery_passes_for_internal_project(self) -> None:
        d = self._make_task_dir()
        (d / "assessment.md").write_text(
            "# 评估\n- `project_engagement_type`: `non_outsourcing`\n",
            encoding="utf-8",
        )
        result = self.run_script("--phase", "delivery", "--task-dir", str(d))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    # ── --all ──

    def test_all_phases_reports_total(self) -> None:
        d = self._make_task_dir()
        (d / "assessment.md").write_text(COMPLETE_HOSTED_ASSESSMENT, encoding="utf-8")
        task_root = d / ".trellis" / "tasks"
        task_root.mkdir(parents=True)
        for name in ("04-14-hosted-deploy", "04-14-source-handover", "04-14-control-handover"):
            (task_root / name).mkdir(parents=True)
        (d / "task_plan.md").write_text(PLAN_WITH_DELIVERY, encoding="utf-8")
        delivery = d / "delivery"
        delivery.mkdir()
        for name, content in DELIVERY_DIR_CONTENT.items():
            (delivery / name).write_text(content, encoding="utf-8")
        result = self.run_script("--all", "--task-dir", str(d))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("总计", result.stdout)

    def test_all_phases_pass_for_internal_project(self) -> None:
        d = self._make_task_dir()
        (d / "assessment.md").write_text(
            "# 评估\n- `project_engagement_type`: `non_outsourcing`\n",
            encoding="utf-8",
        )
        result = self.run_script("--all", "--task-dir", str(d))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_all_phases_fail_for_internal_project_when_assessment_invalid(self) -> None:
        d = self._make_task_dir()
        (d / "assessment.md").write_text("# 评估\n", encoding="utf-8")
        result = self.run_script("--all", "--task-dir", str(d))
        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("project_engagement_type", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
