---
closure-round-version: 1
protocol: workflow-scan-repair-v4
repair-task: .trellis/tasks/05-27-workflow-repair-2026-05-27-create-pr-reference
source-report: /tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md
base-workflow-version: 0.1.2800
round: 1
created-at: 2026-05-27T17:08:41+08:00
total-scenarios: 2
total-findings: 0
in-scope-findings: 0
new-family-findings: 0
round-outcome: clean
---

# Workflow Repair Closure Round 1

## Round Summary

- Repair Task: `.trellis/tasks/05-27-workflow-repair-2026-05-27-create-pr-reference`
- Source Report: `/tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md`
- Base Workflow Version: `0.1.2800`
- Round: `1`
- Scenario Count: `2`
- Total Findings: `0`
- In-Scope Findings: `0`
- New-Family Findings: `0`
- Round Outcome: `clean`

## Scenarios

### clean-outsourcing-all-cli

- Fixture Root: `unittest fixtures created by install-workflow regression tests plus the OpenCode patch-helper fixture`
- Profile: `outsourcing`
- CLI Types: `claude,opencode,codex`
- Status: `passed`
- Commands Run:
  - `python3 -m unittest docs.workflows.新项目开发工作流.commands.shell.test_patch_helpers.PatchHelperScriptTests.test_patch_opencode_inject_subagent_context_adds_block_feedback`
  - `python3 -m unittest docs.workflows.新项目开发工作流.commands.test_workflow_installers.WorkflowInstallerTests.test_build_workflow_content_replaces_task_mechanism_without_legacy_headings`
  - `python3 -m unittest docs.workflows.新项目开发工作流.commands.test_workflow_installers.WorkflowInstallerTests.test_install_patches_trellis_meta_references_with_strong_gate_guidance`
  - `python3 -m unittest docs.workflows.新项目开发工作流.commands.test_workflow_installers.WorkflowInstallerTests.test_install_patches_update_spec_skills_to_real_entry_surfaces`
  - `python3 -m unittest docs.workflows.新项目开发工作流.commands.test_workflow_installers.WorkflowInstallerTests.test_install_workflow_doc_keeps_canonical_allowed_next_examples`
- Notes: `fresh-install path now removes stale create-pr quickrefs, patches OpenCode JSON route parsing, refreshes trellis-meta hook docs, rewrites update-spec entry surfaces, and keeps install self-check green under the tighter drift contract`

### existing-workflow-outsourcing-all-cli

- Fixture Root: `unittest fixtures created by upgrade-compat regression tests`
- Profile: `outsourcing`
- CLI Types: `claude,opencode,codex`
- Status: `passed`
- Commands Run:
  - `python3 -m unittest docs.workflows.新项目开发工作流.commands.test_workflow_installers.WorkflowInstallerTests.test_upgrade_build_workflow_content_replaces_task_mechanism_without_legacy_headings`
  - `python3 -m unittest docs.workflows.新项目开发工作流.commands.test_workflow_installers.WorkflowInstallerTests.test_upgrade_merge_refreshes_update_spec_skills_and_trellis_meta_hooks_docs`
- Notes: `existing-workflow merge path now replays the same source-side fixes instead of leaving stale skill/reference surfaces behind, while upgrade --check catches stale postprocessed skills, references, cross-layer guide text, and the old OpenCode marker-only route parser`

## Follow-Up

- Round Action: `clean`
- Rollback Performed: `no`
- Rollback Scope: `none`
- Next Step: `bump current workflow version from 0.1.2800 to 0.1.2801 and invalidate older scan reports via the stale-report gate`
