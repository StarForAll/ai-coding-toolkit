# workflow-audit Input Template

Natural-language invocation is supported, but when you want to reduce ambiguity, prefer the following field template.

```yaml
workflow_path: docs/workflows/新项目开发工作流/
candidate_issues:
  - <candidate issue 1, optional>
  - <candidate issue 2, optional>
need_runtime_validation: auto
force_full_brainstorm: no
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
    - `yes`: after completing A/B/C, the audit MUST enter task-based runtime mode and proceed to Step D, executing within CLI-allowed boundaries (Codex must stop and hand off before formal embed)
    - `no`: stay on static/document-only audit unless the skill later proves that runtime validation is necessary; in that case it must output a Needs Confirmation block and wait for the user to decide whether to proceed

- `force_full_brainstorm`
  - default: `no`
  - `yes`: enter task-based mode (task + `trellis-brainstorm` mainline); does NOT by itself force runtime validation (Step D), which is judged separately based on Step 2 findings

- `current_cli`
  - optional
  - infer from runtime when possible
  - ask the user only when a CLI-sensitive path is reached and the CLI still cannot be determined safely
  - if provided, use only `claude`, `opencode`, or `codex`

## Notes

- Supported per-CLI audit scope is fixed to `Claude Code`, `OpenCode`, and `Codex`
- Supported workflow target scope is fixed to `docs/workflows/新项目开发工作流/`
- Comparison model inside the audit is `source repo` vs clean `trellis init` baseline vs workflow-installed state after `install-workflow.py` vs `runtime command output`
- Version preflight always runs first: compare `trellis -v` with `COMPATIBLE_TRELLIS_VERSION` in `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
- Any mismatch must stop the audit as `Blocked / Version Drift` and route the user to `workflow-capability-audit`
- No dedicated `preferred_handoff_cli` field
- Default handoff order is always `Claude Code -> OpenCode`
- A user may override the order only by stating the real environment constraint explicitly in natural language

## Full Example

```yaml
workflow_path: docs/workflows/新项目开发工作流/
candidate_issues:
  - Whether Codex really stops and hands off correctly before the formal embed step
  - Whether post-install verification guidance has drifted from the installer behavior
need_runtime_validation: auto
force_full_brainstorm: yes
current_cli: codex
```
