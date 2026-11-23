"""a-3（dogfood 三轮）：验证日志物化接通——`write_materials` 读 Check 记录真实字段 `started_at`。

防的失败：此前实现读 `check.started`（真实字段是 `started_at`），日志复制分支在真实数据上
从不执行——reviewer 只能看到 commands 摘要，看不到完整脱敏日志（十六轮 a-3 声称解决的问题
实际未解决）。

端到端断言：构造带日志目录的真实 Check 记录（`started_at` 与日志目录命名同源）→
`write_materials` 物化 → `materials/check-logs/` 非空、`tests.json["logs"]` 清单带
文件名与 sha256 摘要。回退注入：把字段读回 `started` 后断言变红。
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import review  # noqa: E402


class CheckLogsMaterializationTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        task_dir = self.root / ".wf" / "tasks" / "t-logs"
        task_dir.mkdir(parents=True)
        self.task_dir = task_dir
        # task_dir 定位要求记录存在且 id 匹配
        import json

        (task_dir / "task.json").write_text(
            json.dumps({"id": "t-logs", "title": "日志"}), encoding="utf-8")
        # 真实 Check 记录形态：started_at（ISO）+ 与日志目录命名同源（去冒号点）
        self.started = "2026-11-22T10:30:00.000000Z"
        log_dirname = self.started.replace(":", "").replace(".", "")
        log_dir = task_dir / "check-logs" / log_dirname
        log_dir.mkdir(parents=True)
        (log_dir / "v1.log").write_text("[wf-log] passed output line\n", encoding="utf-8")
        self.task = {"id": "t-logs", "title": "日志", "status": "in_progress", "phase": "check",
                     "baseline_head": None,
                     "entry_snapshot": {"touch_paths": []},
                     "plan": {"version": "v1"},
                     "check": {"id": "c1", "started_at": self.started,
                               "commands": [{"verification_id": "v1", "status": "passed"}]}}

    def tearDown(self):
        self._tmp.cleanup()

    def _ctx(self):
        class Ctx:
            root = str(self.root)
        return Ctx()

    def test_real_check_record_materializes_logs(self):
        materials = self.task_dir / "review" / "round-1" / "materials"
        # 命令记录带证据身份（evidence_ref + log_digest）：a-3（三轮 a4）——
        # 物化时逐文件核对，日志与该次执行一致才 verified=true。
        import hashlib

        log_path = (self.task_dir / "check-logs"
                    / self.started.replace(":", "").replace(".", "") / "v1.log")
        recorded_digest = "sha256:" + hashlib.sha256(log_path.read_bytes()).hexdigest()
        self.task["check"]["commands"] = [
            {"verification_id": "v1", "status": "passed",
             "evidence_ref": f".wf/tasks/{self.task_dir.name}/check-logs/"
                             f"{self.started.replace(':', '').replace('.', '')}/v1.log",
             "log_digest": recorded_digest}]
        facts = review.write_materials(self._ctx(), self.task, 1, "anchor-1",
                                        str(materials), paths=[])
        logs_dir = materials / "check-logs"
        self.assertTrue(logs_dir.is_dir())
        names = sorted(os.listdir(logs_dir))
        self.assertEqual(names, ["v1.log"])
        import json

        tests = json.loads((materials / "tests.json").read_text(encoding="utf-8"))
        self.assertEqual(len(tests.get("logs") or []), 1)
        entry = tests["logs"][0]
        self.assertEqual(entry["file"], "check-logs/v1.log")
        self.assertTrue(entry["digest"].startswith("sha256:"))
        self.assertIs(entry["verified"], True)          # 与命令记录的 log_digest 一致
        self.assertEqual(entry["recorded_digest"], recorded_digest)
        # 真实日志内容确实被复制（reviewer 可复核具体输出）
        self.assertIn("passed output line",
                      (logs_dir / "v1.log").read_text(encoding="utf-8"))

    def test_tampered_log_is_not_materialized_and_reported(self):
        """日志被改写：**不进材料包**（外发面先核身份再物化），只在 status.json.problems 报告。

        旧语义是"先复制、事后标 verified=false"——标注约束不了材料范围（十一轮 b-2）。
        """
        import hashlib
        import json

        log_dirname = self.started.replace(":", "").replace(".", "")
        log_path = self.task_dir / "check-logs" / log_dirname / "v1.log"
        original_digest = "sha256:" + hashlib.sha256(log_path.read_bytes()).hexdigest()
        self.task["check"]["commands"] = [
            {"verification_id": "v1", "status": "passed",
             "evidence_ref": f".wf/tasks/{self.task_dir.name}/check-logs/{log_dirname}/v1.log",
             "log_digest": original_digest}]
        log_path.write_text("[wf-log] 改写过的输出\n", encoding="utf-8")
        materials = self.task_dir / "review" / "round-3" / "materials"
        review.write_materials(self._ctx(), self.task, 3, "anchor-3", str(materials), paths=[])
        tests = json.loads((materials / "tests.json").read_text(encoding="utf-8"))
        self.assertFalse(tests.get("logs"), "被改写的日志不得进入材料包")
        self.assertFalse((materials / "check-logs" / "v1.log").exists())
        status = json.loads((materials / "status.json").read_text(encoding="utf-8"))
        self.assertTrue(any("digest mismatch" in item.get("reason", "")
                            for item in status.get("problems") or []),
                        status.get("problems"))

    def test_referenced_but_missing_log_is_reported(self):
        # 命令引用的日志复制不到：进 status.json.problems，不静默省略
        import json

        log_dirname = self.started.replace(":", "").replace(".", "")
        self.task["check"]["commands"] = [
            {"verification_id": "v1", "status": "passed",
             "evidence_ref": f".wf/tasks/{self.task_dir.name}/check-logs/{log_dirname}/v1.log",
             "log_digest": "sha256:" + "0" * 64}]
        (self.task_dir / "check-logs" / log_dirname / "v1.log").unlink()
        materials = self.task_dir / "review" / "round-4" / "materials"
        review.write_materials(self._ctx(), self.task, 4, "anchor-4", str(materials), paths=[])
        status = json.loads((materials / "status.json").read_text(encoding="utf-8"))
        self.assertTrue(any("not materialized" in str(p.get("reason"))
                            for p in status.get("problems") or []))

    def test_legacy_started_field_alone_does_not_materialize(self):
        # 旧字段名（started）不再被读——它不是真实 Check 记录字段；
        # 只有 started_at 同源目录才物化。
        task = dict(self.task)
        task["check"] = dict(self.task["check"])
        task["check"]["started"] = self.started
        task["check"]["started_at"] = None
        materials = self.task_dir / "review" / "round-2" / "materials"
        review.write_materials(self._ctx(), task, 2, "anchor-2", str(materials), paths=[])
        tests_path = materials / "tests.json"
        import json

        tests = json.loads(tests_path.read_text(encoding="utf-8"))
        self.assertNotIn("logs", tests)
        self.assertFalse((materials / "check-logs").exists())


if __name__ == "__main__":
    unittest.main()
