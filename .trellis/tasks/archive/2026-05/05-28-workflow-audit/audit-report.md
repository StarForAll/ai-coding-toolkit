# workflow-audit: 新项目开发工作流

## Audit Target and Boundary
- Workflow Root: `docs/workflows/新项目开发工作流/`
- Resolved Workflow Root Rule: always `docs/workflows/新项目开发工作流/`
- Compatible Anchor Version: `0.5.17`
- Current Trellis Version: `0.5.17`
- Version Gate: `passed`
- Bypass Detail: `none`
- Audit Scope: `task-based runtime evidence already available from the current same-version temp project; no fresh formal embed executed in this audit turn`
- Current CLI: `codex`
- Candidate Issues:
  - repeated repair-lineage non-convergence on the same `/tmp/trellis-0.5.17-2`
    report lineage
  - possible runtime-carrier contract blind spots around route breadcrumbs,
    subagent strong-gate enforcement, and integrity verification
- Generated Target Project Root: `/tmp/trellis-0.5.17-2`
- Comparison Model: `source repo` vs `generated target project` baseline
  (`trellis init`) vs `generated target project` workflow-installed state
  (`install-workflow.py`) vs `runtime command output`

## Evidence-Gathering Actions Executed in This Round
- Read `.trellis/spec/skills/workflow-audit.md`, the behavioral source of
  truth for the maintainer skill — Layer: `source repo`
- Read `.agents/skills/workflow-audit/SKILL.md` and confirmed it still routes
  conflicts back to the repo-local spec — Layer: `source repo`
- Diffed `.agents/skills/workflow-audit/SKILL.md` against
  `.claude/skills/workflow-audit/SKILL.md`; no deployed-copy drift found —
  Layer: `source repo`
- Read `docs/workflows/新项目开发工作流/commands/workflow_assets.py` and ran
  `trellis -v`; both resolve to `0.5.17` — Layer: `source repo` +
  `runtime command output`
- Read the current same-version scan report
  `/tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md` — Layer:
  `generated target project` — Stage: `workflow-installed state after install-workflow.py`
- Read current source contracts:
  `CLI原生适配边界矩阵.md`,
  `装后隐藏目录与托管边界核对清单.md`,
  `工作流嵌入执行规范.md` — Layer: `source repo`
- Read current source patch and integrity scripts:
  `commands/shell/patch-inject-workflow-state.py`,
  `commands/shell/patch-opencode-inject-subagent-context.py`,
  `commands/shell/embed_integrity.py` — Layer: `source repo`
- Read current source tests and closure artifacts:
  `commands/test_workflow_installers.py`,
  `commands/shell/test_patch_helpers.py`,
  `commands/shell/test_workflow_state.py`,
  and the latest v4 `closure-round-1.md` files from 2026-05-27 — Layer:
  `source repo`
- Read installed runtime carriers under `/tmp/trellis-0.5.17-2/`:
  `.claude/hooks/inject-workflow-state.py`,
  `.codex/hooks/inject-workflow-state.py`,
  `.opencode/plugins/inject-workflow-state.js`,
  `.opencode/plugins/inject-subagent-context.js`,
  `.claude/hooks/inject-subagent-context.py` — Layer:
  `generated target project` — Stage: `workflow-installed state after install-workflow.py`
- Executed `python3 .trellis/scripts/workflow/embed_integrity.py` inside
  `/tmp/trellis-0.5.17-2`; it returned success with no invalid-state output
  even though the same temp project still exhibits the OpenCode blocked-path
  contradiction — Layer: `runtime command output`
- Checked the latest official docs available for the CLI adaptation surfaces in
  scope:
  Claude Code hooks reference, OpenCode plugins documentation, and official
  Codex AGENTS/config docs — Layer: `runtime command output` backed by official
  web documentation

## Confirmed Issues

