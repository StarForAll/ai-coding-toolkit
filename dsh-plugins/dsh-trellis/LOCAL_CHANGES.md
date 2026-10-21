# Local changes against upstream dsh-trellis 0.1.12

This copy is modified in place (Strategy A). Upstream files keep their
behaviour unless listed here. Runtime package identity (`name`,
`cordis.patch.yml` id, settings namespace, exports) is unchanged, so this copy
replaces upstream `dsh-trellis` rather than coexisting with it. The version is
bumped to `0.1.0` so installers do not treat the local build as "already at
0.1.12" and skip it.

## Version scheme (restarted 2026-10-21)

The carrier's version numbering restarted at `0.1.0`. Pre-reset versions
(`0.1.12` upstream through local `0.3.10`) remain only as history below and in
the `validation-0.3.*` records.

- Normal fixes/features/docs bump the patch: `0.1.0` -> `0.1.1` -> `0.1.2`.
- Minor/major bumps are reserved for significant changes (breaking runtime or
  configuration contracts, manifest/settings-surface breaks, or a rewrite that
  requires re-verifying integration). Do not use `0.2.0+` for ordinary work.
- `package.json`, `README.md`, this file, and the release record must agree;
  `pnpm run build:client` re-stamps `PLUGIN_VERSION` in `lib/client.js`.

## Added files

| File | Purpose |
| --- | --- |
| `lib/text.js` | Shared UTF-8 truncation used by every model-visible payload. |
| `lib/message-projection.js` | Generic replayable message identity: one projection key per message family. |
| `lib/bootstrap.js` | The no-task `<trellis-bootstrap>` message: own `source.form`, own projection, own dedupe. |
| `lib/session-composer.js` | Resolves the Trellis state once per step and returns every message the state calls for. |
| `lib/project.js` | One resolution of cwd → `.trellis` root → `config.yaml`, shared by every capability. |
| `lib/conflicts.js` | Detects another enabled `dsh-trellis*` loader entry; never auto-disables, never fabricates "no conflict". |
| `lib/dispatch-guard.js` | Fail-closed guard for `trellis-agent-implement` / `check` dispatches; research notice. |
| `lib/doctor.js` | `/trellis-doctor`: JS-only project/plugin/wiring diagnostics. |
| `lib/upstream.js` | Host-side Atom/registry lookup and the same-origin `/dsh-trellis/version-check` route. |
| `src/client/conflicts.js` | Reads the conflict route and builds stable identity/summary text. |
| `src/client/conflict-view.js` | JSX-free banner view plus the permission-request action, so all permission states are unit-testable. |
| `src/client/ConflictBanner.jsx` | Desktop notification plus a frame-wide banner for a competing plugin. |
| `lib/trellis-config.js` | Minimal readers for `.trellis/config.yaml` `spec_injection` and `context_injection`. |
| `lib/spec-glob.js` | Spec glob validation/translation and repo-relative normalisation. |
| `lib/spec-index.js` | Bounded frontmatter parsing, spec scanning, specificity-ordered matching. |
| `lib/spec-inject.js` | Pure FULL / TICKET / silent decision engine, rendering, character budgets. |
| `lib/spec-state.js` | Atomic per-session spec-injection state shards under `.trellis/.runtime/spec-inject/`; corrupt/read-only state safely re-teaches. |
| `lib/spec-policy.js` | `tools/pre-execute` deny-once gate, `tools/post-execute` ticket delivery, persistent state, `compaction/end` reset. |
| `lib/subagent-context.js` | First-step task-context push for `trellis-agent-*` children. |
| `test/bootstrap.test.js` | Bootstrap message family and its projection's independence. |
| `test/trellis-config.test.js` | Config section parsing and defaults. |
| `test/spec-glob.test.js` | Glob grammar and path normalisation. |
| `test/spec-index.test.js` | Frontmatter parsing and match ordering. |
| `test/spec-inject.test.js` | Decision order, truncation, budget ceilings, index degradation. |
| `test/spec-policy.test.js` | Deny-once, read-tool delivery, restart persistence, compaction reset (memory + disk), host-decision preservation. |
| `test/spec-state.test.js` | State shard round-trip, corruption/version fallback, malformed-record filtering, clearing, path containment. |
| `test/subagent-context.test.js` | Dispatch parsing, role-contract extraction, manifest/artifact materialisation, first-step push, missing-skill fallback. |
| `test/conflicts.test.js` | Loader-entry conflict detection and honest unknown states. |
| `test/dispatch-guard.test.js` | Evidence-based task proof, deny path, research notice. |
| `test/doctor.test.js` | Report fields, broken task, disabled spec injection, command input rejection. |
| `test/upstream.test.js` | Atom parsing, URL/package validation, route status/error handling. |
| `test/client-conflicts.test.js` | Conflict route parsing, unavailable degradation, summary text. |
| `test/conflict-view.test.js` | All four conflict permission states, permission request/notify ordering, locale copy. |
| `src/client/version-check.js` | GitHub commit/release lookup, baseline storage, notification and due-time logic. |
| `src/client/version.js` | Build-time plugin version (`__DSH_TRELLIS_VERSION__`). |
| `src/client/VersionMonitor.jsx` | Manual check UI with per-source results and update badges. |
| `test/version-check.test.js` | Repo parsing, commit/release normalization, baseline vs changed sha, due time. |
| `docs/validation-0.3.4-local.md` | Verification record for this local branch. |
| `docs/validation-0.3.5-local.md` | Independent re-verification and fix record for the 0.3.5 round. |
| `docs/validation-0.3.6-local.md` | Follow-up re-verification and residual-fix record for the 0.3.6 round. |
| `docs/validation-0.3.7-local.md` | Role-contract push, persistent spec state, and bootstrap documentation record for 0.3.7. |
| `docs/validation-0.3.8-local.md` | Verification record for the 0.3.8 parity-fix round (state parsing, status mapping, workflow selection, skip keyword, inline, role-push wording). |
| `docs/validation-0.3.9-local.md` | Verification record for the DSH `dsh.dispatch_mode` inline feature. |
| `docs/validation-0.1.0-local.md` | Release record for 0.1.0: version restart, automatic `dsh.dispatch_mode` bootstrap, inline boundary fixes, and the inline dispatch gate. |
| `docs/manual-verification.md` | User-only manual acceptance steps and expected effects (no automated checks). |
| `UPSTREAM_BASE.yaml` | Maintenance metadata (upstream baseline, unknown commit). |
| `LOCAL_CHANGES.md` | This file. |

