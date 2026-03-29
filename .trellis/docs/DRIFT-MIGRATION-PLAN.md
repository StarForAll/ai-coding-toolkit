# Drift Migration Plan — ai-coding-toolkit

## Overview

This document records the migration from an unmanaged state (0 tracked imports, 298 library assets)
to a properly tracked state (62 tracked imports) following the **Phased Alignment** strategy (Plan B).

## Migration Date

2026-03-29

## Strategy: Plan B — Phased Alignment

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | Backup | ✓ complete |
| Phase 2 | Pilot sync (6 core assets) | ✓ complete |
| Phase 3 | Batch sync (3 batches, 56 assets) | ✓ complete |
| Phase 4 | Cleanup & integration | ✓ complete |
| Phase 5 | Continuous sync | ✓ complete |

## Phase 1: Backup

Created `.trellis/.backup-phase1-20260329-174019/` containing:
- Original `library-lock.yaml` (empty imports)
- Full `.trellis/spec/` directory

## Phase 2: Pilot Sync (6 assets)

Synced core project-governance and verification specs to validate the workflow.

## Phase 3: Batch Sync

### Problem: Bootstrap Gap

`sync-library-assets.py` requires existing `imports` entries to iterate. When `imports` is empty
(first-time), the script exits silently with nothing to sync.

### Solution: Manual Bootstrap

Created manual import entries in `library-lock.yaml` with:
- Computed SHA-256 checksums per asset
- Proper `depends_on` (only tracked deps)
- Schema-compliant 15-field structure
- Files copied via `shutil.copytree` / `shutil.copy2`

### Batch 1 (18 assets)

| Domain | Assets |
|--------|--------|
| `ai-execution` | 4 specs (prompt-boundaries, tool-call-policy, structured-output-policy, model-selection-and-fallback) |
| `context-engineering` | 3 specs + 1 checklist |
| `agent-collaboration` | 4 specs + 2 checklists + 1 template |
| `scripts/validation` | 3 scripts |

### Batch 2 (15 assets)

| Domain | Assets |
|--------|--------|
| `project-governance` | library-sync-governance, risk-tiering |
| `verification` | definition-of-done |
| `platforms/cli` | command-interface |
| `scripts/sync` | 4 scripts (sync, diff, propose, apply) |
| `scripts/assembly` | 3 scripts (write-library-lock, analyze-library-pull, assemble-init-set) |
| `scripts/contribution` | 1 script (verify-upstream-contribution) |
| `checklists/templates` | 3 assets |

### Batch 3 (23 assets)

| Domain | Assets |
|--------|--------|
| `product-and-requirements` | 6 specs + 3 checklists + 3 templates + 2 examples + 1 directory examples |
| `verification` | release-readiness spec + checklist + 2 templates |
| `project-governance` | 2 checklists + 2 templates |

## Phase 4: Cleanup

- All 62 import targets verified on disk
- No local-only assets accidentally tracked
- Library-lock.yaml schema-compliant (15 fields per entry)
- Backup directory preserved for rollback

## Phase 5: Continuous Sync

### Verification

All 62 assets report `unchanged` via `diff-library-assets.py --json`.

### Sync Commands

```bash
# Check for drift
python3 trellis-library/scripts/sync/diff-library-assets.py --library-root trellis-library --target . --json

# Update lock with drift results
python3 trellis-library/scripts/sync/diff-library-assets.py --library-root trellis-library --target . --update-lock

# Sync from library
python3 trellis-library/scripts/sync/sync-library-assets.py --manifest trellis-library/manifest.yaml --lock .trellis/library-lock.yaml --target .
```

## Remaining Untracked Assets

236 assets remain untracked (79% of library). These are mostly:
- Framework-specific templates (82)
- Assembled packs (24)
- Platform assets (web/mobile/desktop, 24)
- Domain-specific assets (defect-and-debugging, security, delivery, etc.)

These are **not relevant** to the ai-coding-toolkit meta-project and intentionally excluded.

## Lessons Learned

1. **Bootstrap gap**: First-time imports require manual entry creation since `sync-library-assets.py` has no `--init` mode.
2. **Dir-level tracking**: Directory-format assets track all files within; individual file list is shown as LOCAL in lock vs. disk comparison but is correct behavior.
3. **Dependency filtering**: `depends_on` should only include deps that are actually tracked in the lock (not all manifest deps).
