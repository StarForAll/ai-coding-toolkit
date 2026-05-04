# Library Drift Report — 2026-05-04

Run via: `python3 ./.trellis/scripts/diff-library-assets.py --library-root trellis-library --target .`

## Summary

| Status | Count |
|--------|-------|
| unchanged | 44 |
| modified | 15 |
| missing | 0 |
| **Total** | **59** (tracked in library-lock.yaml: 62 entries, 3 are directory-level re-exports counted once) |

## Modified Assets (content drift from upstream)

### Scripts (local modifications expected)

These scripts were imported from trellis-library and then had local modifications (our sys.path fix). The `eligible=false, action=keep-local-and-pin` status means: local changes override upstream, and upstream won't overwrite them on sync.

| Asset ID | Scope | Note |
|----------|-------|------|
| script.validation.validate-library-sync | content-change | Local modification |
| script.assembly.write-library-lock | content-change | Local modification |
| script.assembly.analyze-library-pull | content-change | Local modification |
| script.assembly.assemble-init-set | content-change | Local modification |
| script.sync.diff-library-assets | content-change | Local modification (includes our sys.path fix) |
| script.sync.propose-library-sync | content-change | Local modification |
| script.sync.sync-library-assets | content-change | Local modification |
| script.sync.apply-library-sync | content-change | Local modification |
| script.contribution.verify-upstream-contribution | content-change | Local modification |

### Specs / Checklists / Templates (content drift)

These assets have diverged from upstream since the 2026-03-29 import.

| Asset ID | Scope | Note |
|----------|-------|------|
| spec.universal-domains.product-and-requirements.prd-documentation-customer-facing | content-change | Upstream evolved |
| spec.universal-domains.product-and-requirements.prd-documentation-developer-facing | content-change | Upstream evolved |
| checklist.universal-domains.product-and-requirements.acceptance-quality-checklist | content-change | Upstream evolved |
| checklist.universal-domains.product-and-requirements.customer-facing-prd-checklist | content-change | Upstream evolved |
| checklist.universal-domains.product-and-requirements.developer-facing-prd-checklist | content-change | Upstream evolved |
| template.universal-domains.product-and-requirements.customer-facing-prd-template | content-change | Upstream evolved |
| template.universal-domains.product-and-requirements.developer-facing-prd-template | content-change | Upstream evolved |

## Unchanged Assets

44 assets remain identical to upstream. No action needed.

## Recommended Action

The 7 spec/checklist/template drift items in `product-and-requirements` domain are **upstream-evolved** (not local modifications). They should be synced down from trellis-library to bring local copies up to date.

The 9 script drift items are **local modifications** (including our sys.path fix). These should remain pinned and not be overwritten by upstream sync.
