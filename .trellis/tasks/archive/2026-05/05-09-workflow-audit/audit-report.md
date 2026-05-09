# workflow-audit: 新项目开发工作流

## Audit Target and Boundary
- Workflow Root: `docs/workflows/新项目开发工作流/`
- Resolved Workflow Root Rule: always `docs/workflows/新项目开发工作流/`
- Audit Scope: task-based runtime
- Current CLI: `codex`
- Candidate Issues:
  - workflow should use Trellis native agents
  - workflow docs should become pure English except necessary maintainer-human-reading docs
  - embedded target project should gain default project-level spec requiring paired README updates and Chinese default README
  - `grill-me` can be deleted because native brainstorm covers it
- Generated Target Project Root: none yet
- Comparison Model: `source repo` vs `generated target project` baseline (`trellis init`) vs `generated target project` workflow-installed state (`install-workflow.py`) vs `runtime command output`

## Evidence-Gathering Actions Executed in This Round
- Read `workflow-audit` source-of-truth skill spec and project-level skill file to confirm audit contract and execution mode rules — Layer: `source repo`
- Read Trellis session context and phase index via `.trellis/scripts/get_context.py` to establish no active task and inline Codex workflow state — Layer: `runtime command output`
- Read `docs/workflows/新项目开发工作流/commands/workflow_assets.py` and compared `COMPATIBLE_TRELLIS_VERSION` against local `trellis -v` — Layer: `source repo`
- Ran `trellis -v` and confirmed exact equality with the compatible version — Layer: `runtime command output`
- Indexed workflow-root files and searched workflow docs/scripts for agent, README, AGENTS, handoff, and `grill-me` references — Layer: `source repo`
- Created a clean temporary target project under `/tmp/workflow_audit_target_20260509`, initialized Git + `origin` push URLs + `trellis init --claude --opencode --codex`, and captured the clean baseline file tree — Layer: `generated target project` — Stage: `baseline after trellis init`
- Ran `detect-embed-state.py` against the temporary target project and confirmed `INITIAL_BASELINE_READY` — Layer: `runtime command output`
- Ran `install-workflow.py --dry-run` against the temporary target project and captured the planned install actions plus per-CLI `Agents: 0` summary — Layer: `runtime command output`
- Traced `install-workflow.py` initial spec import to `pack.requirements-discovery-foundation`, then traced that pack’s actual manifest asset set — Layer: `source repo`
- Audited related workflow docs for propagation gaps after the README-governance change, including the lightweight overview, the dual-track walkthrough, and the multi-CLI walkthrough close-out sections — Layer: `source repo`
- Audited the active task metadata (`task.json`, `implement.jsonl`, `check.jsonl`, `prd.md`) for progress drift against the completed implementation and verification state — Layer: `source repo`

## Confirmed Issues

None remaining in the scope of items 1 and 3 after this remediation round.

## Fixed In This Round

### [Resolved] Embed flow now injects a default project-level spec that enforces paired README updates with Chinese as the default README
- Conclusion: The default imported pack now includes a dedicated `readme-governance` spec, and the workflow’s audit evidence surface recognizes that spec as part of the managed initial import.
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - `trellis-library/specs/universal-domains/project-governance/readme-governance/*.md` now defines the reusable README governance concern
  - `trellis-library/manifest.yaml` now registers `spec.universal-domains.project-governance.readme-governance` and includes it in `pack.requirements-discovery-foundation`
  - `docs/workflows/新项目开发工作流/commands/workflow_assets.py` now treats `.trellis/spec/universal-domains/project-governance/readme-governance/overview.md` as part of the initial-pack managed evidence surface
  - Workflow docs that describe the default import path now state that the initial pack includes project-level README bilingual governance
- Validation Action:
  - Added installer and capability-audit tests first, watched the installer test fail because the spec was missing, then implemented the new concern and pack membership
  - Re-ran the targeted installer and capability-audit tests until green
- Impact Scope:
  - Every target project embedded with this workflow
  - Project-level documentation governance and README language consistency
- Suggested Fix Direction:
  - Keep workflow stage docs aligned with the imported spec so future README-rule changes update one source contract rather than drifting across prose

## Unconfirmed Items / False Alarms
- workflow should use Trellis native agents -> false alarm in the audited workflow root; current source and dry-run behavior already match the Trellis-native-agent contract
- embedded target project should gain default project-level spec requiring paired README updates and Chinese default README -> fixed in this round
- `grill-me` can be deleted because native brainstorm covers it -> explicitly reviewed and intentionally not executed in this round at user direction; keep as a closed non-action rather than a dangling unresolved candidate

## Additional Gaps Fixed In This Round

### [Resolved] README-governance propagation gaps in related workflow docs
- Conclusion: Related walkthrough docs that still described the initial pack or install checklist were updated so they no longer omit the new `readme-governance` spec.
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - `docs/workflows/新项目开发工作流/工作流全局流转说明（通俗版）.md` now includes the `readme-governance` import in both the install summary and the minimum post-install checklist
  - `docs/workflows/新项目开发工作流/完整流程演练.md` now states that the default pack also carries the README bilingual governance rule
- Validation Action:
  - Compared the newly updated install-pack references against the already-updated canonical docs (`工作流总纲.md`, `命令映射.md`, `工作流嵌入执行规范.md`, `装后隐藏目录与托管边界核对清单.md`)
  - Patched missing sibling references so the same install contract is described consistently