## Modified files

| File | Change | Reason |
| --- | --- | --- |
| `lib/breadcrumb.js` | No longer embeds the bootstrap notice; truncation moved to `text.js`; composition moved out. | The nudge is a separate message family with its own dedupe, not a substring of the breadcrumb. |
| `lib/breadcrumb-projection.js` | Thin wrapper over `message-projection.js`. | One replayable-identity implementation for every message family. |
| `lib/index.js` | `registerBreadcrumb` → `registerSessionMessages`; composes and dedupes a list of messages, one projection per family. Registers the doctor command, the dispatch guard, and the mount-time conflict warning. | Bootstrap must be deduped independently of workflow state; the new capabilities need one wiring point. |
| `lib/config.js` | `projectRootMarkers` defaults to `[".trellis", ".git"]`; added `specInjection` / `subagentContext` / `dispatchGuard`. | Codex finds the Trellis root by `.trellis/`, so a non-Git Trellis project must still receive context. |
| `test/index.test.js` | Covers two message families, independent dedupe, state churn, compaction, default markers, the extra projection. | Behaviour intentionally changed; no assertion was skipped or deleted. |
| `test/breadcrumb.test.js` | Bootstrap assertions moved to `test/bootstrap.test.js`. | Keep each test file scoped to its module. |
| `test/working-directory*.test.js` | Use `createSessionComposer` (returns a message list). | Composer API changed with the message families. |
| `test/config.test.js` | Asserts the new marker default and `dispatchGuard`. | Non-Git Trellis project parity; explicit guard switch. |
| `src/client/form.js` | All settings fields plus the six version-monitoring fields; Trellis/DSH are npm package names, not repositories; interval validation. | The page must edit every host field, and the official tools are watched by published version. |
| `src/client/TrellisSettingsCard.jsx` | Capability switches first, then breadcrumb behavior, then monitoring; the monitoring group (interval, notify, three sources, panel) is gated by the single `versionCheck` switch. | Keep the safety switches at the top and avoid showing controls that the master switch disables. |
| `src/client/index.jsx` | Registers `settings.section` only; starts the auto-check interval from saved values. | Settings → Trellis is the single configuration entry; monitoring runs while the page is open. |
| `src/client/locales.js`, `src/client/styles.js` | Section, monitor and notification copy/styles. | New surfaces need labels and layout. |
| `src/client/version-check.js` | Calls the Host's same-origin route instead of GitHub/npm directly; Trellis/DSH compare dist-tags, the fork compares commits + release. | GitHub's Atom feeds have no CORS headers, and the REST API's unauthenticated quota produced browser 403s; official version changes are what `npm view` reports. |
| `lib/index.js` | Registers the version-check and conflicts routes once per plugin instance via the optional `webServer` service; no conflict log line. | The routes must exist independently of the workflow runtime switch, and headless profiles simply have no server. |
| `lib/conflicts.js` | Detection stays; the log-only warning is replaced by a JSON route (`/dsh-trellis/conflicts`). Matching is any package name or loader id containing `trellis` (case-insensitive), not only `dsh-trellis*`. | A log line does not reach the user; a fork/wrapper published under another name would still collide, and the browser turns the data into a desktop notification and banner. |
| `src/client/index.jsx` | Registers the frame-overlay conflict banner alongside the settings section. | The user must perceive a competing plugin from any screen. |
| `src/client/locales.js`, `src/client/styles.js` | Conflict copy and banner styles. | New surface needs labels and layout. |
| `tsdown.config.js` | Stamps the package version into the client bundle. | The page shows the installed version without a host round-trip. |
| `src/client/compat.js` | Removed. | The keyed/list plugin-page adapters no longer have a caller. |
| `lib/spec-policy.js` | Uses the shared `project.js` resolver and persists spec state per root + session. | One root-resolution implementation; restarts must not re-deny a spec the session already saw, while compaction must re-teach. |
| `lib/subagent-context.js` | Reads and pushes the installed `.dsh/skills/trellis-agent-<role>/SKILL.md` body before curated context; missing skill falls back to a path pointer. | The child needs the role contract, not only the task path; Codex gets this from agent TOML, DSH must source it from the generated role skill. |
| `README.md` | Bootstrap family, marker default, local install flow. | Document the local divergence and its boundaries. |
| `scripts/compat-hosts.mjs` | Adds `0.2.1-rc.2` and its exact toolchain/working-directory packages to the compatibility matrix. | The shipped host matrix stopped at `0.2.1-alpha.2`, so the actual runtime was untested. |
| `scripts/test-compat.mjs` | Runs native pnpm executables directly; only JavaScript pnpm entries go through `node`. | pnpm 10+ exposes an ELF/PE binary through `npm_execpath`, which `node` cannot parse. |
| `test/compat-hosts.test.js` | Pins the `0.2.1-rc.2` toolchain and working-directory devDeps. | Keep the matrix test aligned with the new host entry. |
| `test/native-working-directory.test.js` | Fixture returns a valid `current --json` payload instead of plain text. | The command now requires the machine-readable payload; the old fixture silently depended on a skipped test. |

