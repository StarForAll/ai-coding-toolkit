# 0.1.2 local validation record

Date: 2026-10-22
Host: DSH 0.2.1-rc.2
Trellis: 0.7.0-beta.4
Plugin: 0.1.2 (local Strategy A copy)

## Scope

This round fixes the four findings confirmed by the 2026-10-22 review plus one
follow-up regression found in the first cut:

- **P2-1** — role detection read only the dispatch prompt; a role named only in
  the dispatch `description` silently lost the push and could bypass the inline
  guard.
- **P2-2** — the push preamble told the child not to re-read task artifacts
  while the parent prompt and the on-disk skill told it to load the role skill
  and pull context, so children loaded both twice.
- **P3-1** — "the task context … was prepared" appeared twice in one push.
- **P1-1** — README claimed the guard enforces the inline contract while the
  denial text handed the model a writable config switch.
- **Follow-up** — the first 0.1.2 cut matched roles as a substring of the
  label, so topical labels (`研究 trellis-agent-implement 插件的 README`,
  `about trellis-agent-check plugin docs`) were refused or pushed the wrong
  role contract. The shipped rule requires the whole label to be a role name.

README also stopped documenting the upstream fork's lineage, release history,
and npm-install flow; it describes this plugin only.

## Automated

```text
node --test "test/*.test.js"
tests 356 / pass 352 / fail 0 / skipped 4
```

The four skips are the pre-existing alpha-only integration cases
(`@deepseek-ai/dsh-working-directory` is not part of the dev baseline).

`node --test test/client-bundle.test.js` passes; `pnpm run build:client`
rebuilt `lib/client.js` and `lib/client.js.map`, `PLUGIN_VERSION` is `0.1.2`.

Coverage added for:

- whole-label role matching (`roleFromLabel`): exact names, wrapping
  backticks/quotes, case folding, trailing punctuation, and topical mentions;
- guard: description-only role still denied in inline and task-less dispatches,
  topical description allowed in both modes;
- push: descriptor-label-only push; topical label stays silent; inlined skill
  must not be reloaded; one prepared statement; fallback asks for the load;
- identity projection: real `sessionProjections` fold, fork-inherited
  descriptor ignored, late registration, legacy registry shape, missing-registry
  degradation;
- real AgentLoop + Session integration: label-only push and topical silence.

## Real DSH E2E

All runs used an isolated copy profile (`file:` pointing at this checkout) and
the scripted local adapter; the user `web`/`trellis-headless` profiles were not
modified. The real `subagent` tool, `dsh-subagent` runtime, child sessions, and
`subagent/descriptor` events were exercised; only the model response was
scripted.

| Scenario | Result | Evidence |
| --- | --- | --- |
| auto mode, `description = trellis-agent-implement`, `Active task:` prelude, no role in prompt | dispatch succeeded; child descriptor label = role; push before first request with role skill + curated context; prepared statement ×1; `## Task Context` ×1 | `~/.dsh/sessions/--tmp-dsh-trellis-fix-auto-proj--/session-f35ebb81…`, child `d14ff346…` |
| auto mode, generic `description` | child received no push | child `e2489674…` |
| auto mode, `description = trellis-agent-research`, no task | dispatch allowed; parent received the research notice | root session with `<trellis-dispatch-guard>` |
| auto mode, `description = trellis-agent-implement`, no task | fail-closed `no readable active task` | `session-e40564cd…` |
| inline mode, `description = trellis-agent-implement` | denied with "user's decision … Do not edit `.trellis/config.yaml` … not a security boundary"; no child session | `--tmp-dsh-trellis-fix-inline-proj--/session-1b52afd2…` |
| auto mode, topical `description = 研究 trellis-agent-implement 插件的 README`, with/without prelude | allowed; child stayed generic and received no push | children `36727ac4…`, `885441b4…` |
| inline mode, topical `description = about trellis-agent-check plugin docs` | allowed; child stayed generic, no push | child `e514d4ff…` |
| auto mode, exact label `` `Trellis-Agent-Check` `` (backticks + case) | child received the Check push; prepared statement ×1 | child `f2c94606…` |

The session directory names above live under `~/.dsh/sessions/` and can be
deleted; the temporary profiles were removed after the runs.

## Boundaries

- No external LLM was used. The plugin's behavior under a given dispatch
  request is deterministic; model compliance with the push instructions is not
  claimed.
- The prompt keeps substring role matching because it is the Trellis
  instruction channel; only the display label is restricted to whole names.
- Old-host compatibility (`test:compat` matrix) was not re-run on this machine
  (only `0.2.1-rc.2` is installed); the `0.2.0-rc.1` dev baseline passes the
  full suite and the legacy projection branch has unit coverage.
- The configurable "source repository" lane of version monitoring still exists
  in code and the settings page; README no longer prints its address.
