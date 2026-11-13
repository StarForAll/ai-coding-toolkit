"""D6：报告输入校验只有一个实现（lint / 导入 / 判定同源）。

防的失败（dogfood）：`lint` 只核字段存在、导入再核一遍字段、判定才核非空与敏感面——
于是"lint 通过 → 导入成功 → 判定失败 → 另开一轮"。同一份报告在三处必须给同一输入结论。

断言：
1. 每种非法输入在 `lint` 的 checks 与 `report_input_problems` 的 checks 里同名出现；
2. 同一份报告经导入入口被拒时，facts 里的问题也带同一个 check 名；
3. 合法报告 lint 通过且导入成功（正对照，避免"全拒"假绿）。
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import records, review, tasks as tasks_mod  # noqa: E402

ANCHOR = "sha256:" + "b" * 64
MARKER = review.REPORT_MARKER
COVERED = ["node_modules/**", ".env", "*.pem", ".codex/**", "../**", ".wf/tasks/**"]
AXES = {name: "pass" for name in review.REVIEW_AXES}


def payload(**overrides):
    body = {"protocol": "wf-review-v1", "task-id": "t1", "round": 1,
            "review-time": "2026-11-12T00:00:00.000000Z", "review-focus": "x",
            "check-anchor": {"check_id": "c1", "check_anchor": ANCHOR},
            "read-scope": ["pkg/**"], "excluded-scope": list(COVERED),
            "scope-exceptions": [], "axes": dict(AXES), "findings": [], "verdict": "pass"}
    body.update(overrides)
    return body


def text_of(body, status="done"):
    head = f"<!-- wf-review-agent:v1 status={status} -->\n" if status is not None else ""
    return head + MARKER + "\n\n```json\n" + json.dumps(body, ensure_ascii=False) + "\n```\n"


class Ctx:
    def __init__(self, root):
        self.root = str(root)

    def require_held(self, task=None):
        return {"id": "sess-test"}, {"id": "human:test"}


class ImportHarness(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.ctx = Ctx(self.root)
        self.task_dir = self.root / ".wf" / "tasks" / "t1"
        self.task_dir.mkdir(parents=True)
        records.write_json(self.task_dir / "task.json", {
            "id": "t1", "title": "t", "status": "in_progress", "phase": "check",
            "revision": 1, "check": {"id": "c1", "result": "pass",
                                     "anchor": {"check_anchor": ANCHOR}},
            "entry_snapshot": {"touch_paths": []},
            "reviews": {"launches": [{"round": 1, "implementation_cli": "dsh",
                                      "slots": [{"slot": "s1"}], "temp_paths": []}],
                        "imported": []}})
        self.staging = self.root / "staging" / "round-1"
        self.staging.mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, body, status="done", name="review-pi.md"):
        path = self.staging / name
        path.write_text(text_of(body, status=status), encoding="utf-8")
        return path

    def import_report(self, path):
        def _start(_ctx, directory, task, *_args, **_kwargs):
            task = dict(task)
            task["action"] = {"id": "a1", "state": "started"}
            records.write_json(os.path.join(directory, "task.json"), task)
            return task, task["action"]

        with mock.patch.object(review, "_current_anchor", return_value=(ANCHOR, {})), \
                mock.patch.object(review, "staging_root",
                                  lambda _ctx, _task: str(self.root / "staging")), \
                mock.patch.object(tasks_mod, "_start_task_action", _start), \
                mock.patch.object(tasks_mod, "_finish_task_action",
                                  lambda _ctx, _path, task, *_a, **_k: (task, {"ok": True})):
            return review.import_report(self.ctx, {"id": "t1"}, 1, None, str(path),
                                        _from_discovery=True, agent="pi")


class SingleSourceTest(ImportHarness):
    def check_names(self, text):
        facts = review.lint_report(None, None, text)
        return {item["check"] for item in facts["checks"] if not item["ok"]}, facts

    def test_bad_inputs_are_named_the_same_by_lint_and_importer(self):
        cases = {
            "read-scope": payload(**{"read-scope": []}),
            "excluded-scope": payload(**{"excluded-scope": ["node_modules/**"]}),
            "required-fields": {k: v for k, v in payload().items() if k != "verdict"},
            "axes-and-verdict": payload(axes={**AXES, "contract": "fail"}),
            "declared-verdict": payload(verdict="fail"),
        }
        for name, body in cases.items():
            with self.subTest(check=name):
                text = text_of(body)
                lint_names, lint_facts = self.check_names(text)
                self.assertFalse(lint_facts["ok"])
                self.assertIn(name, lint_names)
                path = self.write(body)
                with self.assertRaises(review.ReviewError) as caught:
                    self.import_report(path)
                problems = caught.exception.facts.get("problems") or []
                self.assertIn(name, {item.get("check") for item in problems},
                              caught.exception.facts)

    def test_status_header_rules_are_shared_but_only_where_the_file_is_staged(self):
        for status in (None, "in-progress"):
            with self.subTest(status=status):
                text = text_of(payload(), status=status)
                names, facts = self.check_names(text)
                self.assertIn("status-head", names)
                # 扫描模式看不到未完成的报告 → 导入侧给"没有已完成报告"，不是静默成功
                path = self.write(payload(), status=status or "missing")
                with self.assertRaises(review.ReviewError):
                    self.import_report(path)

    def test_valid_report_passes_both(self):
        text = text_of(payload())
        names, facts = self.check_names(text)
        self.assertTrue(facts["ok"], facts["problems"])
        self.assertEqual(names, set())
        result = self.import_report(self.write(payload()))
        self.assertEqual(result["facts"]["slot"], "s1")

    def test_non_object_axes_is_reported_without_crashing(self):
        body = payload(axes=["range"])
        facts = review.report_input_problems(body, text=text_of(body))
        self.assertIn("axes-and-verdict", facts["checks"])
        self.assertEqual(facts["verdict"], None)
        linted = review.lint_report(None, None, text_of(body))
        self.assertFalse(linted["ok"])
        self.assertIn("axes-and-verdict",
                      {item["check"] for item in linted["checks"] if not item["ok"]})


if __name__ == "__main__":
    unittest.main()
