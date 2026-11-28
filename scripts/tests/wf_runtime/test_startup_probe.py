"""启动面的三项断言（2026-11-28）：

- §23：startup ⑩ 用 `exclude_scope`（不是旧 `exclude_id`）问 `wip_blockers`；
- §37：挂起复评事实作为**固定顺序之后**的投影项输出（`step=reassess`），且不占序位；
- §41：run 绑定的会话在无 task 时得到 `instances` 三探针项。
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import cli, tasks  # noqa: E402


class StartupProbeTest(unittest.TestCase):
    def _ctx(self):
        root = tempfile.mkdtemp()
        (Path(root) / ".wf").mkdir(exist_ok=True)
        ctx = mock.Mock(root=root)
        ctx.key = lambda required=True: "s-k"
        return ctx

    def test_workspace_step_uses_exclude_scope_and_reassess_is_appended(self):
        ctx = self._ctx()
        task = {"id": "2026-" + "a" * 32, "status": "in_progress", "phase": "execute"}
        seen = {}

        def _blockers(root, **kwargs):
            seen.update(kwargs)
            return []

        with mock.patch.object(tasks, "iter_tasks", return_value=[]), \
                mock.patch.object(tasks, "_reassess_empty_set",
                                  return_value={"waiting_tasks": [{"id": task["id"]}],
                                                "waiting": True, "unknown": [],
                                                "conditions": {}, "suspended_tasks": [],
                                                "reassessed": []}), \
                mock.patch.object(tasks, "dependency_blockers", return_value=[]), \
                mock.patch.object(tasks, "approved_touch_paths", return_value=[]), \
                mock.patch("wflib.cli.wip_blockers", side_effect=_blockers):
            findings = tasks.startup_check(ctx, task)
        self.assertEqual(seen.get("exclude_scope"), {"kind": "task", "id": task["id"]},
                         "⑩ 必须按 exclude_scope 排除本任务")
        self.assertEqual(findings[-1].get("step"), "reassess", "复评投影必须在固定顺序之后")
        self.assertEqual(findings[-1].get("status"), "waiting")

    def test_run_binding_gets_instance_probe(self):
        ctx = self._ctx()
        run_id = "2026-" + "f" * 32
        with mock.patch.object(tasks, "iter_tasks", return_value=[]), \
                mock.patch("wflib.session.load_binding",
                           return_value={"object": {"kind": "run", "id": run_id}}), \
                mock.patch("wflib.runs.load_run",
                           return_value={"id": run_id, "terminal": None,
                                         "definition": {"digest": "sha256:x"},
                                         "cursor": {"task_id": None}}):
            findings = tasks.startup_check(ctx)
        steps = [item.get("step") for item in findings]
        self.assertIn("instances", steps)
        # ⑧⑨ 是无条件项（R27 F3 / R28 F2）：未绑定/ run 绑定会话也必须出现；
        # tempdir 没有 .wf/bin → assets 必须是 blocked（锚事实而不是锚措辞）。
        self.assertIn("marker", steps)
        assets = [item for item in findings if item.get("step") == "assets"][0]
        self.assertEqual(assets.get("status"), "blocked")
        self.assertIn(".wf/bin/wf.py", assets.get("missing") or [])
        self.assertEqual([item for item in findings if item.get("step") == "instances"][0].get("status"),
                         "ok")


if __name__ == "__main__":
    unittest.main()