## Fix round 0.3.5 (2026-10-20)

Independent verification found two functional defects and two documentation
claims that did not match the code. The fixes address the causes rather than the
symptoms:

| File | Fix | Why this is the cause |
| --- | --- | --- |
| `lib/session-composer.js` | Delegated children (`session.header.origin === "subagent"`) no longer receive the root-session `no_task` breadcrumb or bootstrap. A child that has bound its own task still receives that task's breadcrumb, but never bootstrap. | The composer resolved the child's own session pointer, which does not exist, and spoke for a workflow the child does not own. The push message already carries the child's task; silence is the only non-contradictory state. Forks keep the root behavior because they have `parentSession` but no `origin: "subagent"`. |
| `lib/commands.js` | `/trellis-status` and `/trellis-finish` read `task.py current --json` and treat exit 1 with `current_task: null` as a valid no-task answer. `runTrellisScript` now preserves stdout/stderr and the exit code on failure. | Trellis documents exit 1 as "no active task" and prints the machine-readable payload; treating every non-zero exit as a script failure discarded that contract and the payload. A bare exit 1 without the payload still fails. |
| `src/client/ConflictBanner.jsx` | The conflict banner offers a "Enable desktop notifications" button when permission is still `default`, and explains the site-setting path when it is `denied`. | `requestNotificationPermission()` needs a user gesture. We cannot silently request it on page load; a button in the banner is the smallest reliable gesture. The desktop notification remains the primary warning and the banner remains the fallback. |
| `README.md` | Removed the "DSH and Codex are identical" claim; the remaining differences are listed explicitly. | The same README already documented differences (bootstrap frequency, `read` cannot deny, in-process state, stricter guard), so the claim contradicted its own evidence. |

