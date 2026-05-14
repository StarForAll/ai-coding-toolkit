# workflow-audit: 新项目开发工作流

## Audit Target and Boundary
- Workflow Root: `docs/workflows/新项目开发工作流/`
- Resolved Workflow Root Rule: always `docs/workflows/新项目开发工作流/`
- Compatible Anchor Version: `0.5.14`
- Current Trellis Version: `0.5.15`
- Version Gate: `bypassed`
- Bypass Detail: user-approved patch-only stable mismatch; run-local only; not compatibility approval
- Audit Scope: task-based runtime
- Current CLI: `codex`
- Candidate Issues:
  - 目标项目中的 `AGENTS.md` 是否与 workflow 产生冲突、分歧或漂移
  - 基于已有 `0.5.14` Trellis 样本，嵌入当前 workflow 后上述判断是否仍成立
- Generated Target Project Root: `/tmp/trellis-0.5.14-1`
- Comparison Model: `source repo` vs `generated target project` baseline (`trellis init`) vs `generated target project` workflow-installed state (`install-workflow.py`) vs `runtime command output`
- Runtime Note: This run follows a user-approved bounded sample path using an existing `0.5.14` target project. It is not the strict same-runtime Step D path that would require a fresh target initialized by the current local `trellis -v`.

## Evidence-Gathering Actions Executed in This Round
- Compared workflow anchor version in `workflow_assets.py` with current `trellis -v`; classified as user-approved patch-only mismatch — Layer: `source repo`
- Read installer, drift checker, uninstaller, boundary matrix, and hidden-directory contract with focus on `AGENTS.md` ownership and runtime checks — Layer: `source repo`
- Inspected `/tmp/trellis-0.5.14-1/AGENTS.md`; confirmed it currently contains only the Trellis managed block and no `workflow-nl-routing` block — Layer: `generated target project` — Stage: `baseline after trellis init`
- Checked `/tmp/trellis-0.5.14-1/.trellis/workflow-installed.json` and `/tmp/trellis-0.5.14-1/.trellis/workflow-embed-attempt.json`; both are absent — Layer: `generated target project` — Stage: `baseline after trellis init`
- Confirmed current baseline carrier surfaces under `/tmp/trellis-0.5.14-1` include `.claude/commands/trellis/continue.md`, `.claude/commands/trellis/finish-work.md`, and baseline `.agents/skills/trellis-*` skills — Layer: `generated target project` — Stage: `baseline after trellis init`
- Initialized Git and dual-push `origin` on `/tmp/trellis-0.5.14-1` so the sample satisfies installer preconditions without changing workflow-managed content — Layer: `generated target project` — Stage: `baseline after trellis init`
- Ran `detect-embed-state.py --json` against `/tmp/trellis-0.5.14-1`; result was `INITIAL_BASELINE_READY` with no blockers — Layer: `runtime command output`
- Ran `install-workflow.py --project-root /tmp/trellis-0.5.14-1 --dry-run`; preview shows the installer will write install records, patch `.trellis/workflow.md`, distribute commands/skills/scripts, and inject the `AGENTS.md` NL routing block — Layer: `runtime command output`

## Confirmed Issues
- No change-worthy `AGENTS.md` conflict, divergence, or drift issue is currently confirmed under the bounded `0.5.14` sample + dry-run evidence path.

## Unconfirmed Items / False Alarms
- “workflow 会整文件覆盖目标项目 `AGENTS.md`” -> false alarm
  - Evidence: source script only replaces/appends the marked `workflow-nl-routing` block; target sample currently keeps its standalone Trellis block; dry-run predicts only NL routing block injection
- “已有 `0.5.14` Trellis 样本本身就不能用于分析” -> false alarm for the user's bounded question
  - Evidence: after补齐最小 Git 前置条件，`detect-embed-state.py` directly reports `INITIAL_BASELINE_READY`
- “Claude 官方当前原生规则文件契约与 `AGENTS.md` 的关系” -> separate upstream compatibility question, not confirmed here as a target-project `AGENTS.md` install-time conflict in the bounded Trellis-sample judgment

