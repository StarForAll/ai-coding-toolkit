# Trellis Library

Reusable source assets for Trellis-based project initialization.

This directory is the source library, not a target project's live `.trellis/`
workspace. It exists so future Trellis projects can selectively take reusable
specs, templates, checklists, and pack definitions, then initialize their own
project-local Trellis assets from a stable source of truth.

## Purpose

This library is designed to solve three related problems:

* keep reusable Trellis assets in one maintained source directory
* let different target projects select only the assets they actually need
* support controlled downstream sync and selective upstream contribution

The library keeps source assets split and atomic. Target projects should import
complete concern directories or registered files rather than manually copying
fragments.

## Directory Map

* `specs/`
  Reusable normative rules split by universal domains, scenarios, platforms, and
  technologies.
* `templates/`
  Reusable artifact and document templates, including platform-oriented planning
  templates.
* `checklists/`
  Reusable execution and review checklists, including platform readiness
  checklists.
* `examples/`
  Example assembled packs and selection references that mirror real pack
  composition.
* `schemas/`
  Machine-readable schemas for manifest and lock-file validation.
* `scripts/`
  Automation for selection, assembly, validation, downstream sync, and upstream
  proposal flow.
* `tests/`
  Black-box tests for the unified CLI and sync workflow coverage.
* `cli.py`
  Unified command entry point for validation, assembly, and sync workflows.
* `manifest.yaml`
  Source-library registry for all registered assets, relations, and packs.
* `taxonomy.md`
  Short taxonomy reference for the library structure.

## Specs Taxonomy

`specs/` is organized by four axes:

* `specs/universal-domains/`
  Stable cross-project rules such as requirements, governance, contracts,
  security, testing, verification, AI execution, context engineering, and
  delivery operations.
* `specs/scenarios/`
  Process situations such as debugging, refactoring, release verification,
  rollback decisions, migration safety, and handoff readiness.
* `specs/platforms/`
  Runtime-platform rules such as web/browser behavior, backend-service runtime
  constraints, CLI command contracts, desktop shared and OS-specific behavior,
  Android/iOS lifecycle, HarmonyOS runtime, and miniapp host constraints.
* `specs/technologies/`
  Language-, framework-, runtime-, and tool-specific rules.

Boundary rule:

* `platforms/` and `technologies/` should not directly cross-reference each
  other.
* Common reusable rules should move up into `specs/universal-domains/`.

## Asset Shape

This library uses two source-asset shapes:

* complex concern directories
  Usually a directory with files such as `overview.md`,
  `scope-boundary.md`, `normative-rules.md`, and `verification.md`
* simple single-file assets
  Usually a standalone template, checklist, schema, example, or script

Target projects should treat the concern directory as the smallest import unit
for complex specs.

## How Target Projects Use This Library

Recommended flow:

1. Select assets or packs from `manifest.yaml`.
2. Assemble them into the target project's `.trellis/` directory.
   Spec assets are copied into `.trellis/spec/`; template and checklist assets
   keep their source-relative paths under `.trellis/`.
3. Write the target project's `.trellis/library-lock.yaml`.
4. Optionally generate compiled views for reading convenience.
5. Use controlled downstream sync to receive source-library updates.
6. Use diff and proposal workflows for selective upstream contribution.

Source-library assets remain the source of truth. Generated compiled views are
derived outputs and should not be manually maintained.

Downstream sync expectations:

* imported `target_path` entries in `.trellis/library-lock.yaml` are expected to remain inside `.trellis/`
* merge-mode analysis scans other imported assets for drift by default so scoped operations still surface pending divergence
* `pinned` assets stay read-only by default and only update when the caller explicitly opts in for that sync run

## Recommended Pack Guide

Use packs as a starting point, then add or remove individual assets based on the
target project's real constraints.

Suggested entry points:

* requirements-heavy discovery work
  `pack.requirements-discovery-foundation`
* security and review focused delivery
  `pack.security-and-review-foundation`
* architecture and data shaping work
  `pack.architecture-and-data-foundation`
* debugging, bugfix, and refactoring heavy work
  `pack.debugging-and-refactoring-workbench`
* general API-first backend service
  `pack.api-service-minimal`
* incident-ready backend service
  `pack.incident-ready-service`
* service with frequent cross-layer changes
  `pack.cross-layer-change-heavy-service`
* AI-agent or multi-agent workflow project
  `pack.ai-agent-project-foundation`
* TypeScript web-platform baseline
  `pack.typescript-web-platform-foundation`
* Vue web application baseline
  `pack.vue-web-app-foundation`
* React web application baseline
  `pack.react-web-app-foundation`
* CLI command baseline
  `pack.cli-command-foundation`
* Cross-platform desktop baseline
  `pack.desktop-platform-foundation`
* macOS desktop baseline
  `pack.desktop-macos-foundation`
* Windows desktop baseline
  `pack.desktop-windows-foundation`
* Linux desktop baseline
  `pack.desktop-linux-foundation`
