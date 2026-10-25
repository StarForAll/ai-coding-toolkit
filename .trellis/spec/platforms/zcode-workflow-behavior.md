# ZCode Workflow Behavior

> Project-level ZCode operating rules for this repository.

---

## Purpose

Capture ZCode-specific runtime behavior verified in this repository, starting
with how skills and commands are discovered across the two workspace asset
directories that ZCode scans.

This document is about the **current repository's own operating rules**, not
about workflow product behavior in installed target projects.

---

## Verified Behavior: Dual-Directory Skill Discovery and Shadowing

Verified on 2026-10-24 against the live ZCode client in this repository and
the official `zcode-guide` configuration reference:

- ZCode scans both workspace skill roots: `.zcode/skills/` and
  `.agents/skills/`. Documented discovery order: explicitly configured roots →
  user `~/.zcode/skills` → user `~/.agents/skills` → workspace
  `.zcode/skills` → workspace `.agents/skills` → enabled plugin roots.
- Same-named skills are all discovered, but only the first in discovery order
  is loaded; higher-precedence copies shadow the rest. This repository has no
  user-scope trellis skills, so the trellis skills present in both roots
  (9 names) always load their `.zcode/skills/` copies on ZCode; the
  `.agents/skills/` same-named copies are discovered but never loaded.
- Commands from nested directories join into the name with a colon:
  `.zcode/commands/trellis/continue.md` is invoked as `/trellis:continue`.
  Therefore `/trellis:<name>` references inside the `.zcode/skills/` copies
  are valid ZCode forms for the commands that actually exist
  (`/trellis:continue`, `/trellis:finish-work`). References to commands
  without a command file (for example `/trellis:update-spec`) resolve nowhere
  on ZCode — the same is true on Claude Code, whose command directory holds
  the same two files; this is an upstream template quirk, not a ZCode
  regression. The working surface for those is the same-named skill
  (`/trellis-update-spec`), which exists.

---

## Operating Rules

Do not delete or de-scope either directory to "fix" the same-name
duplication:

- `.zcode/skills/` is the only copy ZCode actually loads for the duplicated
  names, and it is Trellis-managed (tracked in `.trellis/.template-hashes.json`).
  Deleting it would regress ZCode to the neutral-flavor `.agents/` copies, and
  `trellis update` would restore it anyway.
- `.agents/skills/` is the Codex skill surface in this repository and is also
  Trellis-managed.

Do not converge the `.zcode/skills/` copies toward the neutral `.agents/`
wording: the Claude-flavor `/trellis:<name>` command references are valid
forms on ZCode, and converging would weaken them while creating unmanaged
drift against the template hashes.

Treat same-name duplication in ZCode's skill list as expected noise, not a
defect. ZCode offers no per-directory exclusion switch, and per-name disable
overrides disable every copy of a name, so neither mechanism is a tool for
resolving this duplication.

---

## Verified Behavior: Hook Variables Bind the Live Session cwd (Drift Deadlock)

Verified on 2026-10-25 against the ZCode host source
`/opt/ZCode/resources/glm/zcode.cjs` (hook env construction:
`ZCODE_PROJECT_DIR: t.cwd || n`) and the live failure in session
`session_b6fd816ad7423725734fb309c8d8b7ec` (trace
`24f60fda-5b66-43ca-b595-98dfe3896779`):

- Template variables expanded in configuration-hook commands
  (`.zcode/config.json`) bind the **session working directory at
  hook-fire time**, not a fixed project root. On Claude Code the
  same-named `CLAUDE_PROJECT_DIR` is fixed to the project root; the
  ZCode variable has divergent semantics. No supported hook variable
  on ZCode provides a fixed project root.
- ZCode's Bash tool persists cwd across calls. After a persistent `cd`
  moves the cwd to any directory other than the repository root itself
  (subdirectories inside the repo included), every subsequent
  configuration hook (`SessionStart`, `UserPromptSubmit`,
  `PreToolUse`) resolves `${ZCODE_PROJECT_DIR}` to the drifted
  directory and fails with "No such file or directory" (e.g. a turn
  that ran `cd docs/workflows && rg ...` broke all hooks from the
  next turn).
- The failure mode was a **session deadlock**, not noise: the hook
  command `python3 <missing script>` exits with code 2, which ZCode's
  hook contract interprets as a deliberate block. A failing
  `UserPromptSubmit` hook blocked the prompt itself, so the
  "cd back to the repo root" instruction could never reach the model.
  Observed live in session `session_b6fd816ad7423725734fb309c8d8b7ec`
  and `session_bdd26e0778875da7ca6089cc741ef257`: even when the agent
  recognized the failure and attempted `cd` back, the PreToolUse hook
  blocked that recovery command too. **As of 2026-10-25 the deadlock
  is neutralized by the guarded hook commands** (see the local
  hardening record below): resolution failures now exit 0 instead of 2,
  so inputs are never blocked. Drift's secondary harms remain (see
  operating rules), and the structural host-side causes are unfixed
  upstream.

### Operating Rules (cwd discipline)

- The session cwd must remain **exactly the repository root directory
  itself** at all times. Being "inside the repository" is not enough:
  `${ZCODE_PROJECT_DIR}` is the verbatim cwd, and the hook scripts
  exist only at `<repo-root>/.zcode/hooks/`, so a cwd parked in any
  subdirectory — even one inside the repo, e.g. `docs/workflows` —
  breaks every configuration hook (before the hardening: fatally;
  after: functionally tolerated by the git-root fallback).