Verification after the fixes: 242 tests, 238 pass, 0 fail, 4 skip; client bundle
rebuilt and its render/lifecycle tests pass. The real-repository command probe
now prints `Current task: (none)` instead of `Trellis script failed`. See
`docs/validation-0.3.5-local.md`.

## Fix round 0.3.6 (2026-10-20)

The second verification round confirmed both functional fixes and left three
follow-up items that this round closes without changing the 0.3.5 behaviour:

| File | Fix | Why this is not a patch |
| --- | --- | --- |
| `src/client/conflict-view.js`, `test/conflict-view.test.js` | Split the conflict banner into a stateful container and a JSX-free view/action module; committed tests cover `default` / `denied` / `granted` / `unsupported`, the permission request, and notify-on-grant only. | The untested logic was real page-load behaviour. Testing it through a pure view and an injected request/notify pair covers the same production path the container calls, instead of asserting on a mock DOM. |
| `lib/commands.js`, `test/commands.test.js` | When Trellis rejects `current --json` with argparse's `unrecognized arguments: --json` (exit 2), fall back to the documented `current --source` output. Only the documented `Current task:` line is accepted; a bare failure still errors. | The 0.3.5 fix used a contract added in Trellis 0.6.10. 0.6.5 and earlier only expose `--source`; a versioned protocol adapter keeps the same no-task semantics without weakening failure detection. |
| `test/index.test.js`, `README.md` | A generic sub-agent (no `trellis-agent-*` role) is now covered by an explicit test and documented as silent. | Codex's `inject-subagent-context.py` exits 0 for non-Trellis subagent types; silence is parity, not an accidental regression. |

Verification: 254 tests, 250 pass, 0 fail, 4 skip; the client bundle is rebuilt
at `0.3.6`. The historical M1 acceptance record remains `N/A` (not
reconstructable); the 0.3.4 and 0.3.5 records keep their history markers. Current
full-scope acceptance is `USER_ACCEPTANCE: NOT_APPLICABLE` (there is no
partial-parity reduction left); fixed exclusions and manual checks are in
`../plugin-create.md` and `docs/manual-verification.md`.

## Fix round 0.3.7 (2026-10-20)

This round closes the two structural gaps from the Codex comparison instead of
documenting them as permanent differences:

