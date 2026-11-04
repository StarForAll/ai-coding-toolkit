"""锁原语与机制稿 §4.1 的排他创建/不认领语义。"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                "docs", "workflows", "新项目开发工作流", "payload", "lib"))

from wflib import lock  # noqa: E402


class LockContractTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="wf-lock-")
        self.path = os.path.join(self.root, lock.LOCK_NAME)

    def test_first_acquire_creates_mark_exclusively(self):
        handle = lock.acquire(self.root)
        try:
            with open(self.path, "rb") as stream:
                content = stream.read()
            # 首行是固定标记；其后是持锁者事实行（供只读存活探测）
            self.assertTrue(content.startswith(lock.LOCK_MARK))
            self.assertIn(b"holder pid=", content)
        finally:
            handle.release()
        with open(self.path, "rb") as stream:
            self.assertEqual(stream.read(), lock.LOCK_MARK)

    def test_verify_holder_reports_live_process(self):
        handle = lock.acquire(self.root)
        try:
            alive, facts = lock.verify_holder(self.root)
            self.assertTrue(alive)
            self.assertEqual(str(os.getpid()), str(facts.get("pid")))
        finally:
            handle.release()
        alive_after, _facts = lock.verify_holder(self.root)
        self.assertFalse(alive_after, "释放后不应再报告存活")

    def test_existing_mark_is_reused(self):
        with open(self.path, "wb") as stream:
            stream.write(lock.LOCK_MARK)
        handle = lock.acquire(self.root)
        handle.release()

    def test_empty_mark_is_not_claimed(self):
        open(self.path, "wb").close()
        with self.assertRaises(lock.LockUnavailable):
            lock.acquire(self.root)
        with open(self.path, "rb") as stream:
            self.assertEqual(stream.read(), b"", "普通入口不得补写空锁")

    def test_partial_mark_is_not_overwritten(self):
        with open(self.path, "wb") as stream:
            stream.write(b"wf-lock")
        with self.assertRaises(lock.LockUnavailable):
            lock.acquire(self.root)
        with open(self.path, "rb") as stream:
            self.assertEqual(stream.read(), b"wf-lock")

    def test_symlinked_lock_outside_root_is_refused(self):
        outside = tempfile.mkdtemp(prefix="wf-lock-out-")
        with open(os.path.join(outside, "target"), "wb") as stream:
            stream.write(lock.LOCK_MARK)
        os.symlink(os.path.join(outside, "target"), self.path)
        with self.assertRaises(lock.LockUnavailable):
            lock.acquire(self.root)


if __name__ == "__main__":
    unittest.main()
