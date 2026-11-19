"""R3：托管套件的临时材料按命令归属，源码里不得残留绝对 `/tmp` 材料路径。

两层验收：

- 静态：`units.json` 的全部可计划脚本与登记 fixture/init helper 不得含未登记的 `/tmp/`
  字面量；登记项必须写明原因与覆盖它的测试。
- 动态：`execution.py --local-tmp-root` 为每个命令建唯一私有根、把目标的 TMPDIR/TMP/TEMP
  指向它，并在 supervision 清理确认后回收；创建失败时收据明确记“未创建”，不伪报保留路径。
"""
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
FULL = HERE / "full"
PLANNABLE = ("suite", "candidate", "flow", "extra")
# fixture/init 建立入口与来源解析代码：同样属于“按次创建材料”的白名单扫描面。
HELPERS = ("wf_fixture.sh", "f2_setup.sh", "f1_init.py")
# 精确路径契约的登记（空 = 当前没有需要保留的绝对 /tmp 材料路径）。
# 每项：{"path": <相对 full/ 的路径>, "literal": <字面量>, "reason": <为什么必须保留>,
#        "test": <覆盖该契约的测试名>}
REGISTERED_LITERALS = ()

LITERAL = re.compile(r"""["'](/tmp/[^"'\n]*)""")


