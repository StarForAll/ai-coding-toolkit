# workflow-audit Input Template

Natural-language invocation is supported, but when you want to reduce ambiguity, prefer the following field template.

```yaml
workflow_path: docs/workflows/新项目开发工作流/
candidate_issues:
  - <candidate issue 1, optional>
  - <candidate issue 2, optional>
need_runtime_validation: auto
force_full_brainstorm: no
allow_minor_version_mismatch: no
current_cli: <optional; infer from runtime when omitted>
```

Comparison model used by the audit:

- `source repo`
- clean `trellis init` baseline in the generated target project
- workflow-installed state after `install-workflow.py`
- `runtime command output`

## Field Rules

- `workflow_path`
  - only supported value: `docs/workflows/新项目开发工作流/`
  - defaults to `docs/workflows/新项目开发工作流/` when omitted
  - natural-language requests such as "audit this workflow" must resolve to the same fixed workflow root
  - never infer the target from repo root, current working directory, active task, or sibling workflow directories
  - if multiple targets are supplied, `workflow-audit` must stop, explain that it supports only `docs/workflows/新项目开发工作流/`, and require the user to continue with that single supported root only
  - if the resolved path is not `docs/workflows/新项目开发工作流/`, `workflow-audit` must stop as `Blocked / Invalid Input`
  - if the supported root does not exist on disk, `workflow-audit` must stop as `Blocked / Invalid Input` and report that the repository checkout is missing the supported workflow root

- `candidate_issues`
  - optional
  - every item is treated as a hypothesis pending validation
  - nothing here is automatically treated as a confirmed defect
  - they do not switch execution paths; they only act as supplementary focus points within the normal evidence mainline and comparison model

- `need_runtime_validation`
  - default: `auto`
  - meanings:
    - `auto`: start with static evidence and escalate only when runtime validation is actually required
    - `yes`: after completing A/B/C, the audit MUST enter task-based runtime mode and proceed to Step D; when Step D reaches the formal embed boundary, the audit must stop and require a human terminal transcript for the remaining embed commands
    - `no`: stay on static/document-only audit unless the skill later proves that runtime validation is necessary; in that case it must output a Needs Confirmation block and wait for the user to decide whether to proceed

- `force_full_brainstorm`
  - default: `no`
  - `yes`: enter task-based mode (task + `trellis-brainstorm` mainline); does NOT by itself force runtime validation (Step D), which is judged separately based on Step 2 findings

- `allow_minor_version_mismatch`
  - default: `no`
  - `yes`: allow Step 0 to continue only when `COMPATIBLE_TRELLIS_VERSION` and `trellis -v` differ solely by `patch`, share the same `major.minor`, and neither side has a prerelease label
  - does **not** allow `rc` / `beta` to stable, prerelease-to-prerelease, or wider version drift
  - despite the name, this does **not** mean semver minor-number drift such as `0.5.x` vs `0.6.x`
  - equivalent explicit natural-language instructions may be treated the same way only when they unambiguously limit the bypass to that patch-only stable scope
  - if the field form is not used and the wording is ambiguous, treat it as `no`

- `current_cli`
  - optional
  - infer from runtime when possible
  - ask the user only when a CLI-sensitive path is reached and the CLI still cannot be determined safely
  - if provided, use only `claude`, `opencode`, or `codex`

### Natural-Language Equivalence Boundary

Accept as equivalent to `allow_minor_version_mismatch: yes`:

- "the versions only differ by patch; allow this audit run"
- "it's just `0.5.0` vs `0.5.5`; continue this run only"
- "skip this patch-only stable mismatch for this run"

Do **not** accept as equivalent:

- "skip the version check"
- "ignore version drift"
- "my minor version is different, allow it"
- any wording that does not explicitly constrain the bypass to a same-`major.minor` stable `patch` difference

## Notes

- Supported per-CLI audit scope is fixed to `Claude Code`, `OpenCode`, and `Codex`
- Supported workflow target scope is fixed to `docs/workflows/新项目开发工作流/`
- Comparison model inside the audit is `source repo` vs clean `trellis init` baseline vs workflow-installed state after `install-workflow.py` vs `runtime command output`
- Version preflight always runs first: compare `trellis -v` with `COMPATIBLE_TRELLIS_VERSION` in `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
- Only an explicit `allow_minor_version_mismatch: yes` can bypass a contract-defined patch-only stable mismatch; all prerelease-related or broader drift still stop as `Blocked / Version Drift`
- No dedicated AI-CLI takeover field exists for formal embed continuation
- Reaching the formal embed boundary always requires a human operator to run the remaining commands in an interactive system terminal
- Agent/sub-agent takeover is intentionally out of scope

## Full Example

```yaml
workflow_path: docs/workflows/新项目开发工作流/
candidate_issues:
  - Whether runtime validation really stops and requires a human terminal transcript before the formal embed step
  - Whether post-install verification guidance has drifted from the installer behavior
need_runtime_validation: auto
force_full_brainstorm: yes
allow_minor_version_mismatch: no
current_cli: codex
```
