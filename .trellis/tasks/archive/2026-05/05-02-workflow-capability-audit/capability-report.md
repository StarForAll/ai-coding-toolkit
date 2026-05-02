# workflow-capability-audit: 新项目开发工作流

## Audit Target and Boundary
- Workflow Root: `docs/workflows/新项目开发工作流/`
- Current CLI: <inferred or explicit>
- Current Trellis Version: 9.9.9
- Compatible Anchor: 0.4.0
- Audit Scope: task-based version-upgrade compatibility audit

## Version Gate Outcome
- Result: passed
- Reason: current Trellis version is newer than the compatible anchor

## Evidence-Gathering Actions Executed In This Round
- Step 0 version gate passed — Layer: runtime command output
- Fresh A fixture created — Layer: generated target project
- Fresh B fixture created — Layer: generated target project

## Discovered Baseline Capabilities
- Claude baseline command carrier discovered under `.claude/commands/trellis/`.
- OpenCode baseline command carrier discovered under `.opencode/commands/trellis/`.
- Shared skills carrier discovered under `.agents/skills/`.
- Codex implementation agent carrier discovered under `.codex/agents/`.
- Codex hook/config carrier discovered under `.codex/`.
- Shared project rules carrier discovered in `AGENTS.md`.

## Workflow-Managed Surface Matrix

