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

## Field Rules

- `workflow_path`
  - must be a single target
  - defaults to `docs/workflows/新项目开发工作流/` when omitted
  - if multiple targets are supplied, `workflow-audit` must stop and require one explicit target
  - if the resolved path does not exist on disk, `workflow-audit` must stop as `Blocked / Invalid Input`

- `candidate_issues`
  - optional
  - every item is treated as a hypothesis pending validation
  - nothing here is automatically treated as a confirmed defect
  - they do not switch execution paths; they only act as supplementary focus points within the normal evidence mainline

- `need_runtime_validation`
  - default: `auto`
  - meanings:
    - `auto`: start with static evidence and escalate only when runtime validation is actually required
    - `yes`: after completing A/B/C, the audit MUST enter task-based runtime mode and proceed to Step D, executing within CLI-allowed boundaries (Codex must stop and hand off before formal embed)
    - `no`: stay on static/document-only audit unless the skill later proves that runtime validation is necessary; in that case it must output a Needs Confirmation block and wait for the user to decide whether to proceed

- `force_full_brainstorm`
  - default: `no`
  - `yes`: enter task-based mode (task + `trellis:brainstorm` mainline); does NOT by itself force runtime validation (Step D), which is judged separately based on Step 2 findings

- `current_cli`
  - optional
  - infer from runtime when possible
  - ask the user only when a CLI-sensitive path is reached and the CLI still cannot be determined safely

## Notes

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
