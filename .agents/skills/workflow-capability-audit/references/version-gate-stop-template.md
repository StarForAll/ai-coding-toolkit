# Version Gate Stop Template

Use one unified template for all version-gate termination states.

```markdown
## Version Gate Stop

- Gate Result: `<equal-version-stop | older-version-block | missing-compatible-anchor | environment-error | version-parse-error>`
- Workflow Root: `docs/workflows/新项目开发工作流/`
- Current Trellis Version: `<value or unavailable>`
- Compatible Anchor: `<value or missing>`

### Why Execution Stops Here
- <reason>

### Task Creation
- Skipped: Yes
- Reason: version gate happens before task creation and audit artifact creation

### Next Action
- <what the user should do next>
```
