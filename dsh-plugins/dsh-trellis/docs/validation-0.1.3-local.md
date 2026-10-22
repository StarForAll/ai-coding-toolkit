# 0.1.3 local validation record

Date: 2026-10-22
Host: DSH 0.2.1-rc.2
Trellis: 0.7.0-beta.4
Plugin: 0.1.3 (local Strategy A copy)

## Scope

Follow-up to 0.1.2. The whole-label rule fixed topical false positives but
also dropped a real dispatch shape: DSH labels are free text, and a role with
an annotation (`trellis-agent-implement (audit round 3)`) is still a role
designation. 0.1.3 accepts a label that *starts* with the role name and
continues with an annotation, while a role mentioned inside prose stays
generic.

## Automated

```text
node --test "test/*.test.js"
tests 356 / pass 352 / fail 0 / skipped 4
```

`node --test test/client-bundle.test.js` passes; `pnpm run build:client`
rebuilt the bundle with `PLUGIN_VERSION = 0.1.3`.

Coverage added/updated:

- `roleFromLabel`: exact labels, annotated labels (`(audit round 3)`,
  `（第 3 轮）`, `: compare options`, `— round 3`, `- docs review`), plain-prose
  labels (`trellis-agent-check plugin docs`, `... task`), topical mentions,
  wrapping quotes/backticks, fullwidth punctuation, and near-miss names
  (`trellis-agent-researcher`, `trellis-agent-checkpoint`).
- Guard and push parse functions consume the same rule.

## Real DSH E2E

Runs use a temporary profile that installs the built package (`file:`), the
real `subagent` tool and subagent runtime; only the model response is scripted.

| Scenario | Result |
| --- | --- |
| `description = "trellis-agent-implement (audit round 3)"`, `Active task:` prelude | dispatch allowed; child receives the Implement role contract and curated context |
| `description = "研究 trellis-agent-implement 插件的 README"` | generic: no push, no guard decision |
| `description = "about trellis-agent-check plugin docs"` (inline) | allowed; child generic, no push |
| `description = "trellis-agent-implement"`, inline | denied with the user-decision wording |

## Boundaries

- No external LLM was used; model compliance is not claimed.
- A label that starts with the role name and continues with plain words
  (`trellis-agent-check plugin docs`) is intentionally generic: the separator
  must be punctuation/annotation, not an unseparated phrase.
- The prompt keeps substring role matching because it is the instruction
  channel (see the 0.1.2 record).
