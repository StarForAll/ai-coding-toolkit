# workflow-audit: 新项目开发工作流

## Audit Target and Boundary
- Workflow Root: `docs/workflows/新项目开发工作流/`
- Resolved Workflow Root Rule: always `docs/workflows/新项目开发工作流/`
- Compatible Anchor Version: `0.5.17`
- Current Trellis Version: `0.5.17`
- Version Gate: `passed`
- Bypass Detail: `none`
- Audit Scope: `task-based runtime`
- Current CLI: `codex`
- Candidate Issues:
  - `workflow.md / 工作流总纲` complexity inflation
  - state-machine learning cost
  - patch-script count and `workflow-state.py` size
- Generated Target Project Root: `/tmp/trellis-0.5.17-2`
- Comparison Model: `source repo` vs `generated target project` baseline (`trellis init`) vs `generated target project` workflow-installed state (`install-workflow.py`) vs `runtime command output`

## Evidence-Gathering Actions Executed in This Round
- Read workflow audit skill/spec, project doc/script specs, and prior issue history — Layer: `source repo`
- Read `docs/workflows/新项目开发工作流/commands/workflow_assets.py` and ran `trellis -v` — Layer: `source repo` + `runtime command output`
- Read `/tmp/trellis-0.5.17-2/.trellis/workflow-installed.json`, inventoried `/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/`, and measured installed `workflow.md` / `workflow-state.py` line counts — Layer: `generated target project` — Stage: `workflow-installed state after install-workflow.py`
- Read `tmp/workflow-issues/0001.md` through `0012.md` for repeat-cluster context — Layer: `source repo`
- Ran `/ops/softwares/python/bin/python3 /tmp/trellis-0.5.17-2/.trellis/scripts/workflow/patch-*.py --help` spot checks and observed `patch-inject-workflow-state.py --help` failing with `⚠️ 不支持的文件类型:` while sibling patch helpers returned argparse usage text — Layer: `generated target project` — Stage: `workflow-installed state after install-workflow.py`
- Measured source-doc size and inspected extracted template blocks inside `工作流总纲.md` — Layer: `source repo`
- Ran `/ops/softwares/python/bin/python3 docs/workflows/新项目开发工作流/commands/shell/test_patch_helpers.py` and `/ops/softwares/python/bin/python3 docs/workflows/新项目开发工作流/commands/test_workflow_installers.py` after repair — Layer: `runtime command output`

## Confirmed Issues

### [P2] patch-inject-workflow-state.py breaks the shared patch-helper CLI contract
- Conclusion: `patch-inject-workflow-state.py` was the lone strong-gate patch helper that still parsed raw `sys.argv`, so `--help` was treated like a target path instead of returning argparse help.
- Evidence Source:
  - Layer: `generated target project`
  - Stage: `workflow-installed state after install-workflow.py`
  - `/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/patch-inject-workflow-state.py`
  - Command: `/ops/softwares/python/bin/python3 /tmp/trellis-0.5.17-2/.trellis/scripts/workflow/patch-inject-workflow-state.py --help`
  - Key result: exit code `1`, output `⚠️ 不支持的文件类型:`
- Validation Action:
  - Compared `--help` behavior across installed patch helpers
  - Read the source script and confirmed it used `sys.argv` directly while sibling helpers already used `argparse`
- Impact Scope:
  - Maintainer/operator usage of the inject-workflow-state patch helper
  - Regression coverage for patch-helper CLI consistency
- Suggested Fix Direction:
  - Convert the helper to `argparse` and include it in the patch-helper `--help` regression list

### [P2] session-start strong-gate reference doc still described an obsolete stage chain
- Conclusion: `commands/session-start-patch-strong-gate.md` still hard-coded a pre-`project-audit` stage list, which overstated the “learning-cost” complaint by teaching an outdated state machine.
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - `docs/workflows/新项目开发工作流/commands/session-start-patch-strong-gate.md`
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
- Validation Action:
  - Searched for old stage-list strings in the workflow source
  - Compared the doc wording against the current installed `.trellis/workflow.md` quick reference and `workflow-state.py` transitions
- Impact Scope:
  - Maintainer understanding of the strong-gate state model
  - Future doc propagation when stages change
- Suggested Fix Direction:
  - Replace the stale hard-coded list with wording that points at the current `workflow-state.py` stage chain and explicitly includes `project-audit`