| File | Fix | Why this is not a patch |
| --- | --- | --- |
| `lib/subagent-context.js`, `test/subagent-context.test.js` | The child's first-step push now contains the role contract from `.dsh/skills/trellis-agent-<role>/SKILL.md` before the curated task context. YAML frontmatter is stripped; the body is capped at 16 KiB; a missing skill falls back to an explicit path pointer. | The role skill is the authoritative, Trellis-generated source; copying the text into the plugin would drift. The push is the same child-visible message, not a second injection path. |
| `lib/spec-state.js`, `lib/spec-policy.js`, `test/spec-state.test.js`, `test/spec-policy.test.js` | Spec dedupe records persist per project + session under `.trellis/.runtime/spec-inject/`; writes are temp+rename; corrupt/read-only state falls back to re-teach; `compaction/end` deletes both memory and shard. | The decision engine is unchanged; only the state owner moved from process memory to a small project-local store. Restart behavior is now explicit and testable instead of relying on process lifetime. |
| `README.md`, `LOCAL_CHANGES.md`, `../docs/capability-inventory.md`, `docs/manual-verification.md`, `docs/validation-0.3.7-local.md` | Bootstrap frequency stays "once per new session"; the documents now state that if the first turn does not start Trellis, later normal turns in the same session deliberately do not repeat the nudge. Compaction/clear or manual `trellis-start` can re-prompt; a new session injects again. | This is a product decision, not a defect. Keeping the code unchanged while making every surrounding document agree prevents the previous "code says X, README says Y" drift. |

Verification: 266 tests, 262 pass, 0 fail, 4 skip; the client bundle is rebuilt
at `0.3.7`. The new tests cover role-contract extraction, missing-skill fallback,
state round-trip, corrupt/version fallback, restart persistence, and persisted
compaction reset.

## Fix round 0.3.8 (2026-10-21)

| File | Fix | Why this is not a patch |
| --- | --- | --- |
| `lib/workflow.js`, `test/workflow.test.js` | The block regex now requires the closing `]` of the opening tag to end its line, exactly like the Codex/Claude Python hook. Previously an inline mention inside workflow.md's breadcrumb-contract comment (`[workflow-state:no_task] → …`) opened a 66-line match that swallowed the real no_task body. | The workflow file is shared with every platform; the parser must implement the same grammar, not a more permissive one. |
| `lib/workflow.js`, `test/workflow.test.js` | Task statuses pass through instead of collapsing into `no_task`: `completed` uses its own block, a custom status falls back to the generic line, and a pointer to a deleted task directory is `stale` (with its own block when defined). | These are real Trellis states; rewriting them made DSH contradict the task record and the workflow contract. |
| `lib/workflow.js`, `lib/trellis-config.js`, `test/workflow.test.js` | Workflow selection mirrors `common/workflow_selection.py`: task `workflow` pin → `.developer` `workflow=` → config `default_workflow` → global workflow.md, with invalid ids and missing variant files falling through. | The variant library is a Trellis feature; a platform that ignores it silently runs a different workflow than Codex/Claude on the same project. |
| `lib/session-composer.js`, `lib/trellis-config.js`, `test/session-composer.test.js` | The per-turn skip keyword is read from `.trellis/config.yaml` `prompt_injection.skip_keyword` first; the plugin-level `skipKeyword` remains the fallback. An explicitly empty project value disables the escape hatch. | Trellis config is the cross-platform authority; a profile-level default must not override it. |
| `lib/workflow.js`, `test/workflow.test.js` | Initially selected the `*-inline` blocks when `codex.dispatch_mode: inline`. **Reverted in the check round**: Trellis marks those blocks Codex-only and its carrier selects them only for `platform == "codex"`; DSH keeps the base blocks that carry its dispatch protocol. | The initial parity argument ignored the platform guard. Honoring a Codex-only setting on DSH hid the DSH-specific sub-agent/`trellis_wait` instructions and contradicted the dispatch guard and sub-agent push. |
| `lib/subagent-context.js` | The pushed role-context message now states explicitly that the role skill's "Load Trellis Context First" section is satisfied, and forbids running `task.py current`, asking for a task path, or re-reading artifacts to discover the task. | The generated skill still says "this platform does not auto-inject"; without an explicit override the child is told to do work the push already did. |
| `lib/dispatch-guard.js`, `lib/subagent-context.js` | A `stale` pointer is not a readable task: it no longer satisfies the dispatch guard and no longer supplies a parent task path for the push. | Guarding on a missing directory would dispatch a child with no context — the exact failure the guard exists to prevent. |

