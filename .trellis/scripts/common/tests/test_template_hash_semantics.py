from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
HASH_FILE = REPO_ROOT / ".trellis/.template-hashes.json"

# Platform deployment directories retired in the 0.7.0 upgrade. Their paths must
# not survive in the hash ledger, and must not be re-pinned in assertions here.
RETIRED_PLATFORM_PREFIXES = (".opencode/", ".qoder/", ".kiro/")

# The receipt values below are what stop `trellis update` from silently
# overwriting repository-local patches. Measured behaviour of
# `analyzeChanges` (dist/commands/update.js, v0.7.0-beta.4), confirmed by
# probing the live CLI:
#
#   existing == incoming template          -> "unchanged"      (skip; receipt ignored)
#   existing != template, receipt == bytes -> "Template updated" (AUTO-UPDATE, no prompt)
#   existing != template, receipt != bytes -> "Modified by you"  (prompts)
#
# So for a file whose content is NOT byte-identical to the incoming template,
# `recorded != actual` IS the overwrite protection, and "repairing" the receipt
# to equal the bytes on disk is exactly what disarms it. Verified against
# `trellis update --dry-run`: precisely these files are listed under
# "Modified by you (need your decision)".
PROTECTED_LOCAL_MODIFICATIONS = (
    # Whole-file local fork. After the 0.7.0 merge it is the upstream template
    # plus the repo-local patches applied by `.trellis/scripts/merge-workflow-md.py`,
    # so its bytes never equal the incoming template. Its receipt is kept
    # divergent on purpose: `existing != template && receipt == bytes` is the
    # auto-update bucket, and would replace the file without prompting.
    ".trellis/workflow.md",
    # Carry the stale_*/task_error breadcrumb normalization patch.
    ".claude/hooks/inject-workflow-state.py",
    ".codex/hooks/inject-workflow-state.py",
    # Carrier for the inline-dispatch project rule.
    ".codex/config.toml",
    ".codex/agents/trellis-check.toml",
    ".codex/agents/trellis-implement.toml",
    ".codex/agents/trellis-research.toml",
    # Retargeted from an upstream-only spec path to a spec that exists in this
    # repository's registry-backed .trellis/spec/ tree.
    ".agents/skills/trellis-meta/references/customize-local/change-task-lifecycle.md",
    ".claude/skills/trellis-meta/references/customize-local/change-task-lifecycle.md",
    # Upstream's Active Task paragraph claims a session-identity *failure*
    # ("may be unable to set the active task ... read the error"). `cmd_start`
    # does not fail: it prints an informational message, still flips
    # `planning` -> `in_progress` and returns 0, so the upstream text sends an
    # AI hunting an error that was never raised and hides the status advance.
    # Same upstream claim as workflow.md patches P1/P6.
    ".agents/skills/trellis-meta/references/local-architecture/task-system.md",
    ".claude/skills/trellis-meta/references/local-architecture/task-system.md",
    # Upstream's JSONL samples point at `.trellis/spec/cli/<layer>/...`, the
    # monorepo layout of the Trellis repository itself. This repository is
    # single-repo — `get_context.py --mode packages` reports no packages and
    # `.trellis/spec/cli/` does not exist — so the samples are retargeted at
    # spec layers that do exist here. That is a content edit, not a refresh,
    # so the receipt has to stay divergent for the patch to be asked about.
    ".agents/skills/trellis-meta/references/local-architecture/spec-system.md",
    ".claude/skills/trellis-meta/references/local-architecture/spec-system.md",
)


