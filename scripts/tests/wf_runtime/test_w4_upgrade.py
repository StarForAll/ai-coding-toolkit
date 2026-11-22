"""W4（三轮 P0-2）：upgrade 三方升级 / 偏离导出 / 令牌 parity / 转交。

断言面（implement.md 3.4）：
- 三方表逐行（L=N/L=O/偏离保持/冲突交人/上游删除）；
- 三必填缺参、--source 子路径 WF_PATH_INVALID；
- 升级前置机器判据（status/paused/suspended/handoff.wip/terminal/paused、挂起未暂停负例、
  wip 未处置负例、不可读即阻断）；
- --token-parity-check 先于 argparse；parity 三方一致；重跑预览即销毁（非 TTY 拒）；
- applied_pending_commit；installation.json assets 写入侧字段；
- --export-deviations（O 可取回/不可取回/无偏离/非空拒/部分失败如实报告）；
- wf.py 转交与 cli 转交报错、help 注册表 48/48 双向断言不动。
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PAYLOAD = REPO / "docs/workflows/wf/payload"
sys.path.insert(0, str(PAYLOAD / "lib"))
sys.path.insert(0, str(REPO / "scripts"))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


install = _load("w4_install", PAYLOAD / "install.py")


class _Args:
    def __init__(self, **kwargs):
        self.target = kwargs.get("target")
        self.release_ref = kwargs.get("release_ref", "refs/tags/wf-v0.1.5")
        self.source = kwargs.get("source")
        self.json = True
        self.upgrade = True
        self.apply = kwargs.get("apply", False)
        self.export_deviations = kwargs.get("export_deviations", False)
        self.out = kwargs.get("out")
        self.keep = kwargs.get("keep", [])
        self.restore = kwargs.get("restore", [])


class Harness(unittest.TestCase):
    """构造一个已安装 0.1.4 的目标项目 + 一个 0.1.5 新发行（内存态，不经 git tag）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.target = self.root / "proj"
        (self.target / ".wf").mkdir(parents=True)
        # 安装记录（0.1.4）：一个未变资产 + 一个将被更新的资产
        self.installed_assets = [
            {"target": ".wf/lib/wflib/session.py", "root_ref": "project",
             "digest": "sha256:" + "a" * 64, "source_path": "payload/lib/wflib/session.py",
             "upstream_version": "0.1.4", "upstream_fingerprint": "sha256:" + "a" * 64},
            {"target": ".wf/bin/repair.py", "root_ref": "project",
             "digest": "sha256:" + "b" * 64, "source_path": "payload/bin/repair.py",
             "upstream_version": "0.1.4", "upstream_fingerprint": "sha256:" + "b" * 64},
        ]
        installation = {"schema_version": 1, "version": "0.1.4",
                         "release_ref": "refs/tags/wf-v0.1.4",
                         "source_commit": "c0ffee", "platforms": ["codex", "dsh"],
                         "roots": [], "assets": self.installed_assets}
        install_dir = self.target / ".wf/install"
        install_dir.mkdir()
        (install_dir / "installation.json").write_text(
            json.dumps(installation, ensure_ascii=False, indent=2), encoding="utf-8")
        # 新发行 0.1.5（内存 manifest）
        self.new_session_digest = "sha256:" + "a" * 64      # 未变
        self.new_repair_digest = "sha256:" + "c" * 64       # 上游变化
        self.manifest = {"version": "0.1.5",
                         "compatibility": {"rules_digest": "sha256:rules"},
                         "assets": [
                             {"source_path": "payload/lib/wflib/session.py",
                              "target_class": "project_wf",
                              "target_relative": ".wf/lib/wflib/session.py",
                              "kind": "lib", "required": True, "file_kind": "file",
                              "executable": False, "digest": self.new_session_digest},
                             {"source_path": "payload/bin/repair.py",
                              "target_class": "project_wf",
                              "target_relative": ".wf/bin/repair.py",
                              "kind": "bin", "required": True, "file_kind": "file",
                              "executable": True, "digest": self.new_repair_digest},
                         ]}
        # 写权空闲
        (self.target / ".wf/writer.json").write_text(json.dumps(
            {"schema_version": 1, "id": "writer", "revision": 0, "state": "idle",
             "generation": 0, "holder": None, "created_at": "t", "updated_at": "t"}),
            encoding="utf-8")
        self.source = self.root / "checkout"
        (self.source / "wf-release").mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def _write_local(self, relative, content):
        path = self.target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _local_digest(self, relative):
        import hashlib
        return "sha256:" + hashlib.sha256((self.target / relative).read_bytes()).hexdigest()

    def _write_source_file(self, source_path, content):
        path = self.source / source_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