def _load_execution():
    spec = importlib.util.spec_from_file_location("wf_execution_temp_test",
                                                  FULL / "execution.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _targets():
    units = json.loads((FULL / "units.json").read_text(encoding="utf-8"))["units"]
    paths = set()
    for entry in units:
        if entry.get("kind") in PLANNABLE:
            paths.add(FULL / entry.get("script", entry["name"] + ".py"))
    for name in HELPERS:
        paths.add(FULL / name)
    return sorted(paths)


def scan(path):
    """返回文件里的绝对 /tmp 字面量（按出现顺序）。"""
    return LITERAL.findall(path.read_text(encoding="utf-8"))


class StaticGuardTest(unittest.TestCase):
    def test_no_unregistered_absolute_tmp_material_paths(self):
        registered = {(FULL / item["path"], item["literal"]): item
                      for item in REGISTERED_LITERALS}
        for item in REGISTERED_LITERALS:
            self.assertTrue(item.get("reason") and item.get("test"),
                            f"登记项缺少原因/测试：{item}")
        problems = []
        for path in _targets():
            for literal in scan(path):
                if (path, literal) not in registered:
                    problems.append(f"{path.relative_to(FULL)}: {literal}")
        self.assertEqual(problems, [], "未分类的绝对 /tmp 路径（迁到 wfdrive.temp()/legacy_root() "
                                       "或登记为精确契约）：\n" + "\n".join(problems))

    def test_guard_detects_a_planted_literal(self):
        with tempfile.TemporaryDirectory(prefix="wf-temp-guard-") as root:
            path = Path(root) / "suite.py"
            path.write_text('path = "/tmp/wf-planted/file.json"\n', encoding="utf-8")
            self.assertEqual(scan(path), ["/tmp/wf-planted/file.json"])

    def test_plannable_scripts_use_the_unit_temp_helpers(self):
        """迁移后的材料路径必须经 wfdrive.temp()/legacy_root()（不直接拼宿主目录）。"""
        markers = ("wfdrive.temp(", "wfdrive.legacy_root(", "tempfile.", "TMPDIR")
        offenders = []
        for path in _targets():
            text = path.read_text(encoding="utf-8")
            if not any(marker in text for marker in markers):
                offenders.append(str(path.relative_to(FULL)))
        self.assertEqual(offenders, [],
                         "这些可计划脚本仍未见按次材料 helper：" + " ".join(offenders))


class HostTempBridgeTest(unittest.TestCase):
    """命令私有 TMPDIR 之外的宿主根必须是有界、可信的临时目录。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-host-tmp-")
        self.addCleanup(self.tmp.cleanup)
        self.host = Path(self.tmp.name)
        spec = importlib.util.spec_from_file_location("wf_fixture_scope_temp_guard",
                                                      FULL / "fixture_scope.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.scope = module

    def test_recorded_host_root_is_bounded(self):
        for value in ("/", str(FULL.parents[3]), str(self.host / "missing")):
            with self.subTest(value=value):
                with mock.patch.dict(os.environ, {"WF_HOST_TMPDIR": value}):
                    with self.assertRaises(self.scope.FixtureError):
                        self.scope._temporary_roots()

    def test_valid_host_root_bridges_private_tmpdir(self):
        private = self.host / "private"
        private.mkdir()
        fixture = self.host / "wf-fixtures" / "run-1"
        fixture.mkdir(parents=True)
        with mock.patch.dict(os.environ, {"TMPDIR": str(private)}):
            with mock.patch.dict(os.environ, {"WF_HOST_TMPDIR": str(self.host)}):
                tempfile.tempdir = None
                try:
                    self.assertIn(self.host.resolve(), self.scope._temporary_roots())
                    self.scope.validate(fixture)
                finally:
                    tempfile.tempdir = None

class ExecutorTempRootTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-temp-root-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.log = self.root / "command.log"
        self.parent = self.root / "logs"
        self.parent.mkdir()

    def test_private_tmpdir_is_created_named_and_reclaimed(self):
        module = _load_execution()
        result = module.run(
            [sys.executable, "-c",
             "import os; print(os.environ['TMPDIR']); print(os.environ['TMP']);"
             " print(os.environ['TEMP']); print(os.getcwd())"],
            self.log, timeout=10, local_tmp_root=str(self.parent))
        self.assertEqual(result["status"], "passed", result.get("reason"))
        lines = self.log.read_text(encoding="utf-8").splitlines()
        created = result["local_tmp_root"]
        self.assertEqual(Path(created), (self.parent / result["command_id"]).resolve())
        self.assertEqual(lines[0], created, "目标的 TMPDIR 必须是本命令私有根")
        self.assertEqual(lines[1], created)
        self.assertEqual(lines[2], created)
        self.assertNotEqual(created, str(self.root), "私有根不能等于父目录")
        self.assertFalse(Path(created).exists(), "命令收口后私有 TMPDIR 必须回收")
        receipt = json.loads(Path(result["evidence_path"]).read_text(encoding="utf-8"))
        self.assertTrue(receipt["local_tmp_created"])
        self.assertEqual(receipt["local_cleanup"], "removed")
        self.assertEqual(receipt["retained_paths"], [])

    def test_creation_failure_is_recorded_without_a_fake_retained_path(self):
        module = _load_execution()
        missing = self.root / "missing-parent"
        result = module.run([sys.executable, "-c", "print('never')"], self.log,
                            timeout=5, local_tmp_root=str(missing))
        self.assertEqual(result["status"], "failed")
        self.assertIn("local tmp root preparation failed", result["reason"])
        receipt = json.loads(Path(result["evidence_path"]).read_text(encoding="utf-8"))
        self.assertFalse(receipt["local_tmp_created"])
        self.assertEqual(receipt["local_cleanup"], "failed")
        self.assertEqual(receipt["retained_paths"], [],
                         "目录未创建时不得伪报 retained path")
        self.assertFalse(missing.exists())

    def test_parallel_slots_never_share_one_local_tmp_root(self):
        module = _load_execution()
        roots = []
        for index in range(2):
            log = self.root / f"command-{index}.log"
            result = module.run(
                [sys.executable, "-c",
                 "import os; print(os.environ['TMPDIR'])"],
                log, timeout=10, local_tmp_root=str(self.parent))
            self.assertEqual(result["status"], "passed", result.get("reason"))
            roots.append(log.read_text(encoding="utf-8").strip().splitlines()[-1])
        self.assertEqual(len(set(roots)), 2, "同一父目录下的不同命令必须各有唯一根")
        self.assertTrue(all(not Path(item).exists() for item in roots),
                        "两个命令的私有根最终都必须回收")
        self.assertEqual(sorted(self.parent.iterdir()), [])

    def test_run_one_passes_one_local_tmp_root_per_supervised_command(self):
        text = (FULL / "run_one.sh").read_text(encoding="utf-8")
        self.assertIn('TMP_PARENT="$RESULTS_DIR/logs"', text)
        self.assertEqual(text.count("--local-tmp-root"), 4,
                         "install/fixture/init/test 四个受监督命令都要拿到私有 TMPDIR")


if __name__ == "__main__":
    unittest.main()
