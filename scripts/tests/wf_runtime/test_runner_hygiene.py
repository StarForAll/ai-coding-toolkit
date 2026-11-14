"""运行器防回归闸门（design D5）：G1 /tmp 导入注入、G2 pyc 策略、G3 .gitignore、
G8 假树清单完整性、G9 假树缺根容错。

这些测试只读源码与真实 `run_all.sh` 的静态引用，不执行运行器；G8 的扫描口径与
design 写死的一致：只认双引号形态 `"$HERE/<相对路径>"`，跳过含 `$`（变量展开）与
含 `..`（纯路径运算）的引用。
"""

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FULL = Path(__file__).resolve().parent / "full"
RUN_ALL = FULL / "run_all.sh"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


plan = _load("wf_runner_plan_hygiene", FULL / "plan.py")
hygiene = _load("wf_source_hygiene", FULL / "source_hygiene.py")


def static_here_refs(text):
    for match in re.finditer(r'"\$HERE/([^"]+)"', text):
        reference = match.group(1)
        if "$" in reference or ".." in reference:
            continue
        yield os.path.normpath(reference)


class ImportHygieneTest(unittest.TestCase):
    """G1：测试源码禁止把 /tmp 提到 sys.path 最高优先级。"""

    # 用拼接构造 needle：本文件自身不能包含该字面量（否则 G1 会命中自己）。
    NEEDLE = "sys.path.insert(0, " + '"/tmp")'

    def test_no_tmp_sys_path_injection(self):
        hits = []
        for path in sorted((REPO / "scripts" / "tests").rglob("*.py")):
            text = path.read_text(encoding="utf-8", errors="replace")
            if self.NEEDLE in text:
                hits.append(str(path.relative_to(REPO)))
        self.assertEqual(hits, [], "/tmp 导入注入会让宿主 /tmp 劫持 harness 模块")


class BytecodePolicyTest(unittest.TestCase):
    """G2：运行器必须统一下发 PYTHONPYCACHEPREFIX，不得再导出 PYTHONDONTWRITEBYTECODE。"""

    def test_pycache_prefix_is_exported(self):
        text = RUN_ALL.read_text(encoding="utf-8")
        self.assertIn("PYTHONPYCACHEPREFIX", text)

    def test_bytecode_writing_is_not_disabled(self):
        for relative in ("run_all.sh", "run_one.sh", "repro/run.sh"):
            text = (FULL / relative).read_text(encoding="utf-8")
            self.assertNotIn("export PYTHONDONTWRITEBYTECODE", text,
                             f"{relative} 不得再关闭字节码写入（策略已改为重定向到结果目录）")


class GitignoreTest(unittest.TestCase):
    """G3：仓库级 .gitignore 覆盖 pyc（不依赖本机全局 excludesFile）。"""

    def test_repository_gitignore_covers_pyc(self):
        lines = (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
        stripped = [line.strip() for line in lines]
        self.assertIn("__pycache__/", stripped)
        self.assertIn("*.pyc", stripped)


class FakeTreeManifestTest(unittest.TestCase):
    """G8：run_all.sh 的静态 `"$HERE/<路径>"` 引用必须全部被三桶清单或注册表 script 覆盖。"""

    def test_every_static_helper_is_classified(self):
        refs = set(static_here_refs(RUN_ALL.read_text(encoding="utf-8")))
        allowed = set(plan.FAKE_TREE_COPY) | set(plan.FAKE_TREE_STUB) | set(plan.FAKE_TREE_SPECIAL)
        registry = plan.load_units()
        allowed_scripts = {entry.get("script", entry["name"] + ".py")
                           for entry in registry["units"] if entry["kind"] in plan.PLANNABLE_KINDS}
        allowed |= allowed_scripts
        uncovered = sorted(refs - allowed)
        self.assertEqual(uncovered, [], "新增 helper 必须归入 plan.py 的假树三桶（或成为注册表 script）")
        self.assertGreaterEqual(len(refs), 9, f"静态引用数量异常偏少：{sorted(refs)}")

    def test_bucket_entries_exist(self):
        missing = [name for name in
                   plan.FAKE_TREE_COPY + plan.FAKE_TREE_STUB + plan.FAKE_TREE_SPECIAL
                   if not (FULL / name).exists()]
        self.assertEqual(missing, [], "三桶清单存在陈旧条目")

    def test_stub_bucket_is_never_copied(self):
        # 假树语义要求：STUB 条目必须由 r67 桩化，不能出现在 COPY 桶里。
        self.assertEqual(set(plan.FAKE_TREE_STUB) & set(plan.FAKE_TREE_COPY), set())
        self.assertEqual(set(plan.FAKE_TREE_STUB) & set(plan.FAKE_TREE_SPECIAL), set())
        self.assertEqual(set(plan.FAKE_TREE_SPECIAL), {"run_all.sh"})


class MissingRootTest(unittest.TestCase):
    """G9：扫描根不存在时按空集合处理并标 absent（r67 假树没有 docs/workflows/wf）。"""

    def test_snapshot_and_check_tolerate_absent_roots(self):
        root = tempfile.mkdtemp(prefix="wf-hygiene-absent-")
        self.addCleanup(lambda: __import__("shutil").rmtree(root, ignore_errors=True))
        out = os.path.join(tempfile.mkdtemp(prefix="wf-hygiene-snap-"), "snap.json")
        self.addCleanup(lambda: __import__("shutil").rmtree(os.path.dirname(out), ignore_errors=True))
        self.assertEqual(hygiene.snapshot(root, out), 0)
        snapshot = json.loads(Path(out).read_text())
        self.assertEqual(len(snapshot["absent"]), 2)
        self.assertEqual(hygiene.check_delta(root, out), 0)

    def test_cli_output_mentions_absent(self):
        root = tempfile.mkdtemp(prefix="wf-hygiene-cli-")
        self.addCleanup(lambda: __import__("shutil").rmtree(root, ignore_errors=True))
        missing = os.path.join(root, "missing-root")
        result = subprocess.run([sys.executable, str(FULL / "source_hygiene.py"), "check", "--strict", missing],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("HYGIENE-ABSENT", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