def _load_merge_script():
    """Import `.trellis/scripts/merge-workflow-md.py` (hyphenated name)."""
    path = REPO_ROOT / ".trellis/scripts/merge-workflow-md.py"
    spec = importlib.util.spec_from_file_location("merge_workflow_md", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load merge script from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _recorded_hashes() -> dict[str, str]:
    return json.loads(HASH_FILE.read_text(encoding="utf-8"))["hashes"]


def _actual_hash(rel_path: str) -> str:
    return hashlib.sha256((REPO_ROOT / rel_path).read_bytes()).hexdigest()


def _read(rel_path: str) -> str:
    return (REPO_ROOT / rel_path).read_text(encoding="utf-8")


class TemplateHashSemanticsTest(unittest.TestCase):
    """Structural invariants of the ledger, and the protection it provides.

    A previous revision of this file read the ledger as a *local-edit detector*:
    "`recorded != actual` means the repository patched this file", asserted for
    a broad list of files. That reading is unstable across a version jump —
    files resolved through a ``.new`` conflict end up with a receipt that
    matches neither the old nor the new template content — so the protection
    assertion below is scoped to the paths this repository actually patches.
    """

    def test_ledger_entries_refer_to_files_that_exist(self) -> None:
        """Every ledger key must correspond to a file on disk.

        A key whose file is gone is a stale receipt: it makes the ledger claim
        ownership of something that no longer exists, and turns a
        ``recorded[rel_path]`` lookup into a KeyError instead of a real failure.
        """
        recorded = _recorded_hashes()
        missing = sorted(
            rel_path
            for rel_path in recorded
            if not (REPO_ROOT / rel_path).is_file()
        )
        with self.subTest(missing=missing):
            self.assertEqual(missing, [])

    def test_local_modifications_keep_their_overwrite_protection(self) -> None:
        """Locally patched files must stay in the "Modified by you" bucket.

        If a receipt is ever refreshed to equal the on-disk bytes for one of
        these paths, the next `trellis update` refreshes the file without
        prompting and the local patch is lost.
        """
        recorded = _recorded_hashes()
        unprotected: list[str] = []
        for rel_path in PROTECTED_LOCAL_MODIFICATIONS:
            with self.subTest(path=rel_path):
                self.assertIn(rel_path, recorded)
                self.assertTrue(
                    (REPO_ROOT / rel_path).is_file(), f"missing file: {rel_path}"
                )
                if recorded[rel_path] == _actual_hash(rel_path):
                    unprotected.append(rel_path)
        with self.subTest(unprotected=unprotected):
            self.assertEqual(
                unprotected,
                [],
                "receipt refreshed to match disk — local patch is now "
                "overwritable without a prompt",
            )

    def test_only_patched_paths_have_a_divergent_receipt(self) -> None:
        """A diverging receipt must be justified by a local patch.

        ``recorded == actual`` is the pristine signal. The only paths allowed to
        sit outside it are the ones this repository deliberately patches, plus
        the files whose ``.new`` conflict left a receipt that matches neither
        the old nor the new template (a known `trellis update` behaviour that
        cannot be repaired from inside this repository). Anything else that
        diverges is a stale receipt and gets reported here.
        """
        # The three lifecycle/settings paths above oscillate depending on which
        # merge path `trellis update` took; their content is asserted in
        # RepositoryLocalPatchesTest instead of their receipt.
        receipt_may_diverge = set(PROTECTED_LOCAL_MODIFICATIONS)
        receipt_may_diverge |= {
            # Mixed-ownership files. Repo-local edits sit outside the updater's
            # managed sections, so the receipt legitimately diverges from the
            # bytes; keeping it divergent routes them to "Modified by you"
            # instead of the silent auto-update bucket.
            ".trellis/config.yaml",
            ".claude/settings.json",
            # Local content edits made after the 0.7.0 template was written, so
            # the receipt (still the incoming template hash) no longer matches
            # the bytes. Four are the "Skill Routing" -> "Active Task Routing"
            # reference sync; the fifth is a comment correction. A stale receipt
            # here is harmless: nothing about these files is templated.
            ".agents/skills/trellis-meta/references/customize-local/change-workflow.md",
            ".claude/skills/trellis-meta/references/customize-local/change-workflow.md",
            ".agents/skills/trellis-meta/references/local-architecture/workflow.md",
            ".claude/skills/trellis-meta/references/local-architecture/workflow.md",
            ".trellis/scripts/common/task_store.py",
            # Repo-local parser fix: get_phase_index() also strips the tag
            # block's `<!-- Per-turn breadcrumb -->` caption. Upstream's
            # regex leaves it behind, so it is a real local divergence.
            ".trellis/scripts/common/workflow_phase.py",
            # Repo-local doc fix: this repository is single-repo (no packages),
            # so the spec index lives at .trellis/spec/<layer>/index.md. The
            # shipped skill only shows the monorepo <package>/<layer> path.
            ".agents/skills/trellis-before-dev/SKILL.md",
            ".claude/skills/trellis-before-dev/SKILL.md",
            # Repo-local content edit: dropped the trailing blank line at EOF
            # (git diff --check) from the 0.7.0-imported channel reference.
            ".agents/skills/trellis-channel/references/command-reference.md",
            ".claude/skills/trellis-channel/references/command-reference.md",
            # Repo-local content edits: both finish-work carriers now document
            # when to archive with `--skip-branch-validation`, which the shipped
            # template omits (upstream's archive gate refuses a task worked
            # directly on its base branch). Content diverges, receipt stays the
            # incoming template hash so `trellis update` asks first.
            ".agents/skills/trellis-finish-work/SKILL.md",
            ".claude/commands/trellis/finish-work.md",
        }
        recorded = _recorded_hashes()
        unexplained = sorted(
            rel_path
            for rel_path in recorded
            if rel_path not in receipt_may_diverge
            and (REPO_ROOT / rel_path).is_file()
            and recorded[rel_path] != _actual_hash(rel_path)
        )
        with self.subTest(unexplained=unexplained):
            self.assertEqual(unexplained, [])

    def test_retired_platform_paths_are_no_longer_tracked(self) -> None:
        """0.7.0 retired .opencode / .qoder / .kiro; the ledger must agree.

        ``trellis update`` never prunes ledger keys for a platform that stopped
        being configured, so this has to be asserted (and cleaned) explicitly.
        """
        recorded = _recorded_hashes()
        residual = sorted(
            rel_path
            for rel_path in recorded
            if rel_path.startswith(RETIRED_PLATFORM_PREFIXES)
        )
        with self.subTest(residual=residual):
            self.assertEqual(residual, [])

    def test_removed_templates_are_no_longer_tracked(self) -> None:
        recorded = _recorded_hashes()

        for rel_path in (
            ".trellis/scripts/common/registry.py",
            ".trellis/scripts/common/worktree.py",
        ):
            with self.subTest(path=rel_path):
                self.assertNotIn(rel_path, recorded)


class RepositoryLocalPatchesTest(unittest.TestCase):
    """Content assertions for every deliberate local patch.

    The receipt test above proves the updater will *ask* before touching these
    files; this class proves the patch content itself is still in place. Keep
    the set in sync with the "Modified by you" list from
    ``trellis update --dry-run``.
    """

    def test_merged_runtime_modules_carry_the_0_7_0_surface(self) -> None:
        """The 0.7.0 merge into .trellis/scripts/common must stay landed.

        `task.py`, `developer.py`, `task_store.py` and `workflow_selection.py`
        import these names from `common.paths`, so a regression here is an
        ImportError that breaks every `task.py` entry point — the exact failure
        the 0.7.0 merge had to repair.
        """
        paths_surface = (
            "ENV_DEVELOPER",
            "DEVELOPER_HINT",
            "FILE_CURRENT_TASK",
            "def get_developer_workflow",
            "main_worktree_root",
        )
        paths_content = _read(".trellis/scripts/common/paths.py")
        for snippet in paths_surface:
            with self.subTest(module="paths.py", snippet=snippet):
                self.assertIn(snippet, paths_content)

        init_content = _read(".trellis/scripts/common/__init__.py")
        for snippet in ("ENV_DEVELOPER", "DEVELOPER_HINT", "FILE_CURRENT_TASK"):
            with self.subTest(module="__init__.py", snippet=snippet):
                self.assertIn(snippet, init_content)

    def test_inject_workflow_state_keeps_stale_breadcrumb_normalisation(self) -> None:
        """The stale_*/task_error breadcrumb normalization is repository-only.

        Upstream 0.7.0 still *emits* ``stale_<source_type>`` and ``task_error``
        but its ``build_breadcrumb`` has no normalization step, so an
        upstream-only hook degrades both to "Refer to workflow.md for current
        step." Verified against the shipped template:
        ``grep -c display_status`` on
        ``dist/templates/shared-hooks/inject-workflow-state.py`` returns 0.
        """
        for rel_path in (
            ".claude/hooks/inject-workflow-state.py",
            ".codex/hooks/inject-workflow-state.py",
        ):
            content = _read(rel_path)
            with self.subTest(path=rel_path):
                self.assertIn("def _normalize_pseudo_status(", content)
                self.assertIn("display_status", content)
                # Both pseudo-statuses must map onto their own tag block. They
                # are mutually exclusive states: stale = directory gone,
                # task_error = directory present but task.json unreadable.
                for mapping in (
                    'return "stale", "stale"',
                    'return "task_error", "task_error"',
                ):
                    with self.subTest(path=rel_path, mapping=mapping):
                        self.assertIn(mapping, content)
                self.assertIn("_normalize_pseudo_status(", content.split("def _normalize_pseudo_status(")[1])

    def test_codex_config_keeps_inline_rule_and_drops_multi_agent_v2(self) -> None:
        """Project rule survives; the feature table that breaks Codex stays out.

        ``[features.multi_agent_v2]`` was dropped by upstream because the
        structured table form fails on Codex 0.130 and earlier with
        ``data did not match any variant of untagged enum FeatureToml``.
        The parsed table is inspected rather than the text, because the
        upstream explanation comment names the removed key on purpose.
        """
        import tomllib

        rel_path = ".codex/config.toml"
        content = _read(rel_path)
        self.assertIn("main Codex session must remain", content)

        with self.subTest(path=rel_path):
            config = tomllib.loads(content)
            self.assertNotIn(
                "multi_agent_v2",
                config.get("features", {}),
                "the feature table that aborts Codex 0.130 must stay removed",
            )
            self.assertEqual(config.get("agents", {}).get("max_depth"), 1)

    def test_codex_agent_carriers_keep_inline_mode_header(self) -> None:
        header = "# This agent definition is a carrier for explicit delegated/non-inline Codex"
        for rel_path in (
            ".codex/agents/trellis-check.toml",
            ".codex/agents/trellis-implement.toml",
            ".codex/agents/trellis-research.toml",
        ):
            with self.subTest(path=rel_path):
                self.assertTrue(_read(rel_path).startswith(header))

    def test_workflow_md_keeps_platform_routing_blocks(self) -> None:
        """The platform routing contract must survive any workflow.md refresh.

        After the 0.7.0 merge this file is the upstream template plus the
        repo-local patches applied by ``.trellis/scripts/merge-workflow-md.py``; the
        routing blocks themselves are upstream-owned. Upstream renamed the old
        ``### Skill Routing`` / ``### DO NOT skip skills`` sections to
        ``### Active Task Routing`` / ``### Guardrails``, so assert the routing
        *contract* — both capability groups still route intents to skills — and
        not the retired section names.
        """
        content = _read(".trellis/workflow.md")
        for marker in (
            "### Active Task Routing",
            "### Guardrails",
            "### Request Triage",
            "### Planning Artifacts",
            "### Parent / Child Task Trees",
        ):
            with self.subTest(section=marker):
                self.assertIn(marker, content)

        for route in (
            "[Claude Code, Cursor, OpenCode, codex-sub-agent",
            "[codex-inline,",
            "`trellis-brainstorm`",
            "`trellis-implement`",
            "`trellis-check`",
            "`trellis-break-loop`",
            "`trellis-update-spec`",
        ):
            with self.subTest(routing=route):
                self.assertIn(route, content)

        for retired in ("### Skill Routing", "### DO NOT skip skills"):
            with self.subTest(retired=retired):
                self.assertNotIn(retired, content)

    def test_workflow_md_matches_the_recorded_merge_inputs(self) -> None:
        """`workflow.md` must equal the recorded baseline plus the patch list.

        The file is generated, not hand-maintained: a hand edit either diverges
        from `merge-workflow-md.py`'s PATCHES here, or is silently reverted the
        next time the merge runs. Asserting the two agree is what keeps the
        merge script usable as the upgrade record.
        """
        module = _load_merge_script()
        merged = module.TEMPLATE.read_text(encoding="utf-8")
        for label, anchor, replacement in module.PATCHES:
            with self.subTest(patch=label):
                self.assertEqual(
                    merged.count(anchor),
                    1,
                    f"[{label}] anchor does not occur exactly once",
                )
            merged = merged.replace(anchor, replacement, 1)
        self.assertEqual(
            merged,
            module.TARGET.read_text(encoding="utf-8"),
            "workflow.md is not baseline + PATCHES; re-run "
            ".trellis/scripts/merge-workflow-md.py or update its PATCHES",
        )

    def test_task_system_documents_the_degraded_start_it_actually_has(self) -> None:
        """The bundled task-system reference must match `cmd_start`'s behaviour.

        Upstream still says the AI should "read the error" when no session
        identity is available, but `task.py start` degrades instead: status
        still advances and the command exits 0. The patched copies must say so,
        or an AI treats a successful degraded start as a failure and skips the
        recovery step.
        """
        self.assertIn("Degraded mode", _read(".trellis/scripts/task.py"))
        for rel_path in (
            ".agents/skills/trellis-meta/references/local-architecture/task-system.md",
            ".claude/skills/trellis-meta/references/local-architecture/task-system.md",
        ):
            content = _read(rel_path)
            with self.subTest(path=rel_path):
                self.assertIn("falls back to degraded mode", content)
                self.assertNotIn("The AI should read the error", content)

    def test_task_system_documents_the_empty_manifest_start_it_refuses_without(self) -> None:
        """The recovery advice must name the flag ``cmd_start`` refuses without.

        ``cmd_start`` gates on a manifest that exists but holds zero curated
        entries and returns 1 unless ``--allow-empty-context`` is passed. Inline
        platforms never curate the manifests, so the plain ``task.py start
        <task-dir>`` the reference used to recommend is exactly the command that
        fails for them.
        """
        for rel_path in (
            ".agents/skills/trellis-meta/references/local-architecture/task-system.md",
            ".claude/skills/trellis-meta/references/local-architecture/task-system.md",
        ):
            with self.subTest(path=rel_path):
                self.assertIn("--allow-empty-context", _read(rel_path))

    def test_workflow_md_create_command_carries_the_required_description(self) -> None:
        """Every `task.py create` form in workflow.md must show `--description`.

        ``cmd_create`` returns 1 for a blank or missing description, so a
        documented form without the flag is a command that cannot be run. The
        shipped 0.7.0 template still shows the pre-0.7.0 forms, so the merge
        patches them — this keeps the next baseline bump from dropping it.
        """
        content = _read(".trellis/workflow.md")
        forms = [
            line
            for line in content.splitlines()
            if "task.py create" in line
            and ('"<title>"' in line or '"<task title>"' in line)
        ]
        with self.subTest(check="forms found"):
            self.assertGreaterEqual(len(forms), 3, forms)
        for line in forms:
            with self.subTest(form=line[:80]):
                self.assertIn("--description", line)

    def test_finish_work_documents_the_non_pr_archive_path(self) -> None:
        """Both finish-work carriers must name `--skip-branch-validation`.

        `_validate_branch_metadata` refuses to archive a task whose `branch`
        equals its `base_branch`, which is exactly the metadata of work done
        directly on `main`: `create` stamps `base_branch` from the repo default
        and `start` records the checked-out branch. The flag is the documented
        escape for a task that never had a branch of its own, so a finish-work
        carrier that omits it leaves the ordinary local flow unable to close
        out — while still needing to send real PR tasks to `set-branch` /
        `set-base-branch` instead.
        """
        self.assertIn("--skip-branch-validation", _read(".trellis/scripts/task.py"))
        for rel_path in (
            ".agents/skills/trellis-finish-work/SKILL.md",
            ".claude/commands/trellis/finish-work.md",
        ):
            content = _read(rel_path)
            with self.subTest(path=rel_path):
                self.assertIn("--skip-branch-validation", content)
                # The flag must stay scoped: PR-backed tasks are repaired, not
                # waved through with a validation skip.
                self.assertIn("set-branch", content)
                self.assertIn("set-base-branch", content)

    def test_task_system_and_spec_system_refresh_claims_are_example_paths(self) -> None:
        """Sample context paths must resolve inside this repository.

        Both references used to show `.trellis/spec/cli/...`, which is the
        Trellis repository's own monorepo layout. This repository has no
        packages, so the samples are rewritten as paths that exist here — and
        the rewrite has to be re-proved whenever either file is refreshed.
        """
        examples = {
            ".agents/skills/trellis-meta/references/local-architecture/task-system.md": (
                ".trellis/spec/docs/index.md",
            ),
            ".claude/skills/trellis-meta/references/local-architecture/task-system.md": (
                ".trellis/spec/docs/index.md",
            ),
            ".agents/skills/trellis-meta/references/local-architecture/spec-system.md": (
                ".trellis/spec/docs/index.md",
                ".trellis/spec/library-assets/index.md",
            ),
            ".claude/skills/trellis-meta/references/local-architecture/spec-system.md": (
                ".trellis/spec/docs/index.md",
                ".trellis/spec/library-assets/index.md",
            ),
        }
        for rel_path, paths in examples.items():
            content = _read(rel_path)
            with self.subTest(path=rel_path):
                # A path in a fenced sample is a literal at best; assert both
                # that the sample carries one and that the file exists.
                self.assertNotIn(".trellis/spec/cli/", content)
                for spec_path in paths:
                    with self.subTest(path=rel_path, spec=spec_path):
                        self.assertIn(spec_path, content)
                        self.assertTrue((REPO_ROOT / spec_path).is_file())

    def test_claude_settings_keeps_preserved_status_line(self) -> None:
        """``statusLine`` is user-owned, so the updater must re-attach it.

        The shipped template omits it; ``preserveExistingClaudeStatusLine``
        copies it back at update time. Its absence means the merge dropped it.
        """
        settings = json.loads(_read(".claude/settings.json"))
        self.assertIn("statusLine", settings)
        hooks = settings.get("hooks", {})
        for event in ("SessionStart", "PostToolUse", "PreToolUse", "UserPromptSubmit"):
            with self.subTest(event=event):
                self.assertIn(event, hooks)

    def test_research_agents_keep_skill_and_mcp_access(self) -> None:
        carrier = _read(".claude/agents/trellis-research.md")
        tools_lines = [ln for ln in carrier.splitlines() if ln.startswith("tools:")]
        with self.subTest(check="claude tools: line"):
            self.assertEqual(len(tools_lines), 1, tools_lines)
        for snippet in ("Skill", "mcp__"):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, tools_lines[0])

        codex_carrier = _read(".codex/agents/trellis-research.toml")
        for snippet in (
            "Trellis Context Loading Protocol",
            "Active task: <path>",
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, codex_carrier)


