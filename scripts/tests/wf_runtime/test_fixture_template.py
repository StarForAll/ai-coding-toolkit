"""夹具模板副本的空态契约（`full/template_check.py` + 真实复制）。

run-scoped 模板把「夹具 + 初始化任务」构建一次、逐套件 `cp -a`。复制**不会**搬走记录里的
绝对路径和外部暂存目录，所以：
- 快测试：校验器必须能识别「缺 wf.py / 缺安装记录 / 记录残留模板路径 / 版本不符」；
- 慢测试（`WF_SLOW_TESTS=1`）：真实构建模板 → 复制到**另一个目录** → 用**新进程**、
  **空 TMPDIR** 跑一次 CLI，必须 `WF_OK`（换目录/新进程/空 tempdir 三件套）。
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
FULL = Path(__file__).resolve().parents[0] / "full"
SLOW = os.environ.get("WF_SLOW_TESTS") == "1"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = _load("wf_template_check", FULL / "template_check.py")
wfdrive = _load("wf_runner_wfdrive", FULL / "wfdrive.py")


def make_project(root, version="0.1.0", ref="refs/tags/wf-v0.1.0", leak=None):
    os.makedirs(os.path.join(root, ".wf", "bin"), exist_ok=True)
    with open(os.path.join(root, ".wf", "bin", "wf.py"), "w", encoding="utf-8") as handle:
        handle.write("print('ok')\n")
    os.makedirs(os.path.join(root, ".wf", "install"), exist_ok=True)
    with open(os.path.join(root, ".wf", "install", "installation.json"), "w", encoding="utf-8") as handle:
        json.dump({"version": version, "release_ref": ref}, handle)
    if leak:
        with open(os.path.join(root, ".wf", "state.json"), "w", encoding="utf-8") as handle:
            json.dump({"path": leak}, handle)
    return root


class TemplateCheckTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="wf-template-check-")
        self.addCleanup(lambda: shutil.rmtree(self.dir, ignore_errors=True))

    def test_clean_copy_passes(self):
        root = make_project(os.path.join(self.dir, "proj"))
        self.assertEqual(checker.check(root), [])

    def test_missing_cli_is_reported(self):
        root = make_project(os.path.join(self.dir, "proj"))
        os.unlink(os.path.join(root, ".wf", "bin", "wf.py"))
        problems = checker.check(root)
        self.assertTrue(any("wf.py" in item for item in problems), problems)

    def test_missing_installation_is_reported(self):
        root = make_project(os.path.join(self.dir, "proj"))
        os.unlink(os.path.join(root, ".wf", "install", "installation.json"))
        problems = checker.check(root)
        self.assertTrue(any("installation.json" in item for item in problems), problems)

    def test_template_path_leak_is_reported(self):
        template = os.path.join(self.dir, "template")
        root = make_project(os.path.join(self.dir, "proj"), leak=template)
        self.assertEqual(checker.check(root), [])
        problems = checker.check(root, leak_from=template)
        self.assertTrue(any("残留模板路径" in item for item in problems), problems)

    def test_version_and_ref_mismatch_are_reported(self):
        root = make_project(os.path.join(self.dir, "proj"), version="0.1.0")
        problems = checker.check(root, version="0.1.2", ref="refs/tags/wf-v0.1.2")
        self.assertTrue(any("version" in item for item in problems), problems)
        self.assertTrue(any("release_ref" in item for item in problems), problems)

    def test_dev_placeholder_is_rejected_when_version_expected(self):
        root = make_project(os.path.join(self.dir, "proj"), version="0.0.0-dev")
        problems = checker.check(root, version="0.0.0-dev")
        self.assertTrue(any("0.0.0-dev" in item for item in problems), problems)

    def test_repoint_rewrites_template_path_in_records(self):
        template = os.path.join(self.dir, "template")
        root = make_project(os.path.join(self.dir, "proj"), leak=template)
        touched = checker.repoint(root, template)
        self.assertTrue(touched, "应当改写了记录里的模板路径")
        self.assertEqual(checker.check(root, leak_from=template), [])
        with open(os.path.join(root, ".wf", "state.json"), encoding="utf-8") as handle:
            data = json.load(handle)
        self.assertTrue(data["path"].startswith(os.path.realpath(root)),
                        "记录必须指向复制后的项目，而不是模板")

    def test_repoint_only_touches_prefixed_records(self):
        template = os.path.join(self.dir, "template")
        root = make_project(os.path.join(self.dir, "proj"))
        with open(os.path.join(root, ".wf", "other.json"), "w", encoding="utf-8") as handle:
            json.dump({"unrelated": "/keep/me"}, handle)
        self.assertEqual(checker.repoint(root, template), [])
        with open(os.path.join(root, ".wf", "other.json"), encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)["unrelated"], "/keep/me")

    def test_missing_project_directory_is_reported(self):
        problems = checker.check(os.path.join(self.dir, "nope"))
        self.assertTrue(problems)


@unittest.skipUnless(SLOW, "WF_SLOW_TESTS=1 才构建真实模板（fixture + init，约 2s）")
class TemplateReuseIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="wf-template-real-")
        self.addCleanup(lambda: shutil.rmtree(self.dir, ignore_errors=True))
        self.template = os.path.join(self.dir, "template")
        self.copy = os.path.join(self.dir, "copy")

    def _build(self):
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        fixture = subprocess.run(["bash", str(FULL / "wf_fixture.sh"), self.template],
                                 capture_output=True, text=True, env=env)
        self.assertEqual(fixture.returncode, 0, fixture.stderr[-800:])
        init = subprocess.run([sys.executable, str(FULL / "f1_init.py")], capture_output=True, text=True,
                              env={**env, "WF_FIX": self.template})
        self.assertEqual(init.returncode, 0, (init.stdout + init.stderr)[-800:])

    def test_copy_to_new_path_in_new_process_with_empty_tmpdir(self):
        self._build()
        shutil.copytree(self.template, self.copy, symlinks=True)
        # 复制后先迁移记录里的绝对路径（安装时登记的技能根），再做空态校验
        touched = checker.repoint(self.copy, self.template)
        self.assertTrue(touched, "复制后必须重指记录里的模板路径")
        problems = checker.check(self.copy, leak_from=self.template)
        self.assertEqual(problems, [], "复制后不得残留模板路径")
        empty_tmp = os.path.join(self.dir, "empty-tmp")
        os.makedirs(empty_tmp)
        envelope = json.dumps({"session": {"provider": "host",
                                           "identity": {"host_id": "dsh", "session_id": "sess-T"},
                                           "instance_id": None,
                                           "activation": {"enabled": True, "start_source": "human:test",
                                                          "enabled_at": "2026-11-13T00:00:00Z"}},
                               "inputs": {}})
        result = subprocess.run([wfdrive.PYTHON, os.path.join(self.copy, ".wf", "bin", "wf.py"),
                                 "help", "--json"], input=envelope, capture_output=True, text=True,
                                cwd=self.copy, env={**os.environ, "TMPDIR": empty_tmp})
        self.assertIn("WF_OK", result.stdout, (result.stdout + result.stderr)[-800:])


if __name__ == "__main__":
    unittest.main()
