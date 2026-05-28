## Required Permissions

- `read`: YES - must inspect user-provided briefs, playtest notes, review
  extracts, design notes, screenshots descriptions, or existing analysis files.
- `write`: OPTIONAL - useful when the target project expects the agent to write
  review reports, player-feedback memos, or improvement backlog notes.
- `edit`: OPTIONAL - useful when updating existing analysis documents or
  feedback summaries.
- `glob`: YES - useful for finding local playtest or feedback materials.
- `grep`: YES - useful for searching recurring player complaints, monetization
  terms, device names, crash notes, or competitor references in local files.
- `bash`: OPTIONAL - useful for lightweight local inspection or formatting, but
  not required for ordinary chat-only analysis.
- `websearch`: YES when current external facts matter - required for app store
  pages, recent public reviews, current competitor behavior, official notices,
  probability disclosures, policy changes, and live-ops events.
- `webfetch`: YES when current external facts matter - required to inspect
  primary pages directly instead of relying on search snippets.

## Recommended Permission Posture

- Prefer read-only plus web access for pure review tasks.
- Allow workspace write/edit only when the target project wants persistent
  research notes or report files.
- Keep bash gated or limited to safe inspection commands unless the target
  project explicitly trusts the agent with broader automation.
- Do not require live web access for analysis that is explicitly limited to
  user-provided playtest notes; in that case, mark public/current facts as
  `[Evidence Gap]`.

## Forbidden Operations

- destructive bulk deletion
- git history rewriting
- publishing app store replies, social posts, or public announcements without
  explicit user approval
- modifying production game configuration, live-ops events, pricing, or payment
  settings
- fabricating app store ratings, public review trends, competitor mechanics,
  gacha probabilities, retention metrics, revenue data, or legal conclusions
- presenting unverified public facts as current evidence
- collecting or exposing private player data

## Evidence Boundary Rule

If live verification tools are fully or partially unavailable, the agent must:

1. say which evidence path is unavailable
2. label the gap explicitly as `[Evidence Gap]`
3. continue only with stable, clearly bounded assumptions or user-provided facts
4. avoid upgrading partial evidence into a full current-market or competitor
   claim

## Mapping Reminder

When adapting this source asset:

- Claude Code usually maps capability through `tools`, optional
  `permissionMode`, and project/session permissions.
- OpenCode should prefer `permission`, not legacy `tools`; `permission.edit`
  covers write/edit/patch-style file mutation.
- Codex should express file mutation scope through `sandbox_mode`; live web
  behavior depends on the target session's actual Web or MCP capability, not on
  a custom standalone agent key.
