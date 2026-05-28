# Workflow Finding Triage

## Scope

- Report: `/tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md`
- Temp project: `/tmp/trellis-0.5.17-2`
- Workflow version: `0.1.2803`
- Trellis version: `0.5.17`

This document records the user-requested per-finding judgment after the
ordinary repair flow stopped at the cross-task lineage gate. It is a
task-local analysis artifact only; no workflow source files were modified.

## Shared Contract Used For Judgment

- Codex shared workflow skills live under `.agents/skills/*/SKILL.md`.
- `.codex/skills/*/SKILL.md` is a secondary carrier only for Codex-specific or
  project-local extra skills.
- The current installed target has no Codex-specific workflow skill that must
  live under `.codex/skills/`.
- Uppercase `SKILL.md` is the repository and installed workflow skill-file
  convention.
- `.codex/agents/*.toml` may remain as a disabled compatibility carrier, but
  the embedded workflow explicitly forbids agent/subagent dispatch.
- `parallel` is intentionally removed from active command/skill surfaces.

## Findings

### WS-001: Missing Codex skills directory content

**Judgment**: false problem / ignored.

**Reason**: `.codex/skills/` being empty is expected. The source Codex README
defines `.agents/skills/*/SKILL.md` as the shared workflow primary carrier and
`.codex/skills/*/SKILL.md` as secondary-only. The installed target contains
`trellis-start`, `trellis-continue`, and `trellis-finish-work` under
`.agents/skills/`, and source integrity code checks `patched_codex_skills`
against `.agents/skills`, not `.codex/skills`.

**No repair needed**: the report misinterprets the carrier boundary.

### WS-002: Skill file naming case inconsistency

**Judgment**: false problem / ignored.

**Reason**: uppercase `SKILL.md` is intentional in this repository and in the
installed workflow. The repo-local skill spec lists `SKILL.md` as the required
skill definition file, source platform docs reference `.agents/skills/*/SKILL.md`,
and the temp project contains all installed skill definitions in that form.
No lowercase `skill.md` requirement is part of the current workflow contract.

**No repair needed**: the report assumes the wrong filename convention.

### WS-003: Retained Codex agent configs despite explicit disable

**Judgment**: false problem / ignored under the disabled-carrier rule.

**Reason**: `.codex/agents/*.toml` are retained compatibility/subagent carriers.
The installed `AGENTS.md` and `.trellis/workflow.md` explicitly forbid
`trellis-research`, `trellis-implement`, `trellis-check`, and any other
agent/subagent dispatch. The installed `.codex/config.toml` also sets
`features.multi_agent_v2.enabled = false`. No checked installed surface routes
users into those agents as an allowed workflow path.

**No repair needed**: carrier presence alone is not a defect when the carrier is
explicitly disabled and no active surface contradicts that rule.

### WS-004: Stale cross-references to disabled agent/subagent paths

**Judgment**: false problem / ignored.

**Reason**: the report conflates valid Codex skill references with disabled
agent/subagent references. `trellis-continue` and `trellis-finish-work` are valid
Codex skill entries under `.agents/skills/`. References to
`trellis-research` / `trellis-implement` / `trellis-check` appear in a
"do not dispatch" context, which is the correct disabled-carrier contract.
The workflow-docs re-entry card points to `continue` / `trellis-continue`, which
is an active implementation re-entry surface rather than a disabled agent path.

**No repair needed**: the installed references are consistent with the current
main-session-only workflow contract.

### WS-005: Disabled command `parallel` has no verification artifact

**Judgment**: false problem / ignored.

**Reason**: active absence is the intended result for `parallel`. The install
record lists `disabled_commands: ["parallel"]`, `AGENTS.md` states that
parallel/worktree dispatch is disabled, and the installer removes existing
Codex `parallel` skills instead of leaving an invalid placeholder `SKILL.md`.
Source still contains `parallel-disabled.md` as the disabled-command template,
but the embedded active command/skill surface should not expose `parallel`.

**No repair needed**: no active `parallel` file is expected after disable.

### WS-006: Unclear whether uppercase `SKILL.md` is intentional

**Judgment**: evidence gap closed as false problem / ignored.

**Reason**: WS-006 repeats the same filename assumption as WS-002. Source specs,
platform docs, installer code, tests, and the installed temp project consistently
use uppercase `SKILL.md`. There is no evidence that lowercase `skill.md` is
required for this workflow's supported Claude Code / OpenCode / Codex surfaces.

**No repair needed**: the observed uppercase convention is intentional.

## Overall Conclusion

All six findings should be treated as non-repair findings for the current
workflow source:

| Finding | Final judgment |
|---------|----------------|
| WS-001 | false problem / ignored |
| WS-002 | false problem / ignored |
| WS-003 | expected disabled carrier / ignored |
| WS-004 | false problem / ignored |
| WS-005 | expected disabled command absence / ignored |
| WS-006 | evidence gap closed as false problem / ignored |

The recurring issue is scan-side classification quality: the report should not
classify these observations as confirmed workflow-source defects unless it can
show an active installed surface that contradicts the documented carrier
contract.
