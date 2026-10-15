from __future__ import annotations

import importlib.util
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
WORKFLOW_MD = REPO_ROOT / ".trellis" / "workflow.md"
HOOK_SCRIPT = REPO_ROOT / ".codex" / "hooks" / "inject-workflow-state.py"


WORKFLOW_STATE_RE = re.compile(
    r"\[workflow-state:([A-Za-z0-9_-]+)\]\s*\n(.*?)\n\s*\[/workflow-state:\1\]",
    re.DOTALL,
)
REQUIRED_ONCE_STEP_RE = re.compile(r"^- (\d+\.\d+) .*\[required · once\]", re.MULTILINE)


class WorkflowPhaseContractsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow_text = WORKFLOW_MD.read_text(encoding="utf-8")
        cls.blocks = {
            match.group(1): match.group(2)
            for match in WORKFLOW_STATE_RE.finditer(cls.workflow_text)
        }
        spec = importlib.util.spec_from_file_location("trellis_hook", HOOK_SCRIPT)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load hook module from {HOOK_SCRIPT}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.hook_module = module

    def test_required_once_constraints_are_represented_in_workflow_state_blocks(self) -> None:
        """Every `[required · once]` step must be reinforced in its tag block.

        Assertions are grouped as "any of these" rather than pinned to one
        exact sentence: the 0.7.0 template rewrote the block prose (step 1.0
        now says "create a Trellis task", the in_progress block says
        "commit (Phase 3.4)"), while the contract — a mandatory step must be
        mentioned in the breadcrumb that gates it — is unchanged. Pinning
        upstream wording here would re-break the test on every template refresh
        without catching a real regression.
        """
        # step id -> (block, groups of substring alternatives)
        reinforcement = {
            "1.0": ("no_task", (("task.py create", "Trellis task"), ("consent", "ask"))),
            "1.3": ("planning", (("implement.jsonl", "check.jsonl"),)),
            "1.4": ("planning", (("task.py start",), ("review", "in_progress"))),
            "3.3": ("in_progress", (("trellis-update-spec", "spec update"),)),
            "3.4": ("in_progress", (("commit",), ("Phase 3.4", "finish-work"))),
        }

        required_once_steps = REQUIRED_ONCE_STEP_RE.findall(self.workflow_text)
        self.assertTrue(required_once_steps, "Expected required-once steps in workflow.md")

        for step_id, (block_name, group_list) in reinforcement.items():
            with self.subTest(step_id=step_id):
                self.assertIn(step_id, required_once_steps)
                block_body = self.blocks.get(block_name, "")
                self.assertTrue(block_body, f"Missing workflow-state block: {block_name}")
                for group in group_list:
                    self.assertTrue(
                        any(snippet in block_body for snippet in group),
                        f"workflow-state:{block_name} must reinforce step {step_id} "
                        f"(none of {group!r} present)",
                    )

    def test_workflow_state_blocks_cover_stale_and_inline_variants(self) -> None:
        for block_name in (
            "no_task",
            "stale",
            "task_error",
            "planning",
            "planning-inline",
            "in_progress",
            "in_progress-inline",
            "completed",
        ):
            with self.subTest(block_name=block_name):
                self.assertIn(block_name, self.blocks)

    def test_python_hook_maps_stale_pseudo_status_to_stale_block(self) -> None:
        breadcrumb = self.hook_module.build_breadcrumb(
            "sample-task",
            "stale_session",
            self.blocks,
            source="session:demo",
        )
        self.assertIn("Task: sample-task (stale)", breadcrumb)
        self.assertIn("Active task pointer is stale", breadcrumb)
        self.assertNotIn("Refer to workflow.md for current step.", breadcrumb)

    def test_python_hook_maps_codex_inline_stale_pseudo_status_to_stale_block(self) -> None:
        breadcrumb = self.hook_module.build_breadcrumb(
            "sample-task",
            "stale_session",
            self.blocks,
            source="session:demo",
            breadcrumb_key="stale_session-inline",
        )
        self.assertIn("Task: sample-task (stale)", breadcrumb)
        self.assertIn("Active task pointer is stale", breadcrumb)
        self.assertNotIn("Refer to workflow.md for current step.", breadcrumb)

    def test_python_hook_maps_task_error_pseudo_status_to_task_error_block(self) -> None:
        """0.7.0 adds a task_error state; the hook must key it to its own block.

        ``task_error`` means the task directory exists but its ``task.json`` is
        unreadable, which is mutually exclusive with ``stale`` (directory gone)
        — so it must NOT be folded into the stale block.
        """
        for status, breadcrumb_key in (
            ("task_error", None),
            ("task_error", "task_error-inline"),
        ):
            with self.subTest(status=status, breadcrumb_key=breadcrumb_key):
                breadcrumb = self.hook_module.build_breadcrumb(
                    "sample-task",
                    status,
                    self.blocks,
                    source="session:demo",
                    breadcrumb_key=breadcrumb_key,
                )
                self.assertIn("Task: sample-task (task_error)", breadcrumb)
                self.assertIn("active task record could not be read", breadcrumb.lower())
                self.assertNotIn("Active task pointer is stale", breadcrumb)
                self.assertNotIn("Refer to workflow.md for current step.", breadcrumb)

    def test_python_header_does_not_surface_degraded_source(self) -> None:
        breadcrumb = self.hook_module.build_breadcrumb(
            "sample-task",
            "in_progress",
            self.blocks,
            source="degraded",
            breadcrumb_key="in_progress-inline",
        )
        self.assertIn("sample-task", breadcrumb)
        self.assertNotIn("(in_progress · degraded)", breadcrumb)

    def test_workflow_documents_live_degraded_start_behavior(self) -> None:
        self.assertIn("falls back to degraded mode", self.workflow_text)
        self.assertIn("AI continues based on conversation context", self.workflow_text)
        self.assertNotIn("fails with a session identity hint", self.workflow_text)

    def test_workflow_does_not_reference_missing_contract_files(self) -> None:
        self.assertNotIn(
            ".trellis/spec/cli/backend/workflow-state-contract.md",
            self.workflow_text,
        )
        self.assertNotIn(
            ".trellis/scripts/inject-workflow-state.py",
            self.workflow_text,
        )

    def test_degraded_start_recovery_hint_names_a_real_command(self) -> None:
        """The documented degraded-mode recovery must match the real CLI.

        ``task.py start`` can advance a task to `in_progress` without persisting
        an active-task pointer (no session identity). The workflow tells the
        reader how to find that task again, and that hint is only useful while
        the command it names still exists with the flags it shows.
        """
        self.assertIn("task.py list --status in_progress", self.workflow_text)

        import subprocess
        import sys

        run = subprocess.run(
            [sys.executable, str(REPO_ROOT / ".trellis/scripts/task.py"), "list", "--status", "in_progress"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        with self.subTest(check="--status is accepted"):
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertNotIn("unrecognized arguments", run.stderr)

    def test_phase_index_payload_carries_no_tag_blocks_or_captions(self) -> None:
        """`get_phase_index()` feeds the SessionStart orientation payload.

        Tag blocks are injected separately per turn, so neither the blocks, nor
        their bare `[workflow-state:...]` names, nor the optional
        `<!-- Per-turn breadcrumb: ... -->` captions may survive into the
        payload. The caption stripping is a repo-local parser fix: upstream's
        regex consumes the block but leaves the caption behind, which then
        accumulates every time a block is added.
        """
        from common import workflow_phase

        payload = workflow_phase.get_phase_index()
        with self.subTest(check="payload not empty"):
            self.assertIn("## Phase Index", payload)

        for line in payload.splitlines():
            with self.subTest(line=line[:60]):
                self.assertFalse(
                    re.match(r"^\s*\[/?workflow-state:", line),
                    f"bare tag line leaked: {line!r}",
                )
                self.assertNotIn("Per-turn breadcrumb", line)

        # The three sections the merge introduced must still be present.
        for section in ("### Request Triage", "### Planning Artifacts", "### Parent / Child Task Trees"):
            with self.subTest(section=section):
                self.assertIn(section, payload)

    def test_phase_index_never_deletes_prose_between_a_comment_and_a_block(self) -> None:
        """Stripping captions must not run across the prose in front of a block.

        Captions are not always adjacent to their block: the real ``in_progress``
        and ``completed`` captions sit above a paragraph that belongs to the
        Phase Index payload, with the tag block below it. A caption pattern that
        spans from the caption to the block's tag therefore has to swallow that
        paragraph, and an unbounded ``.*?`` does exactly that — silently dropping
        real orientation content. This pins the fix: the caption is stripped, the
        block is stripped, and the prose between them survives. The stripping
        mirrors the official SessionStart hook's independent passes, and that
        independence is what makes a spanning match impossible.
        """
        from common import workflow_phase

        synthetic = (
            "## Phase Index\n"
            "\n"
            "Prose paragraph A.\n"
            "\n"
            "<!-- a normal explanatory comment -->\n"
            "\n"
            "Prose paragraph B that must survive.\n"
            "\n"
            "<!-- Per-turn breadcrumb: shown while status='in_progress'.\n"
            "     Second caption line. -->\n"
            "\n"
            "Prose paragraph C between the caption and its block.\n"
            "\n"
            "[workflow-state:in_progress]\n"
            "Block body.\n"
            "[/workflow-state:in_progress]\n"
            "\n"
            "## Phase 1: Plan\n"
        )
        original = workflow_phase._read_workflow
        workflow_phase._read_workflow = lambda: synthetic
        try:
            payload = workflow_phase.get_phase_index()
        finally:
            workflow_phase._read_workflow = original

        with self.subTest(check="caption stripped"):
            self.assertNotIn("Per-turn breadcrumb", payload)
        with self.subTest(check="tag block stripped"):
            self.assertNotIn("[workflow-state:", payload)
        # The comment pass is the official hook's, so it drops HTML comments
        # wholesale rather than only the `Per-turn breadcrumb:` captions.
        with self.subTest(check="all HTML comments stripped"):
            self.assertNotIn("<!--", payload)
        for survivor in (
            "Prose paragraph A.",
            "Prose paragraph B that must survive.",
            "Prose paragraph C between the caption and its block.",
        ):
            with self.subTest(check=f"prose kept: {survivor[:40]}"):
                self.assertIn(survivor, payload)

    def test_trellis_meta_change_task_lifecycle_references_live_paths(self) -> None:
        """Carrier docs must point at contract locations that actually exist here.

        Two guards live in this case:

        1. Every ``.trellis/spec/**.md`` path these docs cite must resolve on
           disk. 0.7.0 shipped a reference to
           ``.trellis/spec/cli/backend/workflow-state-contract.md`` — a path from
           the upstream spec layout that this repository's registry-backed
           ``.trellis/spec/`` tree does not have. That reference was first
           retargeted to a local spec and then dropped entirely: the local spec
           it pointed at never carried a status-writer table either, so the doc
           now names the real contract locations instead. The generic existence
           check stays as the guard for whatever spec path a later edit adds.
        2. Each doc must still send readers to the live contract — either
           ``.trellis/workflow.md`` or a ``.trellis/scripts/`` implementation —
           so the pointer cannot silently rot into prose with no destination.

        Only platforms this repository still deploys are covered; ``.opencode``
        / ``.qoder`` / ``.kiro`` were retired in the 0.7.0 upgrade.
        """
        rel_paths = (
            ".agents/skills/trellis-meta/references/customize-local/change-task-lifecycle.md",
            ".claude/skills/trellis-meta/references/customize-local/change-task-lifecycle.md",
        )
        spec_ref_re = re.compile(r"\.trellis/spec/[A-Za-z0-9_./-]+\.md")
        live_pointer_re = re.compile(r"\.trellis/(?:workflow\.md|scripts/[A-Za-z0-9_./-]+)")
        for rel_path in rel_paths:
            content = (REPO_ROOT / rel_path).read_text(encoding="utf-8")

            live_pointers = sorted(set(live_pointer_re.findall(content)))
            with self.subTest(path=rel_path, found=bool(live_pointers)):
                self.assertTrue(
                    live_pointers,
                    "doc no longer points at .trellis/workflow.md or a "
                    ".trellis/scripts/ implementation",
                )

            for spec_ref in sorted(set(spec_ref_re.findall(content))):
                with self.subTest(path=rel_path, spec_ref=spec_ref):
                    self.assertTrue(
                        (REPO_ROOT / spec_ref).is_file(),
                        f"dangling spec reference: {spec_ref}",
                    )


if __name__ == "__main__":
    unittest.main()
