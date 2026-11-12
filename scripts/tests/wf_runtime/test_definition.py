"""P1-1：定义准备与静态校验（机制稿 §7.1 格式、§7.2 固定六阶段）。

只做**可机械判定**的部分：格式/schema、局部 id 与保留前缀、引用来源与顺序、路径、
required/skip 与替代映射、完成/验证/人判声明。定义写得够不够清楚、某个 skip 条件该不该
被认可，是人的判断，不在这层。

六阶段是**固定顺序**（机制稿 §7.2「依次检查」），所以问题清单按 `stage` 排序返回——
AI 修的时候按顺序走，不会一边改引用一边被 schema 问题重新打回。
"""

import copy
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import runs  # noqa: E402

# 机制稿 §7.1 的示例定义：它必须干净通过，否则「示例即文档」这条就不成立
SAMPLE = {
    "format_version": 1, "workflow_id": "bounded-change", "content_version": 1,
    "purpose": "完成一个已限定范围的变更", "applicability": "已有项目基线与配置",
    "inputs": {"request": {"type": "text", "required": True, "description": "人的变更要求"}},
    "steps": [{
        "id": "change", "type": "task", "title": "实施变更", "task_kind": "ordinary",
        "inputs": [{"from": "input", "name": "request"}], "outputs": [],
        "required": True, "skip": None,
        "human_points": [{"id": "approve-plan", "question": "是否批准当前规划与复杂度？"}],
        "goal": "按输入形成规划并完成获批变更",
        "acceptance": ["当前批准的验收项实际通过"],
        "actions": [{"id": "work", "text": "在当前任务批准范围内实现并验证",
                     "inputs": [], "outputs": [], "required": True, "skip": None,
                     "human_points": []}],
        "verifications": [{"id": "task-check", "source": "current_plan",
                           "established_by": {"kind": "current_task"},
                           "stored_in": {"kind": "task_plan", "verification_id": "task-check"},
                           "consume_at": "check"}],
    }],
    "completion": ["change 对应任务正常归档"],
}


def _doc(**changes):
    doc = copy.deepcopy(SAMPLE)
    doc.update(changes)
    return doc


def _steps(doc, step):
    doc["steps"] = [step]
    return doc


def _base_step(**changes):
    step = copy.deepcopy(SAMPLE["steps"][0])
    step.update(changes)
    return step


def _problems(doc, workflow_id=None):
    return runs.validate_definition(doc, None, workflow_id=workflow_id)


def _stages(doc):
    return sorted({item["stage"] for item in _problems(doc)})


def _wrap(text_body):
    return "<!-- wf-definition:v1 -->\n```json\n" + text_body + "\n```\n"


class DefinitionParseTest(unittest.TestCase):
    def test_sample_definition_is_clean(self):
        doc, problems = runs.parse_definition(_wrap(json.dumps(SAMPLE, ensure_ascii=False)))
        self.assertEqual(problems, [])
        self.assertEqual(_problems(doc, workflow_id="bounded-change"), [])

    def test_marker_missing(self):
        doc, problems = runs.parse_definition("```json\n{}\n```\n")
        self.assertIsNone(doc)
        self.assertEqual(problems[0]["stage"], 1)

    def test_marker_must_be_unique(self):
        doc, problems = runs.parse_definition(_wrap("{}") + "\n<!-- wf-definition:v1 -->\n")
        self.assertIsNone(doc)
        self.assertIn("unique", problems[0]["reason"])

    def test_block_must_be_adjacent_to_the_marker(self):
        text = "<!-- wf-definition:v1 -->\n\n说明段落\n\n```json\n{}\n```\n"
        _doc, problems = runs.parse_definition(text)
        self.assertIsNone(_doc)
        self.assertIn("directly follow", problems[0]["reason"])

    def test_invalid_json_is_reported_not_raised(self):
        doc, problems = runs.parse_definition(_wrap("{"))
        self.assertIsNone(doc)
        self.assertIn("not valid JSON", problems[0]["reason"])

    def test_definition_marker_is_not_evaluated_elsewhere(self):
        """标记之外的内容只是说明：写错 Markdown 不影响解析。"""
        text = _wrap(json.dumps(SAMPLE, ensure_ascii=False)) + "\n# 说明\n\n随便写。\n"
        doc, problems = runs.parse_definition(text)
        self.assertEqual(problems, [])
        self.assertEqual(doc["workflow_id"], "bounded-change")