## Blocked Items (Blocked / Evidence Gap / Needs Clarification)
- Formal embed step under current executor
  - Type: `Blocked`
  - Cause: current main executor is Codex; per `workflow-audit` contract, the audit must stop at the formal install boundary and hand off before executing non-dry-run embed
  - Impact: this run cannot yet prove the final post-install on-disk `AGENTS.md` content or the post-install `upgrade-compat.py --check` result from actual writes
  - What is needed to continue: hand off the formal install step to a main interactive Claude Code or OpenCode session, or accept that this run stops at dry-run evidence

## Per-CLI Adaptation Conclusions

### Claude Code
- Official docs checked: Claude Code `CLAUDE.md` documentation
- Repo-local evidence checked: workflow Claude README, CLI boundary matrix, installer routing block contract
- Practical development-use evidence checked: bounded `0.5.14` sample baseline + installer dry-run preview
- Agreement / discrepancy: for this bounded target-project AGENTS audit, no install-time conflict is visible; a separate upstream rule-carrier discrepancy remains outside this narrower judgment
- Expected carrier model: in this workflow's target-project contract, `AGENTS.md` carries the shared Trellis block and installer-added NL routing block; command/hook/agent carriers remain elsewhere
- Does the current implementation match: yes for the bounded AGENTS block judgment up to dry-run
- If not, what is wrong: actual formal install was not executed in this run, so only preview-level evidence is available

### OpenCode
- Official docs checked: OpenCode Rules / Skills
- Repo-local evidence checked: workflow OpenCode README, CLI boundary matrix
- Practical development-use evidence checked: bounded `0.5.14` sample baseline + installer dry-run preview
- Agreement / discrepancy: agrees
- Expected carrier model: `AGENTS.md` shared rules + `.opencode/commands/trellis/*` primary entry + `.agents/skills/` shared skill surface
- Does the current implementation match: yes up to dry-run
- If not, what is wrong: actual formal install was not executed in this run

### Codex
- Official docs checked: OpenAI Codex `AGENTS.md` guide and Hooks docs
- Repo-local evidence checked: workflow Codex README, `.codex/config.toml`, boundary matrix
- Practical development-use evidence checked: bounded `0.5.14` sample baseline + installer dry-run preview
- Agreement / discrepancy: agrees
- Expected carrier model: `AGENTS.md` shared rules + `.codex/` hooks/config + `.agents/skills/` shared skills
- Does the current implementation match: yes up to dry-run
- If not, what is wrong: actual formal install was not executed in this run

## Suggested Fix Directions
- If the user only wants a bounded answer to “当前 `0.5.14` 样本下，AGENTS.md 会不会被 workflow 搞冲突/漂移”, the current answer can stop here: no confirmed issue
- If the user wants proof from actual post-install files instead of dry-run projection, perform a formal handoff and complete one non-dry-run embed on the same sample

## Propagation Scope and Synchronized Update Range
- Installer / drift checker / uninstall scripts
- CLI boundary matrix and hidden-directory contract docs
- Claude / OpenCode / Codex platform READMEs
- Installer tests and runtime audit tests
- Propagation risk note: if AGENTS ownership semantics change, docs, installer behavior, drift-check behavior, and tests must be updated together

## Recommended Next Step
- Recommended action: plain-language action
- Trigger condition: the bounded `0.5.14` sample + dry-run path has already answered the user's core AGENTS conflict question at preview level
- Recommendation reason: no confirmed AGENTS conflict is visible; the only remaining gap is whether to collect actual post-install evidence
- Stronger alternatives not selected: a fresh current-version `/tmp` baseline was not used because the user explicitly requested staying on the existing `0.5.14` sample

## Stop Point and Pending Confirmations
- Auto-continue allowed: No
- User confirmation required for:
  - Whether dry-run-level evidence is sufficient for this audit conclusion
  - Whether to hand off the formal install step out of Codex to collect actual post-install evidence