Verification for this round: 282 tests, 278 pass, 0 fail, 4 skip; plus real
`.trellis/workflow.md` parsing (`no_task` 421 chars instead of 4,605) and a
headless DSH session against a fresh `trellis init` project (model request
carries the full no_task guidance; project skip keyword suppresses injection).
See `docs/validation-0.3.8-local.md`.

## Check round 0.3.8 (2026-10-21, `trellis-check`)

Adversarial re-check of the round above against the Python carriers. Two
divergences in the 0.3.8 delta were confirmed by running both implementations on
the same inputs, and fixed:

| File | Fix | Why this is not a patch |
| --- | --- | --- |
| `lib/workflow.js`, `test/workflow.test.js` | A `[workflow-state:*]` block whose body is empty or whitespace-only is no longer stored. `load_breadcrumbs` in both Python carriers keeps a tag only when its body is non-empty (`if body:`), so the hook degrades to the generic line; keeping the empty block here rendered an empty breadcrumb body and let an empty `planning-inline` / `in_progress-inline` shadow the populated base block. | Same grammar and same "no usable template → generic line" degradation as the carriers; the status-level fallback constant already existed, this makes the empty-block case reach it too. |
| `lib/breadcrumb.js`, `test/breadcrumb.test.js` | The skip-keyword matcher now mirrors `prompt_has_skip_keyword`: `(?<![\w-])keyword(?![\w-])` with Unicode word characters, instead of an ASCII `\b` pattern. `foo-no-trellis` therefore no longer skips the turn (hyphen is a word character), while punctuation-delimited keywords such as `skip.` or `#skip` now match. | The project-level `prompt_injection.skip_keyword` is shared with Codex/Claude, so the same prompt must produce the same skip decision on every platform. An ASCII `\b` silently changed that decision in both directions. |

Coverage added for two 0.3.8 behaviors that had no test: a `stale` pointer is
rejected by the dispatch guard (`test/dispatch-guard.test.js`) and supplies no
parent task path for the push (`test/subagent-context.test.js`); the push
message's override of the role skill's "load context yourself" step is now
asserted instead of only described.

Verification after this round: 287 tests, 283 pass, 0 fail, 4 skip.


The same check round also reversed one 0.3.8 change and closed two gaps it
exposed:

| File | Fix | Why |
| --- | --- | --- |
| `lib/workflow.js`, `test/workflow.test.js` | DSH no longer selects `*-inline` blocks; the Codex-only `codex.dispatch_mode` is ignored, with the contract documented in the source comment and README. | `workflow.md` labels the blocks "Codex-only opt-in alternate" and `resolve_breadcrumb_key` gates them on `platform == "codex"`. On this repo's default `dispatch_mode: inline`, the previous behavior replaced the 1635-byte in_progress block (DSH dispatch protocol) with the 325-byte inline block that says "do not dispatch sub-agents". |
| `lib/workflow.js`, `lib/node-fs.js`, `test/workflow.test.js` | Session pointers are normalized like `common/active_task.py` (`tasks/<slug>` → `.trellis/tasks/<slug>`, `./` stripped, absolute kept) and resolved inside the project root; `stale` now also covers a ref that is not a directory (a same-named file or an escaping path). | Previously `tasks/x` produced a false `stale`, absolute paths were joined as relative, and a file ref produced `task_error` instead of `stale`. |
| `lib/doctor.js` | Doctor reports the workflow file actually selected by the task/personal/team precedence (`Workflow file:` line), not always `.trellis/workflow.md`. | After workflow variants became supported, the block count could describe a different file than the one being injected. |
| `test/workflow.test.js` | +4 cases: DSH ignores inline, legacy/absolute pointer refs, file-not-directory stale, escaping ref stale. | Regression coverage for the reversals and the normalization. |

