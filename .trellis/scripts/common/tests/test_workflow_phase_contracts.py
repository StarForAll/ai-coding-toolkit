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
        expected_phrases = {
            "1.0": ("create the task", ("create the task", "task.py create")),
            "1.3": ("curate implement.jsonl and check.jsonl", ("implement.jsonl", "check.jsonl")),
            "1.4": ("activate the task", ("task.py start", "in_progress")),
            "3.3": ("update spec", ("trellis-update-spec", "spec update")),
            "3.4": ("drive the commit", ("git commit", "Phase 3.4 commit")),
        }
        status_to_block = {
            "1.0": "no_task",
            "1.3": "planning",
            "1.4": "planning",
            "3.3": "in_progress",
            "3.4": "in_progress",
        }

        required_once_steps = REQUIRED_ONCE_STEP_RE.findall(self.workflow_text)
        self.assertTrue(required_once_steps, "Expected required-once steps in workflow.md")

        for step_id, (_, snippets) in expected_phrases.items():
            with self.subTest(step_id=step_id):
                self.assertIn(step_id, required_once_steps)
                block_name = status_to_block[step_id]
                block_body = self.blocks.get(block_name, "")
                self.assertTrue(block_body, f"Missing workflow-state block: {block_name}")
                self.assertTrue(
                    any(snippet in block_body for snippet in snippets),
                    f"workflow-state:{block_name} must reinforce step {step_id}",
                )

    def test_workflow_state_blocks_cover_stale_and_inline_variants(self) -> None:
        for block_name in (
            "no_task",
            "stale",
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


if __name__ == "__main__":
    unittest.main()