class DefinitionStaticCheckTest(unittest.TestCase):
    def test_workflow_id_must_match_file_name(self):
        problems = _problems(_doc(), workflow_id="other")
        self.assertTrue(any("equal the definition file name" in item["reason"] for item in problems))

    def test_reserved_human_point_prefix_is_rejected(self):
        doc = _steps(_doc(), _base_step(human_points=[{"id": "plan-q-1", "question": "q"}]))
        self.assertIn(2, _stages(doc))
        self.assertTrue(any("reserved prefix" in item["reason"] for item in _problems(doc)))

    def test_duplicate_step_ids(self):
        doc = _doc()
        doc["steps"] = [copy.deepcopy(SAMPLE["steps"][0]), copy.deepcopy(SAMPLE["steps"][0])]
        self.assertTrue(any("step id must be unique" in item["reason"]
                            for item in _problems(doc)))

    def test_input_reference_must_be_declared(self):
        doc = _steps(_doc(), _base_step(inputs=[{"from": "input", "name": "nope"}]))
        self.assertIn(3, _stages(doc))

    def test_step_reference_must_point_backwards(self):
        first = _base_step(id="first", inputs=[])
        second = _base_step(id="second", inputs=[{"from": "step", "step": "third",
                                                  "output": "out"}])
        third = _base_step(id="third", inputs=[], outputs=[{"id": "out", "kind": "delivery",
                                                            "path": "docs/x.md",
                                                            "description": "d", "required": True}])
        doc = _doc()
        doc["steps"] = [first, second, third]
        self.assertTrue(any("earlier step" in item["reason"] for item in _problems(doc)))

    def test_prior_step_verification_must_match_stored_step(self):
        step = _base_step(verifications=[{
            "id": "v1", "source": "prior_step",
            "established_by": {"kind": "step", "step_id": "change", "action_id": None},
            "stored_in": {"kind": "step_output", "step_id": "other", "output_id": "o",
                          "verification_id": "v"},
            "consume_at": "check"}])
        doc = _steps(_doc(), step)
        self.assertIn(3, _stages(doc))

    def test_step_artifact_must_live_under_the_instance_root(self):
        step = _base_step(outputs=[{"id": "out", "kind": "step_artifact", "path": "artifacts/x.md",
                                    "description": "d", "required": True}])
        doc = _steps(_doc(), step)
        self.assertIn(4, _stages(doc))

    def test_required_step_cannot_declare_skip(self):
        step = _base_step(skip={"condition": "不需要", "decision_point": "approve-plan",
                                "downstream": []})
        doc = _steps(_doc(), step)
        self.assertTrue(any("required step must declare skip=null" in item["reason"]
                            for item in _problems(doc)))

    def test_skip_decision_point_must_be_declared(self):
        step = _base_step(required=False,
                          skip={"condition": "不需要", "decision_point": "missing-point",
                                "downstream": []})
        doc = _steps(_doc(), step)
        self.assertIn(5, _stages(doc))

    def test_downstream_consumer_must_exist(self):
        step = _base_step(required=False,
                          skip={"condition": "不需要", "decision_point": "approve-plan",
                                "downstream": [{"consumer": "no-such-step", "output": "o",
                                                "mode": "unused", "replacement": None}]})
        doc = _steps(_doc(), step)
        self.assertIn(5, _stages(doc))

    def test_task_step_without_any_verification_is_incomplete(self):
        doc = _steps(_doc(), _base_step(verifications=[]))
        self.assertIn(6, _stages(doc))

    def test_problems_are_ordered_by_stage(self):
        doc = _steps(_doc(workflow_id="Bad_ID"), _base_step(verifications=[]))
        stages = [item["stage"] for item in _problems(doc)]
        self.assertEqual(stages, sorted(stages))


if __name__ == "__main__":
    unittest.main()



class PrepareActionTest(unittest.TestCase):
    """准备动作的结案形状（机制稿 §5.1：具名动作在主记录上登记意图并核后置）。"""

    def test_done_action_marks_both_steps(self):
        from wflib import runs

        action = runs._prepare_action_done(
            {"id": "act-1", "kind": "definition.prepare", "state": "applying",
             "steps": [{"id": "static_check", "state": "pending"},
                       {"id": "write_preparation", "state": "pending"}],
             "result": None, "next_step": "write_preparation"}, True)
        self.assertEqual(action["state"], "done")
        self.assertEqual([step["state"] for step in action["steps"]], ["done", "done"])
        self.assertEqual(action["result"]["summary"], "definition.prepare ok")

    def test_draft_only_action_is_labelled(self):
        from wflib import runs

        action = runs._prepare_action_done(
            {"id": "act-2", "kind": "definition.prepare", "state": "applying",
             "steps": [], "result": None, "next_step": None}, False)
        self.assertEqual(action["state"], "done")
        self.assertEqual(action["result"]["summary"], "definition.prepare draft-only")
