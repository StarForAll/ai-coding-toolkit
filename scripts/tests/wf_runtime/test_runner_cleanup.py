"""Command-level cleanup aggregation (AC08): unknown must preserve the site."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

FULL = Path(__file__).resolve().parent / "full"


def _load():
    spec = importlib.util.spec_from_file_location("wf_runner_cleanup",
                                                  FULL / "runner_cleanup.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RunnerCleanupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-runner-cleanup-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.module = _load()

    def write(self, name, supervision):
        (self.root / name).write_text(json.dumps({"name": name, "supervision": supervision}))

    def test_all_cleaned_is_success(self):
        self.write("a.test.log.json", {"cleanup_state": "cleaned"})
        self.assertEqual(self.module.unknown_units(self.root), [])

    def test_unknown_failed_and_unreadable_are_reported(self):
        self.write("a.test.log.json", {"cleanup_state": "unknown"})
        self.write("b.test.log.json", {"cleanup_state": "failed"})
        (self.root / "c.test.log.json").write_text("{broken")
        self.write(".runner.json", {"cleanup_state": "unknown"})
        findings = self.module.unknown_units(self.root)
        self.assertEqual(sorted(item["unit"] for item in findings),
                         sorted(["a", "b", "c", "wf-runner"]))
        self.assertEqual({item["state"] for item in findings if item["unit"] == "c"},
                         {"unreadable"})

    def test_cli_exit_code_and_shell_payload(self):
        import subprocess
        import sys
        self.write("a.test.log.json", {"cleanup_state": "unknown"})
        result = subprocess.run([sys.executable, str(FULL / "runner_cleanup.py"),
                                 "--results-dir", str(self.root), "--format", "sh"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("CLEANUP_UNKNOWN_COUNT=1", result.stdout)
        self.assertIn("a:unknown", result.stdout)


if __name__ == "__main__":
    unittest.main()
