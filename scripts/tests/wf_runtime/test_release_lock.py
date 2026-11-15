"""测试发行 cache 的并发锁与发布 journal（AC2/AC3/AC4）。

断言锚在**行为**上：
- 两个 ensure、ensure×check、以及"外部 ensure/check × 消费期独占 lease"都明确 busy（退出码 75），
  两个只读 check 可共存，释放后可重试，取消不泄漏锁；
- 旧 schema meta 只算 miss 并重建；
- 每个 journal 中断窗口都能前滚到可验证新代、或按冻结旧字节回滚；
- `--check` 对未完成 journal 返回 recovery-required 且不写任何东西；
- 两代都不可验证时 fail closed 并保留现场。
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TESTS = REPO / "scripts" / "tests"

sys.path.insert(0, str(REPO / "scripts"))
test_release = None
common = None


def _load():
    global test_release, common
    if test_release is not None:
        return
    spec = importlib.util.spec_from_file_location("wf_test_release_lock", TESTS / "wf_test_release.py")
    test_release = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(test_release)
    import wf_release_common as module

    common = module


_load()

VERSION = "0.1.0"
DEV = {"version": "0.0.0-dev"}


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-release-lock-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "0.1.0"
        self.meta = Path(str(self.root) + ".meta.json")
        self.owner = Path(str(self.root) + ".owner")
        self.journal = Path(str(self.root) + ".journal.json")

    def make_release(self, marker="old"):
        write(self.root / "wf-release.json", json.dumps({"version": VERSION}) + "\n")
        write(self.root / "x.txt", marker + "\n")
        meta = {
            "schema_version": 2,
            "version": VERSION,
            "release_ref": test_release.ref_for(VERSION),
            "build_inputs": common.test_release_inputs_digest(VERSION),
            "output_tree_digest": common.tree_digest(self.root),
            "manifest_digest": common.manifest_digest({"version": VERSION}),
            "source_tree_digest": common.source_tree_digest(),
            "built_at": "2026-11-15T00:00:00Z",
            "root": str(self.root),
        }
        write(self.meta, json.dumps(meta, sort_keys=True) + "\n")
        write(self.owner, json.dumps({"schema_version": 1, "owner": test_release.OWNER_TAG,
                                      "root": str(self.root), "version": VERSION}, sort_keys=True) + "\n")
        return meta

    def hold_lock(self, exclusive=True, ready_wait=5):
        """子进程持锁并报告 ready，父进程据此建立确定的竞争窗口（不靠 sleep 猜先后）。"""
        code = (
            "import importlib.util, os, sys, time\n"
            f"spec = importlib.util.spec_from_file_location('r', {str(TESTS / 'wf_test_release.py')!r})\n"
            "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
            f"fd = m.acquire_lock({str(self.root)!r}, exclusive={exclusive})\n"
            "print('ready', flush=True)\n"
            "print('pid', flush=True)\n"
            "time.sleep(30)\n"
        )
        proc = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True)
        self.addCleanup(lambda: (proc.poll() is None and (proc.kill(), proc.wait()),
                         proc.stdout.close()))
        self.assertEqual(proc.stdout.readline().strip(), "ready")
        return proc

    def cli(self, *args, timeout=120):
        return subprocess.run([sys.executable, str(TESTS / "wf_test_release.py"), *args],
                              capture_output=True, text=True, timeout=timeout)


class BusyTest(Base):
    def test_second_ensure_is_busy_and_recoverable_after_release(self):
        self.make_release()
        proc = self.hold_lock()
        busy = self.cli("--ensure", "--root", str(self.root), "--version", VERSION)
        self.assertEqual(busy.returncode, test_release.BUSY_EXIT, busy.stdout + busy.stderr)
        self.assertIn("BUSY", busy.stderr)
        proc.kill()
        proc.communicate()
        again = self.cli("--check", "--root", str(self.root), "--version", VERSION)
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)

    def test_external_check_is_busy_during_consuming_lease(self):
        self.make_release()
        self.hold_lock(exclusive=True)
        checked = self.cli("--check", "--root", str(self.root), "--version", VERSION)
        self.assertEqual(checked.returncode, test_release.BUSY_EXIT)
        self.assertIn("busy", checked.stderr)

    def test_two_shared_checks_coexist(self):
        self.make_release()
        first = self.hold_lock(exclusive=False)
        second = self.hold_lock(exclusive=False)
        self.assertIsNone(first.poll())
        self.assertIsNone(second.poll())
        checked = self.cli("--check", "--root", str(self.root), "--version", VERSION)
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

    def test_recovery_needs_the_exclusive_lock_too(self):
        self.make_release()
        write(self.journal, '{"broken": true}')
        held = self.hold_lock()
        busy = self.cli("--ensure", "--root", str(self.root), "--version", VERSION)
        self.assertEqual(busy.returncode, test_release.BUSY_EXIT)
        held.kill()
        held.communicate()


class JournalTest(Base):
    def test_pending_journal_is_recovery_required_and_read_only(self):
        meta = self.make_release()
        write(self.journal, json.dumps({"schema_version": 1, "transaction": "t", "root": str(self.root),
                                        "old": {"present": True}, "new": None}) + "\n")
        before = (self.root / "x.txt").read_text()
        checked = self.cli("--check", "--root", str(self.root), "--version", VERSION)
        self.assertNotEqual(checked.returncode, 0)
        self.assertIn("recovery-required", checked.stderr)
        self.assertTrue(self.journal.is_file())
        self.assertEqual((self.root / "x.txt").read_text(), before)
        self.assertEqual(json.loads(self.meta.read_text())["output_tree_digest"],
                         meta["output_tree_digest"])

    def _journal(self, old, new):
        write(self.journal, json.dumps({"schema_version": 1, "transaction": "tx", "root": str(self.root),
                                        "old": old, "new": new}, sort_keys=True) + "\n")

    def _old_payload(self):
        return {"present": True, "digest": common.tree_digest(self.root),
                "meta": self.meta.read_text(), "owner": self.owner.read_text()}

    def _new_tree(self, marker="new"):
        staging = Path(str(self.root) + ".staging-tx")
        write(staging / "wf-release.json", json.dumps({"version": VERSION}) + "\n")
        write(staging / "x.txt", marker + "\n")
        return staging

    def _new_meta(self, staging):
        meta = {
            "schema_version": 2,
            "version": VERSION,
            "release_ref": test_release.ref_for(VERSION),
            "build_inputs": common.test_release_inputs_digest(VERSION),
            "output_tree_digest": common.tree_digest(staging),
            "manifest_digest": common.manifest_digest({"version": VERSION}),
            "source_tree_digest": common.source_tree_digest(),
            "built_at": "2026-11-15T00:00:00Z",
            "root": str(self.root),
        }
        return meta

    def test_verifiable_new_generation_rolls_forward(self):
        self.make_release()
        old = self._old_payload()
        staging = self._new_tree()
        backup = str(self.root) + ".backup-tx"
        new_meta = self._new_meta(staging)
        owner_text = self.owner.read_text()
        self._journal(old, {"digest": new_meta["output_tree_digest"], "staging": str(staging),
                           "backup": backup, "meta": json.dumps(new_meta, sort_keys=True) + "\n",
                           "owner": owner_text})
        os.rename(self.root, backup)
        result = self.cli("--ensure", "--root", str(self.root), "--version", VERSION)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.root / "x.txt").read_text(), "new\n")
        self.assertFalse(self.journal.exists())
        self.assertEqual(json.loads(self.meta.read_text())["output_tree_digest"],
                         new_meta["output_tree_digest"])

    def test_broken_new_generation_rolls_back_old_bytes(self):
        self.make_release("old")
        old = self._old_payload()
        staging = self._new_tree("new")
        backup = str(self.root) + ".backup-tx"
        new_digest = common.tree_digest(staging)
        self._journal(old, {"digest": new_digest, "staging": str(staging), "backup": backup,
                           "meta": "{\"unused\": true}\n", "owner": self.owner.read_text()})
        os.rename(self.root, backup)
        write(staging / "x.txt", "corrupted\n")          # 新代与 journal 声明不符
        result = self.cli("--ensure", "--root", str(self.root), "--version", VERSION)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.root / "x.txt").read_text(), "old\n")
        self.assertFalse(self.journal.exists())
        self.assertFalse(Path(backup).exists())
        self.assertEqual(self.meta.read_text(), old["meta"])

    def test_first_publication_without_old_generation_only_undoes_new(self):
        sibling = self.root.parent / "keep.txt"
        write(sibling, "keep\n")
        old = {"present": False}
        staging = self._new_tree("new")
        new_meta = self._new_meta(staging)
        self._journal(old, {"digest": new_meta["output_tree_digest"], "staging": str(staging),
                           "backup": str(self.root) + ".backup-tx",
                           "meta": json.dumps(new_meta, sort_keys=True) + "\n",
                           "owner": json.dumps({"schema_version": 1, "owner": test_release.OWNER_TAG,
                                                "root": str(self.root)}, sort_keys=True) + "\n"})
        result = self.cli("--ensure", "--root", str(self.root), "--version", VERSION)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(sibling.read_text(), "keep\n")
        self.assertFalse(self.journal.exists())
        self.assertTrue(self.root.is_dir())

    def test_both_generations_unverifiable_fails_closed(self):
        self.make_release()
        old = self._old_payload()
        staging = self._new_tree("new")
        self._journal(old, {"digest": common.tree_digest(staging), "staging": str(staging),
                           "backup": str(self.root) + ".backup-tx", "meta": "{}\n", "owner": "{}\n"})
        os.rename(self.root, str(self.root) + ".backup-tx")
        write(Path(str(self.root) + ".backup-tx") / "x.txt", "tampered\n")
        write(staging / "x.txt", "also-tampered\n")
        result = self.cli("--ensure", "--root", str(self.root), "--version", VERSION)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("无法恢复", result.stderr)
        self.assertTrue(self.journal.exists())
        self.assertTrue(Path(str(self.root) + ".backup-tx").is_dir())
        self.assertFalse(self.root.exists())

    def test_out_of_bounds_journal_is_refused(self):
        self.make_release()
        write(self.journal, json.dumps({"schema_version": 1, "transaction": "tx",
                                        "root": "/somewhere/else", "old": {"present": False},
                                        "new": None}) + "\n")
        result = self.cli("--ensure", "--root", str(self.root), "--version", VERSION)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("journal", result.stderr)
        self.assertTrue(self.journal.exists())


class SchemaTest(Base):
    def test_legacy_meta_is_a_miss_and_rebuilds_with_schema_two(self):
        meta = self.make_release()
        legacy = dict(meta)
        legacy["schema_version"] = 1
        del legacy["build_inputs"]
        write(self.meta, json.dumps(legacy, sort_keys=True) + "\n")
        self.assertIsNone(test_release._hit_meta(self.root, VERSION, meta["build_inputs"]))
        self.assertNotEqual(self.cli("--check", "--root", str(self.root), "--version", VERSION).returncode, 0)

    def test_consumption_lease_verifies_after_exec(self):
        self.make_release()
        result = subprocess.run(
            [sys.executable, str(TESTS / "wf_test_release.py"), "--lease", "--root", str(self.root),
             "--version", VERSION, "--no-build", "--",
             sys.executable, str(TESTS / "wf_test_release.py"), "--verify-lease",
             "--root", str(self.root)],
            capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK  lease", result.stdout)

    def test_forged_lease_environment_is_rejected(self):
        self.make_release()
        result = subprocess.run(
            [sys.executable, str(TESTS / "wf_test_release.py"), "--verify-lease", "--root", str(self.root)],
            env={**os.environ, "WF_TEST_RELEASE_LEASE_FD": "0", "WF_TEST_RELEASE_LEASE_PID": str(os.getpid()),
                 "WF_TEST_RELEASE_ROOT": str(self.root)},
            capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)

    def test_lock_inode_survives_rebuild_and_is_not_unlinked(self):
        self.make_release()
        fd = test_release.acquire_lock(self.root)
        inode = os.fstat(fd).st_ino
        test_release.release_lock(fd)
        lock = Path(str(self.root) + ".lock")
        self.assertTrue(lock.is_file())
        self.assertEqual(lock.stat().st_ino, inode)


if __name__ == "__main__":
    unittest.main()
