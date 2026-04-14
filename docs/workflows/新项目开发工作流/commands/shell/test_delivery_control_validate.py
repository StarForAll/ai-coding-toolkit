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
- `delivery_control_track`: `hosted_deployment`
- `delivery_control_handover_trigger`: `final_payment_received`
- `delivery_control_retained_scope`: source code and keys
"""

COMPLETE_TRIAL_ASSESSMENT = """\
# 评估
- 总体决策：接
- 是否允许进入 brainstorm：是
- `delivery_control_track`: `trial_authorization`
- `delivery_control_handover_trigger`: `final_payment_received`
- `delivery_control_retained_scope`: source code
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
- 托管部署任务
- 源码移交任务
- 控制权移交任务

### 交付触发条件
- 尾款到账后触发控制权移交（handover_trigger: final_payment_received）

## Trellis Task 清单

| 任务路径 | 类型 | 项目域 | 说明 |
|---------|------|--------|------|
| .trellis/tasks/04-14-hosted-deploy | implementation | delivery | 托管部署任务 |
| .trellis/tasks/04-14-source-handover | delivery | delivery | 源码移交任务 |
| .trellis/tasks/04-14-control-handover | delivery | delivery | 控制权移交任务 |
"""

DELIVERY_DIR_CONTENT = {
    "transfer-checklist.md": "# Transfer Checklist\n\nretained-control delivery\n",
    "deliverables.md": "# Deliverables\n\n交付物清单\n",
    "acceptance.md": "# Acceptance\n",
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
        (d / "assessment.md").write_text("# no delivery fields\n", encoding="utf-8")
        result = self.run_script("--phase", "feasibility", "--task-dir", str(d))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_feasibility_passes_for_complete_hosted_deployment(self) -> None:
        d = self._make_task_dir()
        (d / "assessment.md").write_text(COMPLETE_HOSTED_ASSESSMENT, encoding="utf-8")
        result = self.run_script("--phase", "feasibility", "--task-dir", str(d))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_feasibility_checks_trial_terms(self) -> None:
        d = self._make_task_dir()
        # trial track but no terms
        content = (
            "# 评估\n"
            "- 总体决策：接\n"
            "- 是否允许进入 brainstorm：是\n"
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

    # ── delivery phase ──

    def test_delivery_fails_when_dir_missing(self) -> None:
        d = self._make_task_dir()
        (d / "assessment.md").write_text(COMPLETE_HOSTED_ASSESSMENT, encoding="utf-8")
        result = self.run_script("--phase", "delivery", "--task-dir", str(d))
        self.assertEqual(result.returncode, 1)

    def test_delivery_passes_with_complete_docs(self) -> None:
        d = self._make_task_dir()
        (d / "assessment.md").write_text(COMPLETE_HOSTED_ASSESSMENT, encoding="utf-8")
        delivery = d / "delivery"
        delivery.mkdir()
        for name, content in DELIVERY_DIR_CONTENT.items():
            (delivery / name).write_text(content, encoding="utf-8")
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


if __name__ == "__main__":
    unittest.main()
