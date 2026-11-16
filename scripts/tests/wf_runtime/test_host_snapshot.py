"""Host protection evidence (AC13/AC14): terminal-state tree manifest, not top-level mtime.

The detector must be able to prove itself: deep changes with the top-level mtime restored,
permission changes, link retargeting, additions/removals, missing vs empty, and unreadable
trees all produce distinguishable results; links are never followed outside the tree.
"""

import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

FULL = Path(__file__).resolve().parent / "full"


def _load():
    spec = importlib.util.spec_from_file_location("wf_host_snapshot", FULL / "host_snapshot.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HostSnapshotTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-host-snapshot-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "cache"
        self.root.mkdir()
        self.module = _load()

    def test_deep_change_is_detected_even_when_top_level_mtime_is_restored(self):
        deep = self.root / "a" / "b"
        deep.mkdir(parents=True)
        target = deep / "payload.bin"
        target.write_bytes(b"before")
        top = self.root.stat()
        before = self.module.manifest(self.root)
        target.write_bytes(b"after")
        os.utime(target, (1, 1))
        os.utime(self.root, ns=(top.st_atime_ns, top.st_mtime_ns))
        self.assertEqual(self.root.stat().st_mtime_ns, top.st_mtime_ns)
        differences = self.module.compare(before, self.module.manifest(self.root))
        self.assertTrue(differences["changed"])
        self.assertEqual(differences["modified"], ["a/b/payload.bin"])

    def test_missing_and_empty_are_distinct(self):
        before = self.module.manifest(self.root)
        self.assertEqual(before["state"], "present")
        self.assertEqual(len(before["entries"]), 1)
        empty = Path(self.tmp.name) / "empty"
        empty.mkdir()
        missing = Path(self.tmp.name) / "missing"
        self.assertEqual(self.module.manifest(empty)["state"], "present")
        self.assertEqual(self.module.manifest(missing)["state"], "missing")
        self.assertTrue(self.module.compare(self.module.manifest(empty),
                                            self.module.manifest(missing))["changed"])

    def test_permission_link_and_entry_changes_are_detected(self):
        payload = self.root / "file.txt"
        payload.write_text("x")
        link = self.root / "link"
        link.symlink_to(payload.name)
        before = self.module.manifest(self.root)
        os.chmod(payload, 0o600)
        self.assertTrue(self.module.compare(before, self.module.manifest(self.root))["modified"])
        before = self.module.manifest(self.root)
        link.unlink()
        other = self.root / "other.txt"
        other.write_text("y")
        link.symlink_to(other.name)
        differences = self.module.compare(before, self.module.manifest(self.root))
        self.assertIn("link", differences["modified"])
        before = self.module.manifest(self.root)
        (self.root / "new.txt").write_text("n")
        self.assertIn("new.txt", self.module.compare(before, self.module.manifest(self.root))["added"])
        before = self.module.manifest(self.root)
        (self.root / "new.txt").unlink()
        self.assertIn("new.txt", self.module.compare(before, self.module.manifest(self.root))["removed"])

    def test_links_to_outside_are_not_followed_or_recorded_as_content(self):
        outside = Path(self.tmp.name) / "outside"
        outside.mkdir()
        (outside / "secret.txt").write_text("secret")
        (self.root / "outside-link").symlink_to(outside, target_is_directory=True)
        payload = self.module.manifest(self.root)
        self.assertEqual(payload["entries"]["outside-link"]["type"], "symlink")
        self.assertEqual(payload["entries"]["outside-link"]["target"], str(outside))
        self.assertNotIn("outside-link/secret.txt", payload["entries"])
        self.assertNotIn("secret", json.dumps(payload))

    def test_unreadable_tree_is_unverified_not_empty(self):
        locked = self.root / "locked"
        locked.mkdir()
        (locked / "x").write_text("x")
        os.chmod(locked, 0o000)
        self.addCleanup(os.chmod, locked, 0o755)
        if os.geteuid() == 0:
            self.skipTest("root can read a 0o000 directory")
        with self.assertRaises(self.module.SnapshotError):
            self.module.manifest(self.root)
        proc = subprocess.run([sys.executable, str(FULL / "host_snapshot.py"), "check",
                               str(self.root), "--expect", str(Path(self.tmp.name) / "nope.json")],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("HOST-SNAPSHOT-UNVERIFIED", proc.stderr)

    def test_cli_round_trip(self):
        snapshot = Path(self.tmp.name) / "before.json"
        capture = subprocess.run([sys.executable, str(FULL / "host_snapshot.py"), "capture",
                                  str(self.root), str(snapshot)], capture_output=True, text=True)
        self.assertEqual(capture.returncode, 0, capture.stderr)
        check = subprocess.run([sys.executable, str(FULL / "host_snapshot.py"), "check",
                                str(self.root), "--expect", str(snapshot)],
                               capture_output=True, text=True)
        self.assertEqual(check.returncode, 0)
        (self.root / "added").write_text("x")
        changed = subprocess.run([sys.executable, str(FULL / "host_snapshot.py"), "check",
                                  str(self.root), "--expect", str(snapshot)],
                                 capture_output=True, text=True)
        self.assertEqual(changed.returncode, 1)
        self.assertIn("HOST-CHANGED", changed.stdout)


if __name__ == "__main__":
    unittest.main()