- Never run a bare `cd <subdir>` in a ZCode session. Use absolute
  paths, or a subshell `(cd <subdir> && <cmd>)`, which does not
  persist the cwd.
- Before ending a turn, if the session cwd is not the repository root,
  `cd` back to the repository root. A turn that ends with drifted cwd
  degrades hook behavior and misresolves relative-path Bash commands
  for the rest of the session.
- If a hook degrades silently after drift (breadcrumb stops
  appearing), suspect cwd drift first: check with `pwd` and restore
  with `cd <repo-root>`. The guarded commands intentionally fail
  silently (exit 0) outside the repository; silent loss of the
  `<workflow-state>` breadcrumb is the observable symptom.
- When a hook error names a subdirectory path
  (`.../<subdir>/.zcode/hooks/...`), treat the session as deadlocked:
  do not retry inputs; start a new session (cwd is per-session runtime
  state and a new session starts at the workspace root).
- Do not hand-patch the `.zcode/config.json` hook commands to work
  around this: the file and hook scripts are Trellis-managed (tracked
  in `.trellis/.template-hashes.json`), and any local patch is
  unmanaged drift that `trellis update` reverts. The structural
  fragility (cwd-bound variable + missing script exiting 2 = block)
  is an upstream observation to record, not a local defect to patch.

---

## Local Hardening Record: Guarded Hook Commands (2026-10-25)

The operating rule above says "do not hand-patch the hook commands",
and this section records the deliberate, registered exception that
now exists. Read this before touching `.zcode/config.json` or running
`trellis update`.

**What changed.** All four hook commands in `.zcode/config.json`
(`session-start.py`, `inject-workflow-state.py`,
`inject-subagent-context.py`, `inject-shell-session-context.py`) were
rewritten from the template form
`python3 "${ZCODE_PROJECT_DIR}/.zcode/hooks/<script>.py"` to a
guarded form:

```sh
f=".zcode/hooks/<script>.py"; d="${ZCODE_PROJECT_DIR:-}";
if [ -z "$d" ] || [ ! -f "$d/$f" ]; then d="$(git rev-parse --show-toplevel 2>/dev/null)"; fi;
if [ -n "$d" ] && [ -f "$d/$f" ]; then ZCODE_PROJECT_DIR="$d" exec python3 "$d/$f"; fi;
exit 0
```

**Why.** The host resolves `${ZCODE_PROJECT_DIR}` to the live session
cwd and spawns hooks with that same cwd (both verified in
`/opt/ZCode/resources/glm/zcode.cjs`), so the template command fails
whenever cwd drifts into a subdirectory, and the missing-script exit
code 2 is interpreted by the host as a deliberate block, deadlocking
the session. The guard (1) keeps the original fast path when the
variable points at a directory that actually contains the script,
(2) falls back to the git repository root — which resolves correctly
from any in-repo subdirectory — when it does not, (3) rewrites
`ZCODE_PROJECT_DIR` to the resolved root before `exec` because
`session-start.py` consumes that variable as the project root
(`project_dir / ".trellis"`) with no upward search, and (4) exits 0
on any resolution failure so inputs are never blocked. The other
three scripts locate `.trellis` by walking up from the payload cwd
and only use the variable for platform detection, so the rewrite is
harmless for them.

**Debt.** `.zcode/config.json` is hash-tracked in
`.trellis/.template-hashes.json`; after this edit `trellis update`
classifies it as `skip-modified` — the guarded commands survive, but
the file stops receiving upstream template updates automatically.
After every `trellis update`, diff the new template's config.json
against this file and port any upstream hook-related changes by hand.
Upstream fix to track: the Trellis `templates/shared-hooks` command
form (and/or a ZCode-side fixed project-root variable). When either
lands and this file can return to the template form, remove this
section and the guard together.

**Verified behavior of the guard** (2026-10-25, simulated host
invocation with drifted cwd and `ZCODE_PROJECT_DIR` set to the
drifted value): SessionStart and UserPromptSubmit hooks produce their
`additionalContext` JSON normally from a drifted cwd; all four
commands exit 0 from an out-of-repo or foreign-repo cwd with no
output; healthy-cwd behavior is byte-identical to the template form
except for the added guard stat calls.

---

## Why This Rule Exists

- Both layers are Trellis-deployed with deliberate per-directory flavoring:
  the upstream zcode configurator unconditionally deploys Claude-flavor
  skills to `.zcode/skills/` and `/trellis:<name>` commands to
  `.zcode/commands/trellis/`, while `.agents/skills/` carries the
  platform-neutral flavor that Codex consumes.
- The runtime conflict is already resolved deterministically by ZCode's
  documented precedence; the remaining cost is only duplicate entries in the
  skill list.

---

## Verification Notes

When reviewing ZCode behavior in this repository, verify:

- the same-name shadowing assumption still holds (no user-scope trellis
  skills appeared; client precedence has not changed in an update)
- nobody "cleaned up" either skill root or hand-edited `.zcode/skills/`
  copies away from the template flavor
- upstream changes to the zcode configurator's deployment set are recorded
  as observations against the read-only upstream reference, not as local
  edits

---

**Language**: English
