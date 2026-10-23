# Validation record — dsh-trellis 0.1.8 (manual upstream-skip baseline)

- Date: 2026-10-23
- Version: `0.1.7` → `0.1.8`
- Round type: client-side feature. No Host code change, no settings-schema change.

## Scope and origin

The upstream plugin's last 15 days (2026-10-08 → 2026-10-23) contain three
commits: `b487c1d` (0.1.12 working directories, already absorbed locally),
`32706f7` (Windows test fixture, already absorbed) and `5108b7f` (0.1.13, which
changes no `lib/` or `src/` runtime code). Merging 0.1.13 is therefore
unnecessary — but the monitor kept showing its release as an update, because
`updateAvailable` compared the upstream tag with the compiled `PLUGIN_VERSION`
and the local carrier restarted its numbering at `0.1.0` (so local `0.1.8` can
never exceed upstream `0.1.13`).

This round adds a **manually set baseline**: a reviewed snapshot can be skipped
without merging, and the hints return only when upstream moves past it.

## Design decisions

- **Two independent hints stay independent.** `isNew` follows the stored commit
  sha (or dist-tag signature); `updateAvailable` follows the release tag. The
  acknowledgement records both and suppresses each on its own axis.
- **The acknowledgement outranks `PLUGIN_VERSION` only when present, and never
  lowers the baseline.** Without an ack record the previous comparison is
  unchanged; an ack older than the local version cannot resurrect releases this
  build already supersedes.
- **Prerelease ordering is finer for ack baselines.** `compareVersions` drops
  prerelease suffixes (deliberately conservative). Ack baselines use the new
  `compareReleaseTags`: `0.2.0` is newer than `0.2.0-rc.1`, while `0.2.0-rc.2`
  is not newer than `0.2.0`. `compareVersions` keeps its documented behaviour.
- **Browser state, not configuration.** The record lives in
  `localStorage` (`dsh-trellis:version-check:ack:plugin`) as
  `{sha, tag}`. The Host only proxies the two validated lookups and stores
  nothing, so `lib/upstream.js` is untouched.
- **No refetch after the click.** The row update written to component state is
  exactly what the next lookup recomputes from the stored snapshot
  (`sha` equal → `isNew: false`; tag not newer than itself →
  `updateAvailable: false`).

## Changed files

| File | Change |
| --- | --- |
| `src/client/version-check.js` | `ACK_PREFIX`, `readAck`, `writeAck`, `compareReleaseTags`, `isNewerReleaseTag`; plugin rows report `acknowledged` and `ack`, and compare a release against the acknowledged tag. |
| `src/client/VersionMonitor.jsx` | Per-row "跳过（不合并）" button, "已跳过" state, conditional hint line. |
| `src/client/locales.js` | `monitor.skip`, `monitor.acknowledged`, `monitor.skipHint` (zh/en). |
| `test/version-check.test.js` | Four new tests (see below). |
| `README.md` | 0.1.8 changelog; monitor bullet; current version. |
| `LOCAL_CHANGES.md` | 0.1.8 section. |
| `package.json`, `lib/client.js`, `lib/client.js.map` | Version `0.1.8`; bundle rebuilt with `pnpm run build:client` (`PLUGIN_VERSION = "0.1.8"`). |

## Verification

Targeted: `node --test test/version-check.test.js` → 13 tests, 13 pass, 0 fail.

New coverage:

1. Ack suppresses both hints on the same snapshot; a new commit re-opens only
   `isNew`, a later release re-opens `updateAvailable`.
2. Acked `v0.2.0-rc.1` with an unchanged commit still reports `v0.2.0` as newer.
3. Corrupt / empty / array / partial ack records read as "no acknowledgement"
   and never break the check.
4. `compareReleaseTags` ordering, including the equal-core prerelease cases, and
   `compareVersions` unchanged for `0.2.0` vs `0.2.0-rc.1`.
5. An ack older than the local version never lowers the baseline: superseded
   releases stay silent while a newer one is still flagged.

Full suite: `pnpm test` → 355 tests, 351 pass, 0 fail, 4 skipped (capability
skips on the development host), duration 711 ms. Baseline before this round was
350 tests / 346 pass / 0 fail / 4 skip; the difference is exactly the five new
tests.

Build: `pnpm run build:client` succeeded (`lib/client.js` 72.13 kB, map
30.54 kB); the compiled bundle contains the acknowledgement path and stamps
`0.1.8`.

## Boundaries and not covered

- No browser click-through this round: the settings page was not opened and the
  button was not exercised in a real UI. The unit tests cover the judgement, not
  the React rendering.
- The acknowledgement is per browser (`localStorage`). Clearing site data,
  switching browsers or switching profiles requires one more click; it is not
  written to `cordis.patch.yml` on purpose.
- The record has no undo action. A later commit or higher tag supersedes it
  naturally; a user who wants the old badge back can clear site data.
- The manual "检查" action already advanced the sha baseline before this round;
  the new part is the release baseline and the explicit UI affordance.
- No upstream merge was performed. 0.1.13 remains unmerged and unnecessary per
  the runtime diff above.
