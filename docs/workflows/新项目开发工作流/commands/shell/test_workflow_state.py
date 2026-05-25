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

    VALID_L0_DIRECT_EXECUTION_BASELINE = """## L0 直达 implementation 基线
- `automation_matrix_source`: `existing project verification matrix in .trellis/spec/ and active task records`
- `closeout_baseline_source`: `existing finish-work / delivery baseline already frozen for this project`
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

    VALID_SOURCE_WATERMARK_PLAN = """# Source Watermark Plan

## WMID
- `WMID`: `wm_demo_001`

## Watermark Channels
- visible

## Excluded Paths
- vendor/
- generated/
- migrations/

## Extraction
- 记录提取步骤和片段组合方式

## Verification
- 记录验证命令、校验 hash 和复核方式
"""

    VALID_WATERMARK_TASK_PLAN = """# Task Plan

## 当前推荐执行任务（待确认）

- 可见源码水印任务
- 水印验证任务
- 归属证明包任务

## 依赖关系

- 先完成 `source-watermark-plan.md`
"""

    STRONG_GATE_TASK_PY = (
        "# [workflow-embed-patch:strong-gate-no-status-flip]\n"
        "# Strong-gate mode keeps workflow-state.py route as the only stage authority.\n"
        "print('stage changes still go through workflow-state.py')\n"
        "print('workflow-state.py route is authoritative')\n"
        "# [workflow-embed-patch:strong-gate-task-status-view]\n"
        "print('Filter by workflow display status / stage (e.g. repair_needed, feasibility, design, completed)')\n"
    )
    STRONG_GATE_TASK_STORE = (
        "# [workflow-embed-patch:preserve-parent-active-task]\n"
        "TRELLIS_PRESERVE_ACTIVE_TASK = '1'\n"
        "print('Preserving current active task while creating child task')\n"
        "# [workflow-embed-patch:archive-closeout-gate]\n"
        "print('archive only after workflow close-out gate validation')\n"
        "print('finish-work-checklist.md')\n"
        "print('workflow-state.json')\n"
    )
    STRONG_GATE_TASKS = (
        "# [workflow-embed-patch:strong-gate-task-status-view]\n"
        "def _workflow_state_summary(state):\n"
        "    return state.get('status')\n"
        "def _display_status(task_dir, data):\n"
        "    return 'repair_needed', 'workflow-state.json missing'\n"
    )
    STRONG_GATE_TASK_QUEUE = (
        "# [workflow-embed-patch:strong-gate-task-status-view]\n"
        "def list_pending_tasks(repo_root=None):\n"
        "    return list_tasks_by_status(None, repo_root)\n"
    )
    STRONG_GATE_WORKFLOW_PHASE = (
        "# strong-gate-phase-patch-applied\n"
        "_STRONG_GATE_STAGES = {'feasibility', 'brainstorm'}\n"
    )

    VALID_TASK_CREATION_CHECKLIST = """# Task Creation Checklist

## 概述
- 已完成真实 task 创建前人工确认

## 拟创建的 Trellis Task
- .trellis/tasks/04-15-sample-task
- 性能回归与优化任务

## 依赖与项目域草案
- 当前任务域内串行，不自动续跑

## 人工确认清单
- 已确认当前推荐执行任务

## 人工确认结果
- `task_creation_confirmed`: `yes`
- `confirmed_scope`: `sample-task`
- `post_mainline_performance_task`: `yes`
- 性能回归与优化任务：保留
"""

    VALID_FULL_TASK_PLAN = """# Task Plan: Sample

## 概述
- 需求来源：示例
- 目标：验证脚本

## 项目域执行策略
- 后端域：.trellis/tasks/04-15-sample-task（域内串行，不自动续跑）

## Trellis Task 清单

| 任务路径 | 类型 | 项目域 | 说明 |
|---------|------|--------|------|
| .trellis/tasks/04-15-sample-task | implementation | 后端域 | 当前任务 |
| .trellis/tasks/04-15-performance-opt | implementation | 全局 | 性能回归与优化任务 |
| .trellis/tasks/04-15-performance-opt | implementation | 全局 | 性能回归与优化任务 |

## 当前推荐执行任务（待确认）
- 任务路径：.trellis/tasks/04-15-sample-task
- 任务标题：Sample Task
- 本轮目标：验证计划门禁
- 本轮不做：不进入其他任务
- 前置依赖：无
- 验收锚点：状态校验通过
- 风险提醒：边界变化先回 plan
- 推荐主执行 CLI：Codex

## 依赖关系

- 当前任务无前置依赖

## 任务粒度判断

- `granularity_decision`: keep_current_granularity
- `decision_reason`: 当前任务已是最小闭环
- `closure_target`: 完成单任务验证
- `non_split_risk`: acceptable
- `human_judgement_notes`: none

## 早期探针与骨架任务

- `walking_skeleton_or_smoke`: not_applicable
- `packaging_skeleton`: not_applicable
- `performance_probe`: not_applicable

## 自动化策略摘要

- `ci_strategy`: local-only
- `local_vs_ci_boundary`: local

## 范围收敛与降级预案

- `kill_criteria`: none
- `p1_downgrade_candidates`: none

## 门禁摘要

- 项目级全局门禁：lint / typecheck / test
- task 级门禁：before-dev.md

## 任务图摘要

- 主链：.trellis/tasks/04-15-sample-task

## 阶段出口快照

- `frozen_lanes`: backend
- `current_recommended_task`: .trellis/tasks/04-15-sample-task
- `open_blockers`: none
- `task_creation_confirmed`: yes
- `reopen_conditions`: none
"""

    VALID_OWNERSHIP_PLAN = """# Task Plan

## 概述
- 需求来源：示例
- 目标：完成归属证明计划校验

## 项目域执行策略
- 后端域：.trellis/tasks/04-15-sample-task（域内串行，不自动续跑）

## Trellis Task 清单

| 任务路径 | 类型 | 项目域 | 说明 |
|---------|------|--------|------|
| .trellis/tasks/04-15-sample-task | implementation | 后端域 | 当前任务 |
| .trellis/tasks/04-15-performance-opt | implementation | 全局 | 性能回归与优化任务 |

## 当前推荐执行任务（待确认）
- 任务路径：.trellis/tasks/04-15-sample-task
- 任务标题：Sample Task
- 本轮目标：验证归属证明计划
- 本轮不做：不进入其他任务
- 前置依赖：source-watermark-plan.md
- 验收锚点：相关校验通过
- 风险提醒：边界变化先回 plan
- 推荐主执行 CLI：Codex

## 依赖关系
- 当前任务依赖 `source-watermark-plan.md`
- `性能回归与优化任务` 依赖全部主干任务完成

## 任务粒度判断
- `granularity_decision`: keep_current_granularity
- `decision_reason`: 当前任务已是最小闭环
- `closure_target`: 完成单任务验证
- `non_split_risk`: acceptable
- `human_judgement_notes`: none

## 早期探针与骨架任务
- `walking_skeleton_or_smoke`: not_applicable
- `packaging_skeleton`: not_applicable
- `performance_probe`: not_applicable

## 自动化策略摘要
- `ci_strategy`: local-only
- `local_vs_ci_boundary`: local

## 范围收敛与降级预案
- `kill_criteria`: none
- `p1_downgrade_candidates`: none

## 门禁摘要
- 项目级全局门禁：lint / typecheck / test
- task 级门禁：before-dev.md

## 任务图摘要
- 主链：.trellis/tasks/04-15-sample-task → `性能回归与优化任务`

## 阶段出口快照
- `frozen_lanes`: backend
- `current_recommended_task`: .trellis/tasks/04-15-sample-task
- `open_blockers`: none
- `task_creation_confirmed`: yes
- `reopen_conditions`: none

## 外部项目交付控制（如适用）
- not_applicable

- 可见源码水印任务
- 零宽字符水印任务
- 隐蔽代码标识任务
- 水印验证任务
- 归属证明包任务
- source-watermark-plan.md
"""

    VALID_FINISH_WORK_CHECKLIST = """## 冻结验证矩阵

| Check | Command or Method | Result |
| --- | --- | --- |
| lint | npm run lint | pass |

## 人工验证

- 当前状态：已完成基础人工验证
- 证据缺口：none

## 同步结论

- spec/docs 同步：done
- hidden-dir sync：n/a
"""

    VALID_TASK_CREATION_CHECKLIST = """# Task Creation Checklist

## 概述
- 来源：示例
- 当前阶段目标：先冻结待创建任务，再进入真实 task 创建

## 拟创建的 Trellis Task
- Sample Task：当前任务
- `性能回归与优化任务`：主干任务完成后的固定后置任务（必选）

## 依赖与项目域草案
- 后端域：Sample Task

## 人工确认清单
- [x] 已确认拟创建的 Trellis task 列表
- [x] 已确认主干任务链与项目域 lane
- [x] 已确认当前推荐执行任务的边界与验收锚点

