# Optimize Workflow Installer Integration Tests

## Goal

Reduce the runtime of the workflow installer integration test suite without weakening the behavioral coverage of `install-workflow.py`, post-install checks, upgrade compatibility checks, or uninstall behavior.

## Requirements

- Keep production installer behavior unchanged.
- Add a test-only installed-fixture cache that builds each required installed fixture variant once per unittest process.
- Return a copied fixture per test so tests can mutate files without cross-test pollution.
- Keep real subprocess installer coverage for installer semantics that must be observed directly:
  - profile selection and interactive/non-interactive behavior
  - dry-run/no-write behavior
  - prerequisite failures
  - `WORKFLOW_EMBED_EXECUTOR_CONFIRMED` enforcement
  - attempt-record success and failure handling
  - first-install state blocking
  - at least one all-CLI standard install smoke path
  - profile/CLI variants that prove install output differs
- Convert artifact-only, upgrade-drift, upgrade-merge, and uninstall tests to start from cloned installed fixtures where doing so does not change the behavior under test.
- Do not add a test switch that skips installer post-install self-checks; cache construction must still run the full install path including `upgrade-compat.py --check`.
- Do not introduce a persistent cross-run cache.

## Acceptance Criteria

- [ ] Repeated full `install_workflow()` calls are reduced materially by using cached installed fixtures for downstream-state tests.
- [ ] Cached fixtures are cloned before each test receives them.
- [ ] Fresh install tests remain for the installer behavior boundaries listed above.
- [ ] The modified installer test file passes targeted unittest runs.
- [ ] The full `test_workflow_installers.py` suite is attempted and the actual result is reported.
- [ ] `git status --short` shows only intentional task/code changes.

## Definition of Done

- Tests updated and passing where feasible.
- No production installer behavior changed unless separately justified.
- No new external dependency introduced.
- Verification output is reported truthfully.

## Technical Approach

Introduce class-level test helper methods in `WorkflowInstallerTests`:

- A process-local cache root created in `setUpClass` and removed in `tearDownClass`.
- A cache key that includes `create_fixture` options and installer args/profile/CLI.
- A builder that creates a baseline fixture, runs the real installer once, asserts success, and stores the installed state.
- A clone helper that copies the cached installed state into a fresh temp directory and registers cleanup for the clone.

Then migrate tests in phases:

1. Add helpers and verify a small set of tests still passes.
2. Migrate artifact-only post-install assertions.
3. Migrate upgrade/uninstall tests that mutate installed state after cloning.
4. Keep direct install tests where install behavior itself is the subject.

## Decision (ADR-lite)

Context: The current suite repeatedly runs full installer subprocesses. Static inspection found 165 installer tests, with roughly 130 tests invoking real `install_workflow()`. A representative real install test took about 2.46 seconds, while a static test took about 0.001 seconds.

Decision: Use process-local cached installed fixtures for downstream-state tests, while retaining fresh installer smoke and boundary tests.

Consequences: Suite runtime should drop significantly. The main risk is accidentally moving an installer-behavior test onto a cached fixture, so migration must be conservative and verified incrementally.

## Out of Scope

- Changing `install-workflow.py` runtime behavior.
- Skipping post-install self-checks.
- Adding pytest, xdist, or other test dependencies.
- Creating persistent disk caches across test runs.

## Technical Notes

- Primary file: `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- Installer path includes initial pack import and post-install `upgrade-compat.py --check`, so repeated full installs are expensive.
- Workflow managed-surface constants are owned by `docs/workflows/新项目开发工作流/commands/workflow_assets.py`.
