"""独立 repro `--list` 的纯选择面：不取租约、不建结果/pycache、不读 state。"""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
RUN = REPO / "scripts" / "tests" / "wf_runtime" / "full" / "repro" / "run.sh"


class ReproListTest(unittest.TestCase):
    def test_list_is_pure_and_needs_no_release_env(self):
        with tempfile.TemporaryDirectory(prefix="wf-repro-list-") as cache:
            env = {**os.environ, "WF_TEST_RUN_CACHE": cache}
            for key in ("WF_RESULTS_CACHE", "WF_RELEASE_TREE", "WF_RELEASE_REF", "WF_RELEASE_VERSION",
                        "WF_FIXTURE_DEPLOY", "WF_RELEASE_CONTEXT", "WF_TEST_SCOPE_ROOT",
                        "WF_REPRO_RESULTS", "WF_PYCACHE"):
                env.pop(key, None)
            result = subprocess.run(["bash", str(RUN), "--list"], capture_output=True, text=True,
                                    env=env, cwd=str(REPO), timeout=120)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            lines = [line for line in result.stdout.splitlines() if "\t" in line]
            self.assertGreater(len(lines), 50, "list 必须输出用例/模式")
            self.assertIn("both", lines[0])
            self.assertEqual(sorted(os.listdir(cache)), [], "list 不得写 state 或结果")

    def test_list_rejects_unknown_options(self):
        result = subprocess.run(["bash", str(RUN), "--list", "--bogus"], capture_output=True, text=True,
                                cwd=str(REPO), timeout=120)
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
