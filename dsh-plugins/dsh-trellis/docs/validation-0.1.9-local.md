# Validation record — dsh-trellis 0.1.9 (npm rows compare installed CLIs)

- Date: 2026-10-23
- Version: `0.1.8` → `0.1.9`
- Round type: client + host feature. No settings-schema break; one new switch.

## Scope and origin

The two npm rows only reported "the official package changed" (a dist-tag
signature compared with the previous check). The requested semantics are an
installed-vs-upstream comparison:

- **DSH**: compare the local `dsh --version` with the published `latest` tag.
- **Trellis**: compare the local `trellis -v` with the channel that version is
  already on — `beta` for `x.y.z-beta.N`, `rc` for `x.y.z-rc.N`, otherwise
  `latest`.
- Automatically running both CLIs during scheduled checks is allowed.

## Design decisions

- **The Host owns the probe.** The browser cannot spawn processes. The handler
  gained `?source=local`, which runs two fixed command/argument pairs and returns
  `{local, errors}`. No request value selects a command.
- **Per-probe failure.** Missing binary (`ENOENT`), timeout (5 s), or unparsable
  output is reported per probe; it degrades that row to "local version unknown"
  and never rejects the check or hides the other source.
- **The comparison is additional, not a replacement.** The rows keep detecting
  publish changes. Dropping that would hide `next`/`beta` releases while the
  installed version equals `latest` — exactly the current DSH state
  (`latest = 0.2.1-rc.2`, `next = 0.2.1-rc.3`).
- **Ack applies to npm rows too.** Once a row shows "newer release", the same
  per-row skip action records the dist-tag signature plus the target version. The
  row stays quiet until the published target or signature moves. Each of the
  three rows keeps its own button; there is no "skip everything" control.
- **Ack never lowers the baseline**: a recorded target below the installed
  version does not resurrect releases the machine already superseded.
- **Explicit switch.** Automatic checks spawn two CLIs, so
  `versionCheckLocalProbe` (default on) can turn the probe off; the npm rows then
  fall back to change detection only.

## Changed files

| File | Change |
| --- | --- |
| `lib/local-version.js` | New. `parseVersionOutput`, `probeLocalVersions` (fixed probes, 5 s timeout, per-probe errors, `shell: true` on Windows for `.cmd`). |
| `lib/upstream.js` | `source=local` branch, injectable `probeImpl` / `probeTimeoutMs`. |
| `src/client/version-check.js` | `localRouteUrl`, `requestLocalVersions`, `trellisTagChannel`; npm rows report `localVersion` / `channel` / `targetVersion` / `signature` / `updateAvailable`; ack carries `signature`. |
| `src/client/VersionMonitor.jsx` | npm rows render local/target versions, the "newer release" badge, the probe-failure hint, and the per-row skip action. |
| `src/client/locales.js`, `src/client/form.js`, `src/client/TrellisSettingsCard.jsx`, `lib/config.js` | `versionCheckLocalProbe` switch and updated monitor copy. |
| `test/version-check.test.js`, `test/local-version.test.js`, `test/upstream.test.js` | Channel mapping, comparison matrix, probe failure, probe skipping, ack for npm, local route responses. |
| `README.md`, `LOCAL_CHANGES.md` | 0.1.9 documentation. |
| `package.json`, `lib/client.js`, `lib/client.js.map` | Version `0.1.9`; bundle rebuilt (`PLUGIN_VERSION = "0.1.9"`). |

## Verification

- `node --test test/version-check.test.js` → 19 tests, 19 pass.
- `node --test test/local-version.test.js test/upstream.test.js` → 22 tests, 22 pass.
- Full suite `pnpm test` → 368 tests, 364 pass, 0 fail, 4 skipped, 752 ms.
  (0.1.8 baseline: 355 / 351 / 0 / 4; the difference is the 13 new tests.)
- Real probe on this machine:
  `probeLocalVersions()` → `{"dsh":"0.2.1-rc.2","trellis":"0.7.0-beta.4"}`, no errors.
- Real route: `GET /dsh-trellis/version-check?source=local` → 200,
  `{"local":{"dsh":"0.2.1-rc.2","trellis":"0.7.0-beta.4"},"errors":[]}`.
- Build: `lib/client.js` 79.64 kB, map 33.59 kB, `PLUGIN_VERSION = "0.1.9"`.
- Upstream data used for the design check (registry, 2026-10-23):
  DSH `latest=0.2.1-rc.2`, `next=0.2.1-rc.3`; Trellis `latest=0.6.17`,
  `beta=0.7.0-beta.4`. With the chosen rules both npm rows are "up to date"
  locally, while the plugin row still flags the unmerged upstream `0.1.13`.

## Boundaries and not covered

- `dsh` is resolved through `PATH` and may not be the binary of the running
  host (desktop bundles its own CLI; this README already documents that check).
  The probe reports what `PATH` resolves, not the host process identity.
- Only `beta` and `rc` map to their channels; any other prerelease (`alpha`,
  unknown suffixes) compares against `latest` by design.
- A channel missing upstream shows "(tag not published)" and suppresses the
  comparison instead of falling back to another channel.
- The acknowledgement is per browser (`localStorage`); clearing site data or
  switching browsers/profiles requires one more click.
- No browser click-through: the settings page was not opened in this round; the
  React rendering and the notification path are covered by reading and unit
  tests only. The probe spawns real processes only when the switch is on and a
  package source is configured.
- No upstream merge was performed; 0.1.13 remains unmerged and unnecessary.
