"""P1-2 收口：`step_results` 的产物引用与「续做不依赖 creation 文件」（机制稿 §7.3）。

两件都可机械判定：
- 步骤产物按定义解析成路径引用（字面路径直接用；`{input: name}` 按实例输入解析；
  解不出就**保留声明并标 `resolved: false`**——不猜路径）；
- `run create` 的动作意图固定完整 creation 本体，续做时不必再读 creation 文件。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import runs  # noqa: E402

DOC = {"steps": [{"id": "s1", "outputs": [
    {"id": "literal", "kind": "delivery", "path": "docs/report.md"},
    {"id": "from-input", "kind": "delivery", "path": {"input": "target"}},
    {"id": "unresolved", "kind": "delivery", "path": {"input": "missing"}},
]}]}


class StepOutputsTest(unittest.TestCase):
    def test_literal_path_is_resolved(self):
        outputs = runs._step_outputs(DOC, "s1", {})
        literal = next(item for item in outputs if item["id"] == "literal")
        self.assertEqual(literal["path"], "docs/report.md")
        self.assertTrue(literal["resolved"])

    def test_input_reference_is_resolved_from_instance_inputs(self):
        outputs = runs._step_outputs(DOC, "s1", {"target": "pkg/x.py"})
        entry = next(item for item in outputs if item["id"] == "from-input")
        self.assertEqual(entry["path"], "pkg/x.py")
        self.assertEqual(entry["from_input"], "target")
        self.assertTrue(entry["resolved"])

    def test_unresolvable_reference_is_kept_but_flagged(self):
        outputs = runs._step_outputs(DOC, "s1", {})
        entry = next(item for item in outputs if item["id"] == "unresolved")
        self.assertFalse(entry["resolved"], "解不出必须标 resolved=false，不猜路径")
        self.assertEqual(entry["path"], {"input": "missing"})

    def test_unknown_step_returns_empty(self):
        self.assertEqual(runs._step_outputs(DOC, "nope", {}), [])


if __name__ == "__main__":
    unittest.main()
