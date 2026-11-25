"""规划的正式批准必须同时绑定**内容**与**任务**。

两条失败都真实存在过（2026-11-24 复核）：
- 摘要留空时旧实现只按 `subject` 放行——人答复之后 PRD 再变也算批准；
- 摘要只绑字节：两份 PRD 一模一样的任务之间，同一份决定可以互相顶用。

断言：缺摘要拒、摘要不符拒、subject 不含任务 id 拒、两者都对才通过。
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[2] if (Path(__file__).resolve().parents[2] / "docs").is_dir() \
    else Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import cli as cli_mod, lock as lock_mod, records, tasks  # noqa: E402

PRD = """# t

<!-- wf-plan:v1 -->
```json
{"schema_version": 1, "touch_paths": ["pkg/**"],
 "acceptance": [{"id": "a1", "statement": "x", "verification_ids": ["v1"]}],
 "verifications": [{"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                    "cwd": ".", "input_refs": [], "required": true, "consume_at": "check"}]}
```
"""
DIGEST = "sha256:" + records.sha256_hex(PRD.encode())


def decision(subject, digest, choice="approve", artifacts=None):
    body = {"source": "human:test", "at": "2026-11-24T00:00:00Z", "subject": subject,
            "object_digest": digest, "choice": choice, "reason": "用例",
            # 分级由人的决定承载（0.0.2 起复杂分级缺该键即拒）；本夹具走轻量路径
            "plan": {"complexity": "light", "tdd": False}}
    if artifacts is not None:
        body["artifacts"] = artifacts
    return body


class ApproveBindingTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.task_dir = self.root / ".wf/tasks/t1"
        self.task_dir.mkdir(parents=True)
        (self.task_dir / "prd.md").write_text(PRD, encoding="utf-8")
        for name in ("design.md", "implement.md"):
            (self.task_dir / name).write_text(f"# {name}\n\n内容。\n", encoding="utf-8")
        # 治理面可用且为空：分级提议因此是 light（0.0.2 起复杂分级缺决定即拒，夹具要能判成轻量）
        (self.root / ".wf/baseline.md").write_text(
            "# 基线\n\n<!-- wf-governance:v1 -->\n```json\n"
            '{"paths": [], "reason": "用例", "decided_by": "human:test", '
            '"decided_at": "2026-11-25T00:00:00Z"}\n```\n', encoding="utf-8")
        records.write_json(self.task_dir / "task.json", {
            "id": "t1", "title": "t", "status": "not_started", "phase": "plan", "revision": 1,
            "reviews": {}})
        self.ctx = mock.Mock()
        self.ctx.root = str(self.root)
        self.ctx.inputs.return_value = {}

    def tearDown(self):
        self._tmp.cleanup()

    @staticmethod
    def _action(_ctx, _path, task, *_args, **_kwargs):
        task = dict(task, action={"id": "a1", "state": "started"})
        return task, task["action"]

    def approve(self, payload):
        path = self.root / "decision.json"
        payloads = payload if isinstance(payload, list) else [payload]
        path.write_text(json.dumps(payloads), encoding="utf-8")
        args = mock.Mock()
        args.value.side_effect = lambda name: {"--task": "t1", "--decision": str(path)}.get(name)
        args.flag.return_value = False
        lock_ctx = mock.MagicMock()
        lock_ctx.__enter__.return_value = None
        lock_ctx.__exit__.return_value = False
        with mock.patch.object(tasks, "_require_binding"), \
                mock.patch.object(lock_mod, "acquire", return_value=lock_ctx), \
                mock.patch.object(tasks, "_start_task_action", self._action), \
                mock.patch.object(tasks, "_finish_task_action",
                                  lambda _c, _p, task, *_a, **_k: (task, {"ok": True})):
            self.ctx.require_held.return_value = (records.load_json(self.task_dir / "task.json"),
                                                  {"id": "human:test"})
            return tasks.cmd_task_approve(self.ctx, args)

    def test_missing_digest_is_refused(self):
        with self.assertRaises(tasks.TaskError) as caught:
            self.approve(decision("approve t1", ""))
        self.assertEqual(caught.exception.code, "WF_APPROVAL_MISSING")
        self.assertIn("expected_prd_digest", caught.exception.facts)

    def test_wrong_digest_is_refused(self):
        with self.assertRaises(tasks.TaskError) as caught:
            self.approve(decision("approve t1", "sha256:" + "0" * 64))
        self.assertEqual(caught.exception.code, "WF_APPROVAL_MISSING")

    def test_matching_digest_and_subject_pass(self):
        result = self.approve(decision("approve t1", DIGEST, artifacts=self.artifacts()))
        self.assertEqual(result["code"], "WF_OK")

    def artifacts(self):
        root = str(self.root)
        from wflib import tasks as tasks_mod

        return {item["path"]: item["digest"]
                for item in tasks_mod.artifact_digests(root, {"id": "t1"})}

    def test_reserved_debug_subject_cannot_ride_plan_approval(self):
        """保留 subject 只能经 `task-check --decision` 入账：通用批准路径不得原样 append。

        否则一条 plan-q 答复写成 `debug-ruling-<vid>-99` 就能静音归档门禁。
        """
        reserved = {"source": "human:test", "at": "2026-11-24T00:00:00Z",
                    "subject": "debug-ruling-v1-99", "object_digest": "",
                    "choice": "plan-q", "reason": "伪装成答复"}
        with self.assertRaises(tasks.TaskError) as caught:
            self.approve([decision("approve t1", DIGEST, artifacts=self.artifacts()), reserved])
        self.assertEqual(caught.exception.code, "WF_SEMANTIC_DECISION")
        self.assertIn("task-check", caught.exception.facts["exits"][0])

    def test_artifact_drift_is_refused(self):
        """人答复后 design/implement 再变：旧答复不能连带批准新方案。"""
        declared = self.artifacts()
        (self.task_dir / "design.md").write_text("# design\n\n改过了。\n", encoding="utf-8")
        with self.assertRaises(tasks.TaskError) as caught:
            self.approve(decision("approve t1", DIGEST, artifacts=declared))
        self.assertEqual(caught.exception.code, "WF_APPROVAL_MISSING")
        self.assertIn("design.md", json.dumps(caught.exception.facts["changed"]))

    def test_newly_added_artifact_is_refused(self):
        """草稿在产物缺失时生成、之后补写：新文件同样没被看过，不能算无漂移。"""
        declared = self.artifacts()
        (self.task_dir / "design.md").unlink()
        declared.pop(".wf/tasks/t1/design.md", None)
        (self.task_dir / "design.md").write_text("# design\n\n后补的方案。\n", encoding="utf-8")
        with self.assertRaises(tasks.TaskError) as caught:
            self.approve(decision("approve t1", DIGEST, artifacts=declared))
        self.assertEqual(caught.exception.code, "WF_APPROVAL_MISSING")
        changed = caught.exception.facts["changed"]
        self.assertEqual([item["path"] for item in changed], [".wf/tasks/t1/design.md"])
        self.assertIsNone(changed[0]["declared"])

    def test_artifact_match_passes(self):
        result = self.approve(decision("approve t1", DIGEST, artifacts=self.artifacts()))
        self.assertEqual(result["code"], "WF_OK")

    def test_mechanical_revision_round_trips_from_the_draft(self):
        """草稿是机械修订的唯一来源：它必须自带 artifacts，否则通道自我锁死。"""
        first = self.approve(decision("approve t1", DIGEST, artifacts=self.artifacts()))
        self.assertEqual(first["code"], "WF_OK")
        draft = tasks.cmd_task_approve.__wrapped__ if False else None
        del draft
        args = mock.Mock()
        args.value.side_effect = lambda name: {"--task": "t1"}.get(name)
        args.flag.side_effect = lambda name: name == "--draft"
        skeleton = tasks.cmd_task_approve(self.ctx, args)["facts"]["draft"]
        mechanical = next(item for item in skeleton if item["choice"] == "机械修订")
        self.assertTrue(mechanical.get("artifacts"), "机械修订草稿条目必须带 artifacts")
        mechanical.update({"source": "human:test", "at": records.now_str(), "reason": "只改错字"})
        # 机械修订要求已有批准在案：夹具的手写记录不由命令落盘，这里补上
        stored = records.load_json(self.task_dir / "task.json")
        from wflib import fingerprint

        block = {"acceptance": [{"id": "a1", "statement": "x", "verification_ids": ["v1"]}],
                 "verifications": [{"id": "v1",
                                    "invocation": {"kind": "argv",
                                                   "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                                    "cwd": ".", "input_refs": [], "required": True,
                                    "consume_at": "check"}]}
        stored["plan"] = {"version": "v1", "approved_version": "v1",
                          "approval": {"choice": "approve"},
                          "touch_paths": ["pkg/**"],
                          "acceptance_digest": fingerprint.acceptance_digest(block["acceptance"]),
                          "verifications": block["verifications"]}
        records.write_json(self.task_dir / "task.json", stored)
        result = self.approve(mechanical)
        self.assertEqual(result["code"], "WF_OK")

    def test_subject_must_name_the_task(self):
        with self.assertRaises(tasks.TaskError) as caught:
            self.approve(decision("approve something else", DIGEST, artifacts=self.artifacts()))
        self.assertEqual(caught.exception.code, "WF_APPROVAL_MISSING")
        self.assertIn("subject", caught.exception.facts)


if __name__ == "__main__":
    unittest.main()
