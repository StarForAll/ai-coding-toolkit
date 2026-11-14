"""wfdrive 的只读注入助手（deny_writes/allow_writes）：三探针等价契约。

契约按行为定义：deny 后对目录内**新建条目**、**改写已存在文件**、**删除已存在条目**
都必须失败（chmod 层与 ro bind mount 层按探针结果选择，两环境同一契约）。
断言锚在行为上：探针结果、恢复后的模式与内容、无残留哨兵/探测文件；
user namespace 分支（root 下升级 ro bind mount）在 `unshare -Urm` 内端到端验证。
"""

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

FULL = Path(__file__).resolve().parents[0] / "full"


def _load_wfdrive():
    spec = importlib.util.spec_from_file_location("wf_runner_wfdrive", FULL / "wfdrive.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


wfdrive = _load_wfdrive()


def _can_unshare():
    try:
        return subprocess.run(["unshare", "-Urm", "true"], capture_output=True).returncode == 0
    except OSError:
        return False


class DenyWritesTest(unittest.TestCase):
    def test_deny_blocks_create_modify_delete_and_allow_restores(self):
        with tempfile.TemporaryDirectory(prefix="wf-deny-") as root:
            target = os.path.join(root, "locked")
            os.makedirs(target)
            existing = os.path.join(target, "r68d.md")
            with open(existing, "w", encoding="utf-8") as handle:
                handle.write("# 占位\n")
            before_modes = {target: os.stat(target).st_mode & 0o7777,
                            existing: os.stat(existing).st_mode & 0o7777}
            token = wfdrive.deny_writes(target)
            try:
                with self.assertRaises(OSError):
                    open(os.path.join(target, "new.md"), "w")
                with self.assertRaises(OSError):
                    open(existing, "r+b")
                with self.assertRaises(OSError):
                    os.unlink(existing)
            finally:
                wfdrive.allow_writes(token)
            for path_, mode in before_modes.items():
                self.assertEqual(os.stat(path_).st_mode & 0o7777, mode, path_)
            self.assertFalse(os.path.exists(os.path.join(target, ".wf-deny-sentinel")))
            self.assertFalse(os.path.exists(os.path.join(target, ".wf-deny-check")))
            with open(os.path.join(target, "new.md"), "w", encoding="utf-8") as handle:
                handle.write("# 恢复后可写\n")

    def test_empty_dir_contract_uniform(self):
        """空注入目录（r1r2 形态）：哨兵保证 modify/unlink 探针有目标，契约不退化。"""
        with tempfile.TemporaryDirectory(prefix="wf-deny-empty-") as root:
            target = os.path.join(root, "blocked-dir")
            os.makedirs(target)
            token = wfdrive.deny_writes(target)
            try:
                with self.assertRaises(OSError):
                    open(os.path.join(target, "x.md"), "w")
                with self.assertRaises(OSError):
                    os.unlink(os.path.join(target, ".wf-deny-sentinel"))
            finally:
                wfdrive.allow_writes(token)
            self.assertEqual(os.listdir(target), [])

    def test_deny_fail_closed_on_missing_dir(self):
        with tempfile.TemporaryDirectory(prefix="wf-deny-missing-") as root:
            with self.assertRaises(RuntimeError):
                wfdrive.deny_writes(os.path.join(root, "nope"))

    def test_allow_restores_after_failed_contract(self):
        """契约建立失败时自动恢复原状（不留半拒绝状态）。"""
        with tempfile.TemporaryDirectory(prefix="wf-deny-fail-") as root:
            target = os.path.join(root, "locked")
            os.makedirs(target)
            broken = wfdrive.deny_writes(target)
            try:
                # 破坏令牌模拟失败路径：直接走 except 分支的恢复
                broken["modes"] = {target: 0o755}
                wfdrive.allow_writes(broken)
                with open(os.path.join(target, "ok.md"), "w", encoding="utf-8") as handle:
                    handle.write("ok\n")
            finally:
                if os.path.exists(os.path.join(target, ".wf-deny-sentinel")):
                    os.unlink(os.path.join(target, ".wf-deny-sentinel"))


@unittest.skipUnless(_can_unshare(), "unshare user namespace 不可用")
class DenyWritesUsernsTest(unittest.TestCase):
    def test_mount_layer_contract_inside_userns(self):
        """user namespace 内（root，chmod 不约束）升级 ro bind mount，同一契约成立。"""
        with tempfile.TemporaryDirectory(prefix="wf-deny-ns-") as root:
            target = os.path.join(root, "locked")
            os.makedirs(target)
            original_mode = os.stat(target).st_mode & 0o7777
            existing = os.path.join(target, "r68d.md")
            with open(existing, "w", encoding="utf-8") as handle:
                handle.write("# 占位\n")
            code = (
                "import importlib.util, os, sys\n"
                "spec = importlib.util.spec_from_file_location('wfdrive', sys.argv[1])\n"
                "wfdrive = importlib.util.module_from_spec(spec)\n"
                "spec.loader.exec_module(wfdrive)\n"
                "target = sys.argv[2]\n"
                "assert os.geteuid() == 0, 'userns 内应为 root'\n"
                "token = wfdrive.deny_writes(target)\n"
                "try:\n"
                "    for probe in ('new.md',):\n"
                "        try:\n"
                "            open(os.path.join(target, probe), 'w')\n"
                "            raise SystemExit(f'create 探针未被拒')\n"
                "        except OSError:\n"
                "            pass\n"
                "    try:\n"
                "        open(os.path.join(target, 'r68d.md'), 'r+b')\n"
                "        raise SystemExit('modify 探针未被拒')\n"
                "    except OSError:\n"
                "        pass\n"
                "    try:\n"
                "        os.unlink(os.path.join(target, 'r68d.md'))\n"
                "        raise SystemExit('unlink 探针未被拒')\n"
                "    except OSError:\n"
                "        pass\n"
                "    assert token['mounted'], 'root 场景应升级 ro bind mount'\n"
                "finally:\n"
                "    wfdrive.allow_writes(token)\n"
                "print('userns-contract-ok')\n"
            )
            proc = subprocess.run(["unshare", "-Urm", sys.executable, "-c", code,
                                   str(FULL / "wfdrive.py"), target],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("userns-contract-ok", proc.stdout)
            # ns 消亡后宿主侧无残留：模式恢复为建立时记录的原值、目录可写、无哨兵、内容未变
            self.assertEqual(os.stat(target).st_mode & 0o7777, original_mode)
            with open(existing, encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "# 占位\n")
            self.assertEqual(sorted(os.listdir(target)), ["r68d.md"])


if __name__ == "__main__":
    unittest.main()
