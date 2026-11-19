"""测试发行缓存的 C3 契约：真实 ensure 的确定性窗口、材料归属与维护出口。

覆盖 W1–W5/F1 的 checkpoint→真实恢复→同 key 可用；新 material-owner 只证明材料归属；
inventory 零写；safe-legacy 只收可验证材料；unproven 必须额外 TTY+摘要确认；journal 最后删。
"""

import json
import os
from unittest import mock
import os
import pty
import select
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TESTS = REPO / "scripts" / "tests"
RELEASE = TESTS / "wf_test_release.py"
sys.path.insert(0, str(TESTS))
sys.path.insert(0, str(TESTS / "wf_runtime" / "full"))
import resource_lifecycle as lifecycle  # noqa: E402
import wf_test_release as release  # noqa: E402

VERSION = "0.1.0"


def env_for(scope, results=None):
    env = {key: value for key, value in os.environ.items() if not key.startswith("WF_")}
    env["WF_TEST_SCOPE_ROOT"] = str(scope)
    env.pop("WF_TEST_RELEASE_LEASE_FD", None)
    env.pop("WF_TEST_RELEASE_LEASE_PID", None)
    if results:
        env["PYTHONPYCACHEPREFIX"] = str(Path(results) / "pycache")
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    return env


def run_cli(scope, args, env_extra=None, timeout=300):
    env = env_for(scope)
    env.update(env_extra or {})
    return subprocess.run([sys.executable, str(RELEASE), *args], capture_output=True,
                          text=True, env=env, cwd=str(REPO), timeout=timeout)


def ensure(scope, root, env_extra=None):
    return run_cli(scope, ["--ensure", "--root", str(root), "--version", VERSION],
                   env_extra)


def check(scope, root):
    return run_cli(scope, ["--check", "--root", str(root), "--version", VERSION])


def inventory(scope, cache_root):
    proc = run_cli(scope, ["--inventory", "--cache-root", str(cache_root), "--json"])
    return proc, json.loads(proc.stdout or "{}")


def retire_pty(scope, args, phrase, timeout=120):
    master, slave = pty.openpty()
    env = env_for(scope)
    proc = subprocess.Popen([sys.executable, str(RELEASE), "--retire", *args],
                            stdin=slave, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, env=env, cwd=str(REPO))
    os.close(slave)
    try:
        time.sleep(0.5)
        try:
            os.write(master, (phrase + "\n").encode())
        except OSError:
            pass
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate(timeout=10)
            stderr += "\nPTY-CHILD-TIMEOUT"
    finally:
        try:
            os.close(master)
        except OSError:
            pass
    return proc.returncode, stdout, stderr



class FinishFailureTest(unittest.TestCase):
    def test_material_cleanup_failure_keeps_the_journal(self):
        root = Path(tempfile.mkdtemp(prefix="finish-fail-"))
        self.addCleanup(shutil.rmtree, root, True)
        real = root / VERSION
        real.mkdir()
        journal = Path(str(real) + ".journal.json")
        journal.write_text("{}")
        staging = Path(str(real) + ".staging-tx")
        staging.mkdir()
        (staging / "payload").write_text("x")
        with mock.patch.object(release, "_remove_material_tree",
                               side_effect=OSError("injected cleanup failure")):
            with self.assertRaises(release.TestReleaseError):
                release._finish_transaction(str(real),
                                            {"new": {"staging": str(staging), "backup": None}})
        self.assertTrue(journal.exists(), "材料未清理时不得先删 journal")
        self.assertTrue(staging.exists(), "失败现场保留")




class InventoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import fixture_scope
        cls.scope = fixture_scope.create_test_scope()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.scope, ignore_errors=True)

    def test_inventory_is_read_only_and_lists_entries(self):
        root = Path(tempfile.mkdtemp(prefix="release-", dir=self.scope)) / "cache"
        root.mkdir()
        real = root / VERSION
        self.assertEqual(ensure(self.scope, real).returncode, 0)
        before = sorted(os.listdir(root))
        report = release.inventory(str(root))
        self.assertEqual(report["status"], "complete", report)
        self.assertTrue(report["entries"])
        self.assertEqual(sorted(os.listdir(root)), before, "盘点必须零写")

    def test_inventory_reports_pending_journal_and_orphans_read_only(self):
        root = Path(tempfile.mkdtemp(prefix="release-", dir=self.scope)) / "cache"
        root.mkdir()
        real = root / VERSION
        journal = Path(str(real) + ".journal.json")
        journal.write_text("{broken")
        orphan = Path(str(real) + ".staging-deadbeef")
        orphan.mkdir()
        (orphan / "payload").write_text("x")
        before = sorted(os.listdir(root))
        report = release.inventory(str(root))
        self.assertEqual(report["status"], "partial")
        kinds = [item["kind"] for item in report["entries"]]
        self.assertIn("journal", kinds)
        self.assertIn("release-staging", kinds)
        self.assertEqual(sorted(os.listdir(root)), before, "盘点不得恢复/删除")
        self.assertTrue(journal.exists())



class CheckpointTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import fixture_scope
        cls.scope = fixture_scope.create_test_scope()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.scope, ignore_errors=True)

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="release-", dir=self.scope))
        self.cache = self.root / "cache"
        self.cache.mkdir()
        self.real = self.cache / VERSION

    def test_windows_recover_from_the_real_entry_and_stay_usable(self):
        # 测试发行在 journal 落盘前已冻结新代摘要：W1–W3 前滚，W4/final 收尾同样前滚；
        # 模板缓存的新摘要确认在 repoint 之后，W1–W3 回滚。两者时机不同，不能复制同一断言。
        scenarios = {
            "after-journal": "rolled-forward",
            "after-old-moved": "rolled-forward",
            "after-new-installed": "rolled-forward",
            "after-meta": "rolled-forward",
            "after-material-cleanup-before-journal-remove": "rolled-forward",
        }
        for point, status in scenarios.items():
            with self.subTest(point=point):
                shutil.rmtree(self.cache, ignore_errors=True)
                self.cache.mkdir()
                first = ensure(self.scope, self.real)
                self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
                fault = {"WF_TEST_FAULT_INJECTION": "1", "WF_TEST_RELEASE_TXN_REBUILD": "1",
                         "WF_TEST_RELEASE_TXN_STOP_AFTER": point}
                failed = ensure(self.scope, self.real, fault)
                self.assertEqual(failed.returncode, 97, failed.stdout + failed.stderr)
                self.assertIn("WF-TEST-RELEASE-TXN-STOP", failed.stderr)
                recovered = ensure(self.scope, self.real)
                self.assertEqual(recovered.returncode, 0, recovered.stdout + recovered.stderr)
                self.assertIn(f"TEST-RELEASE-RECOVERED: {status}", recovered.stderr)
                self.assertFalse(Path(str(self.real) + ".journal.json").exists())
                checked = check(self.scope, self.real)
                self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

    def test_w5_first_publication_and_o1_staging_orphan(self):
        failed = ensure(self.scope, self.real,
                        {"WF_TEST_FAULT_INJECTION": "1",
                         "WF_TEST_RELEASE_TXN_STOP_AFTER": "after-new-installed"})
        self.assertEqual(failed.returncode, 97)
        recovered = ensure(self.scope, self.real)
        self.assertEqual(recovered.returncode, 0, recovered.stderr)
        self.assertIn("rolled-forward", recovered.stderr)
        self.assertEqual(check(self.scope, self.real).returncode, 0)

        shutil.rmtree(self.cache, ignore_errors=True)
        self.cache.mkdir()
        orphan = ensure(self.scope, self.real,
                        {"WF_TEST_FAULT_INJECTION": "1",
                         "WF_TEST_RELEASE_TXN_STOP_AFTER": "after-staging-before-journal"})
        self.assertEqual(orphan.returncode, 97)
        proc, report = inventory(self.scope, self.cache)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        staging = [item for item in report["entries"] if item["kind"] == "release-staging"]
        self.assertEqual(len(staging), 1)
        self.assertEqual(staging[0]["provenance"], "owned",
                         "新 material-owner 必须证明 staging 父目录归属")
        selection = self.root / "selection.json"
        selection.write_text(json.dumps({"schema_version": 1, "domain": "test-release-cache",
                                         "root": report["root"], "entries": [staging[0]]}))
        report_path = self.root / "retire.json"
        retired = run_cli(self.scope, ["--retire", "--cache-root", str(self.cache),
                                       "--selection", str(selection),
                                       "--retirement-mode", "safe-legacy",
                                       "--confirm-retirement", "--report", str(report_path)])
        self.assertEqual(retired.returncode, 0, retired.stdout + retired.stderr)
        self.assertFalse(Path(staging[0]["path"]).exists())
        rebuilt = ensure(self.scope, self.real)
        self.assertEqual(rebuilt.returncode, 0, rebuilt.stderr)

    def test_bad_journal_manual_reset_then_rebuild(self):
        self.assertEqual(ensure(self.scope, self.real).returncode, 0)
        journal = Path(str(self.real) + ".journal.json")
        journal.write_text("{broken")
        proc, report = inventory(self.scope, self.cache)
        self.assertEqual(proc.returncode, 1, "坏 journal 必须让盘点明确非零")
        self.assertTrue(any(item["kind"] == "journal" and item["blocked"]
                            for item in report["entries"]))
        selected = [item for item in report["entries"]
                    if item["path"] in (str(journal), str(self.real))]
        selection = self.root / "selection.json"
        selection.write_text(json.dumps({"schema_version": 1, "domain": "test-release-cache",
                                         "root": report["root"], "entries": selected}))
        # 非 TTY：零删除。
        plain = run_cli(self.scope, ["--retire", "--cache-root", str(self.cache),
                                     "--selection", str(selection),
                                     "--retirement-mode", "manual-retained",
                                     "--confirm-retirement",
                                     "--report", str(self.root / "plain.json")])
        self.assertNotEqual(plain.returncode, 0)
        self.assertTrue(self.real.exists())
        digest = lifecycle.selection_digest(lifecycle.selection_entries(
            json.loads(selection.read_text()), "test-release-cache"))
        phrase = f"test-release-cache {report['root']} {digest} abandon"
        rc, stdout, stderr = retire_pty(
            self.scope, ["--cache-root", str(self.cache), "--selection", str(selection),
                         "--retirement-mode", "manual-retained", "--confirm-retirement",
                         "--report", str(self.root / "manual.json")], phrase)
        self.assertEqual(rc, 0, stdout + stderr)
        self.assertFalse(journal.exists())
        self.assertFalse(self.real.exists())
        rebuilt = ensure(self.scope, self.real)
        self.assertEqual(rebuilt.returncode, 0, rebuilt.stderr)
        self.assertEqual(check(self.scope, self.real).returncode, 0)

    def test_bad_journal_reset_requires_the_whole_key_set(self):
        self.assertEqual(ensure(self.scope, self.real).returncode, 0)
        staging_fault = {"WF_TEST_FAULT_INJECTION": "1", "WF_TEST_RELEASE_TXN_REBUILD": "1",
                         "WF_TEST_RELEASE_TXN_STOP_AFTER": "after-staging-before-journal"}
        staged = ensure(self.scope, self.real, staging_fault)
        self.assertEqual(staged.returncode, 97)
        journal = Path(str(self.real) + ".journal.json")
        journal.write_text("{broken")
        proc, report = inventory(self.scope, self.cache)
        self.assertEqual(proc.returncode, 1)
        entry = next(item for item in report["entries"] if item["kind"] == "release-entry")
        journ = next(item for item in report["entries"] if item["kind"] == "journal")
        selection = self.root / "partial.json"
        selection.write_text(json.dumps({"schema_version": 1, "domain": "test-release-cache",
                                         "root": report["root"], "entries": [entry, journ]}))
        partial = run_cli(self.scope, ["--retire", "--cache-root", str(self.cache),
                                       "--selection", str(selection),
                                       "--retirement-mode", "manual-retained",
                                       "--confirm-retirement",
                                       "--report", str(self.root / "partial-report.json")])
        self.assertNotEqual(partial.returncode, 0)
        self.assertIn("集合不完整", partial.stderr)
        self.assertTrue(self.real.exists() and journal.exists())

    def test_unproven_material_needs_unproven_confirmation(self):
        orphan = Path(str(self.real) + ".staging-deadbeef")
        orphan.mkdir()
        (orphan / "payload.txt").write_text("x")
        proc, report = inventory(self.scope, self.cache)
        item = next(entry for entry in report["entries"] if entry["path"] == str(orphan))
        self.assertEqual(item["provenance"], "unproven")
        selection = self.root / "selection.json"
        selection.write_text(json.dumps({"schema_version": 1, "domain": "test-release-cache",
                                         "root": report["root"], "entries": [item]}))
        safe = run_cli(self.scope, ["--retire", "--cache-root", str(self.cache),
                                    "--selection", str(selection),
                                    "--retirement-mode", "safe-legacy",
                                    "--confirm-retirement",
                                    "--report", str(self.root / "safe.json")])
        self.assertNotEqual(safe.returncode, 0)
        self.assertTrue(orphan.exists())
        digest = lifecycle.selection_digest([item])
        wrong = f"test-release-cache {report['root']} {digest} abandon"
        rc, stdout, stderr = retire_pty(
            self.scope, ["--cache-root", str(self.cache), "--selection", str(selection),
                         "--retirement-mode", "manual-retained", "--confirm-retirement",
                         "--report", str(self.root / "wrong.json")], wrong)
        self.assertNotEqual(rc, 0)
        self.assertTrue(orphan.exists())
        right = f"test-release-cache {report['root']} {digest} abandon unproven-cache"
        rc, stdout, stderr = retire_pty(
            self.scope, ["--cache-root", str(self.cache), "--selection", str(selection),
                         "--retirement-mode", "manual-retained", "--confirm-retirement",
                         "--report", str(self.root / "right.json")], right)
        self.assertEqual(rc, 0, stdout + stderr)
        self.assertFalse(orphan.exists())

    def test_inventory_is_read_only_and_lists_materials(self):
        ensure(self.scope, self.real)
        report = release.inventory(str(self.cache))
        self.assertEqual(report["status"], "complete")
        self.assertTrue(report["entries"])
        self.assertEqual(check(self.scope, self.real).returncode, 0)


if __name__ == "__main__":
    unittest.main()