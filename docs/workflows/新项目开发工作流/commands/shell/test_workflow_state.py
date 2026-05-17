from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
import json
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
- `total_effort_hours`: `16`
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
- `source_watermark_level`: `basic`
- `source_watermark_channels`: `visible`
- `zero_width_watermark_enabled`: `no`
- `subtle_code_marker_enabled`: `no`
- `ownership_proof_required`: `yes`
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

    VALID_CONTEXT7_REVIEW = """# Context7 Review

- `context7_review_completed`: `yes`
- `review_scope`: backend + platform specs directly related to the confirmed architecture
- `review_summary`: 已核对直接相关第三方 spec 与官方文档，未发现阻断性冲突
- `blocking_findings`: none
- `open_items`: none
"""

    def run_script(
        self,
        *args: str,
        cwd: Path | None = None,
        env_overrides: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = {**os.environ, "TRELLIS_CONTEXT_ID": "test-context"}
        if env_overrides:
            for key, value in env_overrides.items():
                if value is None:
                    env.pop(key, None)
                else:
                    env[key] = value
        return subprocess.run(
            [PYTHON, str(SCRIPT), *args],
            cwd=cwd or REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            env=env,
        )

    def make_fixture(self) -> tuple[Path, Path]:
        root = Path(tempfile.mkdtemp(prefix="workflow-state-test-"))
        self.addCleanup(shutil.rmtree, root)
        (root / ".trellis" / "tasks").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / ".runtime" / "sessions").mkdir(parents=True, exist_ok=True)
        task_dir = root / ".trellis" / "tasks" / "04-15-sample-task"
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "task.json").write_text('{"status":"planning","children":[]}\n', encoding="utf-8")
        (root / ".trellis" / ".runtime" / "sessions" / "test-context.json").write_text(
            json.dumps({"current_task": ".trellis/tasks/04-15-sample-task"}, ensure_ascii=False) + "\n",
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
        (root / "README.en.md").write_text("# project\n", encoding="utf-8")
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

    def write_context7_review(self, task_dir: Path, content: str | None = None) -> None:
        design_dir = task_dir / "design"
        design_dir.mkdir(parents=True, exist_ok=True)
        (design_dir / "context7-review.md").write_text(
            content or self.VALID_CONTEXT7_REVIEW,
            encoding="utf-8",
        )

    def test_init_and_validate_pass_with_active_task_runtime(self) -> None:
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

    def test_validate_fails_when_active_task_is_missing(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        (root / ".trellis" / ".runtime" / "sessions" / "test-context.json").unlink()

        self.run_script("init", str(task_dir), "--stage", "design")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("无法从 Trellis session runtime 解析当前活动任务", validate.stdout)

    def test_validate_fails_when_active_task_points_to_another_task(self) -> None:
        root, task_dir = self.make_fixture()
        other_task_dir = root / ".trellis" / "tasks" / "04-15-other-task"
        other_task_dir.mkdir(parents=True, exist_ok=True)
        (other_task_dir / "task.json").write_text('{"status":"planning","children":[]}\n', encoding="utf-8")
        (root / ".trellis" / ".runtime" / "sessions" / "test-context.json").write_text(
            json.dumps({"current_task": ".trellis/tasks/04-15-other-task"}, ensure_ascii=False) + "\n",
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

    def test_validate_fails_when_design_exit_missing_english_readme(self) -> None:
        root, task_dir = self.make_fixture()
        requirements_dir = root / "docs" / "requirements"
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        (requirements_dir / "developer-facing-prd.md").write_text("# developer\n- body\n", encoding="utf-8")
        (root / "README.en.md").unlink()

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
        self.assertIn("README.en.md", validate.stdout)

    def test_set_rejects_plan_stage_execution_authorized_true(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.write_context7_review(task_dir)

        self.run_script("init", str(task_dir), "--stage", "plan")
        self.run_script("set", str(task_dir), "--context7-review-completed", "true")
        illegal_set = self.run_script("set", str(task_dir), "--execution-authorized", "true")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(illegal_set.returncode, 1, msg=illegal_set.stdout + illegal_set.stderr)
        self.assertIn("拒绝写入非法 workflow-state", illegal_set.stdout)
        self.assertEqual(validate.returncode, 0, msg=validate.stdout + validate.stderr)

    def test_validate_fails_when_plan_missing_context7_review_artifact(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )

        self.run_script("init", str(task_dir), "--stage", "plan")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("context7-review.md", validate.stdout)

    def test_validate_fails_when_plan_missing_context7_review_checkpoint(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.write_context7_review(task_dir)

        self.run_script("init", str(task_dir), "--stage", "plan")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("context7_review_completed", validate.stdout)

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

    def test_validate_feasibility_stage_checks_assessment_field_completeness(self) -> None:
        root, task_dir = self.make_fixture()
        (task_dir / "assessment.md").write_text(
            "# assessment\n- `project_engagement_type`: `non_outsourcing`\n",
            encoding="utf-8",
        )

        self.run_script("init", str(task_dir), "--stage", "feasibility")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("法律/合规风险结论", validate.stdout)
        self.assertIn("source_watermark_level", validate.stdout)

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

    def test_validate_blocks_internal_stage_when_ownership_policy_missing(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
            assessment_content=self.VALID_INTERNAL_ASSESSMENT.replace(
                "- `source_watermark_level`: `basic`\n"
                "- `source_watermark_channels`: `visible`\n"
                "- `zero_width_watermark_enabled`: `no`\n"
                "- `subtle_code_marker_enabled`: `no`\n"
                "- `ownership_proof_required`: `yes`\n",
                "",
            ),
        )

        self.run_script("init", str(task_dir), "--stage", "design")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("ownership_proof_required", validate.stdout)

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
        self.write_context7_review(task_dir)

        self.run_script("init", str(task_dir), "--stage", "plan")
        self.run_script("set", str(task_dir), "--context7-review-completed", "true")

        # Attempt 1: without awaiting_user_confirmation -> rejected at transition gate
        illegal_set = self.run_script("set", str(task_dir), "--stage", "implementation")
        self.assertEqual(illegal_set.returncode, 1, msg=illegal_set.stdout + illegal_set.stderr)
        self.assertIn("stage_status 必须为 awaiting_user_confirmation", illegal_set.stdout)

        # Attempt 2: set awaiting_user_confirmation but still no execution_authorized -> rejected
        self.run_script(
            "set", str(task_dir),
            "--stage-status", "awaiting_user_confirmation",
            "--awaiting-user-confirmation", "true",
        )
        illegal_set2 = self.run_script("set", str(task_dir), "--stage", "implementation")
        self.assertEqual(illegal_set2.returncode, 1, msg=illegal_set2.stdout + illegal_set2.stderr)
        self.assertIn("execution_authorized 必须为 true", illegal_set2.stdout)

        # Attempt 3: --force bypasses transition gate but NOT execution_boundary
        # (execution_boundary is a shape check, not a transition gate)
        illegal_force = self.run_script("set", str(task_dir), "--stage", "implementation", "--force")
        self.assertEqual(illegal_force.returncode, 1, msg=illegal_force.stdout + illegal_force.stderr)
        self.assertIn("execution_authorized", illegal_force.stdout)

        # Attempt 4: full legal transition with execution_authorized + transition record
        legal_set = self.run_script(
            "set", str(task_dir),
            "--stage", "implementation",
            "--execution-authorized", "true",
            "--transition-from", "plan",
        )
        self.assertEqual(legal_set.returncode, 0, msg=legal_set.stdout + legal_set.stderr)
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))
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

    def test_validate_fails_when_project_estimate_missing_total_effort_hours(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=(
                "## 项目级粗估\n"
                "- 预计总工时：12-16 人时\n"
                "- 预计总工期：3-4 个工作日\n"
                "- 预计完工窗口：2026-04-20 ~ 2026-04-23\n"
                "- 估算置信度：中\n"
                "- 估算前提：需求范围维持当前冻结版本\n"
            ),
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )

        self.run_script("init", str(task_dir), "--stage", "design")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("total_effort_hours", validate.stdout)


    # ------------------------------------------------------------------
    # route subcommand tests
    # ------------------------------------------------------------------

    def test_cmd_route_first_entry(self) -> None:
        """No active task and no tasks anywhere -> first_entry."""
        root = Path(tempfile.mkdtemp(prefix="workflow-state-test-"))
        self.addCleanup(shutil.rmtree, root)
        (root / ".trellis" / "tasks").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / ".runtime" / "sessions").mkdir(parents=True, exist_ok=True)

        result = self.run_script("route", "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        import json as _json
        data = _json.loads(result.stdout)
        self.assertEqual(data["target"], "feasibility")
        self.assertEqual(data["action"], "first_entry")

    def test_cmd_route_without_active_task_enters_recovery(self) -> None:
        """Existing tasks but no active task -> recovery_needed."""
        root = Path(tempfile.mkdtemp(prefix="workflow-state-test-"))
        self.addCleanup(shutil.rmtree, root)
        (root / ".trellis" / ".runtime" / "sessions").mkdir(parents=True, exist_ok=True)
        task_dir = root / ".trellis" / "tasks" / "04-15-sample-task"
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "task.json").write_text('{"status":"planning","children":[]}\n', encoding="utf-8")
        (task_dir / "assessment.md").write_text(self.VALID_INTERNAL_ASSESSMENT, encoding="utf-8")

        result = self.run_script("route", "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        import json as _json
        data = _json.loads(result.stdout)
        self.assertEqual(data["target"], None)
        self.assertEqual(data["action"], "recovery_needed")

    def test_cmd_route_normal_reenter(self) -> None:
        """Active task points to valid leaf task with stage=design, status=in_progress -> reenter."""
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

    def test_cmd_route_reenters_from_session_runtime_without_task_arg(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.run_script("init", str(task_dir), "--stage", "plan")

        result = self.run_script("route", "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        import json as _json
        data = _json.loads(result.stdout)
        self.assertEqual(data["target"], "plan")
        self.assertEqual(data["action"], "reenter")
        self.assertEqual(data["stage"], "plan")

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

    def test_cmd_route_no_active_task_recovery(self) -> None:
        """Existing tasks but no active task -> recovery_needed."""
        root = Path(tempfile.mkdtemp(prefix="workflow-state-test-"))
        self.addCleanup(shutil.rmtree, root)
        (root / ".trellis" / ".runtime" / "sessions").mkdir(parents=True, exist_ok=True)
        task_dir = root / ".trellis" / "tasks" / "04-15-sample-task"
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "task.json").write_text('{"status":"planning","children":[]}\n', encoding="utf-8")
        (task_dir / "assessment.md").write_text(
            "# assessment\n- `project_engagement_type`: `non_outsourcing`\n- 法律/合规风险结论：通过\n",
            encoding="utf-8",
        )

        result = self.run_script("route", "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        import json as _json
        data = _json.loads(result.stdout)
        self.assertEqual(data["action"], "recovery_needed")

    def test_cmd_route_repair_needed(self) -> None:
        """Active task points to task dir without workflow-state.json -> repair_needed."""
        root, task_dir = self.make_fixture()
        # Do NOT run init — no workflow-state.json

        result = self.run_script("route", str(task_dir), "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        import json as _json
        data = _json.loads(result.stdout)
        self.assertEqual(data["action"], "repair_needed")

    def test_cmd_route_repair_needed_when_state_shape_is_invalid(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.run_script("init", str(task_dir), "--stage", "design")
        state_path = task_dir / "workflow-state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["allowed_next_stages"] = ["not-a-stage"]
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        result = self.run_script("route", str(task_dir), "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "repair_needed")
        self.assertIn("allowed_next_stages", "".join(data.get("blockers", [])))

    def test_cmd_route_uses_degraded_fallback_even_when_platform_context_key_exists(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        session_file = root / ".trellis" / ".runtime" / "sessions" / "test-context.json"
        session_file.unlink()
        (root / ".trellis" / ".runtime" / "degraded-active-task.json").write_text(
            json.dumps({"current_task": ".trellis/tasks/04-15-sample-task"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        state = {
            "version": 1,
            "stage": "implementation",
            "stage_status": "in_progress",
            "current_block": None,
            "completed_blocks": [],
            "allowed_next_stages": [],
            "awaiting_user_confirmation": False,
            "last_confirmed_transition": {
                "from": "plan",
                "to": "implementation",
                "confirmed_at": "2026-05-16T00:00:00+00:00",
            },
            "notes": [],
            "checkpoints": {
                "architecture_confirmed": True,
                "context7_review_completed": True,
                "execution_authorized": True,
            },
            "updated_at": "2026-05-16T00:00:00+00:00",
        }
        (task_dir / "workflow-state.json").write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (root / "docs" / "requirements" / "developer-facing-prd.md").write_text("# developer\n", encoding="utf-8")
        self.write_context7_review(task_dir)

        result = self.run_script(
            "route",
            "--project-root",
            str(root),
            env_overrides={"TRELLIS_CONTEXT_ID": None, "CODEX_THREAD_ID": "codex-test-thread"},
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "reenter")
        self.assertEqual(data["stage"], "implementation")

    def test_cmd_route_uses_degraded_when_session_file_exists_without_current_task(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        session_file = root / ".trellis" / ".runtime" / "sessions" / "test-context.json"
        session_file.write_text(json.dumps({}, ensure_ascii=False) + "\n", encoding="utf-8")
        (root / ".trellis" / ".runtime" / "degraded-active-task.json").write_text(
            json.dumps({"current_task": ".trellis/tasks/04-15-sample-task"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        state = {
            "version": 1,
            "stage": "implementation",
            "stage_status": "in_progress",
            "current_block": None,
            "completed_blocks": [],
            "allowed_next_stages": [],
            "awaiting_user_confirmation": False,
            "last_confirmed_transition": {
                "from": "plan",
                "to": "implementation",
                "confirmed_at": "2026-05-16T00:00:00+00:00",
            },
            "notes": [],
            "checkpoints": {
                "architecture_confirmed": True,
                "context7_review_completed": True,
                "execution_authorized": True,
            },
            "updated_at": "2026-05-16T00:00:00+00:00",
        }
        (task_dir / "workflow-state.json").write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (root / "docs" / "requirements" / "developer-facing-prd.md").write_text("# developer\n", encoding="utf-8")
        self.write_context7_review(task_dir)

        result = self.run_script(
            "route",
            "--project-root",
            str(root),
            env_overrides={"TRELLIS_CONTEXT_ID": None, "CODEX_THREAD_ID": "codex-test-thread"},
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "reenter")
        self.assertEqual(data["stage"], "implementation")

    def test_cmd_route_ignores_degraded_when_session_files_exist(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        (root / ".trellis" / ".runtime" / "degraded-active-task.json").write_text(
            json.dumps({"current_task": ".trellis/tasks/04-15-sample-task"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        result = self.run_script(
            "route",
            "--project-root",
            str(root),
            env_overrides={"TRELLIS_CONTEXT_ID": None, "CODEX_THREAD_ID": "codex-test-thread"},
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "repair_needed")
        self.assertIn("workflow-state.json", data["reason"])

    def test_cmd_route_blocks_brainstorm_without_assessment_even_when_customer_prd_missing(self) -> None:
        root, task_dir = self.make_fixture()
        (task_dir / "task.json").write_text('{"status":"planning","children":[]}\n', encoding="utf-8")
        (task_dir / "prd.md").write_text("# sample\n", encoding="utf-8")
        self.run_script("init", str(task_dir), "--stage", "brainstorm")

        result = self.run_script("route", str(task_dir), "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        import json as _json
        data = _json.loads(result.stdout)
        self.assertEqual(data["action"], "repair_needed")
        self.assertIn("assessment", data["reason"])

    def test_cmd_route_blocks_plan_when_recommended_task_prd_missing(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        (task_dir / "prd.md").unlink()
        self.run_script("init", str(task_dir), "--stage", "plan")

        result = self.run_script("route", str(task_dir), "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        import json as _json
        data = _json.loads(result.stdout)
        self.assertEqual(data["action"], "blocked")
        self.assertIn("任务说明", "".join(data.get("blockers", [])))

    def test_cmd_route_blocks_execution_when_task_json_declares_unfinished_dependencies(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        dependency_dir = root / ".trellis" / "tasks" / "04-15-dependency"
        dependency_dir.mkdir(parents=True, exist_ok=True)
        (dependency_dir / "task.json").write_text('{"status":"in_progress","children":[]}\n', encoding="utf-8")
        (task_dir / "task.json").write_text(
            '{"status":"in_progress","children":[],"meta":{"depends_on":["04-15-dependency"]}}\n',
            encoding="utf-8",
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

        result = self.run_script("route", str(task_dir), "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        import json as _json
        data = _json.loads(result.stdout)
        self.assertEqual(data["action"], "blocked")
        self.assertIn("前置", "".join(data.get("blockers", [])))

    def test_cmd_route_plan_prompts_english_readme_requirement_when_design_docs_missing(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        (task_dir / "design").mkdir(parents=True, exist_ok=True)
        (root / "README.en.md").unlink()
        self.run_script("init", str(task_dir), "--stage", "plan")

        result = self.run_script("route", str(task_dir), "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        import json as _json
        data = _json.loads(result.stdout)
        self.assertEqual(data["action"], "blocked")
        self.assertIn("README.en.md", "".join(data.get("blockers", [])))

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

    def test_cmd_repair_infer_plan_from_root_task_plan(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        (task_dir / "design").mkdir(parents=True, exist_ok=True)
        (task_dir / "task_plan.md").write_text("# task plan\n", encoding="utf-8")

        result = self.run_script("repair", str(task_dir), "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout.strip().split("\n}")[0] + "\n}")
        self.assertEqual(data["inferred_stage"], "plan")

    def test_cmd_repair_infer_implementation_from_before_dev(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        (task_dir / "before-dev.md").write_text("# before dev\n", encoding="utf-8")

        result = self.run_script("repair", str(task_dir), "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout.strip().split("\n}")[0] + "\n}")
        self.assertEqual(data["inferred_stage"], "implementation")

    def test_cmd_repair_infer_check_from_check_md(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        (task_dir / "check.md").write_text("# check\n", encoding="utf-8")

        result = self.run_script("repair", str(task_dir), "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout.strip().split("\n}")[0] + "\n}")
        self.assertEqual(data["inferred_stage"], "check")

    def test_cmd_repair_infer_project_audit_from_project_audit_md(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        (task_dir / "project-audit.md").write_text("# project audit\n", encoding="utf-8")

        result = self.run_script("repair", str(task_dir), "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout.strip().split("\n}")[0] + "\n}")
        self.assertEqual(data["inferred_stage"], "project-audit")

    def test_cmd_repair_infer_review_gate_from_task_dir_artifacts(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        review_gate_dir = task_dir / "review-gate"
        review_gate_dir.mkdir(parents=True, exist_ok=True)
        (review_gate_dir / "review-gate-round-1.md").write_text("# review gate\n", encoding="utf-8")

        result = self.run_script("repair", str(task_dir), "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout.strip().split("\n}")[0] + "\n}")
        self.assertEqual(data["inferred_stage"], "review-gate")

    def test_cmd_repair_infer_delivery_from_delivery_artifacts(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        delivery_dir = task_dir / "delivery"
        delivery_dir.mkdir(parents=True, exist_ok=True)
        (delivery_dir / "acceptance.md").write_text("# acceptance\n", encoding="utf-8")

        result = self.run_script("repair", str(task_dir), "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout.strip().split("\n}")[0] + "\n}")
        self.assertEqual(data["inferred_stage"], "delivery")

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

    # ------------------------------------------------------------------
    # Regression tests for state machine fixes (Issue 3-7)
    # ------------------------------------------------------------------

    def test_issue3_non_execution_stage_transition_requires_awaiting(self) -> None:
        """Issue 3: Non-execution stage transitions also require awaiting_user_confirmation."""
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.run_script("init", str(task_dir), "--stage", "brainstorm")
        # Attempt to switch brainstorm→design without awaiting_user_confirmation
        illegal_set = self.run_script("set", str(task_dir), "--stage", "design")
        self.assertEqual(illegal_set.returncode, 1, msg=illegal_set.stdout + illegal_set.stderr)
        self.assertIn("stage_status 必须为 awaiting_user_confirmation", illegal_set.stdout)

        # With awaiting_user_confirmation it should succeed
        self.run_script(
            "set", str(task_dir),
            "--stage-status", "awaiting_user_confirmation",
            "--awaiting-user-confirmation", "true",
        )
        ok_set = self.run_script(
            "set", str(task_dir),
            "--stage", "design",
            "--stage-status", "in_progress",
            "--awaiting-user-confirmation", "false",
            "--transition-from", "brainstorm",
            "--allowed-next", "plan",
        )
        self.assertEqual(ok_set.returncode, 0, msg=ok_set.stdout + ok_set.stderr)

        # feasibility entry should NOT require awaiting (special case)
        self.run_script("init", str(task_dir), "--stage", "feasibility", "--force")
        feas_set = self.run_script("set", str(task_dir), "--stage", "brainstorm", "--force")
        # feasibility is exempt from the awaiting gate, but we use --force here
        # to bypass allowed_next_stages too
        self.assertEqual(feas_set.returncode, 0, msg=feas_set.stdout + feas_set.stderr)

    def test_issue3_force_bypasses_awaiting_gate(self) -> None:
        """Issue 3: --force still bypasses the awaiting_user_confirmation gate."""
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.run_script("init", str(task_dir), "--stage", "brainstorm")
        forced = self.run_script("set", str(task_dir), "--stage", "design", "--force")
        self.assertEqual(forced.returncode, 0, msg=forced.stdout + forced.stderr)

    def test_issue4_route_awaiting_with_blockers(self) -> None:
        """Issue 4: route returns awaiting_confirmation_with_blockers when awaiting but blockers exist."""
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        # Use brainstorm stage without assessment.md to guarantee a readiness blocker
        (task_dir / "assessment.md").unlink()
        self.run_script("init", str(task_dir), "--stage", "brainstorm")
        self.run_script(
            "set", str(task_dir),
            "--stage-status", "awaiting_user_confirmation",
            "--awaiting-user-confirmation", "true",
        )

        result = self.run_script("route", str(task_dir), "--project-root", str(root))
        import json as _json
        data = _json.loads(result.stdout)
        self.assertEqual(data["action"], "awaiting_confirmation_with_blockers")
        self.assertIn("blockers", data)
        self.assertTrue(len(data["blockers"]) > 0, "expected at least one blocker")

    def test_issue5_auto_reset_execution_authorized_on_stage_exit(self) -> None:
        """Issue 5: execution_authorized auto-resets when leaving execution stage."""
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.run_script("init", str(task_dir), "--stage", "implementation")
        self.run_script(
            "set", str(task_dir),
            "--stage-status", "awaiting_user_confirmation",
            "--awaiting-user-confirmation", "true",
            "--execution-authorized", "true",
            "--allowed-next", "check",
        )
        # Switch to check (non-execution stage)
        self.run_script(
            "set", str(task_dir),
            "--stage", "check",
            "--stage-status", "in_progress",
            "--awaiting-user-confirmation", "false",
            "--transition-from", "implementation",
            "--allowed-next", "review-gate,implementation",
        )
        import json as _json
        state = _json.loads((task_dir / "workflow-state.json").read_text(encoding="utf-8"))
        self.assertFalse(state["checkpoints"]["execution_authorized"],
                        "execution_authorized should auto-reset to false when leaving execution stage")

    def test_issue6_empty_allowed_next_stages_blocks_transition(self) -> None:
        """Issue 6: Empty allowed_next_stages list blocks any stage transition."""
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.run_script("init", str(task_dir), "--stage", "record-session")
        # Set allowed_next_stages to empty list (terminal state)
        state_path = task_dir / "workflow-state.json"
        import json as _json
        state = _json.loads(state_path.read_text(encoding="utf-8"))
        state["allowed_next_stages"] = []
        state["stage_status"] = "awaiting_user_confirmation"
        state["awaiting_user_confirmation"] = True
        state_path.write_text(_json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        # Attempt to switch to any stage should be blocked
        blocked = self.run_script("set", str(task_dir), "--stage", "delivery")
        self.assertEqual(blocked.returncode, 1, msg=blocked.stdout + blocked.stderr)
        self.assertIn("不在 allowed_next_stages", blocked.stdout)

    def test_issue7_brainstorm_allows_implementation_transition(self) -> None:
        """Issue 7: brainstorm can transition directly to implementation (L0 path)."""
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.run_script("init", str(task_dir), "--stage", "brainstorm")
        self.run_script(
            "set", str(task_dir),
            "--stage-status", "awaiting_user_confirmation",
            "--awaiting-user-confirmation", "true",
            "--allowed-next", "design,plan,implementation,test-first",
        )
        # L0 path: brainstorm → implementation
        ok_set = self.run_script(
            "set", str(task_dir),
            "--stage", "implementation",
            "--stage-status", "in_progress",
            "--awaiting-user-confirmation", "false",
            "--execution-authorized", "true",
            "--transition-from", "brainstorm",
            "--allowed-next", "test-first,check,project-audit",
        )
        self.assertEqual(ok_set.returncode, 0, msg=ok_set.stdout + ok_set.stderr)

    def test_issue7_brainstorm_allows_test_first_transition(self) -> None:
        """Issue 7: brainstorm can transition directly to test-first (L0 path)."""
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.run_script("init", str(task_dir), "--stage", "brainstorm")
        self.run_script(
            "set", str(task_dir),
            "--stage-status", "awaiting_user_confirmation",
            "--awaiting-user-confirmation", "true",
            "--allowed-next", "design,plan,implementation,test-first",
        )
        ok_set = self.run_script(
            "set", str(task_dir),
            "--stage", "test-first",
            "--stage-status", "in_progress",
            "--awaiting-user-confirmation", "false",
            "--execution-authorized", "true",
            "--transition-from", "brainstorm",
            "--allowed-next", "implementation,check,project-audit",
        )
        self.assertEqual(ok_set.returncode, 0, msg=ok_set.stdout + ok_set.stderr)


if __name__ == "__main__":
    unittest.main()
