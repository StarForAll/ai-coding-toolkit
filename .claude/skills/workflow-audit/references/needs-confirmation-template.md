# Needs Confirmation Template

When the escalation rule triggers — `need_runtime_validation: no` but A/B/C findings conclusively demonstrate that runtime validation is required — output this block and stop. Do NOT proceed to the normal Step D path or finalize the normal Step E report until the user responds.

```markdown
## Needs Confirmation — Runtime Validation Required

### What A/B/C Found
- <specific findings from static analysis that indicate runtime validation is necessary to confirm or refute>
- Layer: <source repo>

### Why Static Analysis Is Insufficient
- <why these findings cannot be conclusively resolved without executing Step D>
- <what specifically needs to be verified via /tmp, trellis init, or embed chain>

### Conflict
The user set `need_runtime_validation: no`, but the evidence above demonstrates that runtime validation (Step D) is required for a reliable audit conclusion.

### Decision Required
Choose one:
1. **Proceed with runtime validation** → the skill will enter task-based runtime mode and execute Step D
2. **Stay in current mode without D** → the findings above will be recorded as Blocked / Evidence Gap items, with a note that runtime validation is pending

Stop and wait for user response before continuing.
```