### [P1] OpenCode strong-gate still allows Task-based subagent execution on a supported managed surface
- Conclusion: the current workflow source still patches OpenCode into a
  prompt-rewrite-only blocked path instead of an execution-deny path, so the
  embedded main-session-only contract is not actually enforced on OpenCode.
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - `docs/workflows/新项目开发工作流/commands/shell/patch-opencode-inject-subagent-context.py`
    inserts `args.prompt = buildBlockedSubagentPrompt(...)` and returns from
    the hook branch, but it does not throw, deny, or cancel the Task call.
  - `docs/workflows/新项目开发工作流/commands/shell/test_patch_helpers.py`
    `test_patch_opencode_inject_subagent_context_adds_block_feedback` asserts
    prompt rewrite and `return false`, but does not assert a hard execution
    stop.
  - Layer: `generated target project`
  - Stage: `workflow-installed state after install-workflow.py`
  - `/tmp/trellis-0.5.17-2/.opencode/plugins/inject-subagent-context.js`
    still contains the same prompt rewrite path and keeps runnable agent
    carriers under `.opencode/agents/trellis-implement.md`,
    `.opencode/agents/trellis-check.md`, and `.opencode/agents/trellis-research.md`.
  - Layer: `runtime command output`
  - Stage: `n/a`
  - Official OpenCode plugins docs show that `tool.execute.before` hooks can
    stop execution by throwing an error, for example the `.env protection`
    sample throws `new Error("Do not read .env files")`.
- Validation Action:
  - Compared the source patch helper against the installed temp-project plugin.
  - Compared the OpenCode blocked-path design with the official OpenCode plugin
    behavior model.
  - Cross-checked the result against the current scan report WS-002.
- Impact Scope:
  - `docs/workflows/新项目开发工作流/commands/shell/patch-opencode-inject-subagent-context.py`
  - installed OpenCode plugin carrier
  - OpenCode task/subagent strong-gate behavior on embedded workflow targets
- Suggested Fix Direction:
  - Change the OpenCode blocked path from prompt-only feedback to a true Task
    execution stop, or remove/disable the runnable OpenCode agent surface when
    the embedded workflow declares main-session-only execution.

