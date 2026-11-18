"""P2-3：`ready` 要给出实例归组（机制稿 §6.1；实现稿 §2.3.11「仍未做」）。

历史状态：`cmd_ready` 只列任务、只把 `WF_BINDING_MISMATCH` 丢进 blockers——而同一个码
同时覆盖「在途实例」「实例正常结束」「异常结束但无保留许可」，人看不出该绑实例还是该走 repair，
也看不到「这些任务属于哪个实例、那个实例到哪一步」。

现在 `runs.binding_state()` 是唯一判定：`_eligible_task_bind` 与 `cmd_ready` 共用它，
`ready` 增 `runs[]` 归组与 `run_in_flight` 细分阻断项，悬空 `run_id` 不静默丢弃。

**不做子仓库归组**：嵌套仓库是 charter T3 B2 的硬边界。
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import cli  # noqa: E402

TASK_A = "2026-" + "a" * 32
TASK_B = "2026-" + "b" * 32
RUN_ID = "run-0001"


def _ctx(root, holder=None):
    record = {"state": "held", "generation": 3, "holder": holder or {"id": "me", "kind": "session"}}
    return SimpleNamespace(root=root, writer=lambda: record, key=lambda required=True: "me")


def _write(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)


def _task(root, task_id, run_id=None, paused=False):
    directory = os.path.join(root, ".wf", "tasks", task_id)
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, "prd.md"), "w", encoding="utf-8") as handle:
        block = {"schema_version": 1, "touch_paths": ["pkg/**"],
                 "acceptance": [{"id": "a1", "statement": "可用", "severity": "required",
                                 "verification_ids": []}],
                 "verifications": []}
        handle.write("# t\n\n<!-- wf-plan:v1 -->\n```json\n"
                     + json.dumps(block, ensure_ascii=False) + "\n```\n")
    record = {
        "schema_version": 1, "id": task_id, "status": "in_progress", "phase": "execute",
        "title": task_id, "created_at": "2026-11-01T00:00:00.000000Z",
        "paused": paused, "suspended": False,
        "plan": {"approval": {"choice": "approve", "source": "human"}},
    }
    if run_id:
        record["run_id"] = run_id
    # 先把记录落盘：`locate_task_dirs` 只认带 task.json 的目录，否则算不出规划版本
    _write(os.path.join(directory, "task.json"), record)
    from wflib import tasks as tasks_mod

    version = (tasks_mod.current_plan_version(root, record) or {}).get("version")
    record["plan"]["version"] = version
    record["plan"]["approved_version"] = version
    _write(os.path.join(directory, "task.json"), record)


def _run(root, run_id, terminal=None, workflow_id="bounded-change"):
    _write(os.path.join(root, ".wf", "workflow-runs", f"{run_id}.json"),
           {"schema_version": 1, "id": run_id, "workflow_id": workflow_id,
            "terminal": terminal, "paused": False})


class ReadyRunsTest(unittest.TestCase):
    def _ready(self, root):
        payload = cli.cmd_ready(_ctx(root), cli.Args([]))
        return payload["facts"]

    def test_in_flight_run_task_is_blocked_with_fine_grained_fact(self):
        root = tempfile.mkdtemp(prefix="wf-ready-")
        _task(root, TASK_A, run_id=RUN_ID)
        _run(root, RUN_ID, terminal=None)
        facts = self._ready(root)
        entry = facts["tasks"][0]
        self.assertIn("WF_BINDING_MISMATCH", entry["blockers"])
        self.assertIn("run_in_flight", entry["blockers"])
        self.assertFalse(entry["ready"])
        self.assertEqual(facts["runs"], [{"run_id": RUN_ID, "workflow_id": "bounded-change",
                                          "terminal": None, "paused": False,
                                          "tasks": [TASK_A]}])

    def test_licensed_abnormal_run_stays_eligible_and_grouped(self):
        root = tempfile.mkdtemp(prefix="wf-ready-")
        _task(root, TASK_A, run_id=RUN_ID)
        record_path = os.path.join(root, ".wf", "tasks", TASK_A, "task.json")
        with open(record_path, encoding="utf-8") as stream:
            record = json.load(stream)
        record["independent_resume"] = {"decision": "keep", "termination_action": "term-1"}
        _write(record_path, record)
        _run(root, RUN_ID, terminal="abnormal")
        facts = self._ready(root)
        entry = facts["tasks"][0]
        self.assertNotIn("run_in_flight", entry["blockers"])
        self.assertTrue(entry["eligible"])
        self.assertEqual(facts["runs"][0]["terminal"], "abnormal")

    def test_plain_tasks_are_not_grouped(self):
        root = tempfile.mkdtemp(prefix="wf-ready-")
        _task(root, TASK_B)
        facts = self._ready(root)
        self.assertEqual(facts["runs"], [])
        self.assertEqual(facts["tasks"][0]["blockers"], ["in_progress"])

    def test_dangling_run_id_is_reported_not_dropped(self):
        root = tempfile.mkdtemp(prefix="wf-ready-")
        _task(root, TASK_A, run_id="run-missing")
        facts = self._ready(root)
        self.assertEqual(len(facts["runs"]), 1)
        self.assertEqual(facts["runs"][0]["run_id"], "run-missing")
        self.assertTrue(facts["runs"][0].get("unknown"))
        self.assertEqual(facts["runs"][0]["tasks"], [TASK_A])


if __name__ == "__main__":
    unittest.main()


class ReadyRunCandidatesTest(unittest.TestCase):
    """`ready` 把实例作为**可绑定候选**（机制稿 §6.1；`bind --run` 交付后的一半）。

    与任务侧同一判据：资格由 `_eligible_run_bind` 决定，暂停/终态进 blockers。
    """

    def _project(self, records):
        import json
        import tempfile

        root = tempfile.mkdtemp(prefix="wf-ready-run-")
        os.makedirs(os.path.join(root, ".wf/workflow-runs"), exist_ok=True)
        for record in records:
            with open(os.path.join(root, ".wf/workflow-runs", f"{record['id']}.json"), "w",
                      encoding="utf-8") as handle:
                json.dump(record, handle, ensure_ascii=False)

        class _Ctx:
            def __init__(self, root):
                self.root = Path(root)

            def key(self, **_kwargs):
                return "sess-x"

            def writer(self):
                return {"state": "idle", "generation": 1}

            def inputs(self):
                return {"generation": 1}

        return _Ctx(root)

    def test_in_flight_run_is_ready_candidate(self):
        from wflib import cli

        run = {"id": "2026-" + "a" * 32, "workflow_id": "demo", "terminal": None,
               "paused": False, "creation_decision": {"at": "2026-11-12T00:00:00Z"},
               "step_results": {"one": {"kind": "satisfied"}}, "task_map": {},
               "cursor": {"step_id": "two", "task_id": None}}
        ctx = self._project([run])
        payload = cli.cmd_ready(ctx, _Args())
        facts = payload["facts"]
        candidates = facts["run_candidates"]
        self.assertEqual([item["id"] for item in candidates], [run["id"]])
        self.assertTrue(candidates[0]["ready"])
        self.assertEqual(candidates[0]["steps_settled"], ["one"])
        self.assertEqual(facts["suggested_run"], run["id"])

    def test_paused_and_terminal_runs_are_blocked(self):
        from wflib import cli

        paused = {"id": "2026-" + "b" * 32, "workflow_id": "demo", "terminal": None,
                  "paused": True, "creation_decision": {"at": "2026-11-12T00:00:00Z"},
                  "step_results": {}, "task_map": {}, "cursor": None}
        ended = {"id": "2026-" + "c" * 32, "workflow_id": "demo", "terminal": "abnormal",
                 "paused": False, "creation_decision": {"at": "2026-11-12T00:00:01Z"},
                 "step_results": {}, "task_map": {}, "cursor": None}
        ctx = self._project([paused, ended])
        facts = cli.cmd_ready(ctx, _Args())["facts"]
        by_id = {item["id"]: item for item in facts["run_candidates"]}
        self.assertIn("paused", by_id[paused["id"]]["blockers"])
        self.assertIn("WF_BINDING_MISMATCH", by_id[ended["id"]]["blockers"])
        self.assertIsNone(facts["suggested_run"])


class _Args:
    def value(self, _name):
        return None
