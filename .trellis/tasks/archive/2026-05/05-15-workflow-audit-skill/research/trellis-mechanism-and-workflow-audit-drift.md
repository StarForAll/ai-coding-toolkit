# Trellis Mechanism and workflow-audit Drift Notes

## Scope

This note records the evidence used to repair the repo-local `workflow-audit`
skill without guessing.

## Repository-level Trellis Mechanism

### 1. `.trellis/` is the runtime truth layer

Evidence:

- `.trellis/workflow.md`
- `.trellis/scripts/task.py`
- `.trellis/scripts/get_context.py`
- `.trellis/config.yaml`

Findings:

- Task state is session-scoped and resolves through `.trellis/.runtime/sessions/`,
  not through a repo-global `.trellis/.current-task`.
- Workflow breadcrumb bodies are parsed from `.trellis/workflow.md`; hook/plugin
  code reads, but does not own, those state instructions.
- Codex dispatch defaults to inline in this repository, so the main Codex session
  performs implementation directly and must not treat sub-agents as the normal path.

### 2. Hidden platform directories are carrier layers, not runtime truth

Evidence:

- `.claude/settings.json`
- `.opencode/plugins/inject-workflow-state.js`
- `.codex/config.toml`
- `.codex/hooks.json`
- `.agents/skills/`
- `.kiro/`
- `.qoder/`

Findings:

- `.claude/` uses hooks plus native agent/command/skill carriers.
- `.opencode/` uses plugins plus native agent/command/skill carriers.
- `.codex/` uses `AGENTS.md`, `config.toml`, `hooks.json`, and optional carriers;
  hooks remain trust-gated / approval-gated at runtime.
- `.agents/skills/` is a shared deployment layer in this source repository and
  also a workflow skill carrier in installed target projects.
- `.kiro/` and `.qoder/` exist in this repository, but `workflow-audit` does not
  include them in its current managed-surface contract.

### 3. Real current version context

Evidence:

- `trellis -v` -> `0.5.15`
- `docs/workflows/新项目开发工作流/commands/workflow_assets.py`

Findings:

- `COMPATIBLE_TRELLIS_VERSION` is `0.5.14`.
- Current environment therefore hits the skill's patch-only stable mismatch path
  unless the run explicitly allows it.
- This is important context for reviewing `workflow-audit`, but it does not by
  itself prove the skill contract is wrong.

## workflow-audit Skill Drift

### Source of truth

- `.trellis/spec/skills/workflow-audit.md` is the behavioral source of truth.
- `.agents/skills/workflow-audit/SKILL.md` and `.claude/skills/workflow-audit/SKILL.md`
  are executable repo-local entry surfaces.

### What is already aligned

- Fixed workflow root: `docs/workflows/新项目开发工作流/`
- Same-version maintenance scope
- Patch-only stable mismatch bypass contract
- Three-layer evidence model
- Codex formal embed handoff boundary
- Non-defect / negative-optimization guardrails
- Native CLI adaptation must combine official docs, repo-local evidence, and
  practical development-use evidence

### Confirmed drift to repair

The current executable skill surfaces are missing or under-expressing the
following repo-local maintainer contract sections already present in the spec:

1. `Remediation Splitting`
2. `Report Contracts`
3. `CLI and Handoff Rules`
4. `Post-audit Routing`
5. `Validation`
6. `Sync Rules`
7. `Related Files`

Impact:

- The main audit workflow is mostly intact, but maintainers reading only the
  executable skill surface do not receive the full repo-local implementation
  contract.
- This is a compatibility / maintainability drift, not a need to redesign the
  audit logic.

### Fix strategy

- Keep `.trellis/spec/skills/workflow-audit.md` unchanged as the source of truth.
- Patch `.agents/skills/workflow-audit/SKILL.md` to restore the missing
  maintainer-contract sections from the spec.
- Apply the same patch to `.claude/skills/workflow-audit/SKILL.md`.
- Avoid touching references/tests unless the repaired surface requires it.

## Verification Plan

Run:

- `./scripts/validate-skills.sh`
- `diff -u .agents/skills/workflow-audit/SKILL.md .claude/skills/workflow-audit/SKILL.md`
- `git diff --check`

Truthful completion rule:

- If these pass, the repair is structurally safe.
- If one fails, report the failure directly and stop short of claiming the skill
  is fully repaired.
