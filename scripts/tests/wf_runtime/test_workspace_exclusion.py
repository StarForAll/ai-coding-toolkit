"""D3：外来未提交改动可被**摘要绑定**地排除（人确认"不属于本任务、保持原样"）。

防的失败（dogfood）：`.unipi/` 与 `.gitignore` 两次把 Check 挡在 `WF_WORKSPACE_UNRESOLVED`，
而"已核对无影响"的出口只覆盖**已提交**的外部变更；未提交外来改动只能靠人亲自提交/裁决。

契约（本轮）：
- 声明形状：`{choice: 排除外来改动, paths: [具体路径], by/at/quote/source}`（乙口径）；
- 记录时按当时内容摘要固定；内容一变即失配 → 路径回到 c 桶（不是永久豁免）；
- 排除只解除开工/Check 的该项阻断：不进交付面、不进指纹、不构成提交授权；
- 路径不在 c 桶（属本任务/其他任务/记录）→ 整批拒绝。

断言：
1. 无声明时 `run_check_scope` 报 `WF_WORKSPACE_UNRESOLVED` 并给两条出口；
2. 记录后 c 桶清空、x 桶列出被排除路径、交付面不变；
3. 被排除文件内容变化 → 排除失效、路径回到 c；
4. glob 与缺确认字段的声明被拒；
5. 路径不在 c 桶时被拒。
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import check, records, scope, tasks as tasks_mod  # noqa: E402


def _run(root, *args):
    subprocess.run(["git", "-c", "user.email=t@example.com", "-c", "user.name=t", *args],
                   cwd=root, check=True, capture_output=True)


class Ctx:
    def __init__(self, root):
        self.root = str(root)


def _declaration(paths, **overrides):
    payload = {"choice": "排除外来改动", "paths": list(paths), "reason": "这是本地工具的临时数据，不属本任务",
               "by": "human:xzc", "at": "2026-11-12T00:00:00Z",
               "quote": "这些不是我的交付，保持原样", "source": "user-declared"}
    payload.update(overrides)
    return payload


class WorkspaceExclusionTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._decl_dir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _run(self.root, "init", "-q")
        (self.root / "pkg").mkdir()
        (self.root / "pkg" / "mine.py").write_text("base\n", encoding="utf-8")
        _run(self.root, "add", "-A")
        _run(self.root, "commit", "-qm", "base")
        self.baseline = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.root, check=True,
                                       capture_output=True, text=True).stdout.strip()
        # 本任务改动 + 外来未提交文件
        (self.root / "pkg" / "mine.py").write_text("changed\n", encoding="utf-8")
        (self.root / ".unipi").mkdir()
        (self.root / ".unipi" / "state.json").write_text('{"local": true}\n', encoding="utf-8")
        self.task_dir = self.root / ".wf" / "tasks" / "t1-task"
        self.task_dir.mkdir(parents=True)
        self.task = {"id": "t1", "title": "t", "status": "in_progress", "phase": "execute",
                     "baseline_head": self.baseline,
                     "entry_snapshot": {"touch_paths": ["pkg/mine.py"]},
                     "plan": {"complexity": "light", "acceptance": [], "verifications": []},
                     "execution": {}}
        records.write_json(self.task_dir / "task.json", self.task)
        self.ctx = Ctx(self.root)

    def tearDown(self):
        self._tmp.cleanup()
        self._decl_dir.cleanup()

    def entries(self, payload=None):
        path = Path(self._decl_dir.name) / "exclusion.json"
        records.write_json(path, payload or _declaration([".unipi/state.json"]))
        return scope.load_exclusion_declarations(str(path))

    def test_without_declaration_the_check_reports_the_blocker_with_exits(self):
        with self.assertRaises(check.CheckError) as caught:
            check.run_check_scope(self.ctx, dict(self.task), [], None)
        self.assertEqual(caught.exception.code, "WF_WORKSPACE_UNRESOLVED")
        self.assertIn(".unipi/state.json", caught.exception.facts["other_tasks"])
        self.assertTrue(caught.exception.facts["exits"])

    def test_declaration_moves_the_path_to_the_excluded_bucket(self):
        entries, problems = self.entries()
        self.assertEqual(problems, [])
        classified = scope.classify_candidates(self.root, dict(self.task))
        self.assertIn(".unipi/state.json", classified["buckets"]["c"])
        task = dict(self.task, execution=dict(self.task["execution"]))
        classified = tasks_mod._apply_exclusion_entries(self.ctx, task, classified, entries)
        self.assertEqual(classified["buckets"]["c"], [])
        self.assertEqual(classified["buckets"]["x"], [".unipi/state.json"])
        self.assertEqual([item["path"] for item in classified["exclusions"]["applied"]],
                         [".unipi/state.json"])
        # 交付面不受影响（排除不是"算作本任务"）
        delivery = scope.delivery_set(self.root, task, classified=classified)
        self.assertNotIn(".unipi/state.json", delivery["paths"])
        self.assertIn("pkg/mine.py", delivery["paths"])

    def test_exclusion_lapses_when_the_content_changes(self):
        entries, _problems = self.entries()
        task = dict(self.task, execution=dict(self.task["execution"]))
        classified = tasks_mod._apply_exclusion_entries(self.ctx, task, scope.classify_candidates(self.root, task), entries)
        self.assertEqual(classified["buckets"]["c"], [])
        (self.root / ".unipi" / "state.json").write_text('{"local": false}\n', encoding="utf-8")
        again = scope.classify_candidates(self.root, task)
        self.assertEqual(again["buckets"]["x"], [])
        self.assertEqual(again["buckets"]["c"], [".unipi/state.json"])
        self.assertEqual([item["path"] for item in again["exclusions"]["lapsed"]], [".unipi/state.json"])

    def test_glob_and_missing_attestation_are_refused(self):
        _entries, problems = self.entries(_declaration([".unipi/**"]))
        self.assertTrue(any("glob" in item["reason"] for item in problems))
        _entries, problems = self.entries(_declaration([".unipi/state.json"], by="ai"))
        self.assertTrue(any(item.get("by") for item in problems))
        _entries, problems = self.entries(_declaration([".unipi/state.json"], quote=" "))
        self.assertTrue(problems)

    def test_unknown_choice_is_refused_not_ignored(self):
        _entries, problems = self.entries(_declaration([".unipi/state.json"], choice="排除"))
        self.assertTrue(any(item.get("choice") for item in problems))

    def test_paths_outside_the_c_bucket_are_refused(self):
        entries, _problems = self.entries(_declaration(["pkg/mine.py"]))
        classified = scope.classify_candidates(self.root, dict(self.task))
        _records, problems = scope.exclusion_records(self.root, classified, entries)
        self.assertTrue(problems)
        self.assertIn("c 桶", problems[0]["reason"])

    def test_task_record_template_declares_the_field(self):
        record = tasks_mod.new_task_record("ordinary", "t")
        self.assertEqual(record["execution"].get("workspace_exclusions"), [])

    def test_unreadable_or_missing_declaration_file_is_reported(self):
        entries, problems = scope.load_exclusion_declarations(str(self.root / "nope.json"))
        self.assertEqual(entries, [])
        self.assertTrue(problems)
        bad = self.root / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        entries, problems = scope.load_exclusion_declarations(str(bad))
        self.assertEqual(entries, [])
        self.assertTrue(problems)
        non_object = self.root / "non-object.json"
        records.write_json(non_object, ["x"])
        _entries, problems = scope.load_exclusion_declarations(str(non_object))
        self.assertTrue(problems)

    def test_quote_is_masked_and_attested(self):
        entries, _problems = self.entries(
            _declaration([".unipi/state.json"], quote="Authorization: Bearer abcdef123456 我确认"))
        classified = scope.classify_candidates(self.root, dict(self.task))
        records_out, _problems = scope.exclusion_records(self.root, classified, entries)
        self.assertNotIn("abcdef123456", records_out[0]["quote"])
        self.assertTrue(records_out[0]["attestation_digest"].startswith("sha256:"))

    def test_duplicate_paths_in_one_declaration_collapse(self):
        entries, _problems = self.entries(_declaration([".unipi/state.json", ".unipi/state.json"]))
        classified = scope.classify_candidates(self.root, dict(self.task))
        records_out, problems = scope.exclusion_records(self.root, classified, entries)
        self.assertEqual(problems, [])
        self.assertEqual([item["path"] for item in records_out], [".unipi/state.json"])

    def test_repeating_the_same_declaration_is_idempotent(self):
        entries, _problems = self.entries()
        task = dict(self.task, execution=dict(self.task["execution"]))
        tasks_mod._apply_exclusion_entries(self.ctx, task, scope.classify_candidates(self.root, task), entries)
        again = scope.classify_candidates(self.root, task)
        new_records, problems = scope.exclusion_records(self.root, again, entries)
        self.assertEqual(problems, [])
        self.assertEqual(new_records, [])
        self.assertEqual(again["buckets"]["c"], [])
        self.assertEqual(len(task["execution"]["workspace_exclusions"]), 1)


if __name__ == "__main__":
    unittest.main()
