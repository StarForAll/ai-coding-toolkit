# 0.1.1 local validation record

Date: 2026-10-21
Host: DSH 0.2.1-rc.2
Trellis: 0.7.0-beta.4
Plugin: 0.1.1 (local Strategy A copy)

## Scope

This round fixes the audit findings P2-1..P2-4 and P3-1..P3-4/P3-6/P3-7. The
default `inline` dispatch mode is an intentional product choice and is not
changed. The reported UI failure `上游 fork This operation was aborted` is
handled as a version-check partial-result problem.

## Automated

```text
pnpm test
tests 340 / pass 336 / fail 0 / skipped 4
```

Coverage added for:

- flow-style `dsh` / `spec_injection` / `prompt_injection` / `context_injection`
  sections;
- zero-state-block and missing-workflow fallback; plain Git repositories stay
  silent;
- DSH command-reference normalization;
- pushed role-contract stripping for implement/check/research;
- research spec-tree context;
- version-check timeout/partial host result and client rendering input;
- read-only `dsh.dispatch_mode` write-failure cache;
- optional `trellis_wait` timeout.

`pnpm run build:client` rebuilt `lib/client.js` and `lib/client.js.map`;
`PLUGIN_VERSION` is `0.1.1`.

## Real DSH E2E

All runs used the isolated `trellis-audit` profile (symlinked to this source)
with the local mock LLM; the user `web` profile was not modified.

| Scenario | Result | Evidence |
| --- | --- | --- |
| broken workflow (zero blocks) | breadcrumb + bootstrap both present; generic fallback | `/tmp/trellis-dsh-parity-20261021/scenarios/s14b2-broken-workflow/` |
| plain Git repo without `.trellis` | 0 breadcrumbs / 0 bootstrap | `s14c-plain-git/` |
| flow-style inline | inline block + `<dsh-mode>`; implement dispatch denied | `s13e2-flow-inline/`, `s13f2-flow-guard/` |
| inline start hint | banner contains `--allow-empty-context` | `s13e2-flow-inline/requests.jsonl` |
| command ref normalization | body says `/trellis-finish-work`, not `/trellis:finish-work` | `s13e2-flow-inline/requests.jsonl` |
| research push | spec tree + search tips; no PRD, no empty-manifest notice | `s23b-research-spec-tree/` |
| implement push | no `MUST load context yourself` / `does NOT auto-inject`; `## Task Context` retained | `s21b-implement-contract/` |
| wait timeout | `state=timeout`, `outcome=unknown`, no false success | `s30b-wait-timeout/` |

## Version-check route

Real GitHub Atom lookup through the updated handler returned 200 with commit
and release. A hanging-feed unit test with a 10 ms timeout returns 200 with
`commit:null`, `release:null`, and `errors[0].message = "GitHub request timed
out after 10 ms"`; the raw `This operation was aborted` string is absent.

The running Web UI process still uses the previously installed bundle. To see
this in the UI, reinstall/update the profile dependency and restart DSH; the
current profile is an ssh git dependency snapshot, not a symlink.

## Not verified here

- Browser-level settings page and real slash-command dispatch (the Web process
  requires its launch-time auth URL; no token was copied into commands/logs).
- Real `/compact` / clear behavior and desktop notifications.
- A real second Trellis plugin conflict.
- Real-model adherence beyond the recorded model payloads.