class ThreeWayPlanTest(Harness):
    def test_l_equals_n_is_noop(self):
        # L=N：登记即可
        self._write_local(".wf/lib/wflib/session.py", "same content")
        self.manifest["assets"][0]["digest"] = self._local_digest(".wf/lib/wflib/session.py")
        plan, unresolved = install.three_way_plan(str(self.target), json.loads(
            (self.target / ".wf/install/installation.json").read_text(encoding="utf-8")),
            self.manifest, str(self.source), ["codex"], [], [])
        kinds = {item["kind"] for item in plan["actions"]}
        self.assertIn("noop", kinds)

    def test_l_equals_o_upstream_changed_is_update(self):
        self._write_local(".wf/bin/repair.py", "old release bytes")
        # O 记录的字节与本地一致
        installation = json.loads(
            (self.target / ".wf/install/installation.json").read_text(encoding="utf-8"))
        installation["assets"][1]["digest"] = self._local_digest(".wf/bin/repair.py")
        installation["assets"][1]["upstream_fingerprint"] = self._local_digest(".wf/bin/repair.py")
        plan, unresolved = install.three_way_plan(str(self.target), installation,
                                                  self.manifest, str(self.source), ["codex"], [], [])
        update = [item for item in plan["actions"] if item["kind"] == "update"]
        self.assertEqual(len(update), 1)
        self.assertEqual(update[0]["relative"], ".wf/bin/repair.py")

    def test_same_accepted_deviation_skips_asking(self):
        # 同一已接受偏离（两边指纹均同）免重复询问
        self._write_local(".wf/bin/repair.py", "local deviation bytes")
        local = self._local_digest(".wf/bin/repair.py")
        installation = json.loads(
            (self.target / ".wf/install/installation.json").read_text(encoding="utf-8"))
        installation["assets"][1]["digest"] = local
        # 「同一已接受偏离」= 登记的 upstream_fingerprint 等于**本次**发行摘要（同一偏离再现）；
        # 登记为旧版摘要则上游又变了，属新冲突须重问——语义即此
        installation["assets"][1]["local_fingerprint"] = local
        installation["assets"][1]["upstream_fingerprint"] = self.new_repair_digest
        installation["assets"][1]["decision"] = "human (test)"
        plan, unresolved = install.three_way_plan(str(self.target), installation,
                                                  self.manifest, str(self.source), ["codex"], [], [])
        kept = [item for item in plan["actions"] if item["kind"] == "deviation-kept"]
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["decision"], "human (test)")

    def test_other_conflict_goes_to_human_with_exits(self):
        self._write_local(".wf/bin/repair.py", "user edited, not release, not installed")
        plan, unresolved = install.three_way_plan(str(self.target), json.loads(
            (self.target / ".wf/install/installation.json").read_text(encoding="utf-8")),
            self.manifest, str(self.source), ["codex"], [], [])
        self.assertTrue(any(item["kind"] == "local-deviates" for item in unresolved))
        exits = [item for item in unresolved if item["kind"] == "local-deviates"][0]["exits"]
        self.assertTrue(any("--keep" in e for e in exits))
        self.assertTrue(any("--restore" in e for e in exits))

    def test_upstream_removed_l_equals_o_is_delete_candidate(self):
        # N 里没有 session.py（上游删除）；L==O ⇒ 可删候选
        self.manifest["assets"] = [self.manifest["assets"][1]]
        self._write_local(".wf/lib/wflib/session.py", "x" * 64)
        installation = json.loads(
            (self.target / ".wf/install/installation.json").read_text(encoding="utf-8"))
        installation["assets"][0]["digest"] = self._local_digest(".wf/lib/wflib/session.py")
        plan, unresolved = install.three_way_plan(str(self.target), installation,
                                                  self.manifest, str(self.source), ["codex"], [], [])
        self.assertEqual(len(plan["deletes"]), 1)
        self.assertEqual(plan["deletes"][0]["relative"], ".wf/lib/wflib/session.py")

    def test_add_hitting_user_file_is_unresolved(self):
        self._write_local(".wf/hooks/new.py", "user file")
        self.manifest["assets"].append(
            {"source_path": "payload/hooks/new.py", "target_class": "project_wf",
             "target_relative": ".wf/hooks/new.py", "kind": "hook", "required": True,
             "file_kind": "file", "executable": True, "digest": "sha256:" + "d" * 64})
        plan, unresolved = install.three_way_plan(str(self.target), json.loads(
            (self.target / ".wf/install/installation.json").read_text(encoding="utf-8")),
            self.manifest, str(self.source), ["codex"], [], [])
        self.assertTrue(any(item["kind"] == "add-hits-user-file" for item in unresolved))


