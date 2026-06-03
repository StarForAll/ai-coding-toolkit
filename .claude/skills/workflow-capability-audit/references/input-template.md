# workflow-capability-audit Input Template

Natural-language invocation is supported. In first version, the effective workflow target is fixed.

```yaml
workflow_path: docs/workflows/新项目开发工作流/
current_cli: <required once the run may continue past the version gate into full audit; infer from current runtime (claude|opencode|codex); optional for version-gate-only stops>
allow_equal_version_continue: <optional; true only when the user explicitly wants a same-version full audit>
continue_after_human_shell: <optional; true only when resuming an existing capability-audit task after the operator has manually executed the shell embed chain for B>
manual_shell_evidence:
  - <optional evidence bullet captured from the returned shell transcript>
```

## Notes

- first-version support is limited to `docs/workflows/新项目开发工作流/`
- no initial `user_supplemented_capabilities` field
- omitted capability supplementation happens only after one discovery pass
- version gating happens before task creation or audit artifact creation
- `current_cli` becomes mandatory before any task or fixture setup begins
- equal-version full audit requires the explicit override above; newer-version drift does not
- older-version drift aborts with a non-zero workflow-contract violation error, not a normal gate-result branch or full-audit path
- `continue_after_human_shell` requires an existing capability-audit `task_dir`; it reuses the same A/B fixtures and updates `capability-report.md`
