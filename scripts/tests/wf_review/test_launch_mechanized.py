"""D10：`review-launch` 的请求由入口机械生成（不再手写 JSON）。

防的失败（dogfood F09）：`export_decision + submitted_scope` 三类材料由模型手写，路由已修但
发起材料本身的协议负担没下沉；漏项/与事实脱节时只会在 reviewer 端暴露。

断言：
1. 只给 `--implementation-cli` 即可发起：三类材料、只读范围、四类敏感排除面由入口生成；
2. 生成结果写进各槽位的 `request.json`（reviewer 侧读的是它）；
3. 没有外发确认时仍被拒（机械生成不放宽 K6）；
4. 生成的材料类集合与外发授权绑定的集合一致。
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import authorize, lock, records, review, tasks as tasks_mod  # noqa: E402

ANCHOR = "sha256:" + "e" * 64
MATERIALS = ["diff", "requirement", "test_results"]


def _run(root, *args):
    subprocess.run(["git", "-c", "user.email=t@example.com", "-c", "user.name=t", *args],
                   cwd=root, check=True, capture_output=True)


class Ctx:
    def __init__(self, root):
        self.root = str(root)

    def require_held(self, task=None):
        return {"id": "sess-test"}, {"id": "human:test"}


class _NullLock:
    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


class LaunchHarness(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _run(self.root, "init", "-q")
        (self.root / "pkg").mkdir()
        (self.root / "pkg" / "a.py").write_text("base\n", encoding="utf-8")
        _run(self.root, "add", "-A")
        _run(self.root, "commit", "-qm", "base")
        self.baseline = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.root, check=True,
                                       capture_output=True, text=True).stdout.strip()
        # 本任务的交付改动（未提交 → e 桶）
        (self.root / "pkg" / "a.py").write_text("changed\n", encoding="utf-8")
        self.task_dir = self.root / ".wf" / "tasks" / "t1"
        self.task_dir.mkdir(parents=True)
        self.task = {"id": "t1", "title": "t", "status": "in_progress", "phase": "check",
                     "revision": 1, "baseline_head": self.baseline,
                     "entry_snapshot": {"touch_paths": ["pkg/a.py"]},
                     "plan": {"complexity": "complex"},
                     "curation": [],
                     "check": {"id": "c1", "result": "pass",
                               "anchor": {"check_anchor": ANCHOR}, "commands": []},
                     "reviews": {}}
        records.write_json(self.task_dir / "task.json", self.task)
        (self.task_dir / "prd.md").write_text("# PRD\n", encoding="utf-8")
        self.ctx = Ctx(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def authorize_export(self, materials=None):
        authorize.record_authorization(
            self.task_dir, "export",
            {"choice": "export", "task": "t1", "materials": list(materials or MATERIALS),
             "by": "human:xzc", "at": "2026-11-12T00:00:00Z",
             "quote": "同意把本任务材料发给两个 reviewer", "source": "user-declared"})

    def launch(self):
        def _start(_ctx, path, task, *_args, **_kwargs):
            task = dict(task)
            task["action"] = {"id": "a1", "state": "started"}
            records.write_json(os.path.join(path, "task.json"), task)
            return task, task["action"]

        with mock.patch.object(review, "_current_anchor", return_value=(ANCHOR, {})), \
                mock.patch.object(lock, "acquire", lambda *a, **k: _NullLock()), \
                mock.patch.object(tasks_mod, "_start_task_action", _start), \
                mock.patch.object(tasks_mod, "_finish_task_action",
                                  lambda _ctx, _path, task, *_a, **_k: (task, {"ok": True})):
            return review.launch(self.ctx, dict(self.task), None, implementation_cli="dsh")


class LaunchHelpTest(unittest.TestCase):
    def test_request_file_is_documented_as_optional(self):
        import json

        from wflib import cli

        text = json.dumps(cli.COMMAND_HELP["review-launch"], ensure_ascii=False)
        self.assertIn("可选", text)
        self.assertNotIn("请求 JSON（必填）", text)


class MechanizedLaunchTest(LaunchHarness):
    def test_defaults_are_generated_from_the_object(self):
        self.authorize_export()
        result = self.launch()
        facts = result["facts"]
        self.assertEqual(facts["round"], 1)
        self.assertEqual(len(facts["temp_paths"]), 2)
        request = json.loads((Path(facts["temp_paths"][0]) / "request.json").read_text(encoding="utf-8"))
        scope = request["submitted_scope"]
        self.assertTrue(scope["diff"]["paths"])
        self.assertIn("prd.md", scope["requirement"])
        self.assertIn("check", scope["test_results"])
        self.assertIn("pkg/a.py", request["readable_scope"]["focus_paths"])
        self.assertEqual(request["readable_scope"]["business_code"], ["**"])
        for required in (".env", "id_rsa", ".npmrc", ".netrc", "secrets.json",
                         ".codex/config.toml", "config.local.json", "../**", ".wf/tasks/**"):
            self.assertIn(required, request["exclusions"])
        self.assertEqual(review.exclusion_gaps({"excluded-scope": request["exclusions"]}), [])

    def test_missing_export_authorization_still_blocks(self):
        with self.assertRaises(review.ReviewError) as caught:
            self.launch()
        self.assertEqual(caught.exception.code, "WF_COMMIT_NOT_AUTHORIZED")

    def test_generated_materials_match_the_authorized_scope(self):
        # 授权只覆盖 diff+requirement 时，机械生成的三类材料不能匹配
        self.authorize_export(["diff", "requirement"])
        with self.assertRaises(review.ReviewError) as caught:
            self.launch()
        facts = caught.exception.facts
        self.assertEqual(facts["materials"], sorted(MATERIALS))
        self.assertTrue(any("范围与本次不一致" in item["reason"]
                            for item in facts["problems"]))


if __name__ == "__main__":
    unittest.main()
