"""R1：交付集合唯一实现（`scope.delivery_set`）与它的消费者。

覆盖三处此前的分叉：
- `check.object_paths` 只取 e 桶；
- 审查材料取 e ∪ f；
- Check 里把已批准扩面的 f 并进 e 只用于展示。

断言锚在行为上：已获 `expand` 确认的越界路径必须同时进入 `delivery_set().paths`、
`object_paths()` 与 `pending_delivery_paths()`；未获确认时仍是 `uncovered_f`。
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import check, scope, tasks  # noqa: E402

TASK_ID = "2026-01-01-0123456789abcdef"


def _run(root, *args):
    subprocess.run(["git", "-c", "user.email=t@example.com", "-c", "user.name=t", *args],
                   cwd=root, check=True, capture_output=True)


def _repo():
    root = tempfile.mkdtemp(prefix="wf-delivery-")
    _run(root, "init", "-q")
    os.makedirs(os.path.join(root, "src"), exist_ok=True)
    with open(os.path.join(root, "src", "a.py"), "w", encoding="utf-8") as handle:
        handle.write("a = 1\n")
    with open(os.path.join(root, "README.md"), "w", encoding="utf-8") as handle:
        handle.write("# demo\n")
    _run(root, "add", ".")
    _run(root, "commit", "-qm", "base")
    return root


def _task(**overrides):
    task = {
        "id": TASK_ID,
        "phase": "execute",
        "entry_snapshot": {"touch_paths": ["src/**"]},
        "baseline_head": None,
        "plan": {"touch_paths": ["src/**"]},
    }
    task.update(overrides)
    return task


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def _authorize(root, action, payload):
    directory = os.path.join(root, ".wf", "tasks", f"{TASK_ID}-demo")
    os.makedirs(directory, exist_ok=True)
    _write(os.path.join(directory, "task.json"), json.dumps({"id": TASK_ID}, ensure_ascii=False))
    _write(os.path.join(directory, f"authorization-{action}.json"),
           json.dumps(dict(payload, action=action), ensure_ascii=False))


class DeliverySetTest(unittest.TestCase):
    def test_in_scope_changes_are_in_the_delivery_set(self):
        root = _repo()
        _write(os.path.join(root, "src", "a.py"), "a = 2\n")
        _write(os.path.join(root, "src", "new.py"), "b = 1\n")
        delivery = scope.delivery_set(root, _task())
        self.assertEqual(delivery["buckets"]["uncovered_f"], [])
        self.assertEqual(delivery["paths"], ["src/a.py", "src/new.py"])
        self.assertEqual(check.object_paths(SimpleNamespace(root=root), _task()), delivery["paths"])

    def test_unapproved_out_of_scope_path_is_uncovered(self):
        root = _repo()
        _write(os.path.join(root, "other", "extra.py"), "x = 1\n")
        task = _task(attribution={"inherited": [{"paths": ["other/extra.py"]}]})
        delivery = scope.delivery_set(root, task)
        self.assertEqual(delivery["buckets"]["f"], ["other/extra.py"])
        self.assertEqual(delivery["buckets"]["covered_f"], [])
        self.assertEqual(delivery["buckets"]["uncovered_f"], ["other/extra.py"])
        self.assertNotIn("other/extra.py", delivery["paths"])

    def test_approved_expansion_enters_delivery_set_and_pending(self):
        root = _repo()
        _write(os.path.join(root, "other", "extra.py"), "x = 1\n")
        _authorize(root, "expand", {"paths": ["other/extra.py"]})
        task = _task(attribution={"inherited": [{"paths": ["other/extra.py"]}]})
        delivery = scope.delivery_set(root, task)
        self.assertEqual(delivery["buckets"]["covered_f"], ["other/extra.py"])
        self.assertEqual(delivery["buckets"]["uncovered_f"], [])
        self.assertIn("other/extra.py", delivery["paths"])
        self.assertIn("other/extra.py", check.object_paths(SimpleNamespace(root=root), task))
        pending = tasks.pending_delivery_paths(SimpleNamespace(root=root), task)
        self.assertIn("other/extra.py", pending)

    def test_project_spec_paths_stay_in_the_delivery_set(self):
        """项目自己的 spec 是项目数据，不是框架自有资产：归了本任务就必须进交付集合。"""
        root = _repo()
        _write(os.path.join(root, ".wf", "spec", "rule.md"), "---\nschema_version: 1\n---\n# r\n")
        task = _task(plan={"touch_paths": ["src/**", ".wf/spec/rule.md"]},
                     entry_snapshot={"touch_paths": ["src/**", ".wf/spec/rule.md"]})
        delivery = scope.delivery_set(root, task)
        self.assertIn(".wf/spec/rule.md", delivery["paths"])
        self.assertIn(".wf/spec/rule.md", check.object_paths(SimpleNamespace(root=root), task))
        self.assertIn(".wf/spec/rule.md", tasks.pending_delivery_paths(
            SimpleNamespace(root=root), task))

    def test_new_file_can_be_covered_by_expansion(self):
        """新增文件不在 `git ls-files` 里：扩面确认必须把未跟踪文件算作真实区域。"""
        root = _repo()
        _write(os.path.join(root, "docs", "new.md"), "# new\n")
        _authorize(root, "expand", {"paths": ["docs/new.md"]})
        task = _task(attribution={"inherited": [{"paths": ["docs/new.md"]}]})
        delivery = scope.delivery_set(root, task)
        self.assertEqual(delivery["buckets"]["uncovered_f"], [])
        self.assertEqual(delivery["buckets"]["covered_f"], ["docs/new.md"])


if __name__ == "__main__":
    unittest.main()
