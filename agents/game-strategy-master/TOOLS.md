## Required Permissions

- `read`: YES - must inspect user-provided briefs, strategy notes, playtest
  reports, analytics summaries, review extracts, design docs, screenshot
  descriptions, or existing strategy files.
- `write`: OPTIONAL - useful when the target project expects the agent to write
  strategy reports, roadmap memos, research notes, or improvement backlog files.
- `edit`: OPTIONAL - useful when updating existing strategy documents or
  feedback summaries.
- `glob`: YES - useful for finding local research, playtest, analytics, and
  strategy materials.
- `grep`: YES - useful for searching recurring complaints, metric names,
  monetization terms, feature names, device names, or competitor references in
  local files.
- `bash`: OPTIONAL - useful for lightweight local inspection, formatting, or
  processing structured evidence, but not required for chat-only analysis.
- `websearch`: YES when current external facts matter - required for app store
  pages, recent public reviews, current competitor behavior, official notices,
  probability disclosures, policy changes, live-ops events, and market signals.
- `webfetch`: YES when current external facts matter - required to inspect
  primary pages directly instead of relying on snippets.

## Recommended Permission Posture

- Prefer read-only plus web access for pure strategy analysis.
- Allow workspace write/edit only when the target project wants persistent
  strategy reports, research notes, or backlog files.
- Keep bash gated or limited to safe inspection commands unless the target
  project explicitly trusts the agent with broader automation.
- Do not require live web access for analysis explicitly limited to
  user-provided playtest notes, private strategy docs, or internal metrics; in
  that case, mark public/current facts as `[Evidence Gap]`.

## Forbidden Operations

- destructive bulk deletion
- git history rewriting
- publishing app store replies, social posts, announcements, patch notes, or
  public statements without explicit user approval
- modifying production game configuration, live-ops events, pricing, payment,
  probability, or reward settings
- fabricating app store ratings, public review trends, competitor mechanics,
  probability disclosures, policy claims, retention metrics, revenue data, or
  player sentiment
- presenting unverified public facts as current evidence
- presenting legal, compliance, publishing, investment, or financial conclusions
  as authoritative advice
- collecting, exposing, or re-identifying private player data

## Evidence Boundary Rule

If live verification tools are fully or partially unavailable, the agent must:

1. say which evidence path is unavailable
2. label the gap explicitly as `[Evidence Gap]`
3. continue only with stable, clearly bounded assumptions or user-provided facts
4. avoid upgrading partial evidence into a full current-market, competitor, or
   public-review claim

## Mapping Reminder

When adapting this source asset:

- Claude Code usually maps capability through `tools`, optional
  `permissionMode`, and project/session permissions.
- OpenCode should prefer `permission`, not legacy `tools`; `permission.edit`
  covers write/edit/patch-style file mutation.
- Codex should express file mutation scope through `sandbox_mode`; live web
  behavior depends on the target session's actual Web or MCP capability, not on
  a custom standalone agent key.