### [P1] Closure verification is blind to the runtime stop semantics that keep re-triggering this repair family
- Conclusion: the recent v4 repair closure rounds can report `clean` while the
  same runtime-carrier family remains behaviorally broken, because they
  validate patch fragments and installer drift but do not exercise the actual
  route-failure breadcrumb reachability or OpenCode blocked-dispatch stop
  semantics.
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - `05-27-workflow-repair-2026-05-27-trellis-brainstorm-subagent-drift/closure-round-1.md`
    validates brainstorm carrier rewrites only.
  - `05-27-workflow-repair-2026-05-27-create-pr-reference/closure-round-1.md`
    runs `test_patch_opencode_inject_subagent_context_adds_block_feedback` and
    installer checks, but not a Task-deny runtime assertion.
  - `05-27-workflow-repair-2026-05-27-codex-start-routing/closure-round-1.md`
    validates Codex/Claude entry text and Claude deny behavior, but not the
    OpenCode execution stop condition or dotted breadcrumb-key reachability.
  - `05-27-workflow-repair-2026-05-27-break-loop-doc-drift/closure-round-1.md`
    runs install/merge/check flows that pass clean without probing the same
    runtime family now reported by the scan.
  - `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
    asserts `workflow-state.route_failed` string presence, but not whether the
    carrier tag parser can ever load that breadcrumb.
  - Layer: `generated target project`
  - Stage: `workflow-installed state after install-workflow.py`
  - The current `/tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md` still reports
    WS-001/WS-002/WS-003 after those latest clean closure rounds.
- Validation Action:
  - Compared the scenario commands listed in the latest v4 closure artifacts
    against the current same-lineage scan findings.
  - Inspected the relevant source tests to see what they actually assert.
- Impact Scope:
  - workflow-repair closure confidence
  - regression coverage for route-helper and OpenCode subagent strong-gate
    behavior
  - future scan/repair convergence on the same lineage
- Suggested Fix Direction:
  - Add closure assertions that execute the real carrier parsing and blocked
    dispatch paths, not just marker/text presence.
  - Treat route-failure breadcrumb reachability and OpenCode Task cancellation
    semantics as first-class closure contracts.

### [P2] `workflow-state.route_failed` is emitted as a status key that the installed hook parsers cannot ever load
- Conclusion: the workflow source introduced a dotted breadcrumb key
  `workflow-state.route_failed`, but the installed breadcrumb tag parsers still
  only accept `[A-Za-z0-9_-]+`, making the dedicated fallback breadcrumb
  unreachable across all managed hook carriers.
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md`
    defines `[workflow-state:workflow-state.route_failed]`.
  - `docs/workflows/新项目开发工作流/commands/shell/patch-inject-workflow-state.py`
    emits `status = "workflow-state.route_failed"` in both Python and JS route
    fallback branches.
  - The same patch helper does not patch the breadcrumb tag regex to accept `.`
    in status names.
  - `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
    only checks that the string `workflow-state.route_failed` appears in the
    installed carriers.
  - Layer: `generated target project`
  - Stage: `workflow-installed state after install-workflow.py`
  - `/tmp/trellis-0.5.17-2/.claude/hooks/inject-workflow-state.py`,
    `/tmp/trellis-0.5.17-2/.codex/hooks/inject-workflow-state.py`, and
    `/tmp/trellis-0.5.17-2/.opencode/plugins/inject-workflow-state.js` all use
    tag parsers restricted to `[A-Za-z0-9_-]+`.
- Validation Action:
  - Compared the source workflow breadcrumb block and patch helper output keys
    against the installed hook parser regexes in the temp project.
  - Cross-checked the mismatch against scan report WS-001.
- Impact Scope:
  - dotted route-failure breadcrumb key across Claude Code, OpenCode, and
    Codex installed carriers
  - route-helper failure UX and diagnosis path
- Suggested Fix Direction:
  - Either normalize action names back to the allowed tag alphabet or expand
    every managed parser and its tests to accept the dotted key consistently.

### [P2] `embed_integrity.py` validates the OpenCode subagent gate by text fragments only, so a broken runtime stop still passes as healthy
- Conclusion: the integrity gate treats the OpenCode subagent strong-gate as
  healthy when a handful of patch fragments exist, even if the runtime still
  permits the Task call to proceed after the blocked branch.
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - `docs/workflows/新项目开发工作流/commands/shell/embed_integrity.py`
    checks the OpenCode subagent gate via required string fragments such as
    `shouldAllowTaskInjection`, `loadRouteData`, and
    `Strong-gate blocked this subagent dispatch.`
  - The same integrity module has a stronger Claude branch that checks deny
    output fragments such as `"permissionDecision": "deny"` and
    `"permission": "deny"`, but no analogous hard-stop proof for OpenCode.
  - Layer: `runtime command output`
  - Stage: `workflow-installed state after install-workflow.py`
  - Running `python3 .trellis/scripts/workflow/embed_integrity.py` inside
    `/tmp/trellis-0.5.17-2` succeeded with no invalid-state output even though
    WS-002 still holds on the same temp project.
- Validation Action:
  - Inspected the integrity contract in source code.
  - Executed the installed integrity checker in the current temp project.
  - Compared the pass result against the current scan report WS-002/WS-003.
- Impact Scope:
  - route integrity gate
  - upgrade/install health signal for OpenCode runtime carriers
  - any future closure logic that trusts `embed_integrity.py` as a hard gate
- Suggested Fix Direction:
  - Strengthen the OpenCode integrity contract so it proves an actual execution
    stop condition, not just the presence of helper fragments.

## Unconfirmed Items / False Alarms
- `workflow-audit` itself is unusable in the current repo state -> false alarm.
  Same-version gate passes, and no skill-surface drift blocks the audit entry.
- `workflow-audit` must stop immediately only because we are in Codex -> false
  alarm. Codex can perform the static main-session portion of this audit; the
  hard boundary applies when a fresh formal embed execution would be required.

## Blocked Items (Blocked / Evidence Gap / Needs Clarification)
- Fresh same-run formal embed reproduction under Codex
  - Type: `Needs Clarification`
  - Cause: a fresh formal embed execution remains subject to the Codex handoff
    contract in `workflow-audit` and `工作流嵌入执行规范.md`
  - Impact: if the user wants this audit run to regenerate a brand-new `/tmp`
    baseline from scratch, the formal install step must be handed off to a main
    interactive Claude Code or OpenCode session
  - What is needed to continue: explicit decision whether the current evidence
    is enough for repair planning, or whether the user wants a fresh handoff
    reproduction run

## Per-CLI Adaptation Conclusions

### Claude Code
- Official docs checked:
  - Claude Code hooks reference (`PreToolUse` can block and return
    `permissionDecision: "deny"`)
- Repo-local evidence checked:
  - `CLI原生适配边界矩阵.md`
  - `commands/shell/patch-inject-workflow-state.py`
  - `commands/test_workflow_installers.py`
- Practical development-use evidence checked:
  - current temp-project installed Claude hook
  - current scan report
- Agreement / discrepancy:
  - agreement on hard-deny hook capability
  - discrepancy on the shared dotted breadcrumb key, which Claude’s installed
    parser still cannot load
- Expected carrier model:
  - main interactive session with deny-capable hook carriers
- Does the current implementation match:
  - `partially`
- If not, what is wrong:
  - shared `workflow-state.route_failed` parser mismatch remains

### OpenCode
- Official docs checked:
  - OpenCode plugins documentation (`tool.execute.before` hook and example
    using `throw new Error(...)` to stop a tool call)
- Repo-local evidence checked:
  - `CLI原生适配边界矩阵.md`
  - `commands/shell/patch-opencode-inject-subagent-context.py`
  - `commands/shell/embed_integrity.py`
  - `commands/shell/test_patch_helpers.py`
- Practical development-use evidence checked:
  - current temp-project installed OpenCode plugin and agents
  - current scan report
- Agreement / discrepancy:
  - clear discrepancy: the workflow contract says main-session-only, but the
    current OpenCode carrier still implements a prompt-only blocked path
- Expected carrier model:
  - main-session-only embedded workflow with a real blocked Task path
- Does the current implementation match:
  - `no`
- If not, what is wrong:
  - blocked branch does not actually deny/cancel Task execution
  - integrity gate does not prove the stop condition

### Codex
- Official docs checked:
  - official Codex config and AGENTS docs from the `openai/codex` repository
- Repo-local evidence checked:
  - `CLI原生适配边界矩阵.md`
  - `工作流嵌入执行规范.md`
  - `commands/shell/patch-inject-workflow-state.py`
- Practical development-use evidence checked:
  - current Codex session
  - current temp-project installed Codex hook
  - current scan report
- Agreement / discrepancy:
  - agreement on AGENTS/hooks main-session model and Codex handoff boundary for
    formal embed
  - discrepancy only on the shared dotted breadcrumb key parser mismatch
- Expected carrier model:
  - main interactive session using AGENTS + hooks, with no formal embed led by
    Codex
- Does the current implementation match:
  - `partially`
- If not, what is wrong:
  - shared `workflow-state.route_failed` parser mismatch remains

## Suggested Fix Directions
- Repair the dotted breadcrumb-key contract as one atomic change across source
  workflow docs, patch helpers, installed carrier parsers, and tests.
- Change the OpenCode blocked-dispatch path from prompt feedback to a true
  execution stop, then tighten `embed_integrity.py` so it fails when that stop
  condition is missing.
- Expand closure/runtime tests to assert behavioral stop conditions and
  breadcrumb reachability, not just string/marker presence.

## Propagation Scope and Synchronized Update Range
- Expected affected source layers if repair proceeds:
  - `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md`
  - `docs/workflows/新项目开发工作流/commands/shell/patch-inject-workflow-state.py`
  - `docs/workflows/新项目开发工作流/commands/shell/patch-opencode-inject-subagent-context.py`
  - `docs/workflows/新项目开发工作流/commands/shell/embed_integrity.py`
  - `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
  - `docs/workflows/新项目开发工作流/commands/shell/test_patch_helpers.py`
  - any workflow docs that restate the main-session-only or route-failure
    contract
- Propagation risk notes:
  - parser-alphabet changes can drift across Claude/OpenCode/Codex if not
    updated together
  - OpenCode blocked-path semantics and integrity-gate semantics must be
    updated in the same repair batch or the same loop can recur

## Recommended Next Step
- Recommended action: `plain-language action`
- Trigger condition: the audit already has enough evidence to justify a focused
  source-side repair plan for the four confirmed issues
- Recommendation reason: the current blocker is no longer “is workflow-audit
  suitable?” but “repair the verified route/subagent/integrity family and add
  the missing closure assertions”
- Stronger alternatives not selected:
  - a fresh same-run formal embed reproduction was not selected first because
    the current same-version temp project already provides consistent
    generated-target evidence, and the Codex handoff boundary would apply if a
    fresh formal install must be re-executed

## Stop Point and Pending Confirmations
- Auto-continue allowed: `No`
- User confirmation required for:
  - whether to continue directly into a repair plan for the four confirmed
    issues
  - whether to also require a fresh handoff-based embed reproduction before any
    source repair begins