class MergeWorkflowMdGuardTest(unittest.TestCase):
    """`.trellis/workflow.md` may only be rewritten against a proven baseline.

    ``merge-workflow-md.py`` takes the recorded 0.7.0 baseline on trust and
    rewrites the whole file, so its cross-check is a mandatory precondition,
    not a best-effort diagnostic. These tests pin that: a machine that cannot
    produce the shipped template must fail the run rather than merge.
    """

    def setUp(self) -> None:
        self.module = _load_merge_script()
        self._env = dict(os.environ)

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._env)

    def test_missing_shipped_template_aborts_without_writing_the_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "workflow.md"
            target.write_text("sentinel: must survive an aborted run\n", encoding="utf-8")
            self.module.TARGET = target
            self.module.discover_shipped_template = lambda: (None, "")
            os.environ.pop(self.module.SHIPPED_TEMPLATE_ENV, None)
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                exit_code = self.module.main()
            with self.subTest(exit_code=exit_code):
                self.assertEqual(exit_code, 1)
            self.assertEqual(
                target.read_text(encoding="utf-8"),
                "sentinel: must survive an aborted run\n",
            )
            # The message has to name the remedy, because finding the installed
            # package is exactly what the operator now has to do.
            self.assertIn("ABORT", stderr.getvalue())
            self.assertIn(self.module.SHIPPED_TEMPLATE_ENV, stderr.getvalue())

    def test_unresolvable_override_aborts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ[self.module.SHIPPED_TEMPLATE_ENV] = str(Path(tmp) / "absent")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                exit_code = self.module.main()
            self.assertEqual(exit_code, 1)
            self.assertIn("ABORT", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
