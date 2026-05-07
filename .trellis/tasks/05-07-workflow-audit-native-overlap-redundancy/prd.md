# workflow-audit: native Trellis overlap and redundancy

## Goal

Audit `docs/workflows/新项目开发工作流/` to determine whether the workflow still duplicates native Trellis 0.5.0-rc.5 capabilities, or whether the observed overlap is actually stale documentation / source-contract drift that should be narrowed and repaired in a follow-up phase.

## What I Already Know

- Target workflow root is fixed to `docs/workflows/新项目开发工作流/`.
- Version preflight passed: `COMPATIBLE_TRELLIS_VERSION = "0.5.0-rc.5"` and `trellis -v` returned `0.5.0-rc.5`.
- User explicitly requested a deep analysis that must not rely on static inspection only.
- The workflow boundary matrix says Trellis 0.5+ natively provides `trellis-research`, `trellis-implement`, and `trellis-check` agents, and the workflow should not overlay these definitions.
- Static evidence found possible drift around old `start` / `record-session` terminology versus current Trellis 0.5 carriers `continue`, `finish-work`, `trellis-continue`, and `trellis-finish-work`.
- Static evidence found possible inconsistency around whether distributed Codex workflow skills are deployed only to `.agents/skills/` or broadly across multiple Codex skills surfaces; the follow-up spec-sync pass now aligns the contract with `.agents/skills/` shared deployment and `.codex/skills/` duplicate cleanup.
- Refined runtime evidence shows `.codex/skills/` can exist as an empty secondary skills directory in a generated Trellis 0.5.0-rc.5 target. The key point is not directory absence; it is that shared workflow skills are not written there and duplicate shared skills there are treated as drift.
- Refined runtime evidence shows fresh Trellis creates the native `trellis-research`, `trellis-implement`, and `trellis-check` agent files, while `install-workflow.py --dry-run` reports `Agents: 0` for all supported CLIs.

## Requirements

- Distinguish confirmed duplication from intentional extension of Trellis native behavior.
- Include source-repo evidence, generated target-project evidence, and runtime command output where runtime validation is required.
- Do not treat this source repository's hidden directories as generated target-project evidence.
- Respect Codex handoff boundary if formal embed execution is reached from Codex.
- Produce an audit conclusion without modifying workflow source assets.

## Acceptance Criteria

- [x] Version preflight result is recorded.
- [x] Static source-repo evidence covers managed surface definitions, CLI boundary docs, install scripts, and relevant specs.
- [x] Runtime validation is attempted or explicitly blocked with command, exit status, and evidence boundary.
  - `trellis -v`, `detect-embed-state.py --json`, and `install-workflow.py --dry-run` were replayed with exit code `0`.
  - Formal install and post-install `upgrade-compat.py --check` remain blocked by the Codex handoff boundary.
- [x] Findings classify confirmed issues, false alarms, evidence gaps, and intentional non-redundant extensions separately.
- [x] Every confirmed issue includes priority, source-layer-tagged evidence, validation action, impact scope, and fix direction.

## Out of Scope

- No remediation edits in this task unless the user explicitly confirms a follow-up repair phase.
- No Trellis version compatibility audit across versions; version drift belongs to `workflow-capability-audit`.
- No audit of `.kiro/` or `.qoder/` as workflow-managed surfaces unless `workflow_assets.py` adds them.

## Technical Notes

- `workflow-audit` same-version gate passed.
- Runtime validation is required because the user requested non-static analysis and the suspected redundancy involves actual install / post-install artifact behavior.

## Review Status

- Review mode: main-thread only for this refinement pass.
- Current audit direction: `docs/workflows/` remediation was performed for the two target maintainer docs; `.trellis/spec` contract drift has now been remediated in the follow-up spec-sync pass.
- Confirmed issue baseline:
  - P1 Codex distributed skills scope conflict between `.trellis/spec/scripts/workflow-installer-upgrade-contracts.md` and current installer / upgrade checker / boundary docs.
  - P1 retired `start` / `record-session` fresh-baseline expectations were present in maintainer docs and quick tables before remediation.
  - P1 boundary matrix quick table previously said `research / implement / check` agents were workflow-deployed, contradicting native Trellis ownership evidence.
- Remediated in `docs/workflows/新项目开发工作流/`:
  - The boundary matrix and hidden-directory checklist now use current fresh-baseline carriers `continue` / `finish-work` and `trellis-continue` / `trellis-finish-work`.
  - `start` / `record-session` remain only as legacy compatibility wording.
  - `trellis-research` / `trellis-implement` / `trellis-check` are described as Trellis-native, with workflow dry-run `Agents: 0` and only legacy bare-name migration.
  - `.agents/skills/` is described as the shared workflow skills target, while `.codex/skills/` is Codex-local / duplicate-drift scope.
- Corrected descriptions:
  - Native-agent overlap is a documentation contradiction, not a confirmed installer overlay.
  - `.codex/skills/` existed in the generated target fixture but contained no shared skill files; report wording should not imply the directory was absent.
  - `record-session` may still exist as a legacy compatibility path in code, but current Trellis 0.5 fresh-baseline checks should not require it.
- Spec contract remediation completed:
  - `.trellis/spec/scripts/workflow-installer-upgrade-contracts.md` now defines `.agents/skills/` as the shared workflow skill deployment target, `.codex/skills/` as Codex-local / duplicate cleanup scope, and `trellis-continue` / `trellis-finish-work` as the active baseline patch targets.
  - The same spec now classifies `trellis-research` / `trellis-implement` / `trellis-check` as Trellis-native assets, with workflow scripts limited to legacy bare-name migration and no native agent content overlay.
- Remaining blocked evidence:
  - Formal install, `workflow-installed.json`, post-install files, and `upgrade-compat.py --check` are still explicit evidence gaps until the Codex handoff boundary is resolved.
