# Manifest Maintenance Guidelines

> How to register, update, and deprecate assets in `trellis-library/manifest.yaml`.

---

## Overview

`manifest.yaml` is the single source of truth for all trellis-library assets. Every spec, template, checklist, example, schema, and script MUST be registered here.

The manifest is validated by:
```bash
python3 trellis-library/cli.py validate --strict-warnings
```

---

## Manifest Structure

```yaml
version: 1
library:
  id: trellis-library
  title: Trellis Reusable Asset Library
  ...
policies:
  require_manifest_registration: true   # All assets must be registered
  require_unique_ids: true              # No duplicate IDs
  require_reverse_links: true           # Bidirectional relations
  allow_unregistered_files: false       # Unregistered = ERROR
enums:
  asset_types: [spec, template, checklist, example, schema, script]
  asset_statuses: [draft, active, deprecated, archived]
  domain_axes: [universal-domains, scenarios, platforms, technologies]
  atomicity_levels: [simple, complex]
  relation_kinds: [depends-on, verified-by, implements-template-for, includes, extends, conflicts-with, replaced-by, related-to]
assets: [...]
relations: [...]
packs: [...]
```

---

## Asset Entry Schema

Each asset entry requires these fields:

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique ID: `{type}.{domain_axis}.{domain}.{concern}` |
| `type` | Yes | One of: `spec`, `template`, `checklist`, `example`, `schema`, `script` |
| `format` | Yes | `file` or `directory` |
| `path` | Yes | Relative path from library root |
| `title` | Yes | Human-readable title |
| `summary` | Yes | One-line description |
| `status` | Yes | `draft`, `active`, `deprecated`, or `archived` |
| `version` | Yes | Semantic version, e.g. `1.0.0` |
| `domain_axis` | Yes | `universal-domains`, `scenarios`, `platforms`, or `technologies` |
| `domain` | Yes | Sub-grouping within axis |
| `concern` | Yes | Concern name (matches directory/file name) |
| `atomicity` | Yes | `simple` (file) or `complex` (directory) |
| `tags` | Yes | List of searchable keywords |
| `applicability` | Yes | Object with `project_types`, `lifecycle_stages`, `platforms`, `technologies` |
| `owners` | Yes | List of ownership identifiers |
| `dependencies` | No | List of asset IDs this depends on |
| `optional_dependencies` | No | List of soft dependencies |
| `provides` | No | List of capabilities this asset provides |
| `change_impact` | No | Object with `level`, `review_required`, `sync_targets` |
| `metadata` | No | Object with `source_of_truth`, `generated`, `notes` |

---

## Path Rules

| Asset Type | Path Prefix | Example |
|-----------|-------------|---------|
| spec | `specs/` | `specs/universal-domains/testing/test-strategy` |
| template | `templates/` | `templates/universal-domains/contracts/api-contract-template.md` |
| checklist | `checklists/` | `checklists/universal-domains/verification/release-readiness-checklist.md` |
| example | `examples/` | `examples/packs/react-web-app-foundation.md` |
| schema | `schemas/` | `schemas/manifest/library-manifest.schema.json` |
| script | `scripts/` | `scripts/validation/validate-library-sync.py` |

---

## Adding a New Asset

1. Create the asset file/directory in the correct location
2. Add an entry to `manifest.yaml` under `assets:`
3. Add relations if the asset depends on or verifies other assets
4. Run validation:
   ```bash
   python3 trellis-library/cli.py validate --strict-warnings
   ```
5. Fix any errors and re-validate

### Example: Adding a New Spec

```yaml
# In manifest.yaml, under assets:
- id: spec.universal-domains.testing.mocking-policy
  type: spec
  format: directory
  path: specs/universal-domains/testing/mocking-policy
  title: Mocking Policy
  summary: Rules for when and how to use mocks in tests
  status: draft
  version: 0.1.0
  domain_axis: universal-domains
  domain: testing
  concern: mocking-policy
  atomicity: complex
  tags: [testing, mocking, unit-test]
  applicability:
    project_types: []
    lifecycle_stages: [development, testing]
    platforms: []
    technologies: []
  owners: [core-library]
  dependencies: []
  provides: [mocking-guidance]
```

---

## Deprecating an Asset

1. Change `status` from `active` to `deprecated`
2. Add a `replaced-by` relation pointing to the replacement asset
3. Update `metadata.notes` to explain why it was deprecated

```yaml
- id: spec.universal-domains.testing.old-approach
  status: deprecated
  metadata:
    notes: "Replaced by spec.universal-domains.testing.new-approach"
```

---

## Relations

Use relations to connect related assets:

```yaml
relations:
- id: rel-test-strategy-verified-by-checklist
  kind: verified-by
  from: spec.universal-domains.testing.test-strategy
  to: checklist.universal-domains.testing.regression-readiness-checklist
  required: false
  sync_policy: review-on-change
```

Relation kinds:
- `depends-on` — source requires target to exist
- `verified-by` — source is verified by target checklist
- `implements-template-for` — template implements a spec concern
- `includes` — source includes target
- `extends` — source extends target
- `conflicts-with` — source conflicts with target
- `replaced-by` — source is replaced by target
- `related-to` — general relationship

---

## Validation

Always run validation after manifest changes:

```bash
# Standard validation
python3 trellis-library/cli.py validate

# Strict mode (warnings also fail)
python3 trellis-library/cli.py validate --strict-warnings

# JSON output for CI
python3 trellis-library/cli.py validate --json
```

Common validation errors:
- `missing-asset-path-on-disk` — path in manifest doesn't exist
- `duplicate-asset-id` — same ID registered twice
- `asset-type-root-mismatch` — path prefix doesn't match type
- `unknown-asset-dependency` — dependency references non-existent asset

---

## Anti-Patterns

- Adding files to trellis-library without registering in manifest
- Using inconsistent ID formats
- Forgetting to update version when content changes
- Skipping validation before committing
- Creating circular dependencies between assets

---

**Language**: English
