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
