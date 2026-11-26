"""跨步骤产物的**事实**核验：解出路径 ≠ 产物存在，缺产物不建下游任务（六轮审查 b-2）。"""

import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import runs  # noqa: E402


def _doc(*steps):
    return {"inputs": {}, "steps": list(steps)}


class StepOutputsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-step-art-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_literal_path_records_existence(self):
        doc = _doc({"id": "a", "type": "task", "outputs": [{"id": "out", "kind": "file",
                                                            "path": "art/a.txt"}]})
        (self.root / "art").mkdir()
        (self.root / "art" / "a.txt").write_text("x\n", encoding="utf-8")
        found = runs._step_outputs(doc, "a", {}, root=self.root)
        self.assertEqual(found[0]["resolved"], True)
        self.assertEqual(found[0]["exists"], True)

    def test_declared_but_missing_artifact_is_not_claimed_as_present(self):
        doc = _doc({"id": "a", "type": "task", "outputs": [{"id": "out", "kind": "file",
                                                            "path": "art/missing.txt"}]})
        found = runs._step_outputs(doc, "a", {}, root=self.root)
        self.assertEqual(found[0]["resolved"], True)
        self.assertFalse(found[0]["exists"], "路径解出但文件不在，不能记成存在")


class UpstreamArtifactGuardTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-step-guard-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "art").mkdir()
        self.step = {"id": "b", "type": "task",
                     "inputs": [{"id": "in", "from": "step", "step": "a", "output": "out"}]}
        self.doc = _doc({"id": "a", "type": "task", "outputs": [{"id": "out", "kind": "file",
                                                                 "path": "art/a.txt"}]},
                        self.step)

    def _results(self, exists):
        return {"a": {"kind": "satisfied",
                      "outputs": [{"id": "out", "path": "art/a.txt", "resolved": True,
                                   "exists": exists}]}}

    def test_ready_artifact_passes(self):
        (self.root / "art" / "a.txt").write_text("x\n", encoding="utf-8")
        ctx = type("C", (), {"root": str(self.root)})()
        runs._require_upstream_outputs(ctx, self.doc, self.step, self._results(True))

    def test_missing_artifact_blocks(self):
        ctx = type("C", (), {"root": str(self.root)})()
        with self.assertRaises(runs.DefinitionError) as caught:
            runs._require_upstream_outputs(ctx, self.doc, self.step, self._results(False))
        self.assertEqual(caught.exception.code, "WF_DEPENDENCY_UNMET")
        self.assertEqual((caught.exception.facts or {})["missing"][0]["output"], "out")

    def test_unsatisfied_upstream_blocks(self):
        ctx = type("C", (), {"root": str(self.root)})()
        with self.assertRaises(runs.DefinitionError) as caught:
            runs._require_upstream_outputs(ctx, self.doc, self.step,
                                           {"a": {"kind": "skipped", "outputs": []}})
        self.assertEqual(caught.exception.code, "WF_DEPENDENCY_UNMET")
        self.assertEqual((caught.exception.facts or {})["missing"][0]["kind"], "skipped")


if __name__ == "__main__":
    unittest.main()
