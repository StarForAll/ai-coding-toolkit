# workflow-capability-audit Input Template

Natural-language invocation is supported. In first version, the effective workflow target is fixed.

```yaml
workflow_path: docs/workflows/新项目开发工作流/
current_cli: <always pass; infer from current runtime (claude|opencode|codex); the script does not auto-detect>
allow_equal_version_continue: <optional; true only when the user explicitly wants a same-version full audit>
```

## Notes

- first-version support is limited to `docs/workflows/新项目开发工作流/`
- no initial `user_supplemented_capabilities` field
- omitted capability supplementation happens only after one discovery pass
- version gating happens before task creation or audit artifact creation
- equal-version full audit requires the explicit override above; newer-version drift does not
- older-version drift aborts with a non-zero workflow-contract violation error, not a normal gate-result branch or full-audit path