| Capability ID | Capability | Latest Trellis Mechanism / Benefit | Discovery Source | Claude Evidence | Claude Classification | OpenCode Evidence | OpenCode Classification | Codex Evidence | Codex Classification | Overall Summary | Structural Signal | Adaptation Decision |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| WM-001 | implementation-agent:check | Workflow deploys a managed implementation-stage internal role asset. | ai-discovered | A=.claude/agents/check.md; B=.claude/agents/check.md | adopted-compatible | A=.opencode/agents/check.md; B=.opencode/agents/check.md | adopted-compatible | A=.codex/agents/check.toml; B=.codex/agents/check.toml | adopted-compatible | adopted-compatible | none detected from A/B surface shape | No action required in fresh B unless later compatibility analysis changes this. |
| WM-002 | implementation-agent:implement | Workflow deploys a managed implementation-stage internal role asset. | ai-discovered | A=.claude/agents/implement.md; B=.claude/agents/implement.md | adopted-compatible | A=.opencode/agents/implement.md; B=.opencode/agents/implement.md | adopted-compatible | A=.codex/agents/implement.toml; B=.codex/agents/implement.toml | adopted-compatible | adopted-compatible | none detected from A/B surface shape | No action required in fresh B unless later compatibility analysis changes this. |
| WM-003 | implementation-agent:research | Workflow deploys a managed implementation-stage internal role asset. | ai-discovered | A=.claude/agents/research.md; B=.claude/agents/research.md | adopted-compatible | A=.opencode/agents/research.md; B=.opencode/agents/research.md | adopted-compatible | A=.codex/agents/research.toml; B=.codex/agents/research.toml | adopted-compatible | adopted-compatible | none detected from A/B surface shape | No action required in fresh B unless later compatibility analysis changes this. |
| WM-004 | brainstorm | Workflow replaces the live baseline copy with workflow-owned content. | ai-discovered | A=.claude/commands/trellis/brainstorm.md; B=.claude/commands/trellis/brainstorm.md | adopted-compatible | A=.opencode/commands/trellis/brainstorm.md; B=.opencode/commands/trellis/brainstorm.md | adopted-compatible | A=.agents/skills/brainstorm/SKILL.md; B=.agents/skills/brainstorm/SKILL.md | adopted-compatible | adopted-compatible | none detected from A/B surface shape | No action required in fresh B unless later compatibility analysis changes this. |
| WM-005 | check | Workflow replaces the live baseline copy with workflow-owned content. | ai-discovered | A=.claude/commands/trellis/check.md; B=.claude/commands/trellis/check.md | adopted-compatible | A=.opencode/commands/trellis/check.md; B=.opencode/commands/trellis/check.md | adopted-compatible | A=.agents/skills/check/SKILL.md; B=.agents/skills/check/SKILL.md | adopted-compatible | adopted-compatible | none detected from A/B surface shape | No action required in fresh B unless later compatibility analysis changes this. |
| WM-006 | delivery | Workflow adds a workflow-only capability beyond the Trellis baseline. | ai-discovered | B=.claude/commands/trellis/delivery.md | adopted-compatible | B=.opencode/commands/trellis/delivery.md | adopted-compatible | B=.agents/skills/delivery/SKILL.md | adopted-compatible | adopted-compatible | none detected from A/B surface shape | No action required in fresh B unless later compatibility analysis changes this. |
| WM-007 | design | Workflow adds a workflow-only capability beyond the Trellis baseline. | ai-discovered | B=.claude/commands/trellis/design.md | adopted-compatible | B=.opencode/commands/trellis/design.md | adopted-compatible | B=.agents/skills/design/SKILL.md | adopted-compatible | adopted-compatible | none detected from A/B surface shape | No action required in fresh B unless later compatibility analysis changes this. |
| WM-008 | shared-doc:workflow.md | Workflow preserves Trellis baseline content and injects workflow patch behavior. | ai-discovered | A=.trellis/workflow.md; B=.trellis/workflow.md | patched-compatible | A=.trellis/workflow.md; B=.trellis/workflow.md | patched-compatible | A=.trellis/workflow.md; B=.trellis/workflow.md | patched-compatible | patched-compatible | none detected from A/B surface shape | No action required in fresh B unless later compatibility analysis changes this. |
| WM-009 | feasibility | Workflow adds a workflow-only capability beyond the Trellis baseline. | ai-discovered | B=.claude/commands/trellis/feasibility.md | adopted-compatible | B=.opencode/commands/trellis/feasibility.md | adopted-compatible | B=.agents/skills/feasibility/SKILL.md | adopted-compatible | adopted-compatible | none detected from A/B surface shape | No action required in fresh B unless later compatibility analysis changes this. |
| WM-010 | finish-work | Workflow preserves Trellis baseline content and injects workflow patch behavior. | ai-discovered | A=.claude/commands/trellis/finish-work.md; B=.claude/commands/trellis/finish-work.md | patched-compatible | A=.opencode/commands/trellis/finish-work.md; B=.opencode/commands/trellis/finish-work.md | patched-compatible | A=.agents/skills/finish-work/SKILL.md; B=.agents/skills/finish-work/SKILL.md | patched-compatible | patched-compatible | none detected from A/B surface shape | No action required in fresh B unless later compatibility analysis changes this. |
| WM-011 | parallel | Workflow intentionally disables a baseline capability on the embedded surface. | ai-discovered | not-applicable | not-applicable | not-applicable | not-applicable | A=.codex/skills/parallel/SKILL.md | intentionally-disabled | intentionally-disabled | none detected from A/B surface shape | No action required in fresh B unless later compatibility analysis changes this. |
| WM-012 | plan | Workflow adds a workflow-only capability beyond the Trellis baseline. | ai-discovered | B=.claude/commands/trellis/plan.md | adopted-compatible | B=.opencode/commands/trellis/plan.md | adopted-compatible | B=.agents/skills/plan/SKILL.md | adopted-compatible | adopted-compatible | none detected from A/B surface shape | No action required in fresh B unless later compatibility analysis changes this. |
| WM-013 | project-audit | Workflow adds a workflow-only capability beyond the Trellis baseline. | ai-discovered | B=.claude/commands/trellis/project-audit.md | adopted-compatible | B=.opencode/commands/trellis/project-audit.md | adopted-compatible | B=.agents/skills/project-audit/SKILL.md | adopted-compatible | adopted-compatible | none detected from A/B surface shape | No action required in fresh B unless later compatibility analysis changes this. |
| WM-014 | record-session | Workflow preserves Trellis baseline content and injects workflow patch behavior. | ai-discovered | A=.claude/commands/trellis/record-session.md; B=.claude/commands/trellis/record-session.md | patched-compatible | A=.opencode/commands/trellis/record-session.md; B=.opencode/commands/trellis/record-session.md | patched-compatible | not-applicable | not-applicable | patched-compatible | none detected from A/B surface shape | No action required in fresh B unless later compatibility analysis changes this. |
| WM-015 | review-gate | Workflow adds a workflow-only capability beyond the Trellis baseline. | ai-discovered | B=.claude/commands/trellis/review-gate.md | adopted-compatible | B=.opencode/commands/trellis/review-gate.md | adopted-compatible | B=.agents/skills/review-gate/SKILL.md | adopted-compatible | adopted-compatible | none detected from A/B surface shape | No action required in fresh B unless later compatibility analysis changes this. |
| WM-016 | helper-script:check-quality.py | Workflow deploys a shared helper script used across CLI carriers. | ai-discovered | B=.trellis/scripts/workflow/check-quality.py | adopted-compatible | B=.trellis/scripts/workflow/check-quality.py | adopted-compatible | B=.trellis/scripts/workflow/check-quality.py | adopted-compatible | adopted-compatible | none detected from A/B surface shape | No action required in fresh B unless later compatibility analysis changes this. |
| WM-017 | helper-script:delivery-control-validate.py | Workflow deploys a shared helper script used across CLI carriers. | ai-discovered | B=.trellis/scripts/workflow/delivery-control-validate.py | adopted-compatible | B=.trellis/scripts/workflow/delivery-control-validate.py | adopted-compatible | B=.trellis/scripts/workflow/delivery-control-validate.py | adopted-compatible | adopted-compatible | none detected from A/B surface shape | No action required in fresh B unless later compatibility analysis changes this. |
| WM-018 | helper-script:design-export.py | Workflow deploys a shared helper script used across CLI carriers. | ai-discovered | B=.trellis/scripts/workflow/design-export.py | adopted-compatible | B=.trellis/scripts/workflow/design-export.py | adopted-compatible | B=.trellis/scripts/workflow/design-export.py | adopted-compatible | adopted-compatible | none detected from A/B surface shape | No action required in fresh B unless later compatibility analysis changes this. |
| WM-019 | helper-script:feasibility-check.py | Workflow deploys a shared helper script used across CLI carriers. | ai-discovered | B=.trellis/scripts/workflow/feasibility-check.py | adopted-compatible | B=.trellis/scripts/workflow/feasibility-check.py | adopted-compatible | B=.trellis/scripts/workflow/feasibility-check.py | adopted-compatible | adopted-compatible | none detected from A/B surface shape | No action required in fresh B unless later compatibility analysis changes this. |
| WM-020 | helper-script:metadata-autocommit-guard.py | Workflow deploys a shared helper script used across CLI carriers. | ai-discovered | B=.trellis/scripts/workflow/metadata-autocommit-guard.py | adopted-compatible | B=.trellis/scripts/workflow/metadata-autocommit-guard.py | adopted-compatible | B=.trellis/scripts/workflow/metadata-autocommit-guard.py | adopted-compatible | adopted-compatible | none detected from A/B surface shape | No action required in fresh B unless later compatibility analysis changes this. |
| WM-021 | helper-script:ownership-proof-validate.py | Workflow deploys a shared helper script used across CLI carriers. | ai-discovered | B=.trellis/scripts/workflow/ownership-proof-validate.py | adopted-compatible | B=.trellis/scripts/workflow/ownership-proof-validate.py | adopted-compatible | B=.trellis/scripts/workflow/ownership-proof-validate.py | adopted-compatible | adopted-compatible | none detected from A/B surface shape | No action required in fresh B unless later compatibility analysis changes this. |
| WM-022 | helper-script:plan-validate.py | Workflow deploys a shared helper script used across CLI carriers. | ai-discovered | B=.trellis/scripts/workflow/plan-validate.py | adopted-compatible | B=.trellis/scripts/workflow/plan-validate.py | adopted-compatible | B=.trellis/scripts/workflow/plan-validate.py | adopted-compatible | adopted-compatible | none detected from A/B surface shape | No action required in fresh B unless later compatibility analysis changes this. |
| WM-023 | helper-script:record-session-helper.py | Workflow deploys a shared helper script used across CLI carriers. | ai-discovered | B=.trellis/scripts/workflow/record-session-helper.py | adopted-compatible | B=.trellis/scripts/workflow/record-session-helper.py | adopted-compatible | B=.trellis/scripts/workflow/record-session-helper.py | adopted-compatible | adopted-compatible | none detected from A/B surface shape | No action required in fresh B unless later compatibility analysis changes this. |
| WM-024 | helper-script:workflow-state.py | Workflow deploys a shared helper script used across CLI carriers. | ai-discovered | B=.trellis/scripts/workflow/workflow-state.py | adopted-compatible | B=.trellis/scripts/workflow/workflow-state.py | adopted-compatible | B=.trellis/scripts/workflow/workflow-state.py | adopted-compatible | adopted-compatible | none detected from A/B surface shape | No action required in fresh B unless later compatibility analysis changes this. |
| WM-025 | start | Workflow preserves Trellis baseline content and injects workflow patch behavior. | ai-discovered | A=.claude/commands/trellis/start.md; B=.claude/commands/trellis/start.md | patched-compatible | A=.opencode/commands/trellis/start.md; B=.opencode/commands/trellis/start.md | patched-compatible | A=.agents/skills/start/SKILL.md; B=.agents/skills/start/SKILL.md | patched-compatible | patched-compatible | none detected from A/B surface shape | No action required in fresh B unless later compatibility analysis changes this. |
| WM-026 | test-first | Workflow adds a workflow-only capability beyond the Trellis baseline. | ai-discovered | B=.claude/commands/trellis/test-first.md | adopted-compatible | B=.opencode/commands/trellis/test-first.md | adopted-compatible | B=.agents/skills/test-first/SKILL.md | adopted-compatible | adopted-compatible | none detected from A/B surface shape | No action required in fresh B unless later compatibility analysis changes this. |