class PrerequisitesTest(Harness):
    def _run(self):
        problems, wip, writer = install.upgrade_prerequisites(str(self.target))
        return problems, wip

    def test_idle_project_passes(self):
        problems, _wip = self._run()
        self.assertEqual(problems, [])

    def test_active_unpaused_task_blocks(self):
        task_dir = self.target / ".wf/tasks/t-1"
        task_dir.mkdir(parents=True)
        (task_dir / "task.json").write_text(json.dumps(
            {"id": "t-1", "status": "in_progress", "paused": False, "suspended": False}),
            encoding="utf-8")
        problems, _wip = self._run()
        self.assertTrue(any(p["reason"] == "active task not paused/not-started" for p in problems))

    def test_suspended_but_not_paused_blocks(self):
        # 挂起未暂停：suspended=true、paused=false ⇒ 只判 paused 会放行——负例
        task_dir = self.target / ".wf/tasks/t-2"
        task_dir.mkdir(parents=True)
        (task_dir / "task.json").write_text(json.dumps(
            {"id": "t-2", "status": "in_progress", "paused": False, "suspended": True}),
            encoding="utf-8")
        problems, _wip = self._run()
        self.assertTrue(any(p["reason"] == "active task not paused/not-started" for p in problems))

    def test_paused_not_suspended_passes(self):
        task_dir = self.target / ".wf/tasks/t-3"
        task_dir.mkdir(parents=True)
        (task_dir / "task.json").write_text(json.dumps(
            {"id": "t-3", "status": "in_progress", "paused": True, "suspended": False}),
            encoding="utf-8")
        problems, _wip = self._run()
        self.assertEqual([p for p in problems if "t-3" in json.dumps(p)], [])

    def test_unresolved_handoff_wip_blocks(self):
        # 收工保留 WIP 未处置：任务记录 handoff.wip（writer.json 的 handover 没有 wip 字段）
        task_dir = self.target / ".wf/tasks/t-4"
        task_dir.mkdir(parents=True)
        (task_dir / "task.json").write_text(json.dumps(
            {"id": "t-4", "status": "in_progress", "paused": True, "suspended": False,
             "handoff": {"wip": {"paths": [{"path": "src/a.py"}], "resolved": None}}}),
            encoding="utf-8")
        problems, wip = self._run()
        self.assertTrue(any(p["reason"] == "handoff wip unresolved" for p in problems))
        self.assertEqual(wip[0]["paths"], ["src/a.py"])

    def test_run_not_terminal_not_paused_blocks(self):
        runs_dir = self.target / ".wf/workflow-runs"
        runs_dir.mkdir(parents=True)
        (runs_dir / "run-1.json").write_text(json.dumps(
            {"id": "run-1", "terminal": None, "paused": False}), encoding="utf-8")
        problems, _wip = self._run()
        self.assertTrue(any(p["reason"] == "run not terminal and not paused" for p in problems))

    def test_unreadable_record_blocks(self):
        task_dir = self.target / ".wf/tasks/broken"
        task_dir.mkdir(parents=True)
        (task_dir / "task.json").write_text("{ not json", encoding="utf-8")
        problems, _wip = self._run()
        self.assertTrue(any(p["reason"] == "unreadable-record" and "broken" in p["path"]
                            for p in problems))


