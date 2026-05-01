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

- `candidate_issues`
  - optional
  - every item is treated as a hypothesis pending validation
  - nothing here is automatically treated as a confirmed defect

- `need_runtime_validation`
  - default: `auto`
  - meanings:
    - `auto`: start with static evidence and escalate only when runtime validation is actually required
    - `yes`: go directly down the runtime-validation path
    - `no`: stay on static/document-only audit unless the skill later proves that runtime validation is necessary; in that case it must explain the escalation and switch

- `force_full_brainstorm`
  - default: `no`
  - `yes`: bypass lightweight shortcuts and enter the full `brainstorm` mainline

- `current_cli`
  - optional
  - infer from runtime when possible
  - ask the user only when a CLI-sensitive path is reached and the CLI still cannot be determined safely

## Notes

- First version: no dedicated `preferred_handoff_cli` field
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