* Android/iOS mobile lifecycle baseline
  `pack.mobile-app-lifecycle-foundation`
* HarmonyOS application baseline
  `pack.harmonyos-app-foundation`
* Miniapp runtime baseline
  `pack.miniapp-runtime-foundation`
* Java Spring service baseline
  `pack.java-spring-service-foundation`
* Python backend baseline
  `pack.python-backend-foundation`
* Go service baseline
  `pack.go-service-foundation`

For concrete pack composition examples, see:

* `examples/assembled-packs/`

Platform-oriented starting points currently available:

* desktop
  Shared cross-platform desktop, plus macOS, Windows, and Linux variants with
  corresponding templates and readiness checklists.
* mobile
  Android/iOS lifecycle baseline plus HarmonyOS runtime baseline.
* miniapp
  Host runtime baseline with capability-matrix template and readiness checklist.
* cli
  Command-interface spec for command contracts, help behavior, and exit
  semantics.

## Sync Model

This library supports two directions:

* downstream sync
  `trellis-library` -> target Trellis project
* upstream contribution
  target Trellis project -> proposal -> controlled apply back into
  `trellis-library`

The expected control points are:

* `manifest.yaml`
  source-library registry
* `.trellis/library-lock.yaml`
  target-project import and state record
* validation scripts
  structural and sync health checks
* proposal / apply scripts
  controlled upstream contribution flow

Any meaningful change to the library's sync model, asset shape, selection flow,
or directory semantics should also update this root `README.md` so the library's
entry documentation stays aligned with actual behavior.

## Main Scripts

Important automation entry points:

* `cli.py`
  Unified wrapper for day-to-day `validate`, `assemble`, `contribute`, and `sync` usage.
* `scripts/validation/validate-library-sync.py`
  Validate source-library registration and sync consistency.
* `scripts/assembly/assemble-init-set.py`
  Assemble selected assets into a target project.
* `scripts/assembly/write-library-lock.py`
  Write the target project's `.trellis/library-lock.yaml`.
* `scripts/contribution/verify-upstream-contribution.py`
  Verify whether local target-project changes are eligible for upstream contribution.
* `scripts/sync/sync-library-assets.py`
  Perform downstream sync into a target project.
* `scripts/sync/diff-library-assets.py`
  Compare target-project local assets against source-library assets.
* `scripts/sync/propose-library-sync.py`
  Generate controlled upstream proposals.
* `scripts/sync/apply-library-sync.py`
  Apply approved upstream proposals back into the source library.

## Unified CLI

For day-to-day usage, prefer the unified CLI entry point:

```bash
python3 trellis-library/cli.py <command> [options]
```

Available commands:

* `validate`
  Run `scripts/validation/validate-library-sync.py`
* `assemble`
  Run `scripts/assembly/assemble-init-set.py`
* `contribute`
  Run `scripts/contribution/verify-upstream-contribution.py`
* `sync`
  Run sync workflows through `--mode`

Examples:

```bash
python3 trellis-library/cli.py validate --strict-warnings

python3 trellis-library/cli.py assemble \
  --target /tmp/test-target \
  --pack pack.go-service-foundation \
  --dry-run

python3 trellis-library/cli.py contribute \
  --target /tmp/test-target \
  --asset spec.technologies.languages.go-package-structure

python3 trellis-library/cli.py sync \
  --mode downstream \
  --target /tmp/test-target \
  --dry-run
```

`sync` mode mapping:

* `--mode downstream`
  Run `scripts/sync/sync-library-assets.py`
* `--mode diff`
  Run `scripts/sync/diff-library-assets.py`
* `--mode propose`
  Run `scripts/sync/propose-library-sync.py`
* `--mode apply`
  Run `scripts/sync/apply-library-sync.py`

## Verification

Use the manifest as the registry and run both structure validation and CLI tests
before claiming library health:

```bash
python3 trellis-library/scripts/validation/validate-library-sync.py --strict-warnings

python3 -m unittest trellis-library/tests/test_cli.py
```

The validation command can also be run through the unified CLI:

```bash
python3 trellis-library/cli.py validate --strict-warnings
```

Current validation schemas live under:

* `schemas/manifest/`
* `schemas/initialization/`

CI also enforces the same baseline through
[`/.github/workflows/trellis-library-ci.yml`](/ops/projects/personal/ai-coding-toolkit/.github/workflows/trellis-library-ci.yml),
running on `pull_request`, on `push` to `main`, and on manual dispatch when
`trellis-library/**` or the workflow itself changes.

## Usage Notes

* Register assets in `manifest.yaml`; do not rely on ad hoc files.
* Keep source assets atomic and reusable; avoid project-private wording in the
  library.
* When changing taxonomy, relation model, sync flow, pack strategy, test
  coverage expectations, or script responsibilities, update this root
  `README.md` in the same change set.
* When a target project improves an imported asset, use diff and proposal
  workflows instead of directly overwriting source assets.
* Keep examples, packs, templates, checklists, and manifest relations aligned
  so selection guidance matches actual registered assets.
