# Validation record — dsh-trellis 0.1.7 (docs round)

- Date: 2026-10-23
- Version: `0.1.6` → `0.1.7`
- Round type: documentation + version re-stamp. **No runtime behaviour change**; no lib logic
  and no tests changed — the only file under `lib/` that differs from 0.1.6 is
  `lib/client.js`, whose `PLUGIN_VERSION` constant is re-stamped to `0.1.7` by
  `pnpm run build:client` (release bookkeeping required by the version scheme).

## Scope and origin

0.1.7 closes findings F1 and F2 from the installed-copy verification round
(task `.trellis/tasks/10-23-dsh-trellis-016-installed-verify`,
`research/verification-report.md` §5/§8; user-approved disposition: document
only).

- **F1 (P3, host limitation)** — `/trellis-*` commands execute only through the
  interactive command input surface (Web/TUI etc.). A headless plain-text prompt containing
  `/trellis-status` is an ordinary task for the model; its answer is
  model-improvised (the verification round observed one headless session
  claiming the plugin was not installed while it was actively injecting).
  Disposition: README note with shell equivalents.
- **F2 (P3, documented boundary)** — old `<dsh-mode>` banners in session
  history are not rewritten after a `dsh.dispatch_mode` change; a model may
  keep quoting the stale banner. Disposition: README guidance (avoid
  mid-session switches; prefer a new session, or tell the model the old banner
  is obsolete and the current config wins).

## Changed files

| File | Change |
| --- | --- |
| `README.md` | "headless 文本限制" note (F1, with shell equivalents); "避免同会话中途切换模式" note (F2); `inline_allow_dispatch` caveat (guard-only, banner unchanged); 0.1.7 changelog section; version line. |
| `.trellis/spec/platforms/dsh-workflow-behavior.md` | "Command routing surface" and "Mid-session mode switches" documented boundaries (repository-level spec). |
| `LOCAL_CHANGES.md` | 0.1.7 entry. |
| `package.json` | Version `0.1.7`. |
| `lib/client.js` | `PLUGIN_VERSION` re-stamp only (build output). |
| `docs/validation-0.1.7-local.md` | This record. |

## Verification

- Unit tests: **350 tests / 346 pass / 0 fail / 4 skip** (identical to the
  0.1.6 baseline; no behaviour changed).
- `git diff --name-only dsh-plugins/dsh-trellis/lib/` → `lib/client.js` only,
  and its diff is the single `PLUGIN_VERSION` line.
- README/LOCAL_CHANGES/package.json/validation record agree on `0.1.7`.

## Boundaries and not-done

- **No runtime fix**: F1 routing and F2 banner staleness still exist by
  design; the documents inform and give recovery paths, they do not change
  model behaviour automatically.
- **Installed copies are not updated**: the real web profile still runs
  0.1.6. This round has no runtime change, so reinstalling only for the
  documentation is unnecessary; users who want the installed README to show
  0.1.7 need a commit/push plus a profile update.
- Version monitors may offer 0.1.7; since it is documentation-only, updating
  is optional (README 0.1.7 section states this).
- No upstream Trellis changes; the Codex-in-DSH identity precedence (O1, "U1" in
  the earlier archived round) and the upstream template/DSH.md staleness (O2,
  "U2" earlier) remain read-only observations.
