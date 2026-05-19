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
  - `task.py current --source` / degraded start 路径因 strong-gate 补丁缺少依赖导入而失效
  - OpenCode `inject-workflow-state` 补丁不自包含，且 breadcrumb 未传递 `extraLines`
  - 安装完成判定把坏补丁误判为已安装
  - 补丁脚本存在“只替换函数体、不补依赖/调用点”的隐藏前提
  - Codex 残留旧 session-start 逻辑造成维护歧义
  - 自动化验证不足导致运行时问题漏检
- Generated Target Project Root: `/tmp/trellis-0.5.17-2`
- Comparison Model: `source repo` vs `generated target project` baseline (`trellis init`) vs `generated target project` workflow-installed state (`install-workflow.py`) vs `runtime command output`

## Evidence-Gathering Actions Executed in This Round
- Read `docs/workflows/新项目开发工作流/commands/workflow_assets.py` and extracted `COMPATIBLE_TRELLIS_VERSION=0.5.17` — Layer: `source repo`
- Ran `trellis -v` and confirmed current runtime is `0.5.17` — Layer: `runtime command output`
- Read `workflow-audit` skill contract and repo specs for workflow installer / script / docs maintenance — Layer: `source repo`
- Created audit task context and seeded `prd.md` for this runtime audit — Layer: `source repo`
- Ran `/ops/softwares/python/bin/python3 ./.trellis/scripts/task.py current --source` in `/tmp/trellis-0.5.17-2` and reproduced `NameError: name 'os' is not defined` — Layer: `runtime command output`
- Read `/tmp/trellis-0.5.17-2/.trellis/scripts/task.py` and confirmed degraded fallback code uses `os` and `re` without imports — Layer: `generated target project` — Stage: `workflow-installed state after install-workflow.py`
- Read `/tmp/trellis-0.5.17-2/.opencode/plugins/inject-workflow-state.js` and confirmed `execFileSync(PYTHON_CMD, ...)` exists without `child_process` import / `PYTHON_CMD` definition, and breadcrumb call omits `task.extraLines` — Layer: `generated target project` — Stage: `workflow-installed state after install-workflow.py`
- Read `/tmp/trellis-0.5.17-2/.trellis/workflow-installed.json` and confirmed install record still marks critical runtime patches as complete despite the broken target files — Layer: `generated target project` — Stage: `workflow-installed state after install-workflow.py`
- Inspected source patchers and health checks under `docs/workflows/新项目开发工作流/commands/` to map generation and validation gaps — Layer: `source repo`
- Ran targeted pytest suites for installer, workflow-state, and upgrade-compat runtime-patch cases; all selected tests passed after fixes — Layer: `runtime command output`

## Confirmed Issues

### [P0] `task.py` degraded/current fallback patch is not self-contained
- Conclusion: the workflow installer injects degraded active-task fallback logic into target-project `task.py` but previously failed to guarantee `os` / `re` imports, causing real runtime crashes in `task.py current --source` and likely the degraded `start` path.
- Evidence Source:
  - Layer: `runtime command output`
  - Stage: `n/a`
  - Command: `/ops/softwares/python/bin/python3 ./.trellis/scripts/task.py current --source` in `/tmp/trellis-0.5.17-2`
  - Key result: `NameError: name 'os' is not defined`
  - Layer: `generated target project`
  - Stage: `workflow-installed state after install-workflow.py`
  - File: `/tmp/trellis-0.5.17-2/.trellis/scripts/task.py`
  - Layer: `source repo`
  - File: `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- Validation Action:
  - Reproduced the crash in the embedded target project.
  - Traced the generated code back to `patch_task_start_degraded_fallback()` and verified the injected block added new runtime dependencies without import repair.
- Impact Scope:
  - Target-project `.trellis/scripts/task.py`
  - Codex / Claude / OpenCode sessions that rely on degraded active-task recovery or `task.py current --source`
- Suggested Fix Direction:
  - Make the installer's `task.py` degraded patch self-contained by repairing imports whenever degraded fallback code is injected.

### [P0] OpenCode `inject-workflow-state` route patch can land as a half-applied runtime failure
- Conclusion: the JS patcher could produce or leave behind an OpenCode plugin that references `execFileSync(PYTHON_CMD, ...)` without declaring those dependencies, and also fail to forward `task.extraLines`, causing runtime degradation to `workflow-state.route_failed` while hiding reason/blocker context.
- Evidence Source:
  - Layer: `generated target project`
  - Stage: `workflow-installed state after install-workflow.py`
  - File: `/tmp/trellis-0.5.17-2/.opencode/plugins/inject-workflow-state.js`
  - Layer: `source repo`
  - Files: `docs/workflows/新项目开发工作流/commands/shell/patch-inject-workflow-state.py`, `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- Validation Action:
  - Compared the installed JS file against the source patcher contract.
  - Verified the pre-fix patcher only recognized one narrow structure and could skip dependency/call-site completion while still leaving route-centered code in place.
