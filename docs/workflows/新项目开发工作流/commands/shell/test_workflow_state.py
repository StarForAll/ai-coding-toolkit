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
SCRIPT = REPO_ROOT / "docs" / "workflows" / "新项目开发工作流" / "commands" / "shell" / "workflow-state.py"


class WorkflowStateScriptTests(unittest.TestCase):
    VALID_BRAINSTORM_ESTIMATE = """## 项目级粗估
- 预计总工时：12-16 人时
- 预计总工期：3-4 个工作日
- 预计完工窗口：2026-04-20 ~ 2026-04-23
- 估算置信度：中
- 估算前提：需求范围维持当前冻结版本，不新增支付与后台审批链路
"""

    VALID_CUSTOMER_ESTIMATE = """## 项目级粗估摘要
- 预计总工期：3-4 个工作日
- 预计完工窗口：2026-04-20 ~ 2026-04-23
- 估算说明：基于当前已确认范围的区间粗估，若范围变化需重新评估
"""

    VALID_INTERNAL_ASSESSMENT = """# assessment
- `project_engagement_type`: `non_outsourcing`
- 法律/合规风险结论：通过
- 是否允许进入 brainstorm：是
"""

    VALID_EXTERNAL_ASSESSMENT = """# assessment
- `project_engagement_type`: `external_outsourcing`
- `kickoff_payment_ratio`: `30%`
- `kickoff_payment_received`: `yes`
- `delivery_control_track`: `hosted_deployment`
- `delivery_control_handover_trigger`: `final_payment_received`
- `delivery_control_retained_scope`: source code and production keys
- `source_watermark_level`: `none`
- `source_watermark_channels`: `none`
- `zero_width_watermark_enabled`: `no`
- `subtle_code_marker_enabled`: `no`
- `ownership_proof_required`: `no`
- 法律/合规风险结论：通过
- 是否允许进入 brainstorm：是
"""

    VALID_EXTERNAL_TRIAL_ASSESSMENT = """# assessment
- `project_engagement_type`: `external_outsourcing`
- `kickoff_payment_ratio`: `40%`
- `kickoff_payment_received`: `yes`
- `delivery_control_track`: `trial_authorization`
- `delivery_control_handover_trigger`: `final_payment_received`
- `delivery_control_retained_scope`: source code
- `trial_authorization_terms.validity`: 90天
- `trial_authorization_terms.clock_source_or_usage_basis`: 首次部署日
- `trial_authorization_terms.expiration_behavior`: 只读模式
- `trial_authorization_terms.renewal_policy`: 续费延长
- `trial_authorization_terms.permanent_authorization_trigger`: 尾款到账
- `source_watermark_level`: `none`
- `source_watermark_channels`: `none`
- `zero_width_watermark_enabled`: `no`
- `subtle_code_marker_enabled`: `no`
- `ownership_proof_required`: `no`
- 法律/合规风险结论：通过
- 是否允许进入 brainstorm：是
"""

    def run_script(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [PYTHON, str(SCRIPT), *args],
            cwd=cwd or REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def make_fixture(self) -> tuple[Path, Path]:
        root = Path(tempfile.mkdtemp(prefix="workflow-state-test-"))
        self.addCleanup(shutil.rmtree, root)
        (root / ".trellis" / "tasks").mkdir(parents=True, exist_ok=True)
        task_dir = root / ".trellis" / "tasks" / "04-15-sample-task"
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "task.json").write_text('{"status":"planning","children":[]}\n', encoding="utf-8")
        (root / ".trellis" / ".current-task").write_text(
            ".trellis/tasks/04-15-sample-task\n",
            encoding="utf-8",
        )
        return root, task_dir

    def write_required_project_docs(
        self,
        root: Path,
        task_dir: Path,
        *,
        task_prd_suffix: str = "",
        customer_prd_suffix: str = "",
        assessment_content: str | None = None,
    ) -> None:
        requirements_dir = root / "docs" / "requirements"
        requirements_dir.mkdir(parents=True, exist_ok=True)
        (root / "README.md").write_text("# project\n", encoding="utf-8")
        (task_dir / "prd.md").write_text(
            "# sample task\n\n"
            f"{task_prd_suffix}",
            encoding="utf-8",
        )
        (requirements_dir / "customer-facing-prd.md").write_text(
            "# customer-facing prd\n\n"
            f"{customer_prd_suffix}",
            encoding="utf-8",
        )
        (task_dir / "assessment.md").write_text(
            assessment_content or self.VALID_INTERNAL_ASSESSMENT,
            encoding="utf-8",
        )

    def test_init_and_validate_pass_with_current_task_pointer(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )

        init = self.run_script("init", str(task_dir), "--stage", "design")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(init.returncode, 0, msg=init.stdout + init.stderr)
        self.assertEqual(validate.returncode, 0, msg=validate.stdout + validate.stderr)
        self.assertIn("workflow-state 校验通过", validate.stdout)

    def test_validate_rejects_unknown_state_version(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )

        self.run_script("init", str(task_dir), "--stage", "design")
        state_path = task_dir / "workflow-state.json"
        text = state_path.read_text(encoding="utf-8").replace('"version": 1', '"version": 999')
        state_path.write_text(text, encoding="utf-8")

        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("version 非法或暂不支持", validate.stdout)

    def test_validate_fails_when_current_task_is_empty(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        (root / ".trellis" / ".current-task").write_text("", encoding="utf-8")

        self.run_script("init", str(task_dir), "--stage", "design")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn(".trellis/.current-task 不能为空", validate.stdout)

    def test_validate_fails_when_current_task_points_to_another_task(self) -> None:
        root, task_dir = self.make_fixture()
        (root / ".trellis" / ".current-task").write_text(
            ".trellis/tasks/04-15-other-task\n",
            encoding="utf-8",
        )
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )

        self.run_script("init", str(task_dir), "--stage", "brainstorm")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("与当前 task", validate.stdout)

    def test_validate_fails_when_task_has_children(self) -> None:
        root, task_dir = self.make_fixture()
        (task_dir / "task.json").write_text('{"status":"planning","children":["04-15-child-task"]}\n', encoding="utf-8")
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )

        self.run_script("init", str(task_dir), "--stage", "plan")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("不应继续作为执行态叶子任务", validate.stdout)

    def test_validate_fails_when_design_before_arch_confirm_has_developer_prd(self) -> None:
        root, task_dir = self.make_fixture()
        requirements_dir = root / "docs" / "requirements"
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        (requirements_dir / "developer-facing-prd.md").write_text("# developer\n", encoding="utf-8")

        self.run_script("init", str(task_dir), "--stage", "design")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("developer-facing-prd.md", validate.stdout)

    def test_validate_passes_after_arch_confirm_with_developer_prd(self) -> None:
        root, task_dir = self.make_fixture()
        requirements_dir = root / "docs" / "requirements"
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        (requirements_dir / "developer-facing-prd.md").write_text("# developer\n", encoding="utf-8")

        self.run_script("init", str(task_dir), "--stage", "design")
        self.run_script(
            "set",
            str(task_dir),
            "--architecture-confirmed",
            "true",
            "--stage-status",
            "in_progress",
        )
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 0, msg=validate.stdout + validate.stderr)

    def test_validate_fails_when_design_exit_missing_developer_prd(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )

        self.run_script("init", str(task_dir), "--stage", "design")
        self.run_script(
            "set",
            str(task_dir),
            "--architecture-confirmed",
            "true",
            "--completed-blocks",
            "block-a,block-b,block-c,block-d",
            "--stage-status",
            "awaiting_user_confirmation",
            "--awaiting-user-confirmation",
            "true",
        )
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("developer-facing-prd.md", validate.stdout)

    def test_validate_allows_design_mid_block_confirmation_without_readme(self) -> None:
        root, task_dir = self.make_fixture()
        requirements_dir = root / "docs" / "requirements"
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        (requirements_dir / "developer-facing-prd.md").write_text("# developer\n- body\n", encoding="utf-8")
        (root / "README.md").unlink()

        self.run_script("init", str(task_dir), "--stage", "design")
        self.run_script(
            "set",
            str(task_dir),
            "--architecture-confirmed",
            "true",
            "--completed-blocks",
            "block-a",
            "--stage-status",
            "awaiting_user_confirmation",
            "--awaiting-user-confirmation",
            "true",
        )
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 0, msg=validate.stdout + validate.stderr)

    def test_validate_fails_when_design_exit_missing_readme(self) -> None:
        root, task_dir = self.make_fixture()
        requirements_dir = root / "docs" / "requirements"
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        (requirements_dir / "developer-facing-prd.md").write_text("# developer\n- body\n", encoding="utf-8")
        (root / "README.md").unlink()

        self.run_script("init", str(task_dir), "--stage", "design")
        self.run_script(
            "set",
            str(task_dir),
            "--architecture-confirmed",
            "true",
            "--completed-blocks",
            "block-a,block-b,block-c,block-d",
            "--stage-status",
            "awaiting_user_confirmation",
            "--awaiting-user-confirmation",
            "true",
        )
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("README.md", validate.stdout)

    def test_set_rejects_plan_stage_execution_authorized_true(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )

        self.run_script("init", str(task_dir), "--stage", "plan")
        illegal_set = self.run_script("set", str(task_dir), "--execution-authorized", "true")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(illegal_set.returncode, 1, msg=illegal_set.stdout + illegal_set.stderr)
        self.assertIn("拒绝写入非法 workflow-state", illegal_set.stdout)
        self.assertEqual(validate.returncode, 0, msg=validate.stdout + validate.stderr)

    def test_validate_fails_when_implementation_has_no_execution_authorization(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )

        self.run_script("init", str(task_dir), "--stage", "implementation")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("execution_authorized 必须为 true", validate.stdout)
        self.assertIn("进入执行阶段的确认记录", validate.stdout)

    def test_validate_passes_when_implementation_has_confirmation_record(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )

        self.run_script("init", str(task_dir), "--stage", "implementation")
        self.run_script(
            "set",
            str(task_dir),
            "--execution-authorized",
            "true",
            "--transition-from",
            "plan",
        )
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 0, msg=validate.stdout + validate.stderr)

    def test_validate_fails_when_post_feasibility_stage_has_no_assessment(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        (task_dir / "assessment.md").unlink()

        self.run_script("init", str(task_dir), "--stage", "design")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("缺少 assessment.md", validate.stdout)

    def test_validate_blocks_external_execution_until_kickoff_received(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
            assessment_content=self.VALID_EXTERNAL_ASSESSMENT.replace("`yes`", "`no`", 1),
        )

        self.run_script("init", str(task_dir), "--stage", "implementation")
        self.run_script(
            "set",
            str(task_dir),
            "--execution-authorized",
            "true",
            "--transition-from",
            "plan",
        )
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("启动款未确认到账前，不得进入 implementation / test-first", validate.stdout)

    def test_validate_allows_external_execution_after_kickoff_received(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
            assessment_content=self.VALID_EXTERNAL_ASSESSMENT,
        )

        self.run_script("init", str(task_dir), "--stage", "implementation")
        self.run_script(
            "set",
            str(task_dir),
            "--execution-authorized",
            "true",
            "--transition-from",
            "plan",
        )
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 0, msg=validate.stdout + validate.stderr)

    def test_validate_blocks_external_stage_when_handover_trigger_missing(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
            assessment_content=self.VALID_EXTERNAL_ASSESSMENT.replace(
                "- `delivery_control_handover_trigger`: `final_payment_received`\n",
                "",
            ),
        )

        self.run_script("init", str(task_dir), "--stage", "design")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("delivery_control_handover_trigger", validate.stdout)

    def test_validate_blocks_external_stage_when_ownership_policy_missing(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
            assessment_content=self.VALID_EXTERNAL_ASSESSMENT.replace(
                "- `source_watermark_level`: `none`\n"
                "- `source_watermark_channels`: `none`\n"
                "- `zero_width_watermark_enabled`: `no`\n"
                "- `subtle_code_marker_enabled`: `no`\n"
                "- `ownership_proof_required`: `no`\n",
                "",
            ),
        )

        self.run_script("init", str(task_dir), "--stage", "design")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("source_watermark_level", validate.stdout)

    def test_validate_blocks_external_stage_when_retained_scope_missing(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
            assessment_content=self.VALID_EXTERNAL_ASSESSMENT.replace(
                "- `delivery_control_retained_scope`: source code and production keys\n",
                "",
            ),
        )

        self.run_script("init", str(task_dir), "--stage", "plan")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("delivery_control_retained_scope", validate.stdout)

    def test_validate_blocks_trial_authorization_when_terms_missing(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
            assessment_content=self.VALID_EXTERNAL_TRIAL_ASSESSMENT.replace(
                "- `trial_authorization_terms.renewal_policy`: 续费延长\n",
                "",
            ),
        )

        self.run_script("init", str(task_dir), "--stage", "design")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("trial_authorization_terms.renewal_policy", validate.stdout)

    def test_set_rejects_plan_to_implementation_without_execution_authorization(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )

        self.run_script("init", str(task_dir), "--stage", "plan")
        illegal_set = self.run_script("set", str(task_dir), "--stage", "implementation")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(illegal_set.returncode, 1, msg=illegal_set.stdout + illegal_set.stderr)
        self.assertIn("拒绝写入非法 workflow-state", illegal_set.stdout)
        self.assertEqual(validate.returncode, 0, msg=validate.stdout + validate.stderr)

    def test_validate_fails_when_transition_record_targets_other_stage(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )

        self.run_script("init", str(task_dir), "--stage", "implementation")
        state_path = task_dir / "workflow-state.json"
        state_path.write_text(
            state_path.read_text(encoding="utf-8")
            .replace('"execution_authorized": false', '"execution_authorized": true')
            .replace(
                '"last_confirmed_transition": null',
                '"last_confirmed_transition": {"from": "plan", "to": "test-first", "confirmed_at": "2026-04-16T00:00:00+00:00"}',
            ),
            encoding="utf-8",
        )

        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("last_confirmed_transition.to 必须等于当前 stage", validate.stdout)

    def test_validate_passes_when_test_first_has_confirmation_record(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )

        self.run_script("init", str(task_dir), "--stage", "test-first")
        self.run_script(
            "set",
            str(task_dir),
            "--execution-authorized",
            "true",
            "--transition-from",
            "plan",
        )
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 0, msg=validate.stdout + validate.stderr)

    def test_validate_fails_when_test_first_tries_to_bypass_project_estimate_gate(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(root, task_dir)

        self.run_script("init", str(task_dir), "--stage", "test-first")
        self.run_script(
            "set",
            str(task_dir),
            "--execution-authorized",
            "true",
            "--transition-from",
            "brainstorm",
        )
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("项目级粗估", validate.stdout)

    def test_validate_passes_when_brainstorm_has_no_customer_prd_yet(self) -> None:
        root, task_dir = self.make_fixture()
        (task_dir / "prd.md").write_text("# sample brainstorm draft\n", encoding="utf-8")
        (task_dir / "assessment.md").write_text(self.VALID_INTERNAL_ASSESSMENT, encoding="utf-8")

        self.run_script("init", str(task_dir), "--stage", "brainstorm")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 0, msg=validate.stdout + validate.stderr)

    def test_validate_passes_when_implementation_uses_task_prd_only_for_l0_path(self) -> None:
        root, task_dir = self.make_fixture()
        (task_dir / "prd.md").write_text(
            "# sample task\n\n"
            f"{self.VALID_BRAINSTORM_ESTIMATE}",
            encoding="utf-8",
        )
        (task_dir / "assessment.md").write_text(self.VALID_INTERNAL_ASSESSMENT, encoding="utf-8")

        self.run_script("init", str(task_dir), "--stage", "implementation")
        self.run_script(
            "set",
            str(task_dir),
            "--execution-authorized",
            "true",
            "--transition-from",
            "brainstorm",
        )
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 0, msg=validate.stdout + validate.stderr)

    def test_validate_passes_when_implementation_ignores_customer_estimate_summary_for_l0_path(self) -> None:
        root, task_dir = self.make_fixture()
        requirements_dir = root / "docs" / "requirements"
        requirements_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "prd.md").write_text(
            "# sample task\n\n"
            f"{self.VALID_BRAINSTORM_ESTIMATE}",
            encoding="utf-8",
        )
        (task_dir / "assessment.md").write_text(self.VALID_INTERNAL_ASSESSMENT, encoding="utf-8")
        (requirements_dir / "customer-facing-prd.md").write_text(
            "# customer-facing prd\n\n"
            "## 需求概览\n- 这是 L0 路径下自愿创建的正式 PRD\n",
            encoding="utf-8",
        )

        self.run_script("init", str(task_dir), "--stage", "implementation")
        self.run_script(
            "set",
            str(task_dir),
            "--execution-authorized",
            "true",
            "--transition-from",
            "brainstorm",
        )
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 0, msg=validate.stdout + validate.stderr)

    def test_validate_fails_when_design_missing_project_estimate_gate(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(root, task_dir)

        self.run_script("init", str(task_dir), "--stage", "design")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("项目级粗估", validate.stdout)

    def test_validate_fails_when_execution_stage_tries_to_bypass_project_estimate_gate(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(root, task_dir)

        self.run_script("init", str(task_dir), "--stage", "implementation")
        self.run_script(
            "set",
            str(task_dir),
            "--execution-authorized",
            "true",
            "--transition-from",
            "plan",
        )
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("项目级粗估", validate.stdout)


    # ------------------------------------------------------------------
    # route subcommand tests
    # ------------------------------------------------------------------

    def test_cmd_route_first_entry(self) -> None:
        """No .current-task, no assessment.md anywhere -> first_entry."""
        root = Path(tempfile.mkdtemp(prefix="workflow-state-test-"))
        self.addCleanup(shutil.rmtree, root)
        (root / ".trellis" / "tasks").mkdir(parents=True, exist_ok=True)
        # No .current-task, no assessment.md

        result = self.run_script("route", "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        import json as _json
        data = _json.loads(result.stdout)
        self.assertEqual(data["target"], "feasibility")
        self.assertEqual(data["action"], "first_entry")

    def test_cmd_route_resume_assessment(self) -> None:
        """No .current-task, but assessment.md exists with brainstorm allowed -> resume_with_assessment."""
        root = Path(tempfile.mkdtemp(prefix="workflow-state-test-"))
        self.addCleanup(shutil.rmtree, root)
        task_dir = root / ".trellis" / "tasks" / "04-15-sample-task"
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "task.json").write_text('{"status":"planning","children":[]}\n', encoding="utf-8")
        # Write assessment.md with brainstorm permission
        (task_dir / "assessment.md").write_text(self.VALID_INTERNAL_ASSESSMENT, encoding="utf-8")
        # No .current-task file

        result = self.run_script("route", "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        import json as _json
        data = _json.loads(result.stdout)
        self.assertEqual(data["target"], "brainstorm")
        self.assertEqual(data["action"], "resume_with_assessment")

    def test_cmd_route_normal_reenter(self) -> None:
        """.current-task points to valid leaf task with stage=design, status=in_progress -> reenter."""
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.run_script("init", str(task_dir), "--stage", "design")

        result = self.run_script("route", str(task_dir), "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        import json as _json
        data = _json.loads(result.stdout)
        self.assertEqual(data["target"], "design")
        self.assertEqual(data["action"], "reenter")
        self.assertEqual(data["stage"], "design")
        self.assertEqual(data["stage_status"], "in_progress")

    def test_cmd_route_awaiting_confirmation(self) -> None:
        """workflow-state has stage_status=awaiting_user_confirmation -> awaiting_confirmation."""
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.run_script("init", str(task_dir), "--stage", "design")
        self.run_script(
            "set",
            str(task_dir),
            "--stage-status",
            "awaiting_user_confirmation",
            "--awaiting-user-confirmation",
            "true",
        )

        result = self.run_script("route", str(task_dir), "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        import json as _json
        data = _json.loads(result.stdout)
        self.assertEqual(data["target"], "design")
        self.assertEqual(data["action"], "awaiting_confirmation")
        self.assertEqual(data["stage"], "design")
        self.assertEqual(data["stage_status"], "awaiting_user_confirmation")

    def test_cmd_route_no_current_task_recovery(self) -> None:
        """No .current-task, assessment exists but lacks brainstorm permission field -> recovery_needed."""
        root = Path(tempfile.mkdtemp(prefix="workflow-state-test-"))
        self.addCleanup(shutil.rmtree, root)
        task_dir = root / ".trellis" / "tasks" / "04-15-sample-task"
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "task.json").write_text('{"status":"planning","children":[]}\n', encoding="utf-8")
        # assessment.md exists but has NO "是否允许进入 brainstorm" line at all
        (task_dir / "assessment.md").write_text(
            "# assessment\n- `project_engagement_type`: `non_outsourcing`\n- 法律/合规风险结论：通过\n",
            encoding="utf-8",
        )
        # No .current-task file

        result = self.run_script("route", "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        import json as _json
        data = _json.loads(result.stdout)
        self.assertEqual(data["action"], "recovery_needed")

    def test_cmd_route_repair_needed(self) -> None:
        """.current-task points to task dir without workflow-state.json -> repair_needed."""
        root, task_dir = self.make_fixture()
        # Do NOT run init — no workflow-state.json

        result = self.run_script("route", str(task_dir), "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        import json as _json
        data = _json.loads(result.stdout)
        self.assertEqual(data["action"], "repair_needed")

    def test_cmd_route_embed_invalid_when_install_record_exists_without_library_lock(self) -> None:
        """workflow-installed.json exists but library-lock.yaml is missing -> embed_invalid."""
        root = Path(tempfile.mkdtemp(prefix="workflow-state-test-"))
        self.addCleanup(shutil.rmtree, root)
        (root / ".trellis" / "tasks").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "workflow-installed.json").write_text('{"installed":"now"}\n', encoding="utf-8")

        result = self.run_script("route", "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        import json as _json
        data = _json.loads(result.stdout)
        self.assertEqual(data["action"], "embed_invalid")
        self.assertIn(".trellis/library-lock.yaml", data["reason"])

    # ------------------------------------------------------------------
    # repair subcommand tests
    # ------------------------------------------------------------------

    def test_cmd_repair_infer_feasibility(self) -> None:
        """Task dir with no assessment.md -> infer feasibility."""
        root, task_dir = self.make_fixture()
        # No assessment.md, no workflow-state.json

        result = self.run_script("repair", str(task_dir), "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        import json as _json
        # May output multiple JSON objects; take the first one
        data = _json.loads(result.stdout.strip().split("\n}")[0] + "\n}")
        self.assertEqual(data["inferred_stage"], "feasibility")

    def test_cmd_repair_infer_design(self) -> None:
        """Task dir with assessment.md, customer-facing-prd.md, and design/ dir -> infer design."""
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        # Create design/ dir (without task_plan.md -> should infer design, not plan)
        (task_dir / "design").mkdir(parents=True, exist_ok=True)

        result = self.run_script("repair", str(task_dir), "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        import json as _json
        data = _json.loads(result.stdout.strip().split("\n}")[0] + "\n}")
        self.assertEqual(data["inferred_stage"], "design")

    def test_cmd_repair_apply(self) -> None:
        """With --apply flag, should create workflow-state.json."""
        root, task_dir = self.make_fixture()
        # No assessment.md -> infer feasibility
        state_path = task_dir / "workflow-state.json"
        self.assertFalse(state_path.exists())

        result = self.run_script("repair", str(task_dir), "--project-root", str(root), "--apply")

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertTrue(state_path.exists(), "workflow-state.json should be created after --apply")
        import json as _json
        state = _json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["stage"], "feasibility")
        self.assertEqual(state["version"], 1)

    # ------------------------------------------------------------------
    # tolerant version handling test
    # ------------------------------------------------------------------

    def test_tolerant_missing_version(self) -> None:
        """workflow-state.json without 'version' field -> validate should not fail on version check."""
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        # Init normally, then strip the version field
        self.run_script("init", str(task_dir), "--stage", "design")
        state_path = task_dir / "workflow-state.json"
        import json as _json
        state = _json.loads(state_path.read_text(encoding="utf-8"))
        del state["version"]
        state_path.write_text(_json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 0, msg=validate.stdout + validate.stderr)
        self.assertIn("workflow-state 校验通过", validate.stdout)


if __name__ == "__main__":
    unittest.main()
