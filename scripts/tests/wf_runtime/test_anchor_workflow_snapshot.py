"""D9：实例任务的 Check 锚点纳入定义快照（设计稿 §4.2 内容指纹末句）。

防的失败：`workflow_snapshot_digest` 恒为 None。属于实例的任务，其固定定义快照是"本任务使用的
规则输入"——快照变了，旧 Check 与旧审查必须失效；否则实例被换定义后仍沿用旧结论。

断言：
1. 无 `run_id` 的普通任务：该键为 None，且 `current_anchor` 不把它算缺项；
2. 实例任务：锚点含快照摘要；快照内容变 → 摘要变；
3. 实例任务的快照/记录缺失 → `WF_RECORD_INVALID`（不静默折成 None）。
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import check, records  # noqa: E402

RUN = "run-1"
DEFINITION_DIGEST = "sha256:" + "d" * 64


class Harness(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".wf").mkdir()
        self.ctx = type("Ctx", (), {"root": str(self.root)})()

    def tearDown(self):
        self._tmp.cleanup()

    def write_run(self, snapshot="定义正文"):
        records.write_json(self.root / ".wf" / "workflow-runs" / f"{RUN}.json",
                           {"id": RUN, "definition": {"id": "flow", "digest": DEFINITION_DIGEST},
                            "cursor": {"step_id": "s1", "task_id": None}})
        path = self.root / ".wf" / "workflow-runs" / RUN / "definition.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(snapshot, encoding="utf-8")

    def task(self, run_id=None):
        # W2-2：anchor_parts 现含 control_plane_digest（v 桶取 classify 单一来源），
        # 夹具按已开工记录口径补全 entry_snapshot.touch_paths（空数组合法）。
        task = {"id": "t1", "plan": {"version": "v1"},
                "entry_snapshot": {"touch_paths": []}, "curation": []}
        if run_id:
            task["run_id"] = run_id
        return task


class WorkflowSnapshotTest(Harness):
    def test_plain_task_keeps_the_key_optional(self):
        self.assertIsNone(check.workflow_snapshot_digest(self.ctx, self.task()))
        (self.root / ".wf" / "baseline.md").write_text("基线", encoding="utf-8")
        (self.root / ".wf" / "project-config.json").write_text("{}", encoding="utf-8")
        task = dict(self.task(), plan={"version": "v1", "acceptance_digest": "sha256:a"})
        with mock.patch.object(check, "object_paths", return_value=[]), \
                mock.patch.object(check, "spec_versions", return_value=[]), \
                mock.patch.object(check, "assertions_digest", return_value="sha256:a"):
            anchor, parts = check.current_anchor(self.ctx, task)
        self.assertIsNone(parts["workflow_snapshot_digest"])
        self.assertTrue(anchor.startswith("sha256:"))

    def test_run_task_anchor_tracks_the_snapshot(self):
        self.write_run("定义正文")
        first = check.workflow_snapshot_digest(self.ctx, self.task(RUN))
        self.assertTrue(first.startswith("sha256:"))
        self.write_run("定义正文（改过）")
        second = check.workflow_snapshot_digest(self.ctx, self.task(RUN))
        self.assertNotEqual(first, second)

    def test_missing_snapshot_is_an_error_not_none(self):
        records.write_json(self.root / ".wf" / "workflow-runs" / f"{RUN}.json",
                           {"id": RUN, "definition": {"digest": DEFINITION_DIGEST}})
        with self.assertRaises(check.CheckError) as caught:
            check.workflow_snapshot_digest(self.ctx, self.task(RUN))
        self.assertEqual(caught.exception.code, "WF_RECORD_INVALID")

    def test_missing_run_record_is_an_error(self):
        with self.assertRaises(check.CheckError) as caught:
            check.workflow_snapshot_digest(self.ctx, self.task(RUN))
        self.assertEqual(caught.exception.code, "WF_RECORD_INVALID")


class AnchorKeyTest(unittest.TestCase):
    def test_anchor_hash_covers_the_snapshot_key(self):
        base = {key: "x" for key in ("plan_version", "entry_snapshot_digest", "touch_paths_digest",
                                     "paths_digest", "content_digest", "acceptance_digest",
                                     "spec_versions", "baseline_digest", "config_digest")}
        from wflib import fingerprint

        without = fingerprint.check_anchor(dict(base, workflow_snapshot_digest=None))
        with_snapshot = fingerprint.check_anchor(dict(base, workflow_snapshot_digest="sha256:1"))
        self.assertNotEqual(without, with_snapshot)


if __name__ == "__main__":
    unittest.main()