- Impact Scope:
  - Target-project `.opencode/plugins/inject-workflow-state.js`
  - OpenCode breadcrumb routing, blocker visibility, and route failure diagnostics
- Suggested Fix Direction:
  - Make the JS patcher repair imports/constants/call-sites independently of exact formatting, and treat missing runtime dependencies or `task.extraLines` forwarding as patch failure.

### [P0] Install-complete health checks had a structural blind spot for bad runtime patches
- Conclusion: the workflow's health checks previously accepted some broken runtime patch states because they relied on marker presence and Python compile checks, without equivalent JS runtime-contract validation or `task.py` degraded import checks; this allowed `workflow-installed.json` to report success while runtime behavior was already broken.
- Evidence Source:
  - Layer: `generated target project`
  - Stage: `workflow-installed state after install-workflow.py`
  - File: `/tmp/trellis-0.5.17-2/.trellis/workflow-installed.json`
  - Layer: `source repo`
  - Files: `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`, `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`
- Validation Action:
  - Confirmed the embedded target project had a success record despite runtime-broken `task.py` and OpenCode plugin files.
  - Verified source checks lacked JS dependency/forwarding checks and lacked `task.py` degraded import validation on the `upgrade-compat --check` path.
- Impact Scope:
  - Post-install self-check in `install-workflow.py`
  - `upgrade-compat.py --check`
  - `workflow-state.py route` embed-invalid detection
- Suggested Fix Direction:
  - Extend health checks to validate JS runtime patch contracts and `task.py` degraded import requirements, and wire those checks into both `workflow-state.py` and `upgrade-compat.py --check`.

### [P1] Existing regression coverage was too string-oriented to catch runtime-half patches
- Conclusion: the workflow already had tests, but they over-relied on marker/existence assertions and compile checks, which missed the exact class of half-applied JS patch and missing-import Python patch that caused the regressions.
- Evidence Source:
  - Layer: `source repo`
  - Files: `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`, `docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py`
- Validation Action:
  - Reviewed the existing tests and found no coverage for OpenCode plugin dependency completeness or `upgrade-compat --check` failing on incomplete runtime patch contracts.
  - Added targeted regression tests and observed them fail before the fixes were completed.
- Impact Scope:
  - Future workflow maintenance and regression prevention
- Suggested Fix Direction:
  - Keep targeted runtime-contract tests for `task.py`, OpenCode plugin patching, `workflow-state` embed-invalid detection, and `upgrade-compat --check`.

## Unconfirmed Items / False Alarms
- `Codex` residual `session-start.py` old READY/NOT READY logic exists in `/tmp/trellis-0.5.17-2/.codex/hooks/session-start.py`, but within the current workflow contract it remains an optional auxiliary surface rather than an active required carrier. This is maintenance debt and ambiguity, but not a confirmed primary runtime defect in the current managed-surface contract.
- “当前完全没有自动化测试” is a false alarm. The workflow already had substantial tests; the real issue was missing runtime-contract coverage for these specific half-patch states.

## Blocked Items (Blocked / Evidence Gap / Needs Clarification)
- None yet.

## Per-CLI Adaptation Conclusions

