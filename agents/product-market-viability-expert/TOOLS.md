## Required Permissions

- `read`: YES — must inspect briefs, notes, specs, product context, and
  existing market materials
- `write`: YES — must create market-analysis notes, decision memos, and
  validation summaries when asked
- `edit`: YES — must update existing research or product-strategy artifacts
- `glob`: YES — must locate relevant local files quickly
- `grep`: YES — must search internal product evidence, feedback, and prior
  research
- `bash`: YES — useful for targeted inspection, export, or lightweight local
  evidence processing
- `websearch`: YES — required for latest market signals, competitor activity,
  pricing, trend checks, and current ecosystem changes
- `webfetch`: YES — required to inspect cited live sources and primary pages
  directly

## Recommended Permission Posture

- Prefer least privilege by default.
- If the target project only wants decision memos, file mutation permissions can
  be tighter.
- If the target project expects research artifacts to be written into the repo,
  allow workspace file changes but keep destructive actions gated.
- Live-web permissions are core to this agent's value. If the target environment
  does not provide them, expect frequent `[Evidence Gap]` outputs.

## Forbidden Operations

- destructive bulk deletion
- git history rewriting unless the user explicitly asks for it
- production deploys, billing changes, or irreversible environment changes
  without explicit approval
- fabricating citations, “latest” claims, search trends, pricing, or community
  sentiment
- presenting outdated competitive or market information as current
- presenting investment, legal, or compliance conclusions as authoritative

## Evidence Boundary Rule

If live verification tools are fully or partially unavailable, the agent must:

1. say which evidence path is unavailable
2. label the gap explicitly as `[Evidence Gap]`
3. continue only with stable, clearly bounded assumptions
4. avoid upgrading partial evidence into a full "current market" conclusion

## Mapping Reminder

When adapting this source asset:

- Claude Code usually maps capability through `tools` and optional
  `permissionMode`
- OpenCode should prefer `permission`, not legacy `tools`; note that
  `permission.edit` covers write/edit/patch style file modification as one
  merged capability
- Codex should express edit scope through `sandbox_mode`; live web behavior
  depends on the target session's actual Web or MCP capability, not on a custom
  standalone agent key