## 人工确认结果
- `task_creation_confirmed`: `yes`
- `confirmed_scope`: 当前任务
- `post_mainline_performance_task`: `yes`
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

    def write_minimal_installed_workflow_record(self, root: Path, *, profile: str) -> None:
        (root / ".trellis" / "workflow-installed.json").write_text(
            json.dumps({"profile": profile}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "library-lock.yaml").write_text(
            "packs:\n  - pack.requirements-discovery-foundation\n",
            encoding="utf-8",
        )
        (root / ".claude" / "hooks").mkdir(parents=True, exist_ok=True)
        (root / ".claude" / "hooks" / "session-start.py").write_text(
            "# strong-gate-session-start-patch-applied\n",
            encoding="utf-8",
        )
        (root / ".claude" / "hooks" / "inject-subagent-context.py").write_text(
            "# [workflow-embed-patch:claude-subagent-gates]\n"
            "def _emit_blocked_subagent_output(*args, **kwargs):\n"
            "    return None\n"
            "# Strong-gate blocked this subagent dispatch.\n"
            "# current embedded workflow disables agent/subagent execution paths\n"
            "_emit_blocked_subagent_output(subagent_type, original_prompt, tool_input)\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "scripts" / "task.py").write_text(self.STRONG_GATE_TASK_PY, encoding="utf-8")
        (root / ".trellis" / "scripts" / "common" / "task_store.py").write_text(self.STRONG_GATE_TASK_STORE, encoding="utf-8")
        (root / ".trellis" / "scripts" / "common" / "tasks.py").write_text(self.STRONG_GATE_TASKS, encoding="utf-8")
        (root / ".trellis" / "scripts" / "common" / "task_queue.py").write_text(self.STRONG_GATE_TASK_QUEUE, encoding="utf-8")
        (root / ".trellis" / "scripts" / "common" / "workflow_phase.py").write_text(self.STRONG_GATE_WORKFLOW_PHASE, encoding="utf-8")

    def write_context7_review(self, task_dir: Path, content: str | None = None) -> None:
        design_dir = task_dir / "design"
        design_dir.mkdir(parents=True, exist_ok=True)
        (design_dir / "context7-review.md").write_text(
            content or self.VALID_CONTEXT7_REVIEW,
            encoding="utf-8",
        )

    def write_finish_work_checklist(self, task_dir: Path, content: str | None = None) -> None:
        (task_dir / "finish-work-checklist.md").write_text(
            content or self.VALID_FINISH_WORK_CHECKLIST,
            encoding="utf-8",
        )

    def write_project_audit_report(self, task_dir: Path, content: str | None = None) -> None:
        (task_dir / "project-audit.md").write_text(
            content
            or """# Project Audit Report

## Mode
- formal

## Project-Level Verification Matrix
- `project-task-coverage`: all code-related tasks complete; no approved exceptions; no delivery blockers
- 项目级统一代码漏洞检测命令：not run + reason
- 项目级统一代码质量总检命令：not run + reason

## Confirmed Findings
- [self] no blocking issue

## Candidate Findings / Reviewer Evidence
- [self] none

## Confirmed Fix Plan
- no-op

## Applied Changes
- no-op
- `project_audit_code_changes`: `no`

## Project-Level Verification Results
- 项目级统一代码漏洞检测：not run + reason
- 项目级统一代码质量总检：not run + reason
- `task_level_check_status`: `not_needed`

## Remaining Risks
- none

## Suggested Next Step
- /trellis:check
""",
            encoding="utf-8",
        )

    def write_task_plan_with_code_tasks(
        self,
        root: Path,
        task_dir: Path,
        *,
        statuses: dict[str, str],
    ) -> None:
        tasks_root = root / ".trellis" / "tasks"
        rows: list[str] = [
            "# Task Plan",
            "",
            "## Trellis Task 清单",
            "",
            "| 任务路径 | 类型 | 项目域 | 说明 |",
            "|---------|------|--------|------|",
        ]
        for task_name, status in statuses.items():
            subdir = tasks_root / task_name
            subdir.mkdir(parents=True, exist_ok=True)
            (subdir / "task.json").write_text(
                json.dumps({"id": task_name, "name": task_name, "status": status}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            rows.append(
                f"| .trellis/tasks/{task_name} | implementation | 全局 | status={status} |"
            )
        rows.append(f"| .trellis/tasks/{task_dir.name} | project-audit | 全局 | current task |")
        (task_dir / "task_plan.md").write_text("\n".join(rows) + "\n", encoding="utf-8")

    def write_review_gate_round(self, task_dir: Path, *, round_no: int = 1, content: str | None = None) -> None:
        review_gate_dir = task_dir / "review-gate"
        review_gate_dir.mkdir(parents=True, exist_ok=True)
        (review_gate_dir / f"review-gate-round-{round_no}.md").write_text(
            content
            or """# Review Gate Round

## Decision
- skip

## Trigger Evidence
- current validation is sufficient

## Mode
- lite

## Recommended Next Step
- /trellis:finish-work
""",
            encoding="utf-8",
        )

    def write_check_report(self, task_dir: Path, content: str | None = None) -> None:
        (task_dir / "check.md").write_text(
            content
            or """# Check Report

## Changed Scope
- src/example.ts

## Applied Specs
- .trellis/spec/scripts/python-conventions.md

## Verification Results
- test: pass
- lint: not run

## Deviations
- none

## Uncovered Risks
- none

## Review-Gate Decision
- `review_gate_decision`: `skip`
- `review_gate_reason`: `未命中 review-gate 硬条件，现有验证证据足够`
- `auth_or_sensitive`: `no`
- `data_migration_or_schema_change`: `no`
- `public_api_or_cross_layer_contract_or_external_integration`: `no`
- `payment_queue_cache_concurrency`: `no`
- `shared_core_with_blast_radius`: `no`
- `explicit_user_review_gate_request`: `no`

## Suggested Next Step
- /trellis:delivery
""",
            encoding="utf-8",
        )

    def write_delivery_artifacts(
        self,
        task_dir: Path,
        *,
        include_outsourcing_proofs: bool = False,
        valid_contract: bool = False,
    ) -> None:
        delivery_dir = task_dir / "delivery"
        delivery_dir.mkdir(parents=True, exist_ok=True)
        if valid_contract:
            (delivery_dir / "acceptance.md").write_text(
                "# Acceptance\n\n"
                "## Acceptance Criteria Status\n"
                "- sample criterion: pass\n\n"
                "## Blocking Findings\n"
                "- none\n\n"
                "## Acceptance Gate\n"
                "- pass\n\n"
                "## 当前交付状态\n"
                "- pass\n",
                encoding="utf-8",
            )
            (delivery_dir / "deliverables.md").write_text(
                "# Deliverables\n\n"
                "## Closeout Assets\n"
                "- source bundle\n\n"
                "## Verification Evidence\n"
                "- lint: pass\n\n"
                "## Current Status\n"
                "- pass\n\n"
                "## Residual Risks\n"
                "- none\n",
                encoding="utf-8",
            )
            (delivery_dir / "transfer-checklist.md").write_text(
                "# Transfer Checklist\n\n"
                "## 当前事件允许移交什么\n"
                "- retained-control delivery\n"
                "- docs\n\n"
                "## 当前事件禁止标记为已移交什么\n"
                "- production keys\n\n"
                "## 触发条件 / 付款 / 权限 / 证明材料是否齐备\n"
                "- milestone_payment_schedule: pass\n"
                "- non_payment_remedy_path: pass\n"
                "- dispute_escalation_path: pass\n",
                encoding="utf-8",
            )
        else:
            (delivery_dir / "acceptance.md").write_text("# acceptance\n", encoding="utf-8")
            (delivery_dir / "deliverables.md").write_text("# deliverables\n", encoding="utf-8")
            (delivery_dir / "transfer-checklist.md").write_text("# transfer checklist\n", encoding="utf-8")
        if include_outsourcing_proofs:
            (delivery_dir / "ownership-proof.md").write_text("# ownership proof\n", encoding="utf-8")
            (delivery_dir / "source-watermark-verification.md").write_text(
                "# source watermark verification\n",
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

        self.assertEqual(validate.returncode, 0, msg=validate.stdout + validate.stderr)
        self.assertIn("workflow-state 校验通过", validate.stdout)

        strict_validate = self.run_script(
            "validate",
            str(task_dir),
            "--project-root",
            str(root),
            "--require-active-task-check",
        )
        self.assertEqual(strict_validate.returncode, 1, msg=strict_validate.stdout + strict_validate.stderr)
        self.assertIn("无法从 Trellis session runtime 解析当前活动任务", strict_validate.stdout)

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
        (task_dir / "prd.md").write_text(
            "# sample task\n\n"
            f"{self.VALID_BRAINSTORM_ESTIMATE}\n"
            f"{self.VALID_L0_DIRECT_EXECUTION_BASELINE}\n"
            "## 阶段出口快照\n"
            "- `complexity_decision`: `L0`\n"
            "- `ui_lane_decision`: `no-ui`\n"
            "- `cross_platform_scope`: `codex-only`\n"
            "- `estimate_refresh_result`: `unchanged`\n"
            "- `kill_criteria`: `none`\n"
            "- `open_items`: `none`\n",
            encoding="utf-8",
        )

        self.run_script("init", str(task_dir), "--stage", "brainstorm")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 0, msg=validate.stdout + validate.stderr)
        self.assertIn("workflow-state 校验通过", validate.stdout)

        strict_validate = self.run_script(
            "validate",
            str(task_dir),
            "--project-root",
            str(root),
            "--require-active-task-check",
        )
        self.assertEqual(strict_validate.returncode, 1, msg=strict_validate.stdout + strict_validate.stderr)
        self.assertIn("与当前 task", strict_validate.stdout)

    def test_validate_allows_parent_task_with_children_during_plan(self) -> None:
        root, task_dir = self.make_fixture()
        (task_dir / "task.json").write_text('{"status":"planning","children":["04-15-child-task"]}\n', encoding="utf-8")
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.write_context7_review(task_dir)
        performance_task_dir = root / ".trellis" / "tasks" / "04-15-performance-opt"
        performance_task_dir.mkdir(parents=True, exist_ok=True)
        (performance_task_dir / "task.json").write_text('{"status":"planning","children":[]}\n', encoding="utf-8")
        (task_dir / "task_plan.md").write_text(self.VALID_OWNERSHIP_PLAN, encoding="utf-8")
        (task_dir / "task_creation_checklist.md").write_text(self.VALID_TASK_CREATION_CHECKLIST, encoding="utf-8")
        (task_dir / "prd.md").write_text(
            "# Leaf Task\n\n"
            f"{self.VALID_BRAINSTORM_ESTIMATE}\n"
            "## Goal\n\n验证 leaf task ready 产物。\n\n## In Scope\n\n- 校验最小 task-ready 产物。\n\n## Out of Scope\n\n- 不进入实现。\n\n## Acceptance Anchors\n\n- 校验脚本通过。\n\n## Preferred CLI\n\n- Codex\n",
            encoding="utf-8",
        )

        self.run_script("init", str(task_dir), "--stage", "plan")
        self.run_script("set", str(task_dir), "--context7-review-completed", "true")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 0, msg=validate.stdout + validate.stderr)
        self.assertIn("workflow-state 校验通过", validate.stdout)

    def test_validate_allows_parent_task_with_children_during_project_audit(self) -> None:
        root, task_dir = self.make_fixture()
        (task_dir / "task.json").write_text('{"status":"planning","children":["04-15-child-task"]}\n', encoding="utf-8")
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.write_project_audit_report(task_dir)

        self.run_script("init", str(task_dir), "--stage", "project-audit")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 0, msg=validate.stdout + validate.stderr)
        self.assertIn("workflow-state 校验通过", validate.stdout)

    def test_validate_plan_requires_task_plan_artifacts(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.write_context7_review(task_dir)
        (task_dir / "task_plan.md").write_text(self.VALID_OWNERSHIP_PLAN, encoding="utf-8")

        self.run_script("init", str(task_dir), "--stage", "plan")
        self.run_script("set", str(task_dir), "--context7-review-completed", "true")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("task_creation_checklist.md", validate.stdout)

    def test_validate_still_rejects_execution_task_with_children(self) -> None:
        root, task_dir = self.make_fixture()
        (task_dir / "task.json").write_text('{"status":"planning","children":["04-15-child-task"]}\n', encoding="utf-8")
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        (root / "docs" / "requirements" / "developer-facing-prd.md").write_text("# developer\n", encoding="utf-8")
        self.write_context7_review(task_dir)

        self.run_script("init", str(task_dir), "--stage", "plan")
        self.run_script("set", str(task_dir), "--context7-review-completed", "true")
        state_path = task_dir / "workflow-state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["stage"] = "implementation"
        state["checkpoints"]["execution_authorized"] = True
        state["last_confirmed_transition"] = {
            "from": "plan",
            "to": "implementation",
            "confirmed_at": "2026-05-18T00:00:00+00:00",
        }
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("执行态叶子任务", validate.stdout)

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
        design_dir = task_dir / "design"
        design_dir.mkdir(parents=True, exist_ok=True)
        (design_dir / "source-watermark-plan.md").write_text(self.VALID_SOURCE_WATERMARK_PLAN, encoding="utf-8")

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

    def test_validate_rejects_unknown_design_current_block(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )

        self.run_script("init", str(task_dir), "--stage", "design")
        invalid_set = self.run_script("set", str(task_dir), "--current-block", "totally-custom-block")
        self.assertEqual(invalid_set.returncode, 1, msg=invalid_set.stdout + invalid_set.stderr)
        self.assertIn("current_block 非法", invalid_set.stdout)

    def test_validate_design_exit_requires_finish_work_patch_contract(self) -> None:
        root, task_dir = self.make_fixture()
        requirements_dir = root / "docs" / "requirements"
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=(
                f"{self.VALID_BRAINSTORM_ESTIMATE}\n"
                "## 自动化检查矩阵\n"
                "- 质量平台门禁：sonar-scanner\n"
                "- close-out 主入口：/trellis:finish-work\n"
                "- archive 前置条件：delivery 完成且当前 active task 已验收\n"
                "- 元数据边界：只允许当前 active task 的 archive + session record\n"
            ),
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        (requirements_dir / "developer-facing-prd.md").write_text("# developer\n- body\n", encoding="utf-8")
        self.write_context7_review(task_dir)
        design_dir = task_dir / "design"
        design_dir.mkdir(parents=True, exist_ok=True)
        (design_dir / "source-watermark-plan.md").write_text(self.VALID_SOURCE_WATERMARK_PLAN, encoding="utf-8")

        self.run_script("init", str(task_dir), "--stage", "design")
        self.run_script(
            "set",
            str(task_dir),
            "--architecture-confirmed",
            "true",
            "--context7-review-completed",
            "true",
            "--completed-blocks",
            "block-a,block-b,block-c,block-d",
            "--stage-status",
            "awaiting_user_confirmation",
            "--awaiting-user-confirmation",
            "true",
        )
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 0, msg=validate.stdout + validate.stderr)

    def test_validate_design_exit_matches_route_for_ownership_design_gate(self) -> None:
        root, task_dir = self.make_fixture()
        requirements_dir = root / "docs" / "requirements"
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        (requirements_dir / "developer-facing-prd.md").write_text("# developer\n- body\n", encoding="utf-8")
        self.write_context7_review(task_dir)

        self.run_script("init", str(task_dir), "--stage", "design")
        self.run_script(
            "set",
            str(task_dir),
            "--architecture-confirmed",
            "true",
            "--context7-review-completed",
            "true",
            "--completed-blocks",
            "block-a,block-b,block-c,block-d",
            "--stage-status",
            "awaiting_user_confirmation",
            "--awaiting-user-confirmation",
            "true",
        )

        route = self.run_script("route", str(task_dir), "--project-root", str(root))
        route_data = json.loads(route.stdout)
        self.assertEqual(route_data["action"], "awaiting_confirmation_with_blockers")
        self.assertIn("source-watermark-plan.md", "".join(route_data.get("blockers", [])))

        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))
        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("source-watermark-plan.md", validate.stdout)

    def test_set_rejects_plan_stage_execution_authorized_true(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.write_context7_review(task_dir)
        performance_task_dir = root / ".trellis" / "tasks" / "04-15-performance-opt"
        performance_task_dir.mkdir(parents=True, exist_ok=True)
        (performance_task_dir / "task.json").write_text('{"status":"planning","children":[]}\n', encoding="utf-8")
        (task_dir / "task_plan.md").write_text(self.VALID_OWNERSHIP_PLAN, encoding="utf-8")
        (task_dir / "task_creation_checklist.md").write_text(self.VALID_TASK_CREATION_CHECKLIST, encoding="utf-8")
        (task_dir / "prd.md").write_text(
            "# Leaf Task\n\n"
            f"{self.VALID_BRAINSTORM_ESTIMATE}\n"
            "## Goal\n\n验证 leaf task ready 产物。\n\n## In Scope\n\n- 校验最小 task-ready 产物。\n\n## Out of Scope\n\n- 不进入实现。\n\n## Acceptance Anchors\n\n- 校验脚本通过。\n\n## Preferred CLI\n\n- Codex\n",
            encoding="utf-8",
        )

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

    def test_validate_returns_cli_error_for_missing_task_dir(self) -> None:
        root, _task_dir = self.make_fixture()

        missing = root / ".trellis" / "tasks" / "does-not-exist"
        result = self.run_script("validate", str(missing), "--project-root", str(root))

        self.assertEqual(result.returncode, 1)
        combined = result.stdout + result.stderr
        self.assertIn("task dir not found", combined)
        self.assertNotIn("Traceback", combined)

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

    def test_validate_check_requires_exit_artifacts(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )

        self.run_script("init", str(task_dir), "--stage", "check")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("check.md", validate.stdout)

    def test_validate_project_audit_requires_report(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )

        self.run_script("init", str(task_dir), "--stage", "project-audit")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("project-audit.md", validate.stdout)

    def test_validate_project_audit_rejects_pre_audit_mode_for_stage_exit(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.write_project_audit_report(
            task_dir,
            content="""# Project Audit Report

## Mode
- pre-audit

## Project-Level Verification Matrix
- project-task-coverage: unknown
- unified-security-check: not run
- unified-quality-check: not run

## Confirmed Findings
- none

## Candidate Findings / Reviewer Evidence
- [self] none

## Confirmed Fix Plan
- none

## Applied Changes
- none

## Project-Level Verification Results
- unified-security-check: not run
- unified-quality-check: not run

## Remaining Risks
- none

## Suggested Next Step
- /trellis:check
""",
        )
        self.run_script("init", str(task_dir), "--stage", "project-audit")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))
        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("pre-audit", validate.stdout)

    def test_validate_project_audit_requires_coverage_and_formal_evidence(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.write_project_audit_report(
            task_dir,
            content="""# Project Audit Report

## Mode
- formal

## Project-Level Verification Matrix
- 项目级统一代码漏洞检测命令：not run + reason
- 项目级统一代码质量总检命令：not run + reason

## Confirmed Findings
- [self] none

## Candidate Findings / Reviewer Evidence
- [self] none

## Confirmed Fix Plan
- none

## Applied Changes
- none

## Project-Level Verification Results
- 项目级统一代码漏洞检测：not run + reason
- 项目级统一代码质量总检：not run + reason

## Remaining Risks
- none

## Suggested Next Step
- /trellis:check
""",
        )
        self.run_script("init", str(task_dir), "--stage", "project-audit")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))
        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("project-task-coverage", validate.stdout)

    def test_validate_project_audit_formal_requires_all_code_tasks_completed(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.write_task_plan_with_code_tasks(
            root,
            task_dir,
            statuses={
                "04-15-code-a": "completed",
                "04-15-code-b": "in_progress",
            },
        )
        self.write_project_audit_report(task_dir)
        self.run_script("init", str(task_dir), "--stage", "project-audit")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))
        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("代码相关", validate.stdout)
        self.assertIn("04-15-code-b", validate.stdout)

    def test_validate_review_gate_requires_round_report(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )

        self.run_script("init", str(task_dir), "--stage", "review-gate")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertRegex(validate.stdout, r"review-gate(?:/|-)?.*目录|review-gate-round-")

    def test_validate_review_gate_rejects_invalid_decision_and_missing_evidence(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.write_review_gate_round(
            task_dir,
            content="""# Review Gate Round

## Decision
- maybe

## Trigger Evidence
- current validation is sufficient

## Mode
- lite

## Recommended Next Step
- /trellis:finish-work
""",
        )
        self.run_script("init", str(task_dir), "--stage", "review-gate")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))
        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("Decision", validate.stdout)

    def test_validate_review_gate_requires_full_mode_aggregation_evidence(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.write_review_gate_round(
            task_dir,
            content="""# Review Gate Round

## Decision
- required

## Trigger Evidence
- auth risk

## Mode
- full

## Recommended Next Step
- /trellis:delivery
""",
        )
        self.run_script("init", str(task_dir), "--stage", "review-gate")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))
        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("reviewer-commands-round", validate.stdout)

    def test_validate_review_gate_required_decision_rejects_lite_mode(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.write_review_gate_round(
            task_dir,
            content="""# Review Gate Round

## Decision
- required

## Trigger Evidence
- auth risk

## Mode
- lite

## Recommended Next Step
- /trellis:delivery
""",
        )
        review_gate_dir = task_dir / "review-gate"
        (review_gate_dir / "reviewer-commands-round-1.md").write_text("# commands\n", encoding="utf-8")
        self.run_script("init", str(task_dir), "--stage", "review-gate")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))
        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("required", validate.stdout)
        self.assertIn("full", validate.stdout)

    def test_validate_delivery_requires_delivery_artifacts(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )

        self.run_script("init", str(task_dir), "--stage", "delivery")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertTrue(
            "缺少交付产物" in validate.stdout
            or "delivery-control-validate.py" in validate.stdout
            or "ownership-proof-validate.py" in validate.stdout
        )

    def test_validate_delivery_requires_finish_work_checklist(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
            assessment_content=self.VALID_EXTERNAL_ASSESSMENT,
        )
        self.write_delivery_artifacts(task_dir, valid_contract=True)
        self.run_script("init", str(task_dir), "--stage", "delivery")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))
        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("finish-work-checklist.md", validate.stdout)

    def test_validate_delivery_rejects_placeholder_delivery_docs_even_when_files_exist(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
            assessment_content=self.VALID_EXTERNAL_ASSESSMENT,
        )
        self.write_delivery_artifacts(task_dir)
        self.write_finish_work_checklist(task_dir)
        self.run_script("init", str(task_dir), "--stage", "delivery")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))
        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertTrue("acceptance.md" in validate.stdout or "deliverables.md" in validate.stdout)

    def test_validate_delivery_accepts_complete_contract_with_finish_work_checklist(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
            assessment_content=self.VALID_EXTERNAL_ASSESSMENT,
        )
        self.write_delivery_artifacts(task_dir, valid_contract=True, include_outsourcing_proofs=True)
        self.write_finish_work_checklist(task_dir)
        self.run_script("init", str(task_dir), "--stage", "delivery")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))
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
        self.assertIn("启动款未确认到账前，不得进入 implementation", validate.stdout)

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
        performance_task_dir = root / ".trellis" / "tasks" / "04-15-performance-opt"
        performance_task_dir.mkdir(parents=True, exist_ok=True)
        (performance_task_dir / "task.json").write_text('{"status":"planning","children":[]}\n', encoding="utf-8")
        (task_dir / "task_plan.md").write_text(self.VALID_OWNERSHIP_PLAN, encoding="utf-8")
        (task_dir / "task_creation_checklist.md").write_text(self.VALID_TASK_CREATION_CHECKLIST, encoding="utf-8")
        design_dir = task_dir / "design"
        design_dir.mkdir(parents=True, exist_ok=True)
        (design_dir / "source-watermark-plan.md").write_text(self.VALID_SOURCE_WATERMARK_PLAN, encoding="utf-8")
        (task_dir / "prd.md").write_text(
            "# Leaf Task\n\n"
            f"{self.VALID_BRAINSTORM_ESTIMATE}\n"
            "## Goal\n\n验证计划到执行阶段门禁。\n\n## In Scope\n\n- 校验合法转场。\n\n## Out of Scope\n\n- 不进入实际实现。\n\n## Acceptance Anchors\n\n- transition gate 通过。\n\n## Preferred CLI\n\n- Codex\n",
            encoding="utf-8",
        )

        # Attempt 1: without awaiting_user_confirmation -> rejected at transition gate
        illegal_set = self.run_script("set", str(task_dir), "--stage", "implementation")
        self.assertEqual(illegal_set.returncode, 1, msg=illegal_set.stdout + illegal_set.stderr)
        self.assertIn("status 必须为 awaiting_user_confirmation", illegal_set.stdout)

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

    def test_set_rejects_execution_stage_on_parent_task_with_children(self) -> None:
        root, task_dir = self.make_fixture()
        (task_dir / "task.json").write_text('{"status":"planning","children":["04-15-child-task"]}\n', encoding="utf-8")
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.run_script("init", str(task_dir), "--stage", "brainstorm")
        self.run_script(
            "set",
            str(task_dir),
            "--stage-status", "awaiting_user_confirmation",
            "--awaiting-user-confirmation", "true",
        )

        illegal_set = self.run_script(
            "set",
            str(task_dir),
            "--stage", "implementation",
            "--execution-authorized", "true",
            "--transition-from", "brainstorm",
        )

        self.assertEqual(illegal_set.returncode, 1, msg=illegal_set.stdout + illegal_set.stderr)
        self.assertIn("children", illegal_set.stdout)

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
                '"last_confirmed_transition": {"from": "plan", "to": "implementation", "confirmed_at": "2026-04-16T00:00:00+00:00"}',
            ),
            encoding="utf-8",
        )

        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 0, msg=validate.stdout + validate.stderr)

    def test_validate_passes_when_implementation_has_confirmation_record_from_brainstorm(self) -> None:
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
            "brainstorm",
        )
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 0, msg=validate.stdout + validate.stderr)

    def test_validate_fails_when_implementation_tries_to_bypass_project_estimate_gate(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(root, task_dir)

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

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("项目级粗估", validate.stdout)

    def test_validate_passes_when_brainstorm_has_no_customer_prd_yet(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        (root / "docs" / "requirements" / "customer-facing-prd.md").unlink()
        (task_dir / "prd.md").write_text(
            "# sample brainstorm draft\n\n"
            f"{self.VALID_BRAINSTORM_ESTIMATE}\n"
            "## 阶段出口快照\n"
            "- `complexity_decision`: `L0`\n"
            "- `ui_lane_decision`: `no-ui`\n"
            "- `cross_platform_scope`: `codex-only`\n"
            "- `estimate_refresh_result`: `initial`\n"
            "- `kill_criteria`: `none`\n"
            "- `open_items`: `none`\n",
            encoding="utf-8",
        )

        self.run_script("init", str(task_dir), "--stage", "brainstorm")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 0, msg=validate.stdout + validate.stderr)

    def test_validate_brainstorm_exit_requires_customer_prd_for_design_path(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix="",
        )
        (task_dir / "prd.md").write_text(
            "# sample brainstorm draft\n\n"
            f"{self.VALID_BRAINSTORM_ESTIMATE}\n"
            "## 阶段出口快照\n"
            "- `complexity_decision`: `M1`\n"
            "- `ui_lane_decision`: `mixed`\n"
            "- `cross_platform_scope`: `claude-opencode-codex`\n"
            "- `estimate_refresh_result`: `initial`\n"
            "- `kill_criteria`: `none`\n"
            "- `open_items`: `none`\n",
            encoding="utf-8",
        )

        self.run_script("init", str(task_dir), "--stage", "brainstorm")
        self.run_script(
            "set",
            str(task_dir),
            "--stage-status",
            "awaiting_user_confirmation",
            "--awaiting-user-confirmation",
            "true",
            "--allowed-next",
            "design,plan",
        )

        route = self.run_script("route", str(task_dir), "--project-root", str(root))
        route_data = json.loads(route.stdout)
        self.assertEqual(route_data["action"], "awaiting_confirmation_with_blockers")
        self.assertIn("customer-facing-prd.md", "".join(route_data.get("blockers", [])))

        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))
        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("customer-facing-prd.md", validate.stdout)

    def test_validate_brainstorm_exit_rejects_placeholder_snapshot_values(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        (task_dir / "prd.md").write_text(
            "# sample brainstorm draft\n\n"
            f"{self.VALID_BRAINSTORM_ESTIMATE}\n"
            "## 阶段出口快照\n"
            "- `complexity_decision`: `M1`\n"
            "- `ui_lane_decision`: `待补充`\n"
            "- `cross_platform_scope`: `claude-opencode-codex`\n"
            "- `estimate_refresh_result`: `initial`\n"
            "- `kill_criteria`: `none`\n"
            "- `open_items`: `TODO`\n",
            encoding="utf-8",
        )

        self.run_script("init", str(task_dir), "--stage", "brainstorm")
        self.run_script(
            "set",
            str(task_dir),
            "--stage-status",
            "awaiting_user_confirmation",
            "--awaiting-user-confirmation",
            "true",
            "--allowed-next",
            "design,plan",
        )

        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))
        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("阶段出口快照字段未填写有效结论", validate.stdout)

        blocked_set = self.run_script(
            "set",
            str(task_dir),
            "--stage",
            "design",
            "--stage-status",
            "in_progress",
            "--awaiting-user-confirmation",
            "false",
            "--transition-from",
            "brainstorm",
            "--allowed-next",
            "plan",
        )
        self.assertEqual(blocked_set.returncode, 1, msg=blocked_set.stdout + blocked_set.stderr)
        self.assertIn("阶段出口快照字段未填写有效结论", blocked_set.stdout)

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

    def test_cmd_route_no_task_requires_entry_choice(self) -> None:
        """No active task and no tasks anywhere -> entry_choice_required."""
        root = Path(tempfile.mkdtemp(prefix="workflow-state-test-"))
        self.addCleanup(shutil.rmtree, root)
        (root / ".trellis" / "tasks").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / ".runtime" / "sessions").mkdir(parents=True, exist_ok=True)

        result = self.run_script("route", "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        import json as _json
        data = _json.loads(result.stdout)
        self.assertEqual(data["target"], "feasibility")
        self.assertEqual(data["action"], "entry_choice_required")
        self.assertIn("只读分析", data["reason"])

    def test_cmd_route_no_task_personal_profile_without_assessment_targets_feasibility(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="workflow-state-test-"))
        self.addCleanup(shutil.rmtree, root)
        (root / ".trellis" / "tasks").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / ".runtime" / "sessions").mkdir(parents=True, exist_ok=True)
        self.write_minimal_installed_workflow_record(root, profile="personal")

        result = self.run_script("route", "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["target"], "feasibility")
        self.assertEqual(data["action"], "entry_choice_required")
        self.assertEqual(data["profile_hint"], "personal")
        self.assertIn("首次进入 feasibility", data["reason"])

    def test_cmd_route_no_task_outsourcing_profile_without_assessment_still_targets_feasibility(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="workflow-state-test-"))
        self.addCleanup(shutil.rmtree, root)
        (root / ".trellis" / "tasks").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "scripts" / "common").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / ".runtime" / "sessions").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "workflow-installed.json").write_text(
            json.dumps({"profile": "outsourcing"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "library-lock.yaml").write_text(
            "packs:\n  - pack.requirements-discovery-foundation\n",
            encoding="utf-8",
        )
        (root / ".claude" / "hooks").mkdir(parents=True, exist_ok=True)
        (root / ".claude" / "hooks" / "inject-subagent-context.py").write_text(
            "# [workflow-embed-patch:claude-subagent-gates]\n"
            "def _emit_blocked_subagent_output(*args, **kwargs):\n"
            "    return None\n"
            "# Strong-gate blocked this subagent dispatch.\n"
            "# current embedded workflow disables agent/subagent execution paths\n"
            "_emit_blocked_subagent_output(subagent_type, original_prompt, tool_input)\n",
            encoding="utf-8",
        )
        (root / ".claude" / "hooks" / "session-start.py").write_text(
            "# strong-gate-session-start-patch-applied\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "task.py").write_text(
            self.STRONG_GATE_TASK_PY,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_store.py").write_text(
            self.STRONG_GATE_TASK_STORE,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "tasks.py").write_text(
            self.STRONG_GATE_TASKS,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_queue.py").write_text(
            self.STRONG_GATE_TASK_QUEUE,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "workflow_phase.py").write_text(
            self.STRONG_GATE_WORKFLOW_PHASE,
            encoding="utf-8",
        )

        result = self.run_script("route", "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["target"], "feasibility")
        self.assertEqual(data["action"], "entry_choice_required")
        self.assertEqual(data["profile_hint"], "outsourcing")

    def test_cmd_route_no_task_unknown_profile_prefers_feasibility_with_unknown_hint(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="workflow-state-test-"))
        self.addCleanup(shutil.rmtree, root)
        (root / ".trellis" / "tasks").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / ".runtime" / "sessions").mkdir(parents=True, exist_ok=True)
        self.write_minimal_installed_workflow_record(root, profile="legacy-unknown")

        result = self.run_script("route", "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["target"], "feasibility")
        self.assertEqual(data["action"], "profile_confirmation_required")
        self.assertEqual(data["profile_hint"], "unknown")
        self.assertIn("请直接询问用户当前项目应按 outsourcing 还是 personal 处理", data["reason"])

    def test_cmd_route_no_task_personal_profile_still_entry_choice_required(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="workflow-state-test-"))
        self.addCleanup(shutil.rmtree, root)
        (root / ".trellis" / "tasks").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / ".runtime" / "sessions").mkdir(parents=True, exist_ok=True)
        self.write_minimal_installed_workflow_record(root, profile="personal")

        result = self.run_script("route", "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["target"], "feasibility")
        self.assertEqual(data["action"], "entry_choice_required")
        self.assertEqual(data["profile_hint"], "personal")

    def test_cmd_route_no_task_reuses_existing_assessment_for_brainstorm(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="workflow-state-test-"))
        self.addCleanup(shutil.rmtree, root)
        (root / ".trellis" / "tasks").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / ".runtime" / "sessions").mkdir(parents=True, exist_ok=True)
        (root / "assessment.md").write_text(self.VALID_INTERNAL_ASSESSMENT, encoding="utf-8")

        result = self.run_script("route", "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["target"], "brainstorm")
        self.assertEqual(data["action"], "entry_choice_required")
        self.assertEqual(data["profile_hint"], "personal")

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
        self.assertEqual(data["status"], "in_progress")

    def test_cmd_route_delivery_reenter_checks_delivery_artifacts(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.run_script("init", str(task_dir), "--stage", "delivery")

        result = self.run_script("route", str(task_dir), "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "reenter")

    def test_cmd_route_review_gate_reenter_blocks_when_check_gate_missing(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.run_script("init", str(task_dir), "--stage", "review-gate")

        result = self.run_script("route", str(task_dir), "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "blocked")
        self.assertIn("check.md", "".join(data.get("blockers", [])))

    def test_cmd_route_reenters_from_session_runtime_without_task_arg(self) -> None:
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

        result = self.run_script("route", "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        import json as _json
        data = _json.loads(result.stdout)
        self.assertEqual(data["target"], "plan")
        self.assertEqual(data["action"], "reenter")
        self.assertEqual(data["stage"], "plan")

    def test_cmd_route_reenters_parent_plan_task_with_children(self) -> None:
        root, task_dir = self.make_fixture()
        (task_dir / "task.json").write_text('{"status":"planning","children":["04-15-child-task"]}\n', encoding="utf-8")
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.write_context7_review(task_dir)
        self.run_script("init", str(task_dir), "--stage", "plan")
        self.run_script("set", str(task_dir), "--context7-review-completed", "true")

        result = self.run_script("route", str(task_dir), "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertNotEqual(data["action"], "repair_needed")
        self.assertNotIn("children", data["reason"])

    def test_cmd_route_reenters_parent_project_audit_task_with_children(self) -> None:
        root, task_dir = self.make_fixture()
        (task_dir / "task.json").write_text('{"status":"planning","children":["04-15-child-task"]}\n', encoding="utf-8")
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.write_project_audit_report(task_dir)
        self.run_script("init", str(task_dir), "--stage", "project-audit")

        result = self.run_script("route", str(task_dir), "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "reenter")
        self.assertNotIn("children", data["reason"])

    def test_cmd_route_returns_context_needed_for_execution_parent_with_children(self) -> None:
        root, task_dir = self.make_fixture()
        (task_dir / "task.json").write_text('{"status":"planning","children":["04-15-child-task"]}\n', encoding="utf-8")
        (task_dir / "workflow-state.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "stage": "implementation",
                    "status": "in_progress",
                    "current_block": None,
                    "completed_blocks": [],
                    "awaiting_user_confirmation": False,
                    "last_confirmed_transition": {
                        "from": "plan",
                        "to": "implementation",
                        "confirmed_at": "2026-05-22T00:00:00+00:00",
                    },
                    "notes": [],
                    "checkpoints": {
                        "architecture_confirmed": True,
                        "context7_review_completed": True,
                        "execution_authorized": True,
                    },
                    "updated_at": "2026-05-22T00:00:00+00:00",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        result = self.run_script("route", str(task_dir), "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "context_needed")
        self.assertEqual(data["stage"], "implementation")
        self.assertIn("04-15-child-task", data["reason"])
        self.assertIn("task.py start <child-task-dir>", data["reason"])

    def test_cmd_route_awaiting_confirmation(self) -> None:
        """workflow-state has status=awaiting_user_confirmation -> awaiting_confirmation."""
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        design_dir = task_dir / "design"
        design_dir.mkdir(parents=True, exist_ok=True)
        (design_dir / "source-watermark-plan.md").write_text(self.VALID_SOURCE_WATERMARK_PLAN, encoding="utf-8")
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
        self.assertEqual(data["status"], "awaiting_user_confirmation")

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
        self.assertIn("workflow-state.py repair <task-dir>", data["reason"])
        self.assertIn("尚未初始化", data["reason"])
        self.assertNotIn("init <task-dir> --stage feasibility", data["reason"])

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
        state["status"] = "totally-invalid-status"
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        result = self.run_script("route", str(task_dir), "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "repair_needed")
        self.assertIn("status 非法", "".join(data.get("blockers", [])))

    def test_cmd_route_blocks_brainstorm_without_assessment_even_when_customer_prd_missing(self) -> None:
        root, task_dir = self.make_fixture()
        (task_dir / "task.json").write_text('{"status":"planning","children":[]}\n', encoding="utf-8")
        (task_dir / "prd.md").write_text("# sample\n", encoding="utf-8")
        self.run_script("init", str(task_dir), "--stage", "brainstorm")

        result = self.run_script("route", str(task_dir), "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        import json as _json
        data = _json.loads(result.stdout)
        self.assertEqual(data["action"], "blocked")
        self.assertIn("assessment", data["reason"])

    def test_validate_rejects_brainstorm_without_assessment_even_for_personal_profile(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_minimal_installed_workflow_record(root, profile="personal")
        (task_dir / "prd.md").write_text(
            "# sample\n\n"
            f"{self.VALID_BRAINSTORM_ESTIMATE}",
            encoding="utf-8",
        )
        self.run_script("init", str(task_dir), "--stage", "brainstorm")

        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("任何项目都必须先经过 feasibility", validate.stdout)

    def test_route_brainstorm_without_assessment_is_blocked_even_for_personal_profile(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_minimal_installed_workflow_record(root, profile="personal")
        (task_dir / "prd.md").write_text(
            "# sample\n\n"
            f"{self.VALID_BRAINSTORM_ESTIMATE}",
            encoding="utf-8",
        )
        self.run_script("init", str(task_dir), "--stage", "brainstorm")

        result = self.run_script("route", str(task_dir), "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "blocked")
        self.assertIn("必须先完成 feasibility", "".join(data.get("blockers", [])))

    def test_route_personal_brainstorm_bootstrap_exemption_ends_after_assessment_file_exists(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_minimal_installed_workflow_record(root, profile="personal")
        (task_dir / "prd.md").write_text("# sample\n", encoding="utf-8")
        self.run_script("init", str(task_dir), "--stage", "brainstorm")
        (task_dir / "assessment.md").write_text(
            "# assessment\n"
            "- `project_engagement_type`: `non_outsourcing`\n"
            "- 法律/合规风险结论：通过\n",
            encoding="utf-8",
        )

        result = self.run_script("route", str(task_dir), "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "blocked")
        self.assertIn("是否允许进入 brainstorm", data["reason"])

    def test_set_personal_brainstorm_to_design_requires_assessment_after_bootstrap_phase(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_minimal_installed_workflow_record(root, profile="personal")
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=(
                f"{self.VALID_BRAINSTORM_ESTIMATE}\n"
                "## 阶段出口快照\n"
                "- `complexity_decision`: `L0`\n"
                "- `ui_lane_decision`: `no-ui`\n"
                "- `cross_platform_scope`: `codex-only`\n"
                "- `estimate_refresh_result`: `unchanged`\n"
                "- `kill_criteria`: `none`\n"
                "- `open_items`: `none`\n"
            ),
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        (task_dir / "assessment.md").unlink()
        self.run_script("init", str(task_dir), "--stage", "brainstorm")
        self.run_script(
            "set",
            str(task_dir),
            "--stage-status",
            "awaiting_user_confirmation",
            "--awaiting-user-confirmation",
            "true",
        )

        transition = self.run_script(
            "set",
            str(task_dir),
            "--stage",
            "design",
            "--stage-status",
            "in_progress",
            "--awaiting-user-confirmation",
            "false",
            "--transition-from",
            "brainstorm",
        )

        self.assertEqual(transition.returncode, 1, msg=transition.stdout + transition.stderr)
        self.assertIn("任何项目都必须先经过 feasibility", transition.stdout)

    def test_validate_personal_brainstorm_with_partial_assessment_reports_specific_missing_fields(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_minimal_installed_workflow_record(root, profile="personal")
        (task_dir / "prd.md").write_text(
            "# sample\n\n"
            f"{self.VALID_BRAINSTORM_ESTIMATE}",
            encoding="utf-8",
        )
        self.run_script("init", str(task_dir), "--stage", "brainstorm")
        (task_dir / "assessment.md").write_text(
            "# assessment\n"
            "- `project_engagement_type`: `non_outsourcing`\n"
            "- 法律/合规风险结论：通过\n",
            encoding="utf-8",
        )

        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("source_watermark_level", validate.stdout)
        self.assertIn("ownership_proof_required", validate.stdout)
        self.assertNotIn("缺少 assessment.md", validate.stdout)

    def test_route_personal_brainstorm_awaiting_confirmation_without_assessment_reports_bootstrap_gap(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_minimal_installed_workflow_record(root, profile="personal")
        (task_dir / "prd.md").write_text(
            "# sample\n\n"
            f"{self.VALID_BRAINSTORM_ESTIMATE}",
            encoding="utf-8",
        )
        self.run_script("init", str(task_dir), "--stage", "brainstorm")
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
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "awaiting_confirmation_with_blockers")
        self.assertIn("必须先完成 feasibility", "".join(data.get("blockers", [])))

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

    def test_route_brainstorm_awaiting_requires_project_estimate(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix="",
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.run_script("init", str(task_dir), "--stage", "brainstorm")
        self.run_script(
            "set",
            str(task_dir),
            "--stage-status", "awaiting_user_confirmation",
            "--awaiting-user-confirmation", "true",
            "--allowed-next", "implementation",
        )

        result = self.run_script("route", str(task_dir), "--project-root", str(root))
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "awaiting_confirmation_with_blockers")
        self.assertIn("项目级粗估", "".join(data.get("blockers", [])))

    def test_route_brainstorm_awaiting_requires_customer_prd_for_design_path(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix="",
        )
        self.run_script("init", str(task_dir), "--stage", "brainstorm")
        self.run_script(
            "set",
            str(task_dir),
            "--stage-status", "awaiting_user_confirmation",
            "--awaiting-user-confirmation", "true",
            "--allowed-next", "design,plan",
        )

        result = self.run_script("route", str(task_dir), "--project-root", str(root))
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "awaiting_confirmation_with_blockers")
        self.assertIn("customer-facing-prd.md", "".join(data.get("blockers", [])))

    def test_route_brainstorm_l0_execution_path_does_not_require_customer_prd(self) -> None:
        root, task_dir = self.make_fixture()
        (task_dir / "prd.md").write_text(
            "# sample task\n\n"
            f"{self.VALID_BRAINSTORM_ESTIMATE}\n"
            f"{self.VALID_L0_DIRECT_EXECUTION_BASELINE}\n"
            "## 阶段出口快照\n"
            "- `complexity_decision`: `L0`\n"
            "- `ui_lane_decision`: `no-ui`\n"
            "- `cross_platform_scope`: `codex-only`\n"
            "- `estimate_refresh_result`: `initial`\n"
            "- `kill_criteria`: `none`\n"
            "- `open_items`: `none`\n",
            encoding="utf-8",
        )
        (task_dir / "assessment.md").write_text(self.VALID_INTERNAL_ASSESSMENT, encoding="utf-8")
        self.run_script("init", str(task_dir), "--stage", "brainstorm")
        self.run_script(
            "set",
            str(task_dir),
            "--stage-status", "awaiting_user_confirmation",
            "--awaiting-user-confirmation", "true",
            "--allowed-next", "implementation",
        )

        result = self.run_script("route", str(task_dir), "--project-root", str(root))
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "awaiting_confirmation")

    def test_route_brainstorm_execution_path_no_longer_forces_l0_blocker(self) -> None:
        root, task_dir = self.make_fixture()
        (task_dir / "prd.md").write_text(
            "# sample task\n\n"
            f"{self.VALID_BRAINSTORM_ESTIMATE}\n"
            "## 阶段出口快照\n"
            "- `complexity_decision`: `L1`\n"
            "- `ui_lane_decision`: `no-ui`\n"
            "- `cross_platform_scope`: `codex-only`\n"
            "- `estimate_refresh_result`: `initial`\n"
            "- `kill_criteria`: `none`\n"
            "- `open_items`: `none`\n",
            encoding="utf-8",
        )
        (task_dir / "assessment.md").write_text(self.VALID_INTERNAL_ASSESSMENT, encoding="utf-8")
        self.run_script("init", str(task_dir), "--stage", "brainstorm")
        self.run_script(
            "set",
            str(task_dir),
            "--stage-status", "awaiting_user_confirmation",
            "--awaiting-user-confirmation", "true",
            "--allowed-next", "implementation",
        )

        result = self.run_script("route", str(task_dir), "--project-root", str(root))
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "awaiting_confirmation_with_blockers")
        self.assertIn("complexity_decision", "".join(data.get("blockers", [])))

    def test_cmd_set_allows_brainstorm_to_execution_when_inputs_are_complete(self) -> None:
        root, task_dir = self.make_fixture()
        (task_dir / "prd.md").write_text(
            "# sample task\n\n"
            f"{self.VALID_BRAINSTORM_ESTIMATE}\n"
            f"{self.VALID_L0_DIRECT_EXECUTION_BASELINE}\n"
            "## 阶段出口快照\n"
            "- `complexity_decision`: `L0`\n"
            "- `ui_lane_decision`: `no-ui`\n"
            "- `cross_platform_scope`: `codex-only`\n"
            "- `estimate_refresh_result`: `initial`\n"
            "- `kill_criteria`: `none`\n"
            "- `open_items`: `none`\n",
            encoding="utf-8",
        )
        (task_dir / "assessment.md").write_text(self.VALID_INTERNAL_ASSESSMENT, encoding="utf-8")
        self.run_script("init", str(task_dir), "--stage", "brainstorm")
        self.run_script(
            "set",
            str(task_dir),
            "--stage-status", "awaiting_user_confirmation",
            "--awaiting-user-confirmation", "true",
            "--allowed-next", "implementation",
        )

        result = self.run_script(
            "set",
            str(task_dir),
            "--stage", "implementation",
            "--execution-authorized", "true",
            "--transition-from", "brainstorm",
            cwd=root,
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_route_execution_stage_blocks_when_project_estimate_markers_missing(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix="",
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

        result = self.run_script("route", str(task_dir), "--project-root", str(root))
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "blocked")
        self.assertIn("项目级粗估", "".join(data.get("blockers", [])))

    def test_cmd_route_warns_when_patched_codex_start_skill_drifts(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="workflow-state-test-"))
        self.addCleanup(shutil.rmtree, root)
        (root / ".trellis" / "tasks").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "scripts" / "common").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "workflow-installed.json").write_text(
            json.dumps(
                {
                    "profile": "outsourcing",
                    "cli_types": ["codex"],
                    "critical_runtime_patches": [
                        "inject-workflow-state",
                        "session-start-strong-gate",
                        "task-start-strong-gate",
                        "task-create-preserve-active",
                        "task-status-view-strong-gate",
                        "workflow-phase-strong-gate",
                    ],
                    "patched_codex_skills": [
                        "trellis-continue",
                        "trellis-finish-work",
                        "trellis-start",
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "library-lock.yaml").write_text(
            "packs:\n  - pack.requirements-discovery-foundation\n",
            encoding="utf-8",
        )
        (root / ".codex" / "hooks").mkdir(parents=True, exist_ok=True)
        (root / ".codex" / "hooks" / "inject-workflow-state.py").write_text(
            "# [workflow-embed-patch:prefer-workflow-state-json]\n",
            encoding="utf-8",
        )
        (root / ".codex" / "hooks" / "session-start.py").write_text(
            "# strong-gate-session-start-patch-applied\n# [workflow-embed-patch:session-start-route-first]\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "task.py").write_text(
            self.STRONG_GATE_TASK_PY,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_store.py").write_text(
            self.STRONG_GATE_TASK_STORE,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "tasks.py").write_text(
            self.STRONG_GATE_TASKS,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_queue.py").write_text(
            self.STRONG_GATE_TASK_QUEUE,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "workflow_phase.py").write_text(
            self.STRONG_GATE_WORKFLOW_PHASE,
            encoding="utf-8",
        )
        skills_root = root / ".agents" / "skills"
        (skills_root / "trellis-continue").mkdir(parents=True, exist_ok=True)
        (skills_root / "trellis-continue" / "SKILL.md").write_text(
            "## Workflow Phase Router Patch `[AI]`\n",
            encoding="utf-8",
        )
        (skills_root / "trellis-finish-work").mkdir(parents=True, exist_ok=True)
        (skills_root / "trellis-finish-work" / "SKILL.md").write_text(
            "<!-- finish-work-projectization-patch -->\n",
            encoding="utf-8",
        )
        (skills_root / "trellis-start").mkdir(parents=True, exist_ok=True)
        (skills_root / "trellis-start" / "SKILL.md").write_text(
            "## Step 4: Decide next action\npython3 ./.trellis/scripts/get_context.py --mode phase --step 2.1 --platform codex\n",
            encoding="utf-8",
        )

        result = self.run_script("route", "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "entry_choice_required")
        self.assertIn("warnings", data)
        self.assertIn("trellis-start", "".join(data["warnings"]))

    def test_cmd_route_warns_when_patched_codex_continue_skill_drifts(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="workflow-state-test-"))
        self.addCleanup(shutil.rmtree, root)
        (root / ".trellis" / "tasks").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "scripts" / "common").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "workflow-installed.json").write_text(
            json.dumps(
                {
                    "profile": "outsourcing",
                    "cli_types": ["codex"],
                    "critical_runtime_patches": [
                        "inject-workflow-state",
                        "session-start-strong-gate",
                        "task-start-strong-gate",
                        "task-create-preserve-active",
                        "task-status-view-strong-gate",
                        "workflow-phase-strong-gate",
                    ],
                    "patched_codex_skills": [
                        "trellis-continue",
                        "trellis-finish-work",
                        "trellis-start",
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "library-lock.yaml").write_text(
            "packs:\n  - pack.requirements-discovery-foundation\n",
            encoding="utf-8",
        )
        (root / ".codex" / "hooks").mkdir(parents=True, exist_ok=True)
        (root / ".codex" / "hooks" / "inject-workflow-state.py").write_text(
            "# [workflow-embed-patch:prefer-workflow-state-json]\n",
            encoding="utf-8",
        )
        (root / ".codex" / "hooks" / "session-start.py").write_text(
            "# strong-gate-session-start-patch-applied\n# [workflow-embed-patch:session-start-route-first]\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "task.py").write_text(
            self.STRONG_GATE_TASK_PY,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_store.py").write_text(
            self.STRONG_GATE_TASK_STORE,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "tasks.py").write_text(
            self.STRONG_GATE_TASKS,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_queue.py").write_text(
            self.STRONG_GATE_TASK_QUEUE,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "workflow_phase.py").write_text(
            self.STRONG_GATE_WORKFLOW_PHASE,
            encoding="utf-8",
        )
        skills_root = root / ".agents" / "skills"
        (skills_root / "trellis-continue").mkdir(parents=True, exist_ok=True)
        (skills_root / "trellis-continue" / "SKILL.md").write_text(
            "---\n"
            "name: trellis-continue\n"
            'description: "Resume work on the current task. Loads the workflow Phase Index, figures out which phase/step to pick up at, then pulls the step-level detail via get_context.py --mode phase. Use when coming back to an in-progress task and you need to know what to do next."\n'
            "---\n\n"
            "## Workflow Phase Router Patch `[AI]`\n",
            encoding="utf-8",
        )
        (skills_root / "trellis-finish-work").mkdir(parents=True, exist_ok=True)
        (skills_root / "trellis-finish-work" / "SKILL.md").write_text(
            "<!-- finish-work-projectization-patch -->\narchive the active task\nrecord the session journal\n",
            encoding="utf-8",
        )
        (skills_root / "trellis-start").mkdir(parents=True, exist_ok=True)
        (skills_root / "trellis-start" / "SKILL.md").write_text(
            "Route initial user intent through the installed workflow router\n## Workflow Phase Router Patch `[AI]`\n",
            encoding="utf-8",
        )

        result = self.run_script("route", "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "entry_choice_required")
        self.assertIn("warnings", data)
        self.assertIn("trellis-continue", "".join(data["warnings"]))

    def test_cmd_route_warns_when_patched_codex_continue_skill_retains_hidden_status_routing(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="workflow-state-test-"))
        self.addCleanup(shutil.rmtree, root)
        (root / ".trellis" / "tasks").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "scripts" / "common").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "workflow-installed.json").write_text(
            json.dumps(
                {
                    "profile": "outsourcing",
                    "cli_types": ["codex"],
                    "critical_runtime_patches": [
                        "inject-workflow-state",
                        "session-start-strong-gate",
                        "task-start-strong-gate",
                        "task-create-preserve-active",
                        "task-status-view-strong-gate",
                        "workflow-phase-strong-gate",
                    ],
                    "patched_codex_skills": [
                        "trellis-continue",
                        "trellis-finish-work",
                        "trellis-start",
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "library-lock.yaml").write_text(
            "packs:\n  - pack.requirements-discovery-foundation\n",
            encoding="utf-8",
        )
        (root / ".codex" / "hooks").mkdir(parents=True, exist_ok=True)
        (root / ".codex" / "hooks" / "inject-workflow-state.py").write_text(
            "# [workflow-embed-patch:prefer-workflow-state-json]\n",
            encoding="utf-8",
        )
        (root / ".codex" / "hooks" / "session-start.py").write_text(
            "# strong-gate-session-start-patch-applied\n# [workflow-embed-patch:session-start-route-first]\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "task.py").write_text(
            self.STRONG_GATE_TASK_PY,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_store.py").write_text(
            self.STRONG_GATE_TASK_STORE,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "tasks.py").write_text(
            self.STRONG_GATE_TASKS,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_queue.py").write_text(
            self.STRONG_GATE_TASK_QUEUE,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "workflow_phase.py").write_text(
            self.STRONG_GATE_WORKFLOW_PHASE,
            encoding="utf-8",
        )
        skills_root = root / ".agents" / "skills"
        (skills_root / "trellis-continue").mkdir(parents=True, exist_ok=True)
        (skills_root / "trellis-continue" / "SKILL.md").write_text(
            "---\n"
            "name: trellis-continue\n"
            'description: "Re-enter the current workflow stage through the workflow router and follow the next action it returns."\n'
            "---\n\n"
            "## Workflow Phase Router Patch `[AI]`\n"
            "workflow router\n"
            "workflow-state.py route\n"
            "Do not use `status=planning` / `status=in_progress`\n"
            "stay in the current phase-router entry\n"
            "Do not assume a public `implementation` skill exists.\n"
            "Hidden stale branch: if task state shows planning, load brainstorm; if task state shows in progress and implementation done, not yet checked, skip ahead.\n",
            encoding="utf-8",
        )
        (skills_root / "trellis-finish-work").mkdir(parents=True, exist_ok=True)
        (skills_root / "trellis-finish-work" / "SKILL.md").write_text(
            "<!-- finish-work-projectization-patch -->\n"
            "complete native Trellis close-out after delivery\n"
            "archive + session-record steps after delivery\n"
            "Code commits are NOT done here\n",
            encoding="utf-8",
        )
        (skills_root / "trellis-start").mkdir(parents=True, exist_ok=True)
        (skills_root / "trellis-start" / "SKILL.md").write_text(
            "## Workflow Phase Router Patch `[AI]`\n"
            "workflow router\n"
            "workflow-state.py route\n"
            "Do not use `status=planning` / `status=in_progress`\n"
            "stay in the current phase-router entry\n"
            "Do not assume a public `implementation` skill exists.\n",
            encoding="utf-8",
        )

        result = self.run_script("route", "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "entry_choice_required")
        self.assertIn("warnings", data)
        self.assertIn("trellis-continue", "".join(data["warnings"]))

    def test_cmd_route_warns_when_patched_codex_finish_work_skill_drifts(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="workflow-state-test-"))
        self.addCleanup(shutil.rmtree, root)
        (root / ".trellis" / "tasks").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "scripts" / "common").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "workflow-installed.json").write_text(
            json.dumps(
                {
                    "profile": "outsourcing",
                    "cli_types": ["codex"],
                    "critical_runtime_patches": [
                        "inject-workflow-state",
                        "session-start-strong-gate",
                        "task-start-strong-gate",
                        "task-create-preserve-active",
                        "task-status-view-strong-gate",
                        "workflow-phase-strong-gate",
                    ],
                    "patched_codex_skills": [
                        "trellis-continue",
                        "trellis-finish-work",
                        "trellis-start",
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "library-lock.yaml").write_text(
            "packs:\n  - pack.requirements-discovery-foundation\n",
            encoding="utf-8",
        )
        (root / ".codex" / "hooks").mkdir(parents=True, exist_ok=True)
        (root / ".codex" / "hooks" / "inject-workflow-state.py").write_text(
            "# [workflow-embed-patch:prefer-workflow-state-json]\n",
            encoding="utf-8",
        )
        (root / ".codex" / "hooks" / "session-start.py").write_text(
            "# strong-gate-session-start-patch-applied\n# [workflow-embed-patch:session-start-route-first]\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "task.py").write_text(
            self.STRONG_GATE_TASK_PY,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_store.py").write_text(
            self.STRONG_GATE_TASK_STORE,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "tasks.py").write_text(
            self.STRONG_GATE_TASKS,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_queue.py").write_text(
            self.STRONG_GATE_TASK_QUEUE,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "workflow_phase.py").write_text(
            self.STRONG_GATE_WORKFLOW_PHASE,
            encoding="utf-8",
        )
        skills_root = root / ".agents" / "skills"
        (skills_root / "trellis-continue").mkdir(parents=True, exist_ok=True)
        (skills_root / "trellis-continue" / "SKILL.md").write_text(
            "Re-enter the current workflow stage through the workflow router\n## Workflow Phase Router Patch `[AI]`\n",
            encoding="utf-8",
        )
        (skills_root / "trellis-finish-work").mkdir(parents=True, exist_ok=True)
        (skills_root / "trellis-finish-work" / "SKILL.md").write_text(
            "---\n"
            "name: trellis-finish-work\n"
            'description: "Wrap up the current session: verify quality gate passed, remind user to commit, archive completed tasks, and record session progress to the developer journal. Use when done coding and ready to end the session."\n'
            "---\n\n"
            "<!-- finish-work-projectization-patch -->\n",
            encoding="utf-8",
        )
        (skills_root / "trellis-start").mkdir(parents=True, exist_ok=True)
        (skills_root / "trellis-start" / "SKILL.md").write_text(
            "Route initial user intent through the installed workflow router\n## Workflow Phase Router Patch `[AI]`\n",
            encoding="utf-8",
        )

        result = self.run_script("route", "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "entry_choice_required")
        self.assertIn("warnings", data)
        self.assertIn("trellis-finish-work", "".join(data["warnings"]))

    def test_cmd_route_warns_when_patched_codex_brainstorm_helper_skill_drifts(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="workflow-state-test-"))
        self.addCleanup(shutil.rmtree, root)
        (root / ".trellis" / "tasks").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "scripts" / "common").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "workflow-installed.json").write_text(
            json.dumps(
                {
                    "profile": "outsourcing",
                    "cli_types": ["codex"],
                    "critical_runtime_patches": [
                        "inject-workflow-state",
                        "session-start-strong-gate",
                        "task-start-strong-gate",
                        "task-create-preserve-active",
                        "task-status-view-strong-gate",
                        "workflow-phase-strong-gate",
                    ],
                    "patched_codex_skills": [
                        "trellis-continue",
                        "trellis-finish-work",
                        "trellis-start",
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "library-lock.yaml").write_text(
            "packs:\n  - pack.requirements-discovery-foundation\n",
            encoding="utf-8",
        )
        (root / ".codex" / "hooks").mkdir(parents=True, exist_ok=True)
        (root / ".codex" / "hooks" / "inject-workflow-state.py").write_text(
            "# [workflow-embed-patch:prefer-workflow-state-json]\n",
            encoding="utf-8",
        )
        (root / ".codex" / "hooks" / "session-start.py").write_text(
            "# strong-gate-session-start-patch-applied\n# [workflow-embed-patch:session-start-route-first]\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "task.py").write_text(
            self.STRONG_GATE_TASK_PY,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_store.py").write_text(
            self.STRONG_GATE_TASK_STORE,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "tasks.py").write_text(
            self.STRONG_GATE_TASKS,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_queue.py").write_text(
            self.STRONG_GATE_TASK_QUEUE,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "workflow_phase.py").write_text(
            self.STRONG_GATE_WORKFLOW_PHASE,
            encoding="utf-8",
        )
        skills_root = root / ".agents" / "skills"
        (skills_root / "trellis-continue").mkdir(parents=True, exist_ok=True)
        (skills_root / "trellis-continue" / "SKILL.md").write_text(
            "Re-enter the current workflow stage through the workflow router\n## Workflow Phase Router Patch `[AI]`\n",
            encoding="utf-8",
        )
        (skills_root / "trellis-finish-work").mkdir(parents=True, exist_ok=True)
        (skills_root / "trellis-finish-work" / "SKILL.md").write_text(
            "<!-- finish-work-projectization-patch -->\narchive the active task\nrecord the session journal\n",
            encoding="utf-8",
        )
        (skills_root / "trellis-start").mkdir(parents=True, exist_ok=True)
        (skills_root / "trellis-start" / "SKILL.md").write_text(
            "Route initial user intent through the installed workflow router\n## Workflow Phase Router Patch `[AI]`\n",
            encoding="utf-8",
        )
        (skills_root / "trellis-brainstorm").mkdir(parents=True, exist_ok=True)
        (skills_root / "trellis-brainstorm" / "SKILL.md").write_text(
            "Triggered from `start` (Trellis command)\n| ``start` (Trellis command)` | Entry point that triggers brainstorm |\n",
            encoding="utf-8",
        )

        result = self.run_script("route", "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "entry_choice_required")
        self.assertIn("warnings", data)
        self.assertIn("trellis-brainstorm", "".join(data["warnings"]))

    def test_cmd_route_blocks_design_reentry_when_ownership_policy_is_invalid(self) -> None:
        root, task_dir = self.make_fixture()
        invalid_assessment = self.VALID_INTERNAL_ASSESSMENT.replace(
            "- `source_watermark_channels`: `visible`\n",
            "",
        )
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
            assessment_content=invalid_assessment,
        )
        self.run_script("init", str(task_dir), "--stage", "design")

        result = self.run_script("route", str(task_dir), "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "blocked")
        self.assertIn("source_watermark_channels", "".join(data.get("blockers", [])))

    def test_cmd_route_blocks_plan_reentry_when_project_doc_boundary_is_invalid(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.run_script("init", str(task_dir), "--stage", "plan")

        result = self.run_script("route", str(task_dir), "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "blocked")
        self.assertIn("context7-review.md", "".join(data.get("blockers", [])))

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

    def test_cmd_route_force_ignore_embed_check_demotes_nonfatal_drift_to_warning(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="workflow-state-test-"))
        self.addCleanup(shutil.rmtree, root)
        (root / ".trellis" / "tasks").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "scripts" / "common").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "workflow-installed.json").write_text(
            json.dumps(
                {
                    "profile": "outsourcing",
                    "cli_types": ["claude", "opencode", "codex"],
                    "commands": ["brainstorm"],
                    "critical_runtime_patches": [
                        "inject-workflow-state",
                        "claude-inject-subagent-context",
                        "opencode-inject-subagent-context",
                        "session-start-strong-gate",
                        "task-start-strong-gate",
                        "task-create-preserve-active",
                        "task-status-view-strong-gate",
                        "workflow-phase-strong-gate",
                    ],
                    "patched_codex_skills": ["trellis-continue", "trellis-finish-work", "trellis-start"],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "library-lock.yaml").write_text(
            "packs:\n  - pack.requirements-discovery-foundation\n",
            encoding="utf-8",
        )
        (root / ".claude" / "hooks").mkdir(parents=True, exist_ok=True)
        (root / ".claude" / "hooks" / "session-start.py").write_text(
            "# strong-gate-session-start-patch-applied\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "task.py").write_text(
            self.STRONG_GATE_TASK_PY,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_store.py").write_text(
            self.STRONG_GATE_TASK_STORE,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "tasks.py").write_text(
            self.STRONG_GATE_TASKS,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_queue.py").write_text(
            self.STRONG_GATE_TASK_QUEUE,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "workflow_phase.py").write_text(
            self.STRONG_GATE_WORKFLOW_PHASE,
            encoding="utf-8",
        )
        (root / ".claude" / "commands" / "trellis").mkdir(parents=True, exist_ok=True)
        (root / ".opencode" / "commands" / "trellis").mkdir(parents=True, exist_ok=True)
        (root / ".agents" / "skills" / "brainstorm").mkdir(parents=True, exist_ok=True)
        (root / ".claude" / "commands" / "trellis" / "brainstorm.md").write_text("# brainstorm\n", encoding="utf-8")
        (root / ".opencode" / "commands" / "trellis" / "brainstorm.md").write_text("# brainstorm\n", encoding="utf-8")
        (root / ".agents" / "skills" / "brainstorm" / "SKILL.md").write_text("# brainstorm\n", encoding="utf-8")

        script = Path(__file__).resolve().parent / "embed_integrity.py"
        result = subprocess.run(
            [PYTHON, str(script), str(root), "--force-ignore-embed-check"],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("⚠️", result.stdout)

    def test_embed_integrity_force_ignore_allows_advisory_drift_script_output(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="workflow-state-test-"))
        self.addCleanup(shutil.rmtree, root)
        (root / ".trellis" / "tasks").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "workflow-installed.json").write_text(
            json.dumps(
                {
                    "profile": "outsourcing",
                    "cli_types": ["claude", "opencode", "codex"],
                    "commands": ["brainstorm"],
                    "critical_runtime_patches": [
                        "inject-workflow-state",
                        "claude-inject-subagent-context",
                        "opencode-inject-subagent-context",
                        "session-start-strong-gate",
                        "task-start-strong-gate",
                        "task-create-preserve-active",
                        "task-status-view-strong-gate",
                        "workflow-phase-strong-gate",
                    ],
                    "patched_codex_skills": ["trellis-continue", "trellis-finish-work", "trellis-start"],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "library-lock.yaml").write_text(
            "packs:\n  - pack.requirements-discovery-foundation\n",
            encoding="utf-8",
        )
        (root / ".claude" / "commands" / "trellis").mkdir(parents=True, exist_ok=True)
        (root / ".opencode" / "commands" / "trellis").mkdir(parents=True, exist_ok=True)
        (root / ".agents" / "skills" / "brainstorm").mkdir(parents=True, exist_ok=True)
        (root / ".claude" / "commands" / "trellis" / "brainstorm.md").write_text("# brainstorm\n", encoding="utf-8")
        (root / ".opencode" / "commands" / "trellis" / "brainstorm.md").write_text("# brainstorm\n", encoding="utf-8")
        (root / ".agents" / "skills" / "brainstorm" / "SKILL.md").write_text("# brainstorm\n", encoding="utf-8")

        script = Path(__file__).resolve().parent / "embed_integrity.py"
        result = subprocess.run(
            [PYTHON, str(script), str(root), "--force-ignore-embed-check"],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("⚠️", result.stdout)

    def test_cmd_route_embed_invalid_when_critical_runtime_patches_are_missing(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="workflow-state-test-"))
        self.addCleanup(shutil.rmtree, root)
        (root / ".trellis" / "tasks").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "scripts" / "common").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / ".runtime" / "sessions").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "workflow-installed.json").write_text(
            json.dumps(
                {
                    "profile": "outsourcing",
                    "cli_types": ["claude", "codex"],
                    "critical_runtime_patches": [
                        "inject-workflow-state",
                        "session-start-strong-gate",
                        "task-start-strong-gate",
                        "task-create-preserve-active",
                        "task-status-view-strong-gate",
                        "workflow-phase-strong-gate",
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "library-lock.yaml").write_text(
            "packs:\n  - pack.requirements-discovery-foundation\n",
            encoding="utf-8",
        )
        (root / ".claude" / "hooks").mkdir(parents=True, exist_ok=True)
        (root / ".claude" / "hooks" / "session-start.py").write_text("# baseline hook\n", encoding="utf-8")
        (root / ".codex" / "hooks").mkdir(parents=True, exist_ok=True)
        (root / ".codex" / "hooks" / "inject-workflow-state.py").write_text(
            "# [workflow-embed-patch:prefer-workflow-state-json]\n",
            encoding="utf-8",
        )
        (root / ".codex" / "hooks" / "session-start.py").write_text("# baseline hook\n", encoding="utf-8")
        (root / ".trellis" / "scripts" / "task.py").write_text("# baseline task helper\n", encoding="utf-8")
        (root / ".trellis" / "scripts" / "common" / "task_store.py").write_text(
            "# baseline task store\n",
            encoding="utf-8",
        )

        result = self.run_script("route", "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "embed_invalid")
        self.assertIn("critical runtime patch", data["reason"])

    def test_cmd_route_embed_invalid_when_runtime_python_patch_has_syntax_error(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="workflow-state-test-"))
        self.addCleanup(shutil.rmtree, root)
        (root / ".trellis" / "tasks").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "scripts" / "common").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "workflow-installed.json").write_text(
            json.dumps(
                {
                    "profile": "outsourcing",
                    "cli_types": ["claude"],
                    "critical_runtime_patches": [
                        "inject-workflow-state",
                        "session-start-strong-gate",
                        "task-start-strong-gate",
                        "task-create-preserve-active",
                        "task-status-view-strong-gate",
                        "workflow-phase-strong-gate",
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "library-lock.yaml").write_text(
            "packs:\n  - pack.requirements-discovery-foundation\n",
            encoding="utf-8",
        )
        (root / ".claude" / "hooks").mkdir(parents=True, exist_ok=True)
        (root / ".claude" / "hooks" / "inject-workflow-state.py").write_text(
            "# [workflow-embed-patch:prefer-workflow-state-json]\n",
            encoding="utf-8",
        )
        (root / ".claude" / "hooks" / "inject-subagent-context.py").write_text(
            "# [workflow-embed-patch:claude-subagent-gates]\n"
            "def _emit_blocked_subagent_output(*args, **kwargs):\n"
            "    return None\n"
            "# Strong-gate blocked this subagent dispatch.\n"
            "# current embedded workflow disables agent/subagent execution paths\n"
            "_emit_blocked_subagent_output(subagent_type, original_prompt, tool_input)\n",
            encoding="utf-8",
        )
        (root / ".claude" / "hooks" / "session-start.py").write_text(
            "# strong-gate-session-start-patch-applied\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "task.py").write_text(
            self.STRONG_GATE_TASK_PY,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "tasks.py").write_text(
            self.STRONG_GATE_TASKS,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_queue.py").write_text(
            self.STRONG_GATE_TASK_QUEUE,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "workflow_phase.py").write_text(
            self.STRONG_GATE_WORKFLOW_PHASE,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_store.py").write_text(
            "# [workflow-embed-patch:preserve-parent-active-task]\n"
            "def broken(:\n"
            "    pass\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "tasks.py").write_text(
            self.STRONG_GATE_TASKS,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_queue.py").write_text(
            self.STRONG_GATE_TASK_QUEUE,
            encoding="utf-8",
        )

        result = self.run_script("route", "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "embed_invalid")
        self.assertIn("task_store.py", data["reason"])
        self.assertIn("SyntaxError", data["reason"])

    def test_cmd_route_embed_invalid_when_runtime_python_patch_marker_exists_but_semantics_drift(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="workflow-state-test-"))
        self.addCleanup(shutil.rmtree, root)
        (root / ".trellis" / "tasks").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "scripts" / "common").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "workflow-installed.json").write_text(
            json.dumps(
                {
                    "profile": "outsourcing",
                    "cli_types": ["claude"],
                    "critical_runtime_patches": [
                        "inject-workflow-state",
                        "session-start-strong-gate",
                        "task-start-strong-gate",
                        "task-create-preserve-active",
                        "task-status-view-strong-gate",
                        "workflow-phase-strong-gate",
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "library-lock.yaml").write_text(
            "packs:\n  - pack.requirements-discovery-foundation\n",
            encoding="utf-8",
        )
        (root / ".claude" / "hooks").mkdir(parents=True, exist_ok=True)
        (root / ".claude" / "hooks" / "inject-workflow-state.py").write_text(
            "# [workflow-embed-patch:prefer-workflow-state-json]\n",
            encoding="utf-8",
        )
        (root / ".claude" / "hooks" / "inject-subagent-context.py").write_text(
            "# [workflow-embed-patch:claude-subagent-gates]\n"
            "def _emit_blocked_subagent_output(*args, **kwargs):\n"
            "    return None\n"
            "# Strong-gate blocked this subagent dispatch.\n"
            "# current embedded workflow disables agent/subagent execution paths\n"
            "_emit_blocked_subagent_output(subagent_type, original_prompt, tool_input)\n",
            encoding="utf-8",
        )
        (root / ".claude" / "hooks" / "session-start.py").write_text(
            "# strong-gate-session-start-patch-applied\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "task.py").write_text(
            "# [workflow-embed-patch:strong-gate-no-status-flip]\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_store.py").write_text(
            self.STRONG_GATE_TASK_STORE,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "tasks.py").write_text(
            self.STRONG_GATE_TASKS,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_queue.py").write_text(
            self.STRONG_GATE_TASK_QUEUE,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "workflow_phase.py").write_text(
            self.STRONG_GATE_WORKFLOW_PHASE,
            encoding="utf-8",
        )

        result = self.run_script("route", "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "embed_invalid")
        self.assertIn("task.py", data["reason"])

    def test_embed_integrity_accepts_real_split_runtime_semantics(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="workflow-state-test-"))
        self.addCleanup(shutil.rmtree, root)
        (root / ".trellis" / "tasks").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "scripts" / "common").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "workflow-installed.json").write_text(
            json.dumps(
                {
                    "profile": "outsourcing",
                    "cli_types": ["claude"],
                    "critical_runtime_patches": [
                        "inject-workflow-state",
                        "session-start-strong-gate",
                        "claude-inject-subagent-context",
                        "task-start-strong-gate",
                        "task-create-preserve-active",
                        "task-status-view-strong-gate",
                        "workflow-phase-strong-gate",
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "library-lock.yaml").write_text(
            "packs:\n  - pack.requirements-discovery-foundation\n",
            encoding="utf-8",
        )
        (root / ".claude" / "hooks").mkdir(parents=True, exist_ok=True)
        (root / ".claude" / "hooks" / "inject-workflow-state.py").write_text(
            "# [workflow-embed-patch:prefer-workflow-state-json]\n",
            encoding="utf-8",
        )
        (root / ".claude" / "hooks" / "inject-subagent-context.py").write_text(
            "# [workflow-embed-patch:claude-subagent-gates]\n"
            "def _emit_blocked_subagent_output(*args, **kwargs):\n"
            "    return None\n"
            "# Strong-gate blocked this subagent dispatch.\n"
            "# current embedded workflow disables agent/subagent execution paths\n"
            "_emit_blocked_subagent_output(subagent_type, original_prompt, tool_input)\n",
            encoding="utf-8",
        )
        (root / ".claude" / "hooks" / "session-start.py").write_text(
            "# strong-gate-session-start-patch-applied\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "task.py").write_text(
            self.STRONG_GATE_TASK_PY,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_store.py").write_text(
            self.STRONG_GATE_TASK_STORE,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "tasks.py").write_text(
            self.STRONG_GATE_TASKS,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_queue.py").write_text(
            "# [workflow-embed-patch:strong-gate-task-status-view]\n"
            "def list_pending_tasks(repo_root=None):\n"
            "    return list_tasks_by_status(None, repo_root)\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "workflow_phase.py").write_text(
            "# strong-gate-phase-patch-applied\n"
            "_STRONG_GATE_STAGES = {'feasibility', 'brainstorm', 'design'}\n",
            encoding="utf-8",
        )

        result = self.run_script("route", "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "entry_choice_required")
        self.assertEqual(data["target"], "feasibility")

    def test_cmd_route_embed_invalid_when_opencode_runtime_patch_is_missing(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="workflow-state-test-"))
        self.addCleanup(shutil.rmtree, root)
        (root / ".trellis" / "tasks").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "scripts" / "common").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "workflow-installed.json").write_text(
            json.dumps(
                {
                    "profile": "outsourcing",
                    "cli_types": ["opencode"],
                    "critical_runtime_patches": [
                        "inject-workflow-state",
                        "claude-inject-subagent-context",
                        "opencode-inject-subagent-context",
                        "session-start-strong-gate",
                        "task-start-strong-gate",
                        "task-create-preserve-active",
                        "task-status-view-strong-gate",
                        "workflow-phase-strong-gate",
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "library-lock.yaml").write_text(
            "packs:\n  - pack.requirements-discovery-foundation\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "task.py").write_text(
            self.STRONG_GATE_TASK_PY,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_store.py").write_text(
            self.STRONG_GATE_TASK_STORE,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "tasks.py").write_text(
            self.STRONG_GATE_TASKS,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_queue.py").write_text(
            self.STRONG_GATE_TASK_QUEUE,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "workflow_phase.py").write_text(
            self.STRONG_GATE_WORKFLOW_PHASE,
            encoding="utf-8",
        )

        result = self.run_script("route", "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "embed_invalid")
        self.assertIn(".opencode", data["reason"])

    def test_cmd_route_embed_invalid_when_opencode_runtime_patch_is_incomplete(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="workflow-state-test-"))
        self.addCleanup(shutil.rmtree, root)
        (root / ".trellis" / "tasks").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "scripts" / "common").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "workflow-installed.json").write_text(
            json.dumps(
                {
                    "profile": "outsourcing",
                    "cli_types": ["opencode"],
                    "critical_runtime_patches": [
                        "inject-workflow-state",
                        "opencode-inject-subagent-context",
                        "session-start-strong-gate",
                        "task-start-strong-gate",
                        "task-create-preserve-active",
                        "task-status-view-strong-gate",
                        "workflow-phase-strong-gate",
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "library-lock.yaml").write_text(
            "packs:\n  - pack.requirements-discovery-foundation\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "task.py").write_text(
            self.STRONG_GATE_TASK_PY,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_store.py").write_text(
            self.STRONG_GATE_TASK_STORE,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "tasks.py").write_text(
            self.STRONG_GATE_TASKS,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_queue.py").write_text(
            self.STRONG_GATE_TASK_QUEUE,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "workflow_phase.py").write_text(
            self.STRONG_GATE_WORKFLOW_PHASE,
            encoding="utf-8",
        )
        (root / ".opencode" / "plugins").mkdir(parents=True, exist_ok=True)
        (root / ".opencode" / "plugins" / "inject-workflow-state.js").write_text(
            "// [workflow-embed-patch:prefer-workflow-state-json]\n"
            "function getActiveTask() { return { status: 'workflow-state.route_failed', source: 'workflow-state.route_failed', extraLines: [] } }\n"
            "function buildBreadcrumb(id, status, templates, source = null, extraLines = []) { return status }\n",
            encoding="utf-8",
        )
        (root / ".opencode" / "lib").mkdir(parents=True, exist_ok=True)
        (root / ".opencode" / "lib" / "session-utils.js").write_text(
            "// [workflow-embed-patch:strong-gate-session-utils]\n",
            encoding="utf-8",
        )
        (root / ".opencode" / "plugins" / "inject-subagent-context.js").write_text(
            "// [workflow-embed-patch:opencode-subagent-gates]\n"
            "function buildBlockedSubagentPrompt(routeData, subagentType, originalPrompt) { return originalPrompt }\n"
            "function shouldAllowTaskInjection(routeData, subagentType) { return subagentType !== \"forbidden\" }\n"
            "function loadRouteData(ctx, taskDir) { return { stage: \"implementation\", action: \"reenter\", target: \"implementation\" } }\n"
            "const allowedStages = new Set([\"implementation\", \"check\", \"review-gate\", \"project-audit\", \"delivery\"])\n"
            "loadRouteData(ctx, ctx.resolveTaskDir(taskDir))\n"
            "Strong-gate blocked this subagent dispatch.\n"
            "strong-gate route does not allow subagent injection\n",
            encoding="utf-8",
        )

        result = self.run_script("route", "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "embed_invalid")
        self.assertIn("execFileSync", data["reason"])

    def test_cmd_route_embed_invalid_when_opencode_subagent_patch_is_missing(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="workflow-state-test-"))
        self.addCleanup(shutil.rmtree, root)
        (root / ".trellis" / "tasks").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "scripts" / "common").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "workflow-installed.json").write_text(
            json.dumps(
                {
                    "profile": "outsourcing",
                    "cli_types": ["opencode"],
                    "critical_runtime_patches": [
                        "inject-workflow-state",
                        "opencode-inject-subagent-context",
                        "session-start-strong-gate",
                        "task-start-strong-gate",
                        "task-create-preserve-active",
                        "task-status-view-strong-gate",
                        "workflow-phase-strong-gate",
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "library-lock.yaml").write_text(
            "packs:\n  - pack.requirements-discovery-foundation\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "task.py").write_text(
            self.STRONG_GATE_TASK_PY,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_store.py").write_text(
            self.STRONG_GATE_TASK_STORE,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "tasks.py").write_text(
            self.STRONG_GATE_TASKS,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_queue.py").write_text(
            self.STRONG_GATE_TASK_QUEUE,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "workflow_phase.py").write_text(
            self.STRONG_GATE_WORKFLOW_PHASE,
            encoding="utf-8",
        )
        (root / ".opencode" / "plugins").mkdir(parents=True, exist_ok=True)
        (root / ".opencode" / "plugins" / "inject-workflow-state.js").write_text(
            'import { execFileSync } from "child_process"\n'
            'const PYTHON_CMD = process.env.TRELLIS_PYTHON || "python3"\n'
            "// [workflow-embed-patch:prefer-workflow-state-json]\n"
            "function buildBreadcrumb(id, status, templates, source = null, task = {}) { return task.extraLines }\n",
            encoding="utf-8",
        )
        (root / ".opencode" / "lib").mkdir(parents=True, exist_ok=True)
        (root / ".opencode" / "lib" / "session-utils.js").write_text(
            "// [workflow-embed-patch:strong-gate-session-utils]\n",
            encoding="utf-8",
        )

        result = self.run_script("route", "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "embed_invalid")
        self.assertIn("inject-subagent-context.js", data["reason"])

    def test_cmd_route_embed_invalid_when_opencode_subagent_patch_is_incomplete(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="workflow-state-test-"))
        self.addCleanup(shutil.rmtree, root)
        (root / ".trellis" / "tasks").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "scripts" / "common").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "workflow-installed.json").write_text(
            json.dumps(
                {
                    "profile": "outsourcing",
                    "cli_types": ["opencode"],
                    "critical_runtime_patches": [
                        "inject-workflow-state",
                        "opencode-inject-subagent-context",
                        "session-start-strong-gate",
                        "task-start-strong-gate",
                        "task-create-preserve-active",
                        "task-status-view-strong-gate",
                        "workflow-phase-strong-gate",
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "library-lock.yaml").write_text(
            "packs:\n  - pack.requirements-discovery-foundation\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "task.py").write_text(
            self.STRONG_GATE_TASK_PY,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_store.py").write_text(
            self.STRONG_GATE_TASK_STORE,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "tasks.py").write_text(
            self.STRONG_GATE_TASKS,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_queue.py").write_text(
            self.STRONG_GATE_TASK_QUEUE,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "workflow_phase.py").write_text(
            self.STRONG_GATE_WORKFLOW_PHASE,
            encoding="utf-8",
        )
        (root / ".opencode" / "plugins").mkdir(parents=True, exist_ok=True)
        (root / ".opencode" / "plugins" / "inject-workflow-state.js").write_text(
            'import { execFileSync } from "child_process"\n'
            'const PYTHON_CMD = process.env.TRELLIS_PYTHON || "python3"\n'
            "// [workflow-embed-patch:prefer-workflow-state-json]\n"
            "function buildBreadcrumb(id, status, templates, source = null, task = {}) { return task.extraLines }\n",
            encoding="utf-8",
        )
        (root / ".opencode" / "plugins" / "inject-subagent-context.js").write_text(
            "// [workflow-embed-patch:opencode-subagent-gates]\n"
            "export function fake() {\n"
            "  return true\n"
            "}\n",
            encoding="utf-8",
        )
        (root / ".opencode" / "lib").mkdir(parents=True, exist_ok=True)
        (root / ".opencode" / "lib" / "session-utils.js").write_text(
            "// [workflow-embed-patch:strong-gate-session-utils]\n",
            encoding="utf-8",
        )

        result = self.run_script("route", "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "embed_invalid")
        self.assertIn("inject-subagent-context.js", data["reason"])

    def test_cmd_route_codex_embed_allows_unwired_session_start_surface(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="workflow-state-test-"))
        self.addCleanup(shutil.rmtree, root)
        (root / ".trellis" / "tasks").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "scripts" / "common").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "workflow-installed.json").write_text(
            json.dumps(
                {
                    "profile": "outsourcing",
                    "cli_types": ["codex"],
                    "critical_runtime_patches": [
                        "inject-workflow-state",
                        "task-start-strong-gate",
                        "task-create-preserve-active",
                        "task-status-view-strong-gate",
                        "workflow-phase-strong-gate",
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "library-lock.yaml").write_text(
            "packs:\n  - pack.requirements-discovery-foundation\n",
            encoding="utf-8",
        )
        (root / ".codex" / "hooks").mkdir(parents=True, exist_ok=True)
        (root / ".codex" / "hooks.json").write_text(
            json.dumps(
                {
                    "hooks": {
                        "UserPromptSubmit": [
                            {
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": "python3 -X utf8 .codex/hooks/inject-workflow-state.py",
                                        "timeout": 15,
                                    }
                                ]
                            }
                        ]
                    }
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (root / ".codex" / "hooks" / "inject-workflow-state.py").write_text(
            "# [workflow-embed-patch:prefer-workflow-state-json]\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "task.py").write_text(
            self.STRONG_GATE_TASK_PY,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_store.py").write_text(
            self.STRONG_GATE_TASK_STORE,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "tasks.py").write_text(
            self.STRONG_GATE_TASKS,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_queue.py").write_text(
            self.STRONG_GATE_TASK_QUEUE,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "workflow_phase.py").write_text(
            self.STRONG_GATE_WORKFLOW_PHASE,
            encoding="utf-8",
        )

        result = self.run_script("route", "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertNotEqual(data["action"], "embed_invalid")

    def test_cmd_route_codex_embed_requires_wired_session_start_patch(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="workflow-state-test-"))
        self.addCleanup(shutil.rmtree, root)
        (root / ".trellis" / "tasks").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "scripts" / "common").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "workflow-installed.json").write_text(
            json.dumps(
                {
                    "profile": "outsourcing",
                    "cli_types": ["codex"],
                    "critical_runtime_patches": [
                        "inject-workflow-state",
                        "task-start-strong-gate",
                        "task-create-preserve-active",
                        "task-status-view-strong-gate",
                        "workflow-phase-strong-gate",
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "library-lock.yaml").write_text(
            "packs:\n  - pack.requirements-discovery-foundation\n",
            encoding="utf-8",
        )
        (root / ".codex" / "hooks").mkdir(parents=True, exist_ok=True)
        (root / ".codex" / "hooks.json").write_text(
            json.dumps(
                {
                    "hooks": {
                        "SessionStart": [
                            {
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": "python3 -X utf8 .codex/hooks/session-start.py",
                                        "timeout": 15,
                                    }
                                ]
                            }
                        ],
                        "UserPromptSubmit": [
                            {
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": "python3 -X utf8 .codex/hooks/inject-workflow-state.py",
                                        "timeout": 15,
                                    }
                                ]
                            }
                        ],
                    }
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (root / ".codex" / "hooks" / "inject-workflow-state.py").write_text(
            "# [workflow-embed-patch:prefer-workflow-state-json]\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "task.py").write_text(
            self.STRONG_GATE_TASK_PY,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_store.py").write_text(
            self.STRONG_GATE_TASK_STORE,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "tasks.py").write_text(
            self.STRONG_GATE_TASKS,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_queue.py").write_text(
            self.STRONG_GATE_TASK_QUEUE,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "workflow_phase.py").write_text(
            self.STRONG_GATE_WORKFLOW_PHASE,
            encoding="utf-8",
        )

        result = self.run_script("route", "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "embed_invalid")
        self.assertIn(".codex/hooks/session-start.py", data["reason"])

    def test_cmd_route_warns_when_distributed_command_content_drifts_across_platforms(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="workflow-state-test-"))
        self.addCleanup(shutil.rmtree, root)
        (root / ".trellis" / "tasks").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "scripts" / "common").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "workflow-installed.json").write_text(
            json.dumps(
                {
                    "profile": "outsourcing",
                    "cli_types": ["claude", "opencode", "codex"],
                    "commands": ["brainstorm"],
                    "critical_runtime_patches": [
                        "inject-workflow-state",
                        "claude-inject-subagent-context",
                        "opencode-inject-subagent-context",
                        "session-start-strong-gate",
                        "task-start-strong-gate",
                        "task-create-preserve-active",
                        "task-status-view-strong-gate",
                        "workflow-phase-strong-gate",
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "library-lock.yaml").write_text(
            "packs:\n  - pack.requirements-discovery-foundation\n",
            encoding="utf-8",
        )
        (root / ".claude" / "hooks").mkdir(parents=True, exist_ok=True)
        (root / ".claude" / "hooks" / "inject-workflow-state.py").write_text(
            "# [workflow-embed-patch:prefer-workflow-state-json]\n",
            encoding="utf-8",
        )
        (root / ".claude" / "hooks" / "session-start.py").write_text(
            "# strong-gate-session-start-patch-applied\n",
            encoding="utf-8",
        )
        (root / ".claude" / "hooks" / "inject-subagent-context.py").write_text(
            "# [workflow-embed-patch:claude-subagent-gates]\n"
            "def _emit_blocked_subagent_output(*args, **kwargs):\n"
            "    return None\n"
            "# Strong-gate blocked this subagent dispatch.\n"
            "# current embedded workflow disables agent/subagent execution paths\n"
            "_emit_blocked_subagent_output(subagent_type, original_prompt, tool_input)\n",
            encoding="utf-8",
        )
        (root / ".codex" / "hooks").mkdir(parents=True, exist_ok=True)
        (root / ".codex" / "hooks" / "inject-workflow-state.py").write_text(
            "# [workflow-embed-patch:prefer-workflow-state-json]\n",
            encoding="utf-8",
        )
        (root / ".codex" / "hooks" / "session-start.py").write_text(
            "# strong-gate-session-start-patch-applied\n# [workflow-embed-patch:session-start-route-first]\n",
            encoding="utf-8",
        )
        (root / ".opencode" / "plugins").mkdir(parents=True, exist_ok=True)
        (root / ".opencode" / "plugins" / "inject-workflow-state.js").write_text(
            "// [workflow-embed-patch:prefer-workflow-state-json]\n"
            'import { execFileSync } from "child_process"\n'
            'const PYTHON_CMD = process.env.TRELLIS_PYTHON || "python3"\n'
            "function buildBreadcrumb(id, status, templates, source = null, extraLines = []) { const task = { extraLines }; return status + task.extraLines.join(\"\\n\") }\n",
            encoding="utf-8",
        )
        (root / ".opencode" / "lib").mkdir(parents=True, exist_ok=True)
        (root / ".opencode" / "lib" / "session-utils.js").write_text(
            "// [workflow-embed-patch:strong-gate-session-utils]\n",
            encoding="utf-8",
        )
        (root / ".opencode" / "plugins" / "inject-subagent-context.js").write_text(
            "// [workflow-embed-patch:opencode-subagent-gates]\n"
            "function buildBlockedSubagentPrompt(routeData, subagentType, originalPrompt) { return originalPrompt }\n"
            "function shouldAllowTaskInjection(routeData, subagentType) { return subagentType !== \"forbidden\" }\n"
            "function loadRouteData(ctx, taskDir) { return { stage: \"implementation\", action: \"reenter\", target: \"implementation\" } }\n"
            "const allowedStages = new Set([\"implementation\", \"check\", \"review-gate\", \"project-audit\", \"delivery\"])\n"
            "loadRouteData(ctx, ctx.resolveTaskDir(taskDir))\n"
            "Strong-gate blocked this subagent dispatch.\n"
            "strong-gate route does not allow subagent injection\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "task.py").write_text(
            self.STRONG_GATE_TASK_PY,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_store.py").write_text(
            self.STRONG_GATE_TASK_STORE,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "tasks.py").write_text(
            self.STRONG_GATE_TASKS,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "task_queue.py").write_text(
            self.STRONG_GATE_TASK_QUEUE,
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "common" / "workflow_phase.py").write_text(
            self.STRONG_GATE_WORKFLOW_PHASE,
            encoding="utf-8",
        )
        (root / ".claude" / "commands" / "trellis").mkdir(parents=True, exist_ok=True)
        (root / ".opencode" / "commands" / "trellis").mkdir(parents=True, exist_ok=True)
        (root / ".agents" / "skills" / "brainstorm").mkdir(parents=True, exist_ok=True)
        (root / ".claude" / "commands" / "trellis" / "brainstorm.md").write_text(
            "# brainstorm\n\n统一正文\n",
            encoding="utf-8",
        )
        (root / ".opencode" / "commands" / "trellis" / "brainstorm.md").write_text(
            "# brainstorm\n\n不同正文\n",
            encoding="utf-8",
        )
        (root / ".agents" / "skills" / "brainstorm" / "SKILL.md").write_text(
            "# brainstorm\n\n第三份正文\n",
            encoding="utf-8",
        )

        result = self.run_script("route", "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "entry_choice_required")
        self.assertIn("warnings", data)
        self.assertIn("brainstorm 内容漂移", "".join(data["warnings"]))

    # ------------------------------------------------------------------
    # repair subcommand tests
    # ------------------------------------------------------------------

    def test_cmd_repair_requires_explicit_stage_when_state_missing(self) -> None:
        root, task_dir = self.make_fixture()

        result = self.run_script("repair", str(task_dir), "--project-root", str(root))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["status"], "manual_confirmation_required")
        self.assertIn("不会根据 prd.md", data["message"])
        self.assertEqual(data["required_confirmation_args"], ["--stage <stage>"])
        self.assertEqual(data["missing_confirmation_items"], ["current_stage"])

    def test_cmd_repair_apply_with_explicit_stage(self) -> None:
        root, task_dir = self.make_fixture()
        state_path = task_dir / "workflow-state.json"

        result = self.run_script(
            "repair",
            str(task_dir),
            "--project-root",
            str(root),
            "--stage",
            "feasibility",
            "--apply",
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertTrue(state_path.exists(), "workflow-state.json should be created after explicit --stage apply")
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["stage"], "feasibility")
        self.assertEqual(state["version"], 1)

    def test_cmd_repair_execution_stage_requires_explicit_confirmation_fields(self) -> None:
        root, task_dir = self.make_fixture()

        result = self.run_script(
            "repair",
            str(task_dir),
            "--project-root",
            str(root),
            "--stage",
            "implementation",
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["status"], "manual_confirmation_required")
        self.assertIn("--execution-authorized true", data["message"])
        self.assertIn("--transition-from <上一阶段>", data["message"])
        self.assertEqual(
            data["required_confirmation_args"],
            ["--execution-authorized true", "--transition-from <上一阶段>"],
        )
        self.assertEqual(
            data["missing_confirmation_items"],
            ["execution_authorized", "transition_from"],
        )

    def test_cmd_repair_execution_stage_apply_succeeds_with_confirmation_fields(self) -> None:
        root, task_dir = self.make_fixture()

        result = self.run_script(
            "repair",
            str(task_dir),
            "--project-root",
            str(root),
            "--stage",
            "implementation",
            "--execution-authorized",
            "true",
            "--transition-from",
            "plan",
            "--apply",
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        repaired = json.loads((task_dir / "workflow-state.json").read_text(encoding="utf-8"))
        self.assertEqual(repaired["stage"], "implementation")
        self.assertTrue(repaired["checkpoints"]["execution_authorized"])
        self.assertEqual(repaired["last_confirmed_transition"]["from"], "plan")
        self.assertEqual(repaired["last_confirmed_transition"]["to"], "implementation")

    def test_cmd_repair_resets_suspicious_semantic_fields_for_same_stage(self) -> None:
        root, task_dir = self.make_fixture()
        broken_state = {
            "version": 1,
            "stage": "plan",
            "stage_status": "awaiting_user_confirmation",
            "current_block": None,
            "completed_blocks": ["split-tasks"],
            "allowed_next_stages": ["implementation"],
            "awaiting_user_confirmation": True,
            "last_confirmed_transition": {
                "from": "design",
                "to": "plan",
                "confirmed_at": "2026-05-18T00:00:00+00:00",
            },
            "notes": ["preserve me"],
            "checkpoints": {
                "architecture_confirmed": True,
                "context7_review_completed": True,
                "execution_authorized": False,
            },
        }
        (task_dir / "workflow-state.json").write_text(
            json.dumps(broken_state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        result = self.run_script("repair", str(task_dir), "--project-root", str(root), "--apply")

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        repaired = json.loads((task_dir / "workflow-state.json").read_text(encoding="utf-8"))
        self.assertEqual(repaired["stage"], "plan")
        self.assertEqual(repaired["status"], "in_progress")
        self.assertNotIn("awaiting_user_confirmation", repaired)
        self.assertNotIn("last_confirmed_transition", repaired)
        self.assertFalse(repaired["checkpoints"]["architecture_confirmed"])
        self.assertFalse(repaired["checkpoints"]["context7_review_completed"])

    def test_cmd_repair_rebuilds_allowed_next_stages_from_canonical_graph(self) -> None:
        root, task_dir = self.make_fixture()
        broken_state = {
            "version": 1,
            "stage": "plan",
            "stage_status": "awaiting_user_confirmation",
            "current_block": None,
            "completed_blocks": ["split-tasks"],
            "allowed_next_stages": ["record-session"],
            "awaiting_user_confirmation": True,
            "last_confirmed_transition": {
                "from": "design",
                "to": "plan",
                "confirmed_at": "2026-05-18T00:00:00+00:00",
            },
            "notes": [],
            "checkpoints": {
                "architecture_confirmed": True,
                "context7_review_completed": True,
                "execution_authorized": False,
            },
        }
        (task_dir / "workflow-state.json").write_text(
            json.dumps(broken_state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        result = self.run_script("repair", str(task_dir), "--project-root", str(root), "--apply")

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        repaired = json.loads((task_dir / "workflow-state.json").read_text(encoding="utf-8"))
        self.assertEqual(repaired["stage"], "plan")
        self.assertEqual(repaired["status"], "in_progress")
        self.assertNotIn("allowed_next_stages", repaired)

    def test_cmd_repair_preserves_valid_execution_confirmation_for_same_stage(self) -> None:
        root, task_dir = self.make_fixture()
        broken_state = {
            "version": 1,
            "stage": "implementation",
            "stage_status": "awaiting_user_confirmation",
            "current_block": None,
            "completed_blocks": ["task-created"],
            "allowed_next_stages": ["invalid-next"],
            "awaiting_user_confirmation": True,
            "last_confirmed_transition": {
                "from": "plan",
                "to": "implementation",
                "confirmed_at": "2026-05-18T00:00:00+00:00",
            },
            "notes": ["keep me"],
            "checkpoints": {
                "architecture_confirmed": True,
                "context7_review_completed": True,
                "execution_authorized": True,
            },
            "updated_at": "2026-05-18T00:00:00+00:00",
        }
        (task_dir / "workflow-state.json").write_text(
            json.dumps(broken_state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        result = self.run_script("repair", str(task_dir), "--project-root", str(root), "--apply")

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        repaired = json.loads((task_dir / "workflow-state.json").read_text(encoding="utf-8"))
        self.assertEqual(repaired["stage"], "implementation")
        self.assertEqual(repaired["status"], "awaiting_user_confirmation")
        self.assertNotIn("awaiting_user_confirmation", repaired)
        self.assertTrue(repaired["checkpoints"]["execution_authorized"])
        self.assertEqual(repaired["last_confirmed_transition"]["from"], "plan")
        self.assertEqual(repaired["last_confirmed_transition"]["to"], "implementation")
        self.assertEqual(repaired["completed_blocks"], ["task-created"])
        self.assertNotIn("allowed_next_stages", repaired)

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
        self.assertIn("status 必须为 awaiting_user_confirmation", illegal_set.stdout)

        # With awaiting_user_confirmation it should succeed
        self.run_script(
            "set", str(task_dir),
            "--stage-status", "awaiting_user_confirmation",
            "--awaiting-user-confirmation", "true",
        )
        (task_dir / "prd.md").write_text(
            "# sample task\n\n"
            f"{self.VALID_BRAINSTORM_ESTIMATE}\n"
            "## 阶段出口快照\n"
            "- `complexity_decision`: `L1`\n"
            "- `ui_lane_decision`: `no-ui`\n"
            "- `cross_platform_scope`: `claude+codex`\n"
            "- `estimate_refresh_result`: `confirmed`\n"
            "- `kill_criteria`: `none`\n"
            "- `open_items`: `none`\n",
            encoding="utf-8",
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

    def test_transition_to_design_uses_target_stage_doc_gate(self) -> None:
        """Entering design must validate design-stage project docs, not the old stage."""
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        (root / "docs" / "requirements" / "customer-facing-prd.md").unlink()

        self.run_script("init", str(task_dir), "--stage", "brainstorm")
        self.run_script(
            "set", str(task_dir),
            "--stage-status", "awaiting_user_confirmation",
            "--awaiting-user-confirmation", "true",
        )

        blocked = self.run_script(
            "set", str(task_dir),
            "--stage", "design",
            "--stage-status", "in_progress",
            "--awaiting-user-confirmation", "false",
            "--transition-from", "brainstorm",
            "--allowed-next", "plan",
        )
        self.assertEqual(blocked.returncode, 1, msg=blocked.stdout + blocked.stderr)
        self.assertIn("customer-facing-prd.md", blocked.stdout)

    def test_transition_to_plan_accepts_checkpoint_flags_from_same_command(self) -> None:
        """Design->plan should validate the fully merged target state from one set call."""
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        requirements_dir = root / "docs" / "requirements"
        (requirements_dir / "developer-facing-prd.md").write_text("# dev prd\n", encoding="utf-8")
        self.write_context7_review(task_dir)
        design_dir = task_dir / "design"
        design_dir.mkdir(parents=True, exist_ok=True)
        (design_dir / "source-watermark-plan.md").write_text(self.VALID_SOURCE_WATERMARK_PLAN, encoding="utf-8")
        task_prd = task_dir / "prd.md"
        task_prd.write_text(
            task_prd.read_text(encoding="utf-8")
            + "\n## 自动化检查矩阵\n"
            + "- 质量平台门禁：sonar-scanner\n"
            + "- close-out 主入口：/trellis:finish-work\n"
            + "- archive 前置条件：delivery 完成且当前 active task 已验收\n"
            + "- 元数据边界：只允许当前 active task 的 archive + session record\n",
            encoding="utf-8",
        )

        self.run_script("init", str(task_dir), "--stage", "design")
        self.run_script(
            "set", str(task_dir),
            "--stage-status", "awaiting_user_confirmation",
            "--awaiting-user-confirmation", "true",
            "--completed-blocks", "A,B,C,D",
        )

        transitioned = self.run_script(
            "set", str(task_dir),
            "--stage", "plan",
            "--stage-status", "in_progress",
            "--awaiting-user-confirmation", "false",
            "--transition-from", "design",
            "--allowed-next", "implementation",
            "--architecture-confirmed", "true",
            "--context7-review-completed", "true",
        )
        self.assertEqual(transitioned.returncode, 0, msg=transitioned.stdout + transitioned.stderr)
        state = json.loads((task_dir / "workflow-state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["stage"], "plan")
        self.assertTrue(state["checkpoints"]["context7_review_completed"])

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
        blocked = self.run_script("init", str(task_dir), "--stage", "record-session")
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("invalid choice: 'record-session'", blocked.stderr)

    def test_set_rejects_transition_outside_canonical_graph_even_if_allowed_next_is_dirty(self) -> None:
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
            "--allowed-next", "record-session",
        )

        blocked = self.run_script(
            "set",
            str(task_dir),
            "--stage", "record-session",
            "--stage-status", "in_progress",
            "--awaiting-user-confirmation", "false",
            "--transition-from", "brainstorm",
            "--allowed-next",
        )

        self.assertNotEqual(blocked.returncode, 0, msg=blocked.stdout + blocked.stderr)
        self.assertIn("invalid choice: 'record-session'", blocked.stderr)

    def test_issue7_brainstorm_direct_implementation_requires_baseline_sources(self) -> None:
        """Issue 7: L0 direct path needs explicit baseline-source markers."""
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
            "--allowed-next", "design,plan,implementation",
        )
        (task_dir / "prd.md").write_text(
            "# sample task\n\n"
            f"{self.VALID_BRAINSTORM_ESTIMATE}\n"
            "## 阶段出口快照\n"
            "- `complexity_decision`: `L0`\n"
            "- `ui_lane_decision`: `no-ui`\n"
            "- `cross_platform_scope`: `codex-only`\n"
            "- `estimate_refresh_result`: `confirmed`\n"
            "- `kill_criteria`: `none`\n"
            "- `open_items`: `none`\n",
            encoding="utf-8",
        )
        blocked = self.run_script(
            "set", str(task_dir),
            "--stage", "implementation",
            "--stage-status", "in_progress",
            "--awaiting-user-confirmation", "false",
            "--execution-authorized", "true",
            "--transition-from", "brainstorm",
            "--allowed-next", "check,project-audit",
        )
        self.assertEqual(blocked.returncode, 1, msg=blocked.stdout + blocked.stderr)
        self.assertIn("automation_matrix_source", blocked.stdout)

    def test_issue7_brainstorm_allows_implementation_transition_when_baseline_sources_present(self) -> None:
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
            "--allowed-next", "design,plan,implementation",
        )
        (task_dir / "prd.md").write_text(
            "# sample task\n\n"
            f"{self.VALID_BRAINSTORM_ESTIMATE}\n"
            f"{self.VALID_L0_DIRECT_EXECUTION_BASELINE}\n"
            "## 阶段出口快照\n"
            "- `complexity_decision`: `L0`\n"
            "- `ui_lane_decision`: `no-ui`\n"
            "- `cross_platform_scope`: `codex-only`\n"
            "- `estimate_refresh_result`: `confirmed`\n"
            "- `kill_criteria`: `none`\n"
            "- `open_items`: `none`\n",
            encoding="utf-8",
        )
        ok_set = self.run_script(
            "set", str(task_dir),
            "--stage", "implementation",
            "--stage-status", "in_progress",
            "--awaiting-user-confirmation", "false",
            "--execution-authorized", "true",
            "--transition-from", "brainstorm",
            "--allowed-next", "check,project-audit",
        )
        self.assertEqual(ok_set.returncode, 0, msg=ok_set.stdout + ok_set.stderr)

    def test_issue7_brainstorm_direct_execution_path_uses_implementation(self) -> None:
        """Issue 7: L0 direct execution path should stay in implementation stage."""
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
            "--allowed-next", "design,plan,implementation",
        )
        (task_dir / "prd.md").write_text(
            "# sample task\n\n"
            f"{self.VALID_BRAINSTORM_ESTIMATE}\n"
            f"{self.VALID_L0_DIRECT_EXECUTION_BASELINE}\n"
            "## 阶段出口快照\n"
            "- `complexity_decision`: `L0`\n"
            "- `ui_lane_decision`: `no-ui`\n"
            "- `cross_platform_scope`: `codex-only`\n"
            "- `estimate_refresh_result`: `confirmed`\n"
            "- `kill_criteria`: `none`\n"
            "- `open_items`: `none`\n",
            encoding="utf-8",
        )
        ok_set = self.run_script(
            "set", str(task_dir),
            "--stage", "implementation",
            "--stage-status", "in_progress",
            "--awaiting-user-confirmation", "false",
            "--execution-authorized", "true",
            "--transition-from", "brainstorm",
            "--allowed-next", "check,project-audit",
        )
        self.assertEqual(ok_set.returncode, 0, msg=ok_set.stdout + ok_set.stderr)

    def test_completed_status_routes_as_awaiting_confirmation_and_allows_transition(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.run_script("init", str(task_dir), "--stage", "brainstorm")
        self.run_script(
            "set",
            str(task_dir),
            "--stage-status",
            "completed",
            "--awaiting-user-confirmation",
            "true",
            "--allowed-next",
            "implementation",
        )
        (task_dir / "prd.md").write_text(
            "# sample task\n\n"
            f"{self.VALID_BRAINSTORM_ESTIMATE}\n"
            f"{self.VALID_L0_DIRECT_EXECUTION_BASELINE}\n"
            "## 阶段出口快照\n"
            "- `complexity_decision`: `L0`\n"
            "- `ui_lane_decision`: `no-ui`\n"
            "- `cross_platform_scope`: `codex-only`\n"
            "- `estimate_refresh_result`: `confirmed`\n"
            "- `kill_criteria`: `none`\n"
            "- `open_items`: `none`\n",
            encoding="utf-8",
        )
        routed = self.run_script("route", str(task_dir), "--project-root", str(root))
        routed_data = json.loads(routed.stdout)
        self.assertEqual(routed_data["action"], "awaiting_confirmation")
        self.assertEqual(routed_data["status"], "completed")

        transitioned = self.run_script(
            "set",
            str(task_dir),
            "--stage",
            "implementation",
            "--stage-status",
            "in_progress",
            "--awaiting-user-confirmation",
            "false",
            "--execution-authorized",
            "true",
            "--transition-from",
            "brainstorm",
            "--allowed-next",
            "check,project-audit",
        )
        self.assertEqual(transitioned.returncode, 0, msg=transitioned.stdout + transitioned.stderr)

    def test_check_allows_project_audit_transition(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.write_check_report(task_dir)
        self.run_script("init", str(task_dir), "--stage", "check")
        self.run_script(
            "set",
            str(task_dir),
            "--stage-status", "awaiting_user_confirmation",
            "--awaiting-user-confirmation", "true",
            "--allowed-next", "project-audit,review-gate,implementation,finish-work",
        )

        ok_set = self.run_script(
            "set",
            str(task_dir),
            "--stage", "project-audit",
            "--stage-status", "in_progress",
            "--awaiting-user-confirmation", "false",
            "--transition-from", "check",
            "--allowed-next", "check,review-gate",
        )
        self.assertEqual(ok_set.returncode, 0, msg=ok_set.stdout + ok_set.stderr)

    def test_review_gate_allows_project_audit_transition(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.write_check_report(task_dir)
        self.write_review_gate_round(task_dir)
        self.run_script("init", str(task_dir), "--stage", "review-gate")
        self.run_script(
            "set",
            str(task_dir),
            "--stage-status", "awaiting_user_confirmation",
            "--awaiting-user-confirmation", "true",
            "--allowed-next", "project-audit,finish-work,implementation",
        )

        ok_set = self.run_script(
            "set",
            str(task_dir),
            "--stage", "project-audit",
            "--stage-status", "in_progress",
            "--awaiting-user-confirmation", "false",
            "--transition-from", "review-gate",
            "--allowed-next", "check,review-gate",
        )
        self.assertEqual(ok_set.returncode, 0, msg=ok_set.stdout + ok_set.stderr)

    def test_project_audit_to_delivery_requires_project_audit_report(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.run_script("init", str(task_dir), "--stage", "project-audit")
        self.run_script(
            "set",
            str(task_dir),
            "--stage-status", "awaiting_user_confirmation",
            "--awaiting-user-confirmation", "true",
            "--allowed-next", "delivery",
        )

        blocked = self.run_script(
            "set",
            str(task_dir),
            "--stage", "delivery",
            "--stage-status", "in_progress",
            "--awaiting-user-confirmation", "false",
            "--transition-from", "project-audit",
        )
        self.assertEqual(blocked.returncode, 1, msg=blocked.stdout + blocked.stderr)
        self.assertIn("project-audit.md", blocked.stdout)

        self.write_project_audit_report(task_dir)
        allowed = self.run_script(
            "set",
            str(task_dir),
            "--stage", "delivery",
            "--stage-status", "in_progress",
            "--awaiting-user-confirmation", "false",
            "--transition-from", "project-audit",
        )
        self.assertEqual(allowed.returncode, 1, msg=allowed.stdout + allowed.stderr)
        self.assertIn("check.md", allowed.stdout)

    def test_project_audit_to_delivery_requires_task_level_check_status_linkage(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.write_check_report(task_dir)
        self.write_project_audit_report(
            task_dir,
            content="""# Project Audit Report

## Mode
- formal

## Project-Level Verification Matrix
- `project-task-coverage`: all code-related tasks complete; no approved exceptions; no delivery blockers
- 项目级统一代码漏洞检测命令：not run + reason
- 项目级统一代码质量总检命令：not run + reason

## Confirmed Findings
- [self] no blocking issue

## Candidate Findings / Reviewer Evidence
- [self] none

## Confirmed Fix Plan
- no-op

## Applied Changes
- no-op
- `project_audit_code_changes`: `yes`

## Project-Level Verification Results
- 项目级统一代码漏洞检测：not run + reason
- 项目级统一代码质量总检：not run + reason
- `task_level_check_status`: `not_needed`

## Remaining Risks
- none

## Suggested Next Step
- /trellis:delivery
""",
        )
        self.run_script("init", str(task_dir), "--stage", "project-audit")
        self.run_script(
            "set",
            str(task_dir),
            "--stage-status", "awaiting_user_confirmation",
            "--awaiting-user-confirmation", "true",
            "--allowed-next", "delivery",
        )
        blocked = self.run_script(
            "set",
            str(task_dir),
            "--stage", "delivery",
            "--stage-status", "in_progress",
            "--awaiting-user-confirmation", "false",
            "--transition-from", "project-audit",
        )
        self.assertEqual(blocked.returncode, 1, msg=blocked.stdout + blocked.stderr)
        self.assertIn("task_level_check_status", blocked.stdout)

    def test_project_audit_to_delivery_allows_no_code_change_with_task_level_check_evidence(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.write_check_report(task_dir)
        self.write_project_audit_report(task_dir)
        self.run_script("init", str(task_dir), "--stage", "project-audit")
        self.run_script(
            "set",
            str(task_dir),
            "--stage-status", "awaiting_user_confirmation",
            "--awaiting-user-confirmation", "true",
            "--allowed-next", "delivery",
        )
        allowed = self.run_script(
            "set",
            str(task_dir),
            "--stage", "delivery",
            "--stage-status", "in_progress",
            "--awaiting-user-confirmation", "false",
            "--transition-from", "project-audit",
        )
        self.assertEqual(allowed.returncode, 0, msg=allowed.stdout + allowed.stderr)

    def test_set_rejects_transition_outside_current_allowed_next_subset(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.run_script("init", str(task_dir), "--stage", "brainstorm")
        self.run_script(
            "set",
            str(task_dir),
            "--stage-status", "awaiting_user_confirmation",
            "--awaiting-user-confirmation", "true",
            "--allowed-next", "plan",
        )
        blocked = self.run_script(
            "set",
            str(task_dir),
            "--stage", "design",
            "--stage-status", "in_progress",
            "--awaiting-user-confirmation", "false",
            "--transition-from", "brainstorm",
            "--allowed-next", "implementation",
        )
        self.assertEqual(blocked.returncode, 1, msg=blocked.stdout + blocked.stderr)
        self.assertIn("allowed-next", blocked.stdout)

    def test_check_to_delivery_rejects_shell_check_report(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        (task_dir / "check.md").write_text(
            """# Check Report

## Changed Scope
- src/example.ts

## Verification Results
- lint placeholder
""",
            encoding="utf-8",
        )
        self.run_script("init", str(task_dir), "--stage", "check")
        self.run_script(
            "set",
            str(task_dir),
            "--stage-status", "awaiting_user_confirmation",
            "--awaiting-user-confirmation", "true",
            "--allowed-next", "review-gate,implementation,delivery",
        )

        blocked = self.run_script(
            "set",
            str(task_dir),
            "--stage", "delivery",
            "--stage-status", "in_progress",
            "--awaiting-user-confirmation", "false",
            "--transition-from", "check",
        )
        self.assertEqual(blocked.returncode, 1, msg=blocked.stdout + blocked.stderr)
        self.assertIn("Applied Specs", blocked.stdout)

        self.write_check_report(task_dir)
        allowed = self.run_script(
            "set",
            str(task_dir),
            "--stage", "delivery",
            "--stage-status", "in_progress",
            "--awaiting-user-confirmation", "false",
            "--transition-from", "check",
        )
        self.assertEqual(allowed.returncode, 0, msg=allowed.stdout + allowed.stderr)

    def test_check_to_delivery_requires_review_gate_decision_section(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        (task_dir / "check.md").write_text(
            """# Check Report

## Changed Scope
- src/example.ts

## Applied Specs
- .trellis/spec/scripts/python-conventions.md

## Verification Results
- lint: pass
- test: pass

## Deviations
- none

## Uncovered Risks
- none

## Suggested Next Step
- /trellis:delivery
""",
            encoding="utf-8",
        )
        self.run_script("init", str(task_dir), "--stage", "check")
        self.run_script(
            "set",
            str(task_dir),
            "--stage-status", "awaiting_user_confirmation",
            "--awaiting-user-confirmation", "true",
            "--allowed-next", "review-gate,implementation,delivery",
        )

        blocked = self.run_script(
            "set",
            str(task_dir),
            "--stage", "delivery",
            "--stage-status", "in_progress",
            "--awaiting-user-confirmation", "false",
            "--transition-from", "check",
        )
        self.assertEqual(blocked.returncode, 1, msg=blocked.stdout + blocked.stderr)
        self.assertIn("Review-Gate Decision", blocked.stdout)

    def test_check_to_delivery_blocks_when_hard_condition_is_marked_yes(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.write_check_report(
            task_dir,
            content="""# Check Report

## Changed Scope
- src/auth.ts

## Applied Specs
- .trellis/spec/scripts/python-conventions.md

## Verification Results
- lint: pass
- test: pass

## Deviations
- none

## Uncovered Risks
- none

## Review-Gate Decision
- `review_gate_decision`: `skip`
- `review_gate_reason`: `想直接交付`
- `auth_or_sensitive`: `yes`
- `data_migration_or_schema_change`: `no`
- `public_api_or_cross_layer_contract_or_external_integration`: `no`
- `payment_queue_cache_concurrency`: `no`
- `shared_core_with_blast_radius`: `no`
- `explicit_user_review_gate_request`: `no`

## Suggested Next Step
- /trellis:delivery
""",
        )
        self.run_script("init", str(task_dir), "--stage", "check")
        self.run_script(
            "set",
            str(task_dir),
            "--stage-status", "awaiting_user_confirmation",
            "--awaiting-user-confirmation", "true",
            "--allowed-next", "review-gate,implementation,delivery",
        )

        blocked = self.run_script(
            "set",
            str(task_dir),
            "--stage", "delivery",
            "--stage-status", "in_progress",
            "--awaiting-user-confirmation", "false",
            "--transition-from", "check",
        )
        self.assertEqual(blocked.returncode, 1, msg=blocked.stdout + blocked.stderr)
        self.assertIn("review_gate_decision", blocked.stdout)

    def test_delivery_awaiting_rejects_shell_artifacts_without_real_status(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.write_delivery_artifacts(task_dir)
        self.run_script("init", str(task_dir), "--stage", "delivery")
        self.run_script(
            "set",
            str(task_dir),
            "--stage-status", "awaiting_user_confirmation",
            "--awaiting-user-confirmation", "true",
        )

        result = self.run_script("route", str(task_dir), "--project-root", str(root))
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "awaiting_confirmation_with_blockers")
        blockers_text = "".join(data.get("blockers", []))
        self.assertTrue(
            "finish-work-checklist.md" in blockers_text
            or "Acceptance Criteria Status" in blockers_text
            or "Closeout Assets" in blockers_text
            or "触发条件 / 付款 / 权限 / 证明材料是否齐备" in blockers_text
            or "delivery-control-validate.py" in blockers_text
            or "ownership-proof-validate.py" in blockers_text
            or "source-watermark-guard.py" in blockers_text
        )

    def test_route_delivery_awaiting_reports_blockers_when_artifacts_missing(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
            assessment_content=self.VALID_EXTERNAL_ASSESSMENT,
        )
        self.run_script("init", str(task_dir), "--stage", "delivery")
        self.run_script(
            "set",
            str(task_dir),
            "--stage-status", "awaiting_user_confirmation",
            "--awaiting-user-confirmation", "true",
        )

        result = self.run_script("route", str(task_dir), "--project-root", str(root))
        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "awaiting_confirmation_with_blockers")
        self.assertIn("缺少交付产物", "".join(data.get("blockers", [])))

    def test_route_plan_awaiting_reports_plan_gate_blockers(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.write_context7_review(task_dir)
        self.run_script("init", str(task_dir), "--stage", "plan")
        self.run_script(
            "set",
            str(task_dir),
            "--stage-status", "awaiting_user_confirmation",
            "--awaiting-user-confirmation", "true",
        )

        result = self.run_script("route", str(task_dir), "--project-root", str(root))

        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "awaiting_confirmation_with_blockers")
        blockers_text = "".join(data.get("blockers", []))
        self.assertIn("plan-validate.py", blockers_text)
        self.assertTrue(
            "task_plan.md" in blockers_text or "task_creation_checklist.md" in blockers_text
        )

    def test_route_delivery_awaiting_reports_validator_blockers_not_just_file_presence(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
            assessment_content=self.VALID_EXTERNAL_ASSESSMENT,
        )
        self.write_delivery_artifacts(task_dir)
        self.run_script("init", str(task_dir), "--stage", "delivery")
        self.run_script(
            "set",
            str(task_dir),
            "--stage-status", "awaiting_user_confirmation",
            "--awaiting-user-confirmation", "true",
        )

        result = self.run_script("route", str(task_dir), "--project-root", str(root))

        data = json.loads(result.stdout)
        self.assertEqual(data["action"], "awaiting_confirmation_with_blockers")
        self.assertIn("delivery-control-validate.py", "".join(data.get("blockers", [])))

    def test_route_project_audit_awaiting_requires_project_audit_report(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.run_script("init", str(task_dir), "--stage", "project-audit")
        self.run_script(
            "set",
            str(task_dir),
            "--stage-status", "awaiting_user_confirmation",
            "--awaiting-user-confirmation", "true",
            "--allowed-next", "check,review-gate",
        )

        blocked = self.run_script("route", str(task_dir), "--project-root", str(root))
        blocked_data = json.loads(blocked.stdout)
        self.assertEqual(blocked_data["action"], "awaiting_confirmation_with_blockers")
        self.assertIn("project-audit.md", "".join(blocked_data.get("blockers", [])))

        self.write_project_audit_report(task_dir)
        allowed = self.run_script("route", str(task_dir), "--project-root", str(root))
        allowed_data = json.loads(allowed.stdout)
        self.assertEqual(allowed_data["action"], "awaiting_confirmation")

    def test_route_review_gate_awaiting_requires_review_gate_round_report(self) -> None:
        root, task_dir = self.make_fixture()
        self.write_required_project_docs(
            root,
            task_dir,
            task_prd_suffix=self.VALID_BRAINSTORM_ESTIMATE,
            customer_prd_suffix=self.VALID_CUSTOMER_ESTIMATE,
        )
        self.run_script("init", str(task_dir), "--stage", "review-gate")
        self.run_script(
            "set",
            str(task_dir),
            "--stage-status", "awaiting_user_confirmation",
            "--awaiting-user-confirmation", "true",
            "--allowed-next", "finish-work,implementation",
        )

        blocked = self.run_script("route", str(task_dir), "--project-root", str(root))
        blocked_data = json.loads(blocked.stdout)
        self.assertEqual(blocked_data["action"], "awaiting_confirmation_with_blockers")
        self.assertRegex(
            "".join(blocked_data.get("blockers", [])),
            r"review-gate(?:/|-)?.*目录|review-gate-round-",
        )

        self.write_check_report(task_dir)
        self.write_review_gate_round(task_dir)
        allowed = self.run_script("route", str(task_dir), "--project-root", str(root))
        allowed_data = json.loads(allowed.stdout)
        self.assertEqual(allowed_data["action"], "awaiting_confirmation")


if __name__ == "__main__":
    unittest.main()