### Claude Code
- Official docs checked: not checked in this round; no dedicated official-doc retrieval tool was available in-session.
- Repo-local evidence checked: Claude runtime patch and upgrade-check paths in `install-workflow.py`, `upgrade-compat.py`, and generated target artifacts.
- Practical development-use evidence checked: `/tmp/trellis-0.5.17-2` generated target project.
- Agreement / discrepancy: no new Claude-specific runtime break was reproduced in this audit; the main confirmed defects were shared `task.py` and OpenCode plugin paths.
- Expected carrier model: Claude command + agent + hook surfaces managed by workflow installer.
- Does the current implementation match: mostly yes after the source fix set; shared `task.py` health checks now cover the broken degraded path that would also affect Claude/Codex fallback behavior.
- If not, what is wrong: no additional Claude-only defect confirmed in this run.

### OpenCode
- Official docs checked: not checked in this round; no dedicated official-doc retrieval tool was available in-session.
- Repo-local evidence checked: OpenCode plugin/session-utils patch flow in `install-workflow.py`, `patch-inject-workflow-state.py`, and `upgrade-compat.py`.
- Practical development-use evidence checked: `/tmp/trellis-0.5.17-2/.opencode/plugins/inject-workflow-state.js`.
- Agreement / discrepancy: repo-local contract and installed runtime diverged before the fix; the source workflow claimed route-centered breadcrumb behavior, but the generated target plugin lacked required dependencies and dropped `extraLines`.
- Expected carrier model: plugin-driven workflow state injection plus native command/agent carriers.
- Does the current implementation match: yes after the source fix set; patcher and checks now require the runtime contract to be complete.
- If not, what is wrong: pre-fix state could land a route-centered but non-runnable plugin and still pass install health checks.

### Codex
- Official docs checked: not checked in this round; no dedicated official-doc retrieval tool was available in-session.
- Repo-local evidence checked: Codex hook/skill carrier declarations and runtime patch requirements in `workflow_assets.py`, `install-workflow.py`, `upgrade-compat.py`.
- Practical development-use evidence checked: `/tmp/trellis-0.5.17-2` generated target project plus local test fixtures.
- Agreement / discrepancy: current managed-surface contract still intentionally does not require Codex `session-start.py`; however, shared `task.py` degraded fallback defects did affect Codex-installed targets and are now covered by the fix set.
- Expected carrier model: `.codex/config.toml` / `.codex/hooks.json` primary, `.agents/skills/` shared skill carrier, `.codex/agents/` native agent carrier.
- Does the current implementation match: yes for the current required carrier set after the shared `task.py` fix and stronger health checks.
- If not, what is wrong: residual optional `session-start.py` old logic remains a maintenance ambiguity, not a confirmed managed-surface break in this audit.

## Suggested Fix Directions
- Keep installer-applied runtime patches self-contained: if a patch injects new symbols or call paths, the patcher must also repair imports/constants and fail loudly when it cannot.
- Keep runtime-patch health checks symmetric across Python and JS carriers, and ensure `upgrade-compat --check` enforces the same runtime contract that `workflow-state.py route` uses for embed-invalid detection.
- Preserve the new targeted regression tests so future patch drift cannot silently regress back to marker-only success.

## Propagation Scope and Synchronized Update Range
- Likely layers: workflow helper scripts, patchers, installer self-checks, workflow-maintainer docs, workflow tests.
- Propagation risk note: any patch contract change must keep source repo declarations, generated target behavior, and regression tests aligned.

## Recommended Next Step
- Recommended action: `plain-language action`
- Trigger condition: confirmed defects have been fixed in the workflow source and targeted regression validation is green.
- Recommendation reason: if you want broader confidence, run the full workflow installer/upgrade test suite for `docs/workflows/新项目开发工作流/commands/` next; the high-risk regressions identified in this audit are already covered.
- Stronger alternatives not selected: a full end-to-end reinstall into a fresh non-Codex embed executor target project would add confidence, but the current session is constrained to Codex inline execution and the critical source-level regression paths are already verified locally.

## Stop Point and Pending Confirmations
- Auto-continue allowed: No
- User confirmation required for:
  - Final post-fix audit conclusion
  - Any remaining blocked runtime branch, if encountered