## Workflow-Dependent Trellis-Native Surface Matrix

| Capability ID | Capability | Latest Trellis Mechanism / Benefit | Discovery Source | Claude Evidence | Claude Classification | OpenCode Evidence | OpenCode Classification | Codex Evidence | Codex Classification | Overall Summary | Structural Signal | Adaptation Decision |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TN-007 | custom-supplemental-capability | Supplemental capability confirmed from current A/B evidence. | supplemental-confirmed | A=AGENTS.md; B=AGENTS.md | adopted-compatible | not-applicable | not-applicable | not-applicable | not-applicable | adopted-compatible | none detected from supplemental validation | No action required unless later confirmed compatibility analysis changes this. |
| TN-001 | project-rules-and-routing-carrier | Workflow depends on AGENTS-style project rules/routing as a shared long-lived carrier. | ai-discovered | A=AGENTS.md; B=AGENTS.md | adopted-compatible | A=AGENTS.md; B=AGENTS.md | adopted-compatible | A=AGENTS.md; B=AGENTS.md | adopted-compatible | adopted-compatible | none detected from A/B dependency surface shape | No action required in fresh B unless later compatibility analysis changes this. |
| TN-002 | claude-hooks-and-settings-carrier | Workflow may rely on Claude runtime hooks/settings that are Trellis-native or manually maintained rather than installer-managed. | ai-discovered | A=.claude/settings.json,.claude/hooks; B=.claude/settings.json,.claude/hooks | adopted-compatible | not-applicable | not-applicable | not-applicable | not-applicable | adopted-compatible | none detected from A/B dependency surface shape | No action required in fresh B unless later compatibility analysis changes this. |
| TN-003 | opencode-plugin-and-instructions-carrier | Workflow may rely on OpenCode plugin/instruction carrier surfaces outside installer-managed workflow commands. | ai-discovered | not-applicable | not-applicable | A=.opencode/plugins,.opencode/package.json; B=.opencode/plugins,.opencode/package.json | adopted-compatible | not-applicable | not-applicable | adopted-compatible | none detected from A/B dependency surface shape | No action required in fresh B unless later compatibility analysis changes this. |
| TN-004 | codex-hooks-and-config-carrier | Workflow may rely on Codex hook/config surfaces outside installer-managed shared skills. | ai-discovered | not-applicable | not-applicable | not-applicable | not-applicable | A=.codex/hooks.json,.codex/config.toml; B=.codex/hooks.json,.codex/config.toml | adopted-compatible | adopted-compatible | none detected from A/B dependency surface shape | No action required in fresh B unless later compatibility analysis changes this. |
| TN-005 | implementation-agent-carrier | Workflow depends on per-CLI implementation agent carrier directories even beyond installer ownership boundaries. | ai-discovered | A=.claude/agents; B=.claude/agents | adopted-compatible | A=.opencode/agents; B=.opencode/agents | adopted-compatible | A=.codex/agents; B=.codex/agents | adopted-compatible | adopted-compatible | none detected from A/B dependency surface shape | No action required in fresh B unless later compatibility analysis changes this. |
| TN-006 | trellis-runtime-workflow-guide | Workflow depends on Trellis runtime workflow guide and project runtime script surfaces. | ai-discovered | A=.trellis/workflow.md,.trellis/scripts/task.py; B=.trellis/workflow.md,.trellis/scripts/task.py | adopted-compatible | A=.trellis/workflow.md,.trellis/scripts/task.py; B=.trellis/workflow.md,.trellis/scripts/task.py | adopted-compatible | A=.trellis/workflow.md,.trellis/scripts/task.py; B=.trellis/workflow.md,.trellis/scripts/task.py | adopted-compatible | adopted-compatible | none detected from A/B dependency surface shape | No action required in fresh B unless later compatibility analysis changes this. |
## Rejected / Unconfirmed Supplemental Points
- none yet

## Structural-Break Judgment
- Result: no
- Signals:
- none detected from current report state
- Why:
- Current report state does not show structural-break signals that require escalation.
- Required next action:
- Continue with the current confirmation boundary.

## Confirmed Fix Scope
- pending user confirmation

## Applied Corrections
- none yet

## Post-Fix Revalidation
- none yet

## A/B Fixture Status
- A Root: /tmp/workflow-capability-audit-a-e3wi9_lj
- B Root: /tmp/workflow-capability-audit-b-pjl9qn2p
- Destroyed: no
- Final destruction confirmed by user: no

## Stop Point and Pending Confirmations
- Auto-continue allowed: No
- User confirmation required for:
  - whether to proceed from audit into confirmed compatibility-fix work