Verification after the full check round: 291 tests, 287 pass, 0 fail, 4 skip;
live pointer resolves to `in_progress` (1635 bytes), not `in_progress-inline`.

## Feature round 0.3.9 (2026-10-21)

The 0.3.8 check round reverted the Codex-only `*-inline` selection on DSH. That
left no supported way to run a DSH Trellis task entirely in the main session:
the base in_progress block says "Main-session default: dispatch … sub-agents".
This round adds a DSH-owned switch instead of reusing Codex's setting.

| File | Change | Why |
| --- | --- | --- |
| `lib/workflow.js`, `test/workflow.test.js` | New `dsh.dispatch_mode` (`auto` default, `inline` opt-in) read from `.trellis/config.yaml`. `inline` selects the platform-neutral `planning-inline` / `in_progress-inline` phase block and appends the `DSH_INLINE_NOTE` banner; `auto`, invalid values, or a missing inline block keep the base block. `codex.dispatch_mode` stays ignored on DSH. | The `*-inline` blocks are Codex-only and omit DSH-specific mechanics, so selecting them alone was wrong. Reusing their phase contract plus an explicit DSH mode banner gives the main session a supported inline path without forking workflow.md or losing the DSH dispatch details. |
| `lib/doctor.js` | Reports `Dispatch mode: <auto|inline> (dsh.dispatch_mode)`. | The mode changes which block is injected; diagnostics must show it. |
| `.trellis/config.yaml` | This repository pins `dsh.dispatch_mode: inline`. | The authoring repo's standing rule is main-session work; the DSH counterpart must state the same, while Codex keeps its own `codex.dispatch_mode`. |
| `README.md` | Documents the project-level `dsh.dispatch_mode` and the banner. | Mode is project policy, not a plugin profile setting. |

Verification: 295 tests, 291 pass, 0 fail, 4 skip. Real headless DSH session
with `dsh.dispatch_mode: inline` receives `Trellis workflow state:
in_progress-inline` with the `<dsh-mode>` banner (788 bytes); `auto` and
`no_task` sessions are unchanged.

## Release 0.1.0 (2026-10-21, version restart)

Installed-state end-to-end audit (`10-21-dsh-trellis-installed-e2e-inline-audit`)
found two inline-mode boundaries:

- A workflow variant without a `*-inline` block silently dropped the mode banner,
  so a trimmed workflow re-taught auto semantics to an inline project (Codex keeps
  emitting `<codex-mode>inline>` in the same situation). The banner is now emitted
  for every status whenever `dsh.dispatch_mode: inline`, independent of block
  selection.
- Inline mode was advisory only. The dispatch guard now refuses
  `trellis-agent-implement` / `trellis-agent-check` dispatch under inline mode and
  keeps `trellis-agent-research` allowed; `dsh.inline_allow_dispatch: true` is the
  explicit project-level escape hatch.