### [P2] 工作流总纲.md kept template-heavy details inline, causing recurrent maintenance drift
- Conclusion: the 3217-line `工作流总纲.md` was carrying long templates and appendix bodies inline, which materially increased propagation drift risk; this is a real source-maintenance problem even though the installed runtime workflow remains concise.
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - `docs/workflows/新项目开发工作流/工作流总纲.md`
  - `tmp/workflow-issues/0001.md` through `0012.md`
- Validation Action:
  - Measured `工作流总纲.md` at `3217` lines before repair
  - Identified large template-only blocks that were not needed inline in the core overview
  - Cross-checked prior issue history showing repeated `partial cross-file update` closures in the same workflow doc surface
- Impact Scope:
  - Maintainer edits to workflow rules and template wording
  - Risk of future source-doc drift across 总纲 / walkthrough / command docs
- Suggested Fix Direction:
  - Keep core rules in `工作流总纲.md`, extract large templates/appendices into companion docs, and add regression tests so the overview stays de-inlined

## Unconfirmed Items / False Alarms
- `installed .trellis/workflow.md itself is too large` -> false alarm; the embedded runtime guide in `/tmp/trellis-0.5.17-2` is 558 lines and already acts as the concise operator surface
- `the strong-gate stage model itself should be reduced/removed` -> false alarm for this run; the current route/validate contract and installed quick reference are internally consistent, and no runtime defect was proven from stage count alone
- `all patch helpers must be merged into one script` -> unconfirmed optimization; current evidence supports fixing the outlier CLI contract, not forcing a risky structural merge
- `workflow-state.py must be split into modules now` -> unconfirmed optimization; size alone did not prove a current runtime or maintenance break that outweighed refactor risk in this run

## Blocked Items (Blocked / Evidence Gap / Needs Clarification)
- none

## Per-CLI Adaptation Conclusions

### Claude Code
- Official docs checked: `not-applicable in this focused repair run`
- Repo-local evidence checked: `not-applicable in this focused repair run`
- Practical development-use evidence checked: `not-applicable in this focused repair run`
- Agreement / discrepancy: `not-applicable`
- Expected carrier model: `not-applicable`
- Does the current implementation match: `not-applicable`
- If not, what is wrong: `not-applicable`

### OpenCode
- Official docs checked: `not-applicable in this focused repair run`
- Repo-local evidence checked: `not-applicable in this focused repair run`
- Practical development-use evidence checked: `not-applicable in this focused repair run`
- Agreement / discrepancy: `not-applicable`
- Expected carrier model: `not-applicable`
- Does the current implementation match: `not-applicable`
- If not, what is wrong: `not-applicable`

### Codex
- Official docs checked: `not-applicable in this focused repair run`
- Repo-local evidence checked: `not-applicable in this focused repair run`
- Practical development-use evidence checked: `not-applicable in this focused repair run`
- Agreement / discrepancy: `not-applicable`
- Expected carrier model: `not-applicable`
- Does the current implementation match: `not-applicable`
- If not, what is wrong: `not-applicable`

## Suggested Fix Directions
- Keep `patch-inject-workflow-state.py` on the shared patch-helper argparse contract and protect it with the helper test suite
- Replace stale hard-coded stage-list wording with source-of-truth-oriented wording that includes `project-audit`
- Continue extracting template-only blocks out of `工作流总纲.md` rather than re-inlining them

## Propagation Scope and Synchronized Update Range
- Affected layers: workflow docs, helper patch scripts, helper tests, and workflow installer/doc regression tests within `docs/workflows/新项目开发工作流/`
- Propagation risk notes: overview-template extraction must keep runtime rules in total纲 while moving only template-heavy content; helper CLI changes must stay aligned with the shared patch-helper test suite

## Recommended Next Step
- Recommended action: `plain-language action`
- Trigger condition: current focused repair run is complete and verified
- Recommendation reason: the confirmed defects were fixed in source, same-pattern variants were swept, and regression tests passed
- Stronger alternatives not selected: full state-machine refactor and blanket patch-helper consolidation were rejected as optimization-heavy changes without enough defect evidence

## Stop Point and Pending Confirmations
- Auto-continue allowed: `No`
- User confirmation required for:
  - none
