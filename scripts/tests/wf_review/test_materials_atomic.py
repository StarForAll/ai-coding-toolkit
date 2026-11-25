"""轮次材料是原子发布：中断不留半包、失败不落半成品（2026-11-24 台账 1.2 的三条断言）。

防的失败（F1a，dogfood 实录）：逐文件直写 + manifest 最后写的中断窗口留下无 manifest 的
半包——下次 review-context 把它当 `legacy` 采纳，reviewer 读到缺件的"材料"。
发布已改为 staging 写全（含 manifest）后一次 rename；本文件锁三条行为：
1. 正常物化后轮次目录无 `materials.staging-*` 残留，materials/ 完整且 manifest 在包内；
2. `write_materials` 注入异常后接口失败、materials/ 只留空目录（半包 ≠ unmaterialized），
   重跑可完整出版；崩溃遗留的 staging 残留由下一次物化起手清掉；
3. 只在 unmaterialized 发布：fixed 重入不重写 manifest（generated_at 不变）。
"""

import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import records, review  # noqa: E402

ANCHOR = "sha256:" + "a" * 64
COVERED = ["node_modules/**", ".env", "*.pem", ".codex/**", "../**", ".wf/tasks/**"]


def _write_diff(*args, **_kwargs):
    """真实 write_materials 的最小替身：往第 5 个位置参数（staging 目录）写一个材料文件。"""
    records.atomic_write(Path(args[4]) / "diff.patch", "read\n")
    return {}


class AtomicPublishTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.task_id = "t1-" + uuid.uuid4().hex[:8]
        self.task_dir = self.root / ".wf" / "tasks" / self.task_id
        self.task_dir.mkdir(parents=True)
        self.task = {"id": self.task_id, "title": "t", "status": "in_progress", "phase": "check",
                     "revision": 1, "check": {"id": "c1", "result": "pass",
                                              "anchor": {"check_anchor": ANCHOR}},
                     "reviews": {"launches": [{"round": 1, "implementation_cli": "dsh",
                                               "slots": [{"slot": "s1"}],
                                               "anchor": {"check_id": "c1", "check_anchor": ANCHOR},
                                               "submitted_scope": {"diff": {"paths": ["pkg/a.py"]}},
                                               "readable_scope": {"business_code": ["**"]},
                                               "exclusions": list(COVERED),
                                               "temp_paths": []}],
                                 "imported": []}}
        records.write_json(self.task_dir / "task.json", self.task)

    def tearDown(self):
        self._tmp.cleanup()

    def _ctx(self):
        return SimpleNamespace(root=str(self.root))

    def _delivery(self):
        return {"paths": ["pkg/a.py"],
                "buckets": {"e": ["pkg/a.py"], "f": [], "covered_f": [], "uncovered_f": []}}

    def _round_dir(self):
        return Path(review.round_dir(self._ctx(), self.task_id, 1))

    def _materials_dir(self):
        return self._round_dir() / "materials"

    def _context(self, write_side_effect=None):
        write = write_side_effect or _write_diff
        with mock.patch.object(review, "_current_anchor", return_value=(ANCHOR, {})), \
                mock.patch.object(review.scope_mod, "delivery_set",
                                  return_value=self._delivery()), \
                mock.patch.object(review, "write_materials", side_effect=write):
            return review.context(self._ctx(), self.task, 1, as_value="pi")

    def _staging_dirs(self):
        return sorted(name.name for name in self._round_dir().iterdir()
                      if name.is_dir() and name.name.startswith("materials.staging-"))

    def test_normal_publish_leaves_no_staging_residue(self):
        result = self._context()
        self.assertEqual(self._staging_dirs(), [], "正常物化不得留下 staging 目录")
        materials = self._materials_dir()
        self.assertTrue((materials / "materials-manifest.json").is_file())
        self.assertTrue((materials / "diff.patch").is_file())
        # facts.materials_check 记的是进入时状态（本轮开始时确实未物化）；发布后的终态用判据函数核
        self.assertEqual(result["facts"]["materials_check"]["state"], "unmaterialized")
        self.assertEqual(review.materials_identity_state(self._ctx(), self.task_id, 1)["state"],
                         "fixed")

    def test_injected_failure_leaves_no_half_package_and_retry_publishes(self):
        def _boom(*_args, **_kwargs):
            raise RuntimeError("interrupted mid-write")

        with self.assertRaises(RuntimeError):
            self._context(write_side_effect=_boom)
        # prepare 起手的 makedirs 会留下空目录；空目录等同 unmaterialized，但绝不许有内容
        self.assertEqual(sorted(p.name for p in self._materials_dir().iterdir()), [],
                         "失败的物化不得留下半包（无 manifest 的内容文件）")
        self.assertEqual(self._staging_dirs(), [], "异常路径必须清掉本次 staging")
        self.assertEqual(review.materials_identity_state(self._ctx(), self.task_id, 1)["state"],
                         "unmaterialized")
        # 崩溃遗留的 staging 残留（进程被杀的形态）由下一次物化起手清掉
        stale = self._round_dir() / "materials.staging-deadbeef"
        stale.mkdir(parents=True)
        records.atomic_write(stale / "diff.patch", "orphan\n")
        result = self._context()
        self.assertEqual(self._staging_dirs(), [], "重跑不得留下崩溃残留")
        self.assertTrue((self._materials_dir() / "materials-manifest.json").is_file())
        self.assertEqual(review.materials_identity_state(self._ctx(), self.task_id, 1)["state"],
                         "fixed")

    def test_fixed_reentry_keeps_manifest_bytes(self):
        self._context()
        manifest = self._materials_dir() / "materials-manifest.json"
        before = manifest.read_bytes()
        self._context()
        self.assertEqual(manifest.read_bytes(), before, "fixed 重入是复用，不重写 manifest")


if __name__ == "__main__":
    unittest.main()
