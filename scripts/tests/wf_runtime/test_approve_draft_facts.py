"""批准入口必须把「机器算出的分级提议」交到人做决定的位置（2026-11-25 第四轮复审 F1）。

三处真实缺口：
1. `task-approve --draft` 只给 TODO 骨架，不带 `_complexity_proposal` 的四项条件与提议值，
   也不带生效 TDD——`wf-continue` 要求"呈现复杂度与 TDD"却没有事实可呈现；
2. 决定文件没写 `plan` 时，正式批准把 `plan.confirmed_source` 记成 `inputs`、`human_inputs={}`，
   实际上该值来自机器提议：记录宣称的确认来源不存在（强度不如实）；
3. 草稿 approve 条目不预填 `plan`，人"照抄草稿"也无法形成 `decision` 来源。
"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import lock as lock_mod, records, tasks  # noqa: E402

PRD = """# t

## 机读块

<!-- wf-plan:v1 -->
```json
{"schema_version": 1, "touch_paths": ["pkg/**"],
 "acceptance": [{"id": "a1", "statement": "x", "verification_ids": ["v1"]}],
 "verifications": [{"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                    "cwd": ".", "input_refs": [], "required": true, "consume_at": "check"}]}
```
"""

BASELINE = """# 基线

## 治理面

<!-- wf-governance:v1 -->
```json
{"paths": [], "reason": "用例", "decided_by": "human:test", "decided_at": "2026-11-25T00:00:00Z"}
```
"""


class ApproveDraftFactsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.task_dir = self.root / ".wf/tasks/t1"
        self.task_dir.mkdir(parents=True)
        (self.task_dir / "prd.md").write_text(PRD, encoding="utf-8")
        for name in ("design.md", "implement.md"):
            (self.task_dir / name).write_text(f"# {name}\n\n内容。\n", encoding="utf-8")
        (self.root / ".wf/baseline.md").write_text(BASELINE, encoding="utf-8")
        shutil.copy(REPO / "docs/workflows/wf/payload/templates/project-config.skeleton.json",
                    self.root / ".wf/project-config.json")
        records.write_json(self.task_dir / "task.json", {
            "id": "t1", "title": "t", "status": "not_started", "phase": "plan",
            "plan": {}, "reviews": {}})
        self.ctx = mock.Mock()
        self.ctx.root = str(self.root)
        self.ctx.inputs.return_value = {}

    def tearDown(self):
        self._tmp.cleanup()

    # -- 草稿面 -----------------------------------------------------------
    def draft(self):
        args = mock.Mock()
        args.value.side_effect = lambda name: {"--task": "t1"}.get(name)
        args.flag.side_effect = lambda name: name == "--draft"
        return tasks.cmd_task_approve(self.ctx, args)

    def test_draft_carries_proposal_and_tdd(self):
        facts = self.draft()["facts"]
        self.assertEqual(facts["complexity_proposal"]["value"], "light")
        # 四项条件里至少 governance 被算过一次（false 不拒；true/unknown 才提议 complex）
        self.assertIsInstance(facts["complexity_proposal"]["reasons"], list)
        self.assertIs(facts["tdd"]["value"], False)
        self.assertIn(facts["tdd"]["source"], ("project-default", "built-in-default"))

    def test_draft_entry_prefills_plan(self):
        entry = next(item for item in self.draft()["facts"]["draft"] if item["choice"] == "approve")
        self.assertEqual(entry["plan"], {"complexity": "light", "tdd": False})
        # 机械修订不是重新批准，不带分级（否则等价链看起来像人重新分级）
        mechanical = next(item for item in self.draft()["facts"]["draft"] if item["choice"] == "机械修订")
        self.assertNotIn("plan", mechanical)

    def test_project_default_tdd_reaches_draft(self):
        config = json.loads((self.root / ".wf/project-config.json").read_text(encoding="utf-8"))
        config["tdd_default"] = True
        (self.root / ".wf/project-config.json").write_text(json.dumps(config), encoding="utf-8")
        facts = self.draft()["facts"]
        self.assertIs(facts["tdd"]["value"], True)
        self.assertEqual(facts["tdd"]["source"], "project-default")

    def test_draft_survives_broken_tdd_default(self):
        """草稿是只读骨架：配置坏掉也要先拿到提议与骨架，问题作为事实回报。"""
        config = json.loads((self.root / ".wf/project-config.json").read_text(encoding="utf-8"))
        config["tdd_default"] = "yes"          # 非法类型：正式批准会拒
        (self.root / ".wf/project-config.json").write_text(json.dumps(config), encoding="utf-8")
        result = self.draft()
        self.assertEqual(result["code"], "WF_OK")
        facts = result["facts"]
        self.assertIsNone(facts["tdd"]["value"])
        self.assertEqual(facts["tdd"]["source"], "unavailable")
        self.assertIn("tdd_default", json.dumps(facts["tdd"]["problem"], ensure_ascii=False))
        entry = next(item for item in facts["draft"] if item["choice"] == "approve")
        self.assertEqual(entry["plan"], {"complexity": "light"})   # 不预填坏值

    def test_draft_reports_incomplete_complex_artifacts(self):
        """复杂提议下 design/implement 不全会让人"批准完才第一次失败"：草稿先报出来。"""
        baseline = (self.root / ".wf/baseline.md")
        baseline.write_text(
            "# 基线\n\n<!-- wf-governance:v1 -->\n```json\n"
            '{"paths": [".wf/spec/**"], "reason": "用例", "decided_by": "human:test", '
            '"decided_at": "2026-11-25T00:00:00Z"}\n```\n', encoding="utf-8")
        prd = (self.task_dir / "prd.md")
        prd.write_text(PRD.replace('["pkg/**"]', '[".wf/spec/**"]'), encoding="utf-8")
        (self.task_dir / "design.md").write_text("# design\n\n{{WF_REQUIRED:contract}}\n", encoding="utf-8")
        result = self.draft()
        facts = result["facts"]
        self.assertEqual(facts["complexity_proposal"]["value"], "complex")
        self.assertTrue(facts["complex_artifacts"])

    # -- 正式批准面 -------------------------------------------------------
    def _action(self, _ctx, _path, task, *_args, **_kwargs):
        task = dict(task, action={"id": "a1", "state": "started"})
        return task, task["action"]

    def _finish(self, _ctx, _path, task, *_args, **_kwargs):
        # 真实入口在锁内把记录写回任务目录；用例只替换动作簿记，落盘仍按同一点写。
        records.write_json(self.task_dir / "task.json", task)
        return task, {"ok": True}

    def approve(self, payload):
        path = self.root / "decision.json"
        path.write_text(json.dumps([payload]), encoding="utf-8")
        args = mock.Mock()
        args.value.side_effect = lambda name: {"--task": "t1", "--decision": str(path)}.get(name)
        args.flag.return_value = False
        lock_ctx = mock.MagicMock()
        lock_ctx.__enter__.return_value = None
        lock_ctx.__exit__.return_value = False
        with mock.patch.object(tasks, "write_scope"), \
                mock.patch.object(lock_mod, "acquire", return_value=lock_ctx), \
                mock.patch.object(tasks, "_start_task_action", self._action), \
                mock.patch.object(tasks, "_finish_task_action", self._finish):
            self.ctx.require_held.return_value = (records.load_json(self.task_dir / "task.json"),
                                                  {"id": "human:test"})
            return tasks.cmd_task_approve(self.ctx, args)

    def _decision(self, with_plan):
        entry = next(item for item in self.draft()["facts"]["draft"] if item["choice"] == "approve")
        entry = dict(entry, source="human:test", at="2026-11-25T00:00:00Z", reason="用例")
        if not with_plan:
            entry.pop("plan", None)
        return entry

    def test_draft_round_trip_records_decision_source(self):
        result = self.approve(self._decision(with_plan=True))
        self.assertEqual(result["code"], "WF_OK")
        plan = records.load_json(self.task_dir / "task.json")["plan"]
        self.assertEqual(plan["confirmed_source"], "decision")
        self.assertEqual(plan["human_inputs"], {"complexity": "light", "tdd": False})

    def test_missing_plan_is_recorded_as_proposed(self):
        result = self.approve(self._decision(with_plan=False))
        self.assertEqual(result["code"], "WF_OK")
        plan = records.load_json(self.task_dir / "task.json")["plan"]
        self.assertEqual(plan["complexity"], "light")
        # 旧实现会写 "inputs"：请求 inputs 里并没有该值，这是不存在的确认来源
        self.assertEqual(plan["confirmed_source"], "proposed")
        self.assertEqual(plan["human_inputs"], {})
        self.assertEqual(result["facts"]["confirmed_source"], "proposed")
        self.assertTrue(any("proposed" in warning for warning in result["warnings"]))
        # TDD 也按缺省取值：记录来源如实，并给出"未由人确认"的提示（设计稿 §4.4）
        self.assertEqual(plan["tdd"], False)
        self.assertTrue(any("TDD 未由人确认" in warning for warning in result["warnings"]))

    def test_complex_from_inputs_is_refused(self):
        """复杂分级必须由人的决定承载（设计稿 §4.3）：请求 inputs 只算提议，批准时即拒。"""
        self.ctx.inputs.return_value = {"complexity": "complex"}
        with self.assertRaises(tasks.TaskError) as caught:
            self.approve(self._decision(with_plan=False))
        self.assertEqual(caught.exception.code, "WF_SEMANTIC_DECISION")
        self.assertEqual(caught.exception.facts["confirmed_source"], "inputs")
        self.assertTrue(any("plan.complexity" in exit_ for exit_ in caught.exception.facts["exits"]))

    def test_inputs_source_is_recorded_and_flagged(self):
        """inputs 只作提议：分级来源如实记 `inputs`；TDD 不生效，按缺省并提示未确认。"""
        self.ctx.inputs.return_value = {"complexity": "light", "tdd": True}
        result = self.approve(self._decision(with_plan=False))
        self.assertEqual(result["code"], "WF_OK")
        plan = records.load_json(self.task_dir / "task.json")["plan"]
        self.assertEqual(plan["confirmed_source"], "inputs")
        # 模型不能靠 inputs 自行开启 TDD（设计稿 §4.3）；缺省仍是关闭
        self.assertEqual(plan["tdd"], False)
        self.assertTrue(any("TDD 未由人确认" in warning for warning in result["warnings"]))


if __name__ == "__main__":
    unittest.main()