- Impact Scope:
  - Human post-install verification guidance
  - Workflow documentation consistency across entry-point walkthroughs

### [Resolved] Finish-work / session-record terminology drift in walkthrough docs
- Conclusion: The multi-CLI walkthrough and the dual-track close-out example now align with the current fresh baseline, where `finish-work` is the final close-out entry and session recording happens inside that path via `record-session-helper.py`.
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md` stage 10 title now matches the current `finish-work` entrypoint
  - `docs/workflows/新项目开发工作流/完整流程演练.md` now explicitly tells readers to enter through `/trellis:finish-work` before showing the helper-level session-record commands
  - `docs/workflows/新项目开发工作流/工作流全局流转说明（通俗版）.md` now frames the final stage as `Finish-Work（Session Record）`
- Validation Action:
  - Compared stage titles, CLI entry rows, helper examples, and completion bullets against the current baseline described in `CLI原生适配边界矩阵.md` and the installed command patches
  - Updated mismatched labels while preserving the truthful helper/archive order
- Impact Scope:
  - Reader understanding of the close-out control plane
  - Avoiding legacy `record-session` misinterpretation as the primary fresh-baseline entrypoint

### [Resolved] Task tracking drift and decision-closure gaps
- Conclusion: The task metadata now reflects the actual in-progress remediation state, the jsonl context files are no longer placeholders, and candidate issue 4 is explicitly closed as a user-directed non-action for this round.
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - `.trellis/tasks/05-09-workflow-audit/task.json` now carries `in_progress`, related files, and scoped notes
  - `.trellis/tasks/05-09-workflow-audit/implement.jsonl` and `check.jsonl` now contain real spec-context entries
  - `.trellis/tasks/05-09-workflow-audit/prd.md` now records the narrowed remediation scope and the explicit no-op decision for candidate issue 4
- Validation Action:
  - Compared task metadata and jsonl files against the already-completed implementation/testing evidence
  - Replaced placeholder task artifacts with truthful context entries only
- Impact Scope:
  - Trellis task continuity for future maintainers
  - Preventing repeated re-litigation of candidate issue 4 as an unresolved dangling item

## Blocked Items (Blocked / Evidence Gap / Needs Clarification)
- Target-project post-install verification
  - Type: `Evidence Gap`
  - Cause: formal `install-workflow.py` execution was intentionally not run because the current main executor is Codex and the workflow contract requires a non-Codex executor plus `WORKFLOW_EMBED_EXECUTOR_CONFIRMED=1` for the formal embed step
  - Impact: full workflow-installed filesystem state after formal embed remains unverified, even though the current findings above are already conclusive from source evidence + baseline + dry-run
  - What is needed to continue: hand off formal embed execution to Claude Code or OpenCode, then return `detect-embed-state.py`, `install-workflow.py`, and `upgrade-compat.py --check` evidence

## Per-CLI Adaptation Conclusions

### Claude Code
- Expected carrier model: phase commands under `.claude/commands/trellis/*.md`; Trellis-native `trellis-*` agents under `.claude/agents/*.md`; workflow installer patches commands but does not overlay agent contents
- Does the current implementation match: yes, based on source contract, clean baseline, and dry-run `Agents: 0`
- If not, what is wrong: no confirmed Claude-specific agent drift in this audit

### OpenCode
- Expected carrier model: phase commands under `.opencode/commands/trellis/*.md`; Trellis-native `trellis-*` agents under `.opencode/agents/*.md`; `.agents/skills/` is only a shared carrier surface, not the formal OpenCode entry
- Does the current implementation match: yes, based on source contract, clean baseline, and dry-run `Agents: 0`
- If not, what is wrong: no confirmed OpenCode-specific agent drift in this audit

### Codex
- Expected carrier model: shared workflow skills under `.agents/skills/*/SKILL.md`; Trellis-native `trellis-*` agents under `.codex/agents/*.toml`; installer patches `trellis-continue` / `trellis-finish-work` but does not overlay agent contents
- Does the current implementation match: yes for the native-agent boundary, based on `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md:11-18`, `commands/workflow_assets.py:106-119`, `commands/install-workflow.py:1193-1248`, clean baseline agent files, and dry-run `Agents: 0`
- If not, what is wrong: formal post-install state remains unverified because Codex cannot lead the first formal embed execution

## Suggested Fix Directions
- Optional follow-up only: convert the workflow’s operator-facing docs and platform READMEs to English if you want to address candidate item 2 in a separate round
- Optional follow-up only: complete the formal non-Codex embed handoff if you want the remaining post-install evidence gap closed

## Propagation Scope and Synchronized Update Range
- Affected layers for the README-rule change: installer pack selection, imported spec assets, workflow stage docs (`design`-adjacent contracts), and workflow audit/capability evidence surfaces
- Propagation risk notes: the native-agent boundary is already consistent and should not be regressed while changing docs or default spec composition

## Recommended Next Step
- Recommended action: `check`
- Trigger condition: item 3 has been implemented and item 1 was preserved; the remaining work in this round is verification and optional formal non-Codex embed handoff if you want full runtime closure
- Recommendation reason: implementation is complete enough for quality closure
- Stronger alternatives not selected: `trellis-brainstorm` is no longer needed for the scoped work you kept, and `update-spec` is not the next bottleneck unless new durable lessons emerge beyond the new imported spec itself

## Stop Point and Pending Confirmations
- Auto-continue allowed: No
- User confirmation required for:
  - whether to proceed to commit with the current scoped changes for items 1 and 3 only