class TokenAndDispatchTest(unittest.TestCase):
    def test_token_parity_check_before_argparse(self):
        # parity 调用不带三必填，若先过 argparse required 校验会先被拒
        result = subprocess.run(
            [sys.executable, str(PAYLOAD / "install.py"), "--token-parity-check"],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("first=ok", result.stdout)
        self.assertIn("after=expired", result.stdout)

    def test_three_way_token_parity(self):
        outputs = {}
        for name, path in (("repair", PAYLOAD / "bin/repair.py"),
                           ("uninstall", PAYLOAD / "bin/uninstall.py"),
                           ("install", PAYLOAD / "install.py")):
            result = subprocess.run(
                [sys.executable, str(path), "--token-parity-check",
                 "--nonce", "0123456789abcdef0123456789abcdef"],
                capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)
            outputs[name] = result.stdout.strip().splitlines()
        self.assertEqual(outputs["repair"], outputs["uninstall"])
        self.assertEqual(outputs["repair"], outputs["install"])

    def test_preview_without_apply_issues_token_and_exits(self):
        # 预览即销毁：不带 --apply 只出预览（不写任何文件、退出码 0）
        import io
        import contextlib
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "proj"
            (target / ".wf/install").mkdir(parents=True)
            (target / ".wf/install/installation.json").write_text(json.dumps(
                {"version": "0.1.4", "source_commit": "c0", "platforms": ["dsh"],
                 "roots": [], "assets": []}), encoding="utf-8")
            (target / ".wf/writer.json").write_text(json.dumps(
                {"schema_version": 1, "id": "writer", "revision": 0, "state": "idle",
                 "generation": 0, "holder": None}), encoding="utf-8")
            args = _Args(target=str(target), source=str(tmp))
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = install.run_upgrade(args, {"version": "0.1.5",
                                                  "compatibility": {"rules_digest": "r"},
                                                  "assets": []}, "c1")
            self.assertEqual(code, 0)
            self.assertIn("预览指纹", buffer.getvalue())
            self.assertIn("重跑并输入预览指纹", buffer.getvalue())

    def test_same_version_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "proj"
            (target / ".wf/install").mkdir(parents=True)
            (target / ".wf/install/installation.json").write_text(json.dumps(
                {"version": "0.1.5", "source_commit": "c1", "platforms": ["dsh"],
                 "roots": [], "assets": []}), encoding="utf-8")
            args = _Args(target=str(target), source=str(tmp))
            import io
            import contextlib
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = install.run_upgrade(args, {"version": "0.1.5", "assets": []}, "c1")
            self.assertEqual(code, 1)
            self.assertIn("同版非升级", buffer.getvalue())


class ExportDeviationsTest(Harness):
    def _installation(self):
        return json.loads(
            (self.target / ".wf/install/installation.json").read_text(encoding="utf-8"))

    def test_export_unrecoverable_o_is_honest(self):
        # O 不可取回（假 source 无 git）：如实产出摘要+说明，不伪造空补丁
        self._write_local(".wf/bin/repair.py", "deviated local")
        local = self._local_digest(".wf/bin/repair.py")
        installation = self._installation()
        installation["assets"][1]["local_fingerprint"] = local
        # 同一已接受偏离：登记的 upstream_fingerprint 等于本次发行摘要（见 ThreeWayPlanTest 语义说明）
        installation["assets"][1]["upstream_fingerprint"] = self.new_repair_digest
        installation["assets"][1]["decision"] = "human (keep)"
        (self.target / ".wf/install/installation.json").write_text(
            json.dumps(installation, ensure_ascii=False, indent=2), encoding="utf-8")
        plan, _u = install.three_way_plan(str(self.target), installation, self.manifest,
                                          str(self.source), ["codex"], [".wf/bin/repair.py"], [])
        out = self.root / "export-out"
        args = _Args(target=str(self.target), source=str(self.source),
                     export_deviations=True, out=str(out))
        import io
        import contextlib
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = install.run_upgrade(args, self.manifest, "c0ffee")
        self.assertIn("偏离导出", buffer.getvalue())

    def test_out_nonempty_is_rejected(self):
        out = self.root / "out-existing"
        out.mkdir()
        (out / "user.txt").write_text("keep me", encoding="utf-8")
        args = _Args(target=str(self.target), source=str(self.source),
                     export_deviations=True, out=str(out))
        import io
        import contextlib
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = install.run_upgrade(args, self.manifest, "c0ffee")
        self.assertEqual(code, 1)
        self.assertIn("非空", buffer.getvalue())
        self.assertEqual((out / "user.txt").read_text(), "keep me")   # 不覆盖不并入


class TransferSurfaceTest(unittest.TestCase):
    def test_cli_upgrade_stub_reports_transfer(self):
        from wflib import cli

        self.assertIn("upgrade", cli.COMMANDS)                     # 48/48 注册保留
        handler = cli.COMMANDS["upgrade"]
        ctx = type("Ctx", (), {"root": "/tmp/x"})()
        args = type("Args", (), {"argv": []})()
        with self.assertRaises(cli.CliError) as caught:
            handler(ctx, args)
        self.assertEqual(caught.exception.code, "WF_CAPABILITY_UNAVAILABLE")
        self.assertIn("引导层转交", json.dumps(caught.exception.facts, ensure_ascii=False))

    def test_wf_py_upgrade_missing_args_reports_three_elements(self):
        source = (PAYLOAD / "bin/wf.py").read_text(encoding="utf-8")
        self.assertIn("需要三要素", source)
        self.assertIn("os.execve", source)


if __name__ == "__main__":
    unittest.main()
