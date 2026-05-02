# workflow-capability-audit Input Template

Natural-language invocation is supported. In first version, the effective workflow target is fixed.

```yaml
workflow_path: docs/workflows/新项目开发工作流/
current_cli: <optional; infer from runtime when omitted>
```

## Notes

- first-version support is limited to `docs/workflows/新项目开发工作流/`
- no initial `user_supplemented_capabilities` field
- omitted capability supplementation happens only after one discovery pass
- version gating happens before task creation or audit artifact creation
