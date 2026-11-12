"""P2-6：Check 的验证命令必须在**锁外**执行（机制稿 §4.1「长操作不长期持 OS 锁」）。

历史状态：`cmd_task_check` 的 `lock.acquire` 覆盖 `run_check` 全程，其中步骤③用
`subprocess.run` 执行人的验证命令——验证命令有多长，互斥窗口就有多长
（已有 `verification_timeout_seconds` 作上界，但那是缓解不是结构）。

现在拆三段：锁内准备（范围核对 + 锚点固定）→ **锁外执行** → 锁内定稿。
「锁外期间对象被改」不引入新判据：回锁后**重算锚点**（变了即 `WF_CHECK_STALE`），
且 `run_check_finish` 里既有的扫描前后比对本就是同一件事。

本文件钉住两侧：① 执行段确实不持锁（期间别的会话能推进写权）；② 期间对象变化 → `WF_CHECK_STALE`。
"""

import sys
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import check as check_mod  # noqa: E402
from wflib import lock as lock_mod  # noqa: E402


def _state(anchor="sha256:" + "a" * 64):
    return {"anchor": anchor, "plan": {"verifications": []}, "decisions": [],
            "started": "2026-11-12T00:00:00.000000Z", "scan_before": [],
            "scope_facts": {"buckets": {k: [] for k in "abcdef"}, "external_changes": []},
            "coverage": {}, "governance_violations": [], "parts": {},
            "review_notes_path": None}


class CheckLockWindowTest(unittest.TestCase):
    def test_execute_phase_does_not_hold_the_project_lock(self):
        """执行段运行期间，另一个进程能取到同一把项目锁（否则就是「长操作占锁」）。"""
        import os
        import tempfile

        root = tempfile.mkdtemp(prefix="wf-lockwin-")
        os.makedirs(os.path.join(root, ".wf"), exist_ok=True)
        acquired = {}

        def take_lock():
            try:
                with lock_mod.acquire(root, holder_hint="other-session"):
                    acquired["ok"] = True
            except Exception as exc:  # noqa: BLE001
                acquired["error"] = repr(exc)

        state = _state()
        with mock.patch.object(check_mod, "_task_dir", return_value=root), \
                mock.patch.object(check_mod, "_run_argv",
                                  side_effect=lambda *a, **k: (time.sleep(0.3) or {"status": "passed"})):
            thread = threading.Thread(target=take_lock)
            thread.start()
            check_mod.run_check_execute(mock.Mock(root=root), {"id": "t1", "plan": {}}, state)
            thread.join(timeout=5)
        self.assertTrue(acquired.get("ok"), f"执行段期间取锁失败：{acquired}")

    def test_finish_compares_scan_and_anchor(self):
        """锁外窗口里的内容变化必须由既有比对挡住（不是新加的判据）。"""
        state = _state()
        task = {"id": "t1", "plan": {"verifications": []}, "check_history": []}
        with mock.patch.object(check_mod, "_task_dir", return_value="/tmp/x"), \
                mock.patch.object(check_mod, "_parse_review_notes", return_value=({"standard": {"conclusion": "pass"},
                                                                                   "requirement": {"conclusion": "pass"}}, None)), \
                mock.patch.object(check_mod, "object_paths", return_value=[]), \
                mock.patch.object(check_mod, "fingerprint") as fake_fingerprint, \
                mock.patch.object(check_mod.scope, "classify_candidates",
                                  return_value={"buckets": {k: [] for k in "abcdef"}, "candidates": [],
                                                "touch_paths": []}), \
                mock.patch.object(check_mod.scope, "external_changes", return_value=({}, [])), \
                mock.patch.object(check_mod.scope, "declaration_violations", return_value=([], {})), \
                mock.patch.object(check_mod, "_acceptance_results", return_value=[]):
            fake_fingerprint.items.return_value = [{"path": "pkg/a.py", "digest": "sha256:changed"}]
            with self.assertRaises(check_mod.CheckError) as caught:
                check_mod.run_check_finish(mock.Mock(root="/tmp/x"), task, state, [])
        self.assertEqual(caught.exception.code, "WF_CHECK_STALE")
        self.assertIn("扫描前后不一致", caught.exception.facts["reason"])

    def test_command_check_has_three_phases(self):
        """结构断言：`cmd_task_check` 必须在两次取锁之间调用执行段。"""
        source = (REPO / "docs" / "workflows" / "wf" / "payload" / "lib" / "wflib"
                  / "tasks.py").read_text(encoding="utf-8")
        body = source[source.index("def cmd_task_check("):source.index("def _require_task_dir(")]
        self.assertEqual(body.count("lock.acquire("), 2, "应当恰好两段锁内")
        first_lock = body.index("lock.acquire(")
        second_lock = body.index("lock.acquire(", first_lock + 1)
        scope = body.index("check_mod.run_check_scope(")
        execute = body.index("check_mod.run_check_execute(")
        finish = body.index("check_mod.run_check_finish(")
        self.assertLess(first_lock, scope, "准备段在第一段锁内")
        self.assertLess(scope, second_lock)
        self.assertLess(execute, second_lock, "执行段必须在第二次取锁之前（即锁外）")
        self.assertLess(first_lock, execute)
        self.assertLess(second_lock, finish, "定稿段在第二段锁内")
        # 缩进不能区分「锁内」与「try 内」，因此不靠它判：锁外这一事实由上一条线程用例证明。
        self.assertIn('"WF_CHECK_STALE"', body[execute:second_lock + 2000],
                      "回锁后必须重算锚点并以 WF_CHECK_STALE 拒绝")


if __name__ == "__main__":
    unittest.main()