Also documented: cross-platform `spec_injection.tools` naming (shared config must
use Trellis' capitalized names because Codex does not normalize), the invalid
`dsh.dispatch_mode` fallback to `auto`, and the `task.py start
--allow-empty-context` friction in inline mode.

### Automatic `dsh.dispatch_mode` bootstrap

Enabling the plugin now migrates a Trellis project on first use: before the
first state resolution, `.trellis/config.yaml` is ensured to contain
`dsh.dispatch_mode: inline`. The migration only adds a missing key, preserves
comments/order/line endings, never overwrites an explicit value, never creates a
missing config, writes atomically under a directory lock, re-reads the file while
holding the lock before merging (so a stale snapshot cannot duplicate the key or
overwrite concurrent edits), and degrades to `auto` with one warning on failure. The pure merge (`mergeDshDispatchMode`) and the IO
policy (`createDshDefaultsEnsurer`) live in `lib/project-defaults.js`; the
composer reuses one project root for the bootstrap and the state resolver so the
first turn already sees the new mode.

### Pre-push client build

Git dependencies never run `prepack`, so a pushed checkout must already carry a
current `lib/client.js`. The repository now tracks `scripts/git-hooks/pre-push`
and installs it into `.git/hooks/pre-push` via `scripts/install-git-hooks.sh`.
It builds only when the pushed commits touch `dsh-plugins/dsh-trellis`, and it
aborts the push when the rebuild dirties `lib/client.js`/`lib/client.js.map`
(the commit that is being pushed cannot carry a post-commit build). Existing
`core.hooksPath` managers that chain to `.git/hooks` (Sonar) keep working.

### Version restart

Version reset to `0.1.0`; see the version scheme section above and
`.trellis/spec/platforms/dsh-workflow-behavior.md`.

See `docs/validation-0.1.0-local.md`.

## Known differences from Codex

- Codex's `PreToolUse` deny also carries `additionalContext`; DSH's
  `PreToolDecision` has no context channel, so the spec body travels in the
  deny `reason` instead.
- A `read` trigger cannot be denied: its payload is delivered by
  `tools/post-execute` with the next request, so the read always completes.
- Codex stores spec-injection state in user-global JSONL shards; this copy stores
  a project-local JSON shard under `.trellis/.runtime/spec-inject/` with atomic
  temp+rename writes. Both survive a normal plugin/CLI restart; `compaction/end`
  is the explicit reset point for DSH.
- Codex emits the no-task nudge every turn; this copy emits it once per new root
  session and again only after compaction removed it. If the first turn does not
  start Trellis, later normal turns in that session deliberately do not repeat
  the nudge: this is a noise-reduction choice, not a defect. Load `trellis-start`
  manually to re-open the workflow; a new session injects again.
- Codex pushes role instructions from `agent.toml`; this copy reads the installed
  `.dsh/skills/trellis-agent-<role>/SKILL.md` body and pushes it before curated
  task context. Missing skill falls back to a path pointer, and the child-side
  skill remains the pull fallback.
- The dispatch guard is stricter than Codex: Codex injects nothing and lets a
  task-less role child run; this plugin refuses an implement/check dispatch that
  has no readable task. Research is allowed with a follow-up notice.
- Conflict detection reports a competing `dsh-trellis*` plugin; it never
  disables the other plugin (upstream/operator decision stays outside the plugin).
- Upstream monitoring is triggered from the browser but performed by the Host
  (a closed page performs no checks; the interval resumes on the next load).
  Only a page can raise a desktop notification; only the Host can read GitHub's
  CORS-less Atom feeds without the REST API quota.
- The monitor sends only repository or package names to `github.com` and
  `registry.npmjs.org`; it sends no project content, settings, or credentials.
  The route accepts only GET and only fetches URLs it constructs from validated
  `owner/repo` or package names — never a URL supplied by the caller.
- Trellis and DSH are watched by npm **dist-tags**, not by commits: `latest`,
  `beta`, `next`, `alpha` are all compared, because a project can publish a
  release channel ahead of `latest` (Trellis currently does).
- No `TRELLIS_HOOKS=0` / `TRELLIS_DISABLE_HOOKS=1` environment kill switch is
  honoured; the profile config (`enabled`, `specInjection`, `subagentContext`,
  `dispatchGuard`, `versionCheck*`) is the switch.

## Local-only boundaries

This copy is maintained for personal use: it is not published to npm, and the
absence of a LICENSE file is accepted (`package.json` remains MIT). Upgrade of
existing 0.2.0 sessions is not migrated to the split bootstrap family; acceptance
covers new sessions after this local branch is complete. Project-level policy and
vendored auto-sync scripts/patch directories are explicitly not needed; plugin
exclusivity is limited to a desktop notification warning. See
`../plugin-create.md` ("范围排除") and `docs/manual-verification.md` for the
authoritative scope and manual checks.
