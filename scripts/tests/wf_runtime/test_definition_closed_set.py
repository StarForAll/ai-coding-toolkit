"""定义的字段闭集与可略声明（机制稿 §7.1、§7.2）。

四件事各一条断言：
- 未登记键被拒（拼错 `required`/`skip` 不再静默改变行为）；
- `required=false` 必须声明完整 `skip`（含 condition）；
- `acceptance[].verification_ids` 必须指向本步骤声明的验证；
- 合法定义不受影响。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import runs  # noqa: E402


def _step(**extra):
    step = {"id": "s1", "type": "task", "title": "t", "inputs": [], "outputs": [],
            "required": True, "skip": None, "human_points": [], "task_kind": "ordinary",
            "goal": "g", "acceptance": ["给人看的验收文本"],
            "actions": [{"id": "a1", "text": "do", "inputs": [], "outputs": [],
                         "required": True, "skip": None, "human_points": []}],
            "verifications": [{"id": "v1", "source": "current_plan",
                               "established_by": {"kind": "current_task"},
                               "stored_in": {"kind": "task_plan", "verification_id": "v1"},
                               "consume_at": "check"}]}
    step.update(extra)
    return step


def _doc(**extra):
    doc = {"format_version": 1, "workflow_id": "probe", "content_version": 1, "purpose": "p",
           "applicability": "a", "inputs": {}, "steps": [_step()], "completion": ["done"]}
    doc.update(extra)
    return doc


def _problems(doc):
    return [item["reason"] for item in runs.validate_definition(doc, None, workflow_id="probe")]


class ClosedSetTest(unittest.TestCase):
    def test_baseline_is_accepted(self):
        self.assertEqual(_problems(_doc()), [])

    def test_unknown_root_key_is_rejected(self):
        self.assertTrue(any("unknown root key" in reason for reason in _problems(_doc(notes="x"))))

    def test_misspelled_required_is_rejected_not_silently_defaulted(self):
        doc = _doc(steps=[_step(requird=False)])
        step = dict(doc["steps"][0])
        step.pop("required")
        doc["steps"] = [step]
        self.assertTrue(any("unknown step key" in reason for reason in _problems(doc)),
                        "拼错 required 必须报出来，不能静默当成必需")

    def test_misspelled_skip_is_rejected(self):
        self.assertTrue(any("unknown step key" in reason
                            for reason in _problems(_doc(steps=[_step(skp={"condition": "c"})]))))

    def test_skippable_without_skip_declaration_is_rejected(self):
        self.assertTrue(any("skippable step must declare skip" in reason
                            for reason in _problems(_doc(steps=[_step(required=False)]))))

    def test_skip_requires_condition(self):
        reasons = _problems(_doc(steps=[_step(required=False,
                                              skip={"decision_point": None, "downstream": []})]))
        self.assertTrue(any("skip.condition" in reason for reason in reasons))

    def test_acceptance_reference_must_be_declared(self):
        doc = _doc(steps=[_step(acceptance=[{"id": "a1", "statement": "x",
                                             "verification_ids": ["v9"]}])])
        self.assertTrue(any("undeclared verification" in reason for reason in _problems(doc)))

    def test_acceptance_reference_to_declared_is_accepted(self):
        doc = _doc(steps=[_step(acceptance=[{"id": "a1", "statement": "x",
                                             "verification_ids": ["v1"]}])])
        self.assertEqual(_problems(doc), [])


if __name__ == "__main__":
    unittest.main()
