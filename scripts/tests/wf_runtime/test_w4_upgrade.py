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
import shutil
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
        self.upgrade = kwargs.get("upgrade", True)
        self.apply = kwargs.get("apply", False)
        self.platform = kwargs.get("platform", [])
        self.confirm = kwargs.get("confirm", False)
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
            self.manifest, str(self.source), [])
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
                                                  self.manifest, str(self.source), [])
        update = [item for item in plan["actions"] if item["kind"] == "update"]
        self.assertEqual(len(update), 1)
        self.assertEqual(update[0]["relative"], ".wf/bin/repair.py")

    def test_same_accepted_deviation_skips_asking(self):
        # 同一已接受偏离（两边指纹均同）免重复询问
        self._write_local(".wf/bin/repair.py", "local deviation bytes")
        local = self._local_digest(".wf/bin/repair.py")
        installation = json.loads(
            (self.target / ".wf/install/installation.json").read_text(encoding="utf-8"))
        installation["assets"][1]["digest"] = self.new_repair_digest
        # 「同一已接受偏离」= 登记的 upstream_fingerprint 等于**本次**发行摘要（同一偏离再现）；
        # 登记为旧版摘要则上游又变了，属新冲突须重问——语义即此
        installation["assets"][1]["local_fingerprint"] = local
        installation["assets"][1]["upstream_fingerprint"] = self.new_repair_digest
        installation["assets"][1]["decision"] = "human (test)"
        plan, unresolved = install.three_way_plan(str(self.target), installation,
                                                  self.manifest, str(self.source), [])
        kept = [item for item in plan["actions"] if item["kind"] == "deviation-kept"]
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["decision"], "human (test)")

    def test_kept_deviation_with_new_upstream_is_conflict_not_update(self):
        # P1-a 回归：digest 是 O/N，不是 L；下一版改同一文件必须交人，不能静默 update
        self._write_local(".wf/bin/repair.py", "kept local bytes")
        local = self._local_digest(".wf/bin/repair.py")
        installation = json.loads(
            (self.target / ".wf/install/installation.json").read_text(encoding="utf-8"))
        installation["assets"][1]["digest"] = self.new_repair_digest
        installation["assets"][1]["local_fingerprint"] = local
        installation["assets"][1]["upstream_fingerprint"] = self.new_repair_digest
        installation["assets"][1]["decision"] = "human (upgrade --keep)"
        self.manifest["assets"][1]["digest"] = "sha256:" + "e" * 64
        plan, unresolved = install.three_way_plan(
            str(self.target), installation, self.manifest, str(self.source), [])
        self.assertFalse([item for item in plan["actions"] if item["kind"] == "update"])
        self.assertTrue(any(item["kind"] == "local-deviates" for item in unresolved))

    def test_other_conflict_goes_to_human_with_exits(self):
        self._write_local(".wf/bin/repair.py", "user edited, not release, not installed")
        plan, unresolved = install.three_way_plan(str(self.target), json.loads(
            (self.target / ".wf/install/installation.json").read_text(encoding="utf-8")),
            self.manifest, str(self.source), [])
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
                                                  self.manifest, str(self.source), [])
        self.assertEqual(len(plan["deletes"]), 1)
        self.assertEqual(plan["deletes"][0]["relative"], ".wf/lib/wflib/session.py")

    def test_local_missing_requires_decision_not_silent_restore(self):
        # 设计稿 §7.2 表首行：本地缺失先让第三人确认，不能直接 reinstall 复活
        installation = json.loads(
            (self.target / ".wf/install/installation.json").read_text(encoding="utf-8"))
        plan, unresolved = install.three_way_plan(
            str(self.target), installation, self.manifest, str(self.source), [])
        self.assertFalse([item for item in plan["actions"] if item["kind"] == "reinstall"])
        self.assertTrue(any(item["kind"] == "local-missing" for item in unresolved))
        exits = [item for item in unresolved if item["kind"] == "local-missing"][0]["exits"]
        self.assertTrue(any("--keep" in e for e in exits))
        self.assertTrue(any("--restore" in e for e in exits))

    def test_local_missing_keep_means_respect_deletion(self):
        installation = json.loads(
            (self.target / ".wf/install/installation.json").read_text(encoding="utf-8"))
        plan, unresolved = install.three_way_plan(
            str(self.target), installation, self.manifest, str(self.source),
            [".wf/lib/wflib/session.py", ".wf/bin/repair.py"], [])
        action = [item for item in plan["actions"] if item["relative"] == ".wf/lib/wflib/session.py"][0]
        self.assertEqual(action["kind"], "deleted-kept")
        self.assertEqual(unresolved, [])

    def test_local_missing_restore_means_reinstall(self):
        installation = json.loads(
            (self.target / ".wf/install/installation.json").read_text(encoding="utf-8"))
        plan, _u = install.three_way_plan(
            str(self.target), installation, self.manifest, str(self.source),
            [], [".wf/lib/wflib/session.py"])
        action = [item for item in plan["actions"] if item["relative"] == ".wf/lib/wflib/session.py"][0]
        self.assertEqual(action["kind"], "reinstall")

    def test_restore_overrides_prior_deletion_decision(self):
        installation = json.loads(
            (self.target / ".wf/install/installation.json").read_text(encoding="utf-8"))
        installation["assets"][0]["decision"] = "human (upgrade --keep)"
        installation["assets"][0]["local_fingerprint"] = None
        installation["assets"][1]["decision"] = "human (upgrade --keep)"
        installation["assets"][1]["local_fingerprint"] = None
        plan, _u = install.three_way_plan(
            str(self.target), installation, self.manifest, str(self.source),
            [], [".wf/lib/wflib/session.py"])
        action = [item for item in plan["actions"] if item["relative"] == ".wf/lib/wflib/session.py"][0]
        self.assertEqual(action["kind"], "reinstall")

    def test_local_missing_prior_deletion_decision_is_not_reasked(self):
        installation = json.loads(
            (self.target / ".wf/install/installation.json").read_text(encoding="utf-8"))
        installation["assets"][0]["decision"] = "human (upgrade --keep)"
        installation["assets"][0]["local_fingerprint"] = None
        installation["assets"][1]["decision"] = "human (upgrade --keep)"
        installation["assets"][1]["local_fingerprint"] = None
        plan, unresolved = install.three_way_plan(
            str(self.target), installation, self.manifest, str(self.source), [])
        action = [item for item in plan["actions"] if item["relative"] == ".wf/lib/wflib/session.py"][0]
        self.assertEqual(action["kind"], "deleted-kept")
        self.assertEqual(unresolved, [])

    def test_deleted_kept_then_upstream_removed_drops_record(self):
        self.manifest["assets"] = [self.manifest["assets"][1]]
        self._write_local(".wf/bin/repair.py", "still installed")
        self.manifest["assets"][0]["digest"] = self._local_digest(".wf/bin/repair.py")
        installation = json.loads(
            (self.target / ".wf/install/installation.json").read_text(encoding="utf-8"))
        installation["assets"][0]["decision"] = "human (upgrade --keep)"
        installation["assets"][0]["local_fingerprint"] = None
        plan, unresolved = install.three_way_plan(
            str(self.target), installation, self.manifest, str(self.source), [])
        self.assertEqual(unresolved, [])
        self.assertFalse([item for item in plan["actions"]
                          if item["relative"] == ".wf/lib/wflib/session.py"])
        self.assertFalse([item for item in plan["deletes"]
                          if item["relative"] == ".wf/lib/wflib/session.py"])

    def test_upstream_removed_local_changed_has_keep_restore_exits(self):
        self.manifest["assets"] = [self.manifest["assets"][1]]
        self._write_local(".wf/lib/wflib/session.py", "user content")
        installation = json.loads(
            (self.target / ".wf/install/installation.json").read_text(encoding="utf-8"))
        plan, unresolved = install.three_way_plan(
            str(self.target), installation, self.manifest, str(self.source), [])
        item = [entry for entry in unresolved if entry["kind"] == "upstream-removed-local-changed"][0]
        self.assertTrue(any("--keep" in e for e in item["exits"]))
        self.assertTrue(any("--restore" in e for e in item["exits"]))
        plan, _u = install.three_way_plan(
            str(self.target), installation, self.manifest, str(self.source),
            [".wf/lib/wflib/session.py"], [])
        self.assertEqual(plan["unmanaged"][0]["kind"], "unmanaged-keep")
        plan, _u = install.three_way_plan(
            str(self.target), installation, self.manifest, str(self.source),
            [], [".wf/lib/wflib/session.py"])
        self.assertTrue(any(item.get("restore") for item in plan["deletes"]))

    def test_add_hitting_user_file_is_unresolved(self):
        self._write_local(".wf/hooks/new.py", "user file")
        self.manifest["assets"].append(
            {"source_path": "payload/hooks/new.py", "target_class": "project_wf",
             "target_relative": ".wf/hooks/new.py", "kind": "hook", "required": True,
             "file_kind": "file", "executable": True, "digest": "sha256:" + "d" * 64})
        plan, unresolved = install.three_way_plan(str(self.target), json.loads(
            (self.target / ".wf/install/installation.json").read_text(encoding="utf-8")),
            self.manifest, str(self.source), [])
        self.assertTrue(any(item["kind"] == "add-hits-user-file" for item in unresolved))

    def test_add_same_content_still_needs_decision(self):
        self._write_local(".wf/hooks/new.py", "same as release")
        self.manifest["assets"].append(
            {"source_path": "payload/hooks/new.py", "target_class": "project_wf",
             "target_relative": ".wf/hooks/new.py", "kind": "hook", "required": True,
             "file_kind": "file", "executable": True,
             "digest": self._local_digest(".wf/hooks/new.py")})
        plan, unresolved = install.three_way_plan(
            str(self.target), json.loads(
                (self.target / ".wf/install/installation.json").read_text(encoding="utf-8")),
            self.manifest, str(self.source), [])
        self.assertFalse([item for item in plan["actions"] if item["kind"] == "register"])
        item = [entry for entry in unresolved if entry["kind"] == "add-hits-user-file"][0]
        self.assertTrue(item["same_content"])
        self.assertTrue(any("--keep" in e for e in item["exits"]))
        self.assertTrue(any("--restore" in e for e in item["exits"]))

    def test_add_same_content_restore_registers_keep_unmanages(self):
        self._write_local(".wf/hooks/new.py", "same as release")
        self.manifest["assets"].append(
            {"source_path": "payload/hooks/new.py", "target_class": "project_wf",
             "target_relative": ".wf/hooks/new.py", "kind": "hook", "required": True,
             "file_kind": "file", "executable": True,
             "digest": self._local_digest(".wf/hooks/new.py")})
        installation = json.loads(
            (self.target / ".wf/install/installation.json").read_text(encoding="utf-8"))
        plan, _u = install.three_way_plan(
            str(self.target), installation, self.manifest, str(self.source),
            [], [".wf/hooks/new.py"])
        action = [item for item in plan["actions"] if item["relative"] == ".wf/hooks/new.py"][0]
        self.assertEqual(action["kind"], "register")
        self.assertTrue(action["restore"])
        plan, _u = install.three_way_plan(
            str(self.target), installation, self.manifest, str(self.source),
            [".wf/hooks/new.py"], [])
        self.assertEqual(plan["unmanaged"][0]["relative"], ".wf/hooks/new.py")


class SelfCheckDeviationTest(unittest.TestCase):
    """P1-2：已接受偏离在自检里按 local_fingerprint 放行；保留删除按 intentional_missing 放行。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.target = Path(self._tmp.name)
        self.rel = ".wf/lib/wflib/session.py"
        self.path = self.target / self.rel
        self.path.parent.mkdir(parents=True)
        self.path.write_text("local deviation\n", encoding="utf-8")
        (self.target / ".wf/bin").mkdir(parents=True)
        (self.target / ".wf/bin/wf.py").write_text("# fixture\n", encoding="utf-8")
        self.manifest = {
            "delivery_round": 1,
            "assets": [{"source_path": "wf-release/lib/wflib/session.py",
                        "target_class": "project_wf", "target_relative": self.rel,
                        "kind": "lib", "required": True, "file_kind": "file",
                        "digest": "sha256:" + "f" * 64}],
            "required_steps": [],
        }
        self._original_runtime = install.runtime_support
        install.runtime_support = lambda target: {"supported": [], "handlers": {}, "commands": []}

    def tearDown(self):
        install.runtime_support = self._original_runtime
        self._tmp.cleanup()

    def _installation(self, decision=True, local=True):
        return {"roots": [], "assets": [{
            "target": self.rel, "root_ref": "project",
            "digest": install.file_digest(self.path),
            "source_path": "wf-release/lib/wflib/session.py",
            "local_fingerprint": install.file_digest(self.path) if local else None,
            "decision": "human (upgrade --keep)" if decision else None,
        }]}

    def test_accepted_deviation_passes(self):
        problems = install.self_check(str(self.target), self.manifest, [],
                                      installation=self._installation())
        self.assertEqual(problems, [])

    def test_unrecorded_deviation_still_fails(self):
        problems = install.self_check(str(self.target), self.manifest, [])
        self.assertTrue(any(item.get("reason") == "digest mismatch after deploy" for item in problems))

    def test_intentional_missing_is_reported_not_failure(self):
        self.path.unlink()
        problems = install.self_check(str(self.target), self.manifest, [],
                                      installation=self._installation(decision=True, local=False),
                                      intentional_missing={str(self.path)})
        self.assertEqual(problems, [])


class ManifestSyncTest(unittest.TestCase):
    """P0-1：升级必须把新发行清单复制到 release-manifest.json 并核对摘要。"""

    def test_stage_copies_new_manifest_and_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "proj"
            (target / ".wf/install").mkdir(parents=True)
            source = root / "release"
            source.mkdir()
            manifest_path = source / "wf-release.json"
            manifest_path.write_text(json.dumps({"version": "0.1.6"}), encoding="utf-8")
            staged, problem = install.stage_release_manifest(str(target), str(source))
            self.assertIsNone(problem)
            self.assertTrue(Path(staged["tmp"]).is_file())
            self.assertEqual(staged["digest"], install.file_digest(str(manifest_path)))
            os.replace(staged["tmp"], staged["path"])
            self.assertEqual(install.file_digest(staged["path"]), staged["digest"])


class UpgradeApplyTest(unittest.TestCase):
    """P0-1/P1-2 端到端：升级后清单副本一致、运行时入口可读、偏离不误判失败、账本落盘。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.target = self.root / "proj"
        (self.target / ".wf/bin").mkdir(parents=True)
        (self.target / ".wf/bin/wf.py").write_text("# fixture\n", encoding="utf-8")
        (self.target / ".gitignore").write_text("", encoding="utf-8")
        (self.target / ".wf/tasks").mkdir()
        self.session_rel = ".wf/lib/wflib/session.py"
        self.repair_rel = ".wf/bin/repair.py"
        session = self.target / self.session_rel
        session.parent.mkdir(parents=True)
        session.write_text("same\n", encoding="utf-8")
        repair = self.target / self.repair_rel
        repair.write_text("local deviation\n", encoding="utf-8")
        self.manifest = {
            "version": "0.1.5",
            "delivery_round": 1,
            "compatibility": {"rules_digest": "sha256:rules"},
            "gitignore_managed": {"begin_marker": "# wf-managed-v1", "end_marker": "# wf-managed-end",
                                  "lines": ["/.wf/.runtime/"]},
            "required_steps": [],
            "assets": [
                {"source_path": "wf-release/lib/wflib/session.py", "target_class": "project_wf",
                 "target_relative": self.session_rel, "kind": "lib", "required": True,
                 "file_kind": "file", "digest": install.file_digest(str(session))},
                {"source_path": "wf-release/bin/repair.py", "target_class": "project_wf",
                 "target_relative": self.repair_rel, "kind": "bin", "required": True,
                 "file_kind": "file", "digest": "sha256:" + "c" * 64},
            ],
        }
        self.source = self.root / "release"
        self.source.mkdir()
        (self.source / "wf-release.json").write_text(
            json.dumps(self.manifest, ensure_ascii=False), encoding="utf-8")
        installation = {
            "schema_version": 1, "version": "0.1.4", "release_ref": "refs/tags/wf-v0.1.4",
            "source_commit": "old", "platforms": ["codex"], "roots": [],
            "assets": [
                {"target": self.session_rel, "root_ref": "project",
                 "digest": install.file_digest(str(session)), "source_path": "wf-release/lib/wflib/session.py",
                 "upstream_version": "0.1.4", "upstream_fingerprint": install.file_digest(str(session))},
                {"target": self.repair_rel, "root_ref": "project",
                 "digest": "sha256:" + "c" * 64, "source_path": "wf-release/bin/repair.py",
                 "local_fingerprint": install.file_digest(str(repair)),
                 "upstream_fingerprint": "sha256:" + "c" * 64,
                 "decision": "human (upgrade --keep)"},
            ],
        }
        (self.target / ".wf/install").mkdir()
        (self.target / ".wf/install/installation.json").write_text(
            json.dumps(installation, ensure_ascii=False, indent=2), encoding="utf-8")
        (self.target / ".wf/writer.json").write_text(json.dumps(
            {"schema_version": 1, "id": "writer", "revision": 0, "state": "idle",
             "generation": 0, "holder": None, "created_at": "t", "updated_at": "t"}),
            encoding="utf-8")
        self._original_runtime = install.runtime_support
        install.runtime_support = lambda target: {"supported": [], "handlers": {}, "commands": []}
        self._original_token = install.PreviewToken
        self._original_stdin = install.sys.stdin

        class FakeToken:
            def issue(self, preview, nonce=None):
                self._digest = "sha256:preview"
                return "deadbeef"

            def digest(self):
                return self._digest

            def confirm(self, supplied):
                return supplied == "deadbeef"

        class FakeStdin:
            def isatty(self):
                return True

            def readline(self):
                return "deadbeef\n"

        install.PreviewToken = FakeToken
        install.sys.stdin = FakeStdin()

    def tearDown(self):
        install.runtime_support = self._original_runtime
        install.PreviewToken = self._original_token
        install.sys.stdin = self._original_stdin
        self._tmp.cleanup()

    def test_apply_updates_manifest_copy_and_runtime_can_load_it(self):
        import contextlib
        import io
        from wflib import assets as wf_assets

        args = _Args(target=str(self.target), source=str(self.source), apply=True)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = install.run_upgrade(args, self.manifest, "newcommit")
        self.assertEqual(code, 0, buffer.getvalue())
        installation = json.loads(
            (self.target / ".wf/install/installation.json").read_text(encoding="utf-8"))
        self.assertEqual(installation["version"], "0.1.5")
        copy = self.target / ".wf/install/release-manifest.json"
        self.assertTrue(copy.is_file())
        self.assertEqual(install.file_digest(str(copy)), installation["manifest_digest"])
        loaded = wf_assets.load_installed_manifest(str(self.target))
        self.assertEqual(loaded["version"], "0.1.5")
        repair_entry = [item for item in installation["assets"] if item["target"] == self.repair_rel][0]
        self.assertEqual(repair_entry["decision"], "human (upgrade --keep)")
        journal = (self.target / ".wf/install/maintenance.jsonl").read_text(encoding="utf-8")
        self.assertIn("upgrade-", journal)
        writer = json.loads((self.target / ".wf/writer.json").read_text(encoding="utf-8"))
        self.assertEqual(writer["state"], "idle")

    def test_apply_restore_missing_path_works(self):
        import contextlib
        import io

        release_file = self.source / "wf-release/bin/repair.py"
        release_file.parent.mkdir(parents=True)
        release_file.write_text("restored by release\n", encoding="utf-8")
        self.manifest["assets"][1]["digest"] = install.file_digest(str(release_file))
        (self.source / "wf-release.json").write_text(
            json.dumps(self.manifest, ensure_ascii=False), encoding="utf-8")
        (self.target / self.repair_rel).unlink()
        args = _Args(target=str(self.target), source=str(self.source), apply=True,
                     restore=[self.repair_rel])
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = install.run_upgrade(args, self.manifest, "newcommit")
        self.assertEqual(code, 0, buffer.getvalue())
        self.assertEqual((self.target / self.repair_rel).read_text(encoding="utf-8"),
                         "restored by release\n")
        installation = json.loads(
            (self.target / ".wf/install/installation.json").read_text(encoding="utf-8"))
        entry = [item for item in installation["assets"] if item["target"] == self.repair_rel][0]
        self.assertEqual(entry["digest"], self.manifest["assets"][1]["digest"])
        self.assertNotIn("decision", entry)

    def test_apply_required_new_asset_user_file_keep_is_blocked(self):
        import contextlib
        import io

        rel = ".wf/hooks/required-new.py"
        local = self.target / rel
        local.parent.mkdir(parents=True)
        local.write_text("my file\n", encoding="utf-8")
        self.manifest["assets"].append({
            "source_path": "wf-release/hooks/required-new.py", "target_class": "project_wf",
            "target_relative": rel, "kind": "hook", "required": True,
            "file_kind": "file", "executable": True, "digest": "sha256:" + "e" * 64,
        })
        (self.source / "wf-release/hooks").mkdir(parents=True)
        (self.source / "wf-release/hooks/required-new.py").write_text("release\n", encoding="utf-8")
        (self.source / "wf-release.json").write_text(
            json.dumps(self.manifest, ensure_ascii=False), encoding="utf-8")
        args = _Args(target=str(self.target), source=str(self.source), apply=True, keep=[rel])
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = install.run_upgrade(args, self.manifest, "newcommit")
        self.assertEqual(code, 2, buffer.getvalue())
        self.assertIn("必需资产", buffer.getvalue())

    def test_apply_user_file_keep_is_unmanaged_and_skips_self_check(self):
        import contextlib
        import io

        rel = ".wf/hooks/new.py"
        local = self.target / rel
        local.parent.mkdir(parents=True)
        local.write_text("my own hook\n", encoding="utf-8")
        self.manifest["assets"].append({
            "source_path": "wf-release/hooks/new.py", "target_class": "project_wf",
            "target_relative": rel, "kind": "hook", "required": False,
            "file_kind": "file", "executable": True, "digest": "sha256:" + "d" * 64,
        })
        (self.source / "wf-release/hooks").mkdir(parents=True)
        (self.source / "wf-release/hooks/new.py").write_text("release hook\n", encoding="utf-8")
        (self.source / "wf-release.json").write_text(
            json.dumps(self.manifest, ensure_ascii=False), encoding="utf-8")
        args = _Args(target=str(self.target), source=str(self.source), apply=True, keep=[rel])
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = install.run_upgrade(args, self.manifest, "newcommit")
        self.assertEqual(code, 0, buffer.getvalue())
        self.assertEqual(local.read_text(encoding="utf-8"), "my own hook\n")
        installation = json.loads(
            (self.target / ".wf/install/installation.json").read_text(encoding="utf-8"))
        self.assertFalse([item for item in installation["assets"] if item["target"] == rel])
        decisions = [item for item in installation.get("decisions") or []
                     if item.get("kind") == "unmanaged-keep" and item.get("path") == rel]
        self.assertEqual(len(decisions), 1)

    def test_apply_required_deletion_is_blocked_before_write(self):
        import contextlib
        import io

        (self.target / self.repair_rel).unlink()
        args = _Args(target=str(self.target), source=str(self.source), apply=True,
                     keep=[self.repair_rel])
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = install.run_upgrade(args, self.manifest, "newcommit")
        self.assertEqual(code, 2, buffer.getvalue())
        self.assertIn("必需资产", buffer.getvalue())
        installation = json.loads(
            (self.target / ".wf/install/installation.json").read_text(encoding="utf-8"))
        self.assertEqual(installation["version"], "0.1.4")     # 未写版本
        self.assertFalse((self.target / ".wf/install/release-manifest.json").exists())

    def test_apply_optional_deletion_keep_is_recorded(self):
        import contextlib
        import io

        self.manifest["assets"][1]["required"] = False
        (self.source / "wf-release.json").write_text(
            json.dumps(self.manifest, ensure_ascii=False), encoding="utf-8")
        (self.target / self.repair_rel).unlink()
        args = _Args(target=str(self.target), source=str(self.source), apply=True,
                     keep=[self.repair_rel])
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = install.run_upgrade(args, self.manifest, "newcommit")
        self.assertEqual(code, 0, buffer.getvalue())
        installation = json.loads(
            (self.target / ".wf/install/installation.json").read_text(encoding="utf-8"))
        entry = [item for item in installation["assets"] if item["target"] == self.repair_rel][0]
        self.assertIsNone(entry["digest"])
        self.assertEqual(entry["decision"], "human (upgrade --keep)")


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

    def test_paused_and_suspended_passes(self):
        # 挂起任务已暂停即可升级；“suspended 残留”不应被读成未暂停
        task_dir = self.target / ".wf/tasks/t-5"
        task_dir.mkdir(parents=True)
        (task_dir / "task.json").write_text(json.dumps(
            {"id": "t-5", "status": "in_progress", "paused": True, "suspended": True}),
            encoding="utf-8")
        problems, _wip = self._run()
        self.assertEqual([p for p in problems if "t-5" in json.dumps(p)], [])

    def test_missing_writer_blocks_instead_of_forging(self):
        (self.target / ".wf/writer.json").unlink()
        problems, _wip, writer = install.upgrade_prerequisites(str(self.target))
        self.assertIsNone(writer)
        self.assertTrue(any(p["reason"] == "writer missing" for p in problems))

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
        installation["assets"][1]["digest"] = self.new_repair_digest
        installation["assets"][1]["local_fingerprint"] = local
        # 同一已接受偏离：登记的 upstream_fingerprint 等于本次发行摘要（见 ThreeWayPlanTest 语义说明）
        installation["assets"][1]["upstream_fingerprint"] = self.new_repair_digest
        installation["assets"][1]["decision"] = "human (keep)"
        (self.target / ".wf/install/installation.json").write_text(
            json.dumps(installation, ensure_ascii=False, indent=2), encoding="utf-8")
        plan, _u = install.three_way_plan(str(self.target), installation, self.manifest,
                                          str(self.source), [".wf/bin/repair.py"], [])
        out = self.root / "export-out"
        args = _Args(target=str(self.target), source=str(self.source),
                     export_deviations=True, out=str(out))
        import io
        import contextlib
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = install.run_upgrade(args, self.manifest, "c0ffee")
        self.assertIn("偏离导出", buffer.getvalue())

    def test_out_inside_project_is_rejected(self):
        out = self.target / "export-out"
        args = _Args(target=str(self.target), source=str(self.source),
                     export_deviations=True, out=str(out))
        import io
        import contextlib
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = install.run_upgrade(args, self.manifest, "c0ffee")
        self.assertEqual(code, 1)
        self.assertIn("项目树外", buffer.getvalue())
        self.assertFalse(out.exists())

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


class ExportSemanticsTest(Harness):
    """2026-11-23：导出是只读回源通道，不按升级前置清场，也不只认已登记 decision。"""

    def _installation(self):
        return json.loads(
            (self.target / ".wf/install/installation.json").read_text(encoding="utf-8"))

    def _busy_project(self):
        writer = {"schema_version": 1, "id": "writer", "revision": 0, "state": "held",
                  "generation": 1, "holder": {"kind": "task", "id": "t-1"}}
        (self.target / ".wf/writer.json").write_text(json.dumps(writer), encoding="utf-8")
        task_dir = self.target / ".wf/tasks/t-1"
        task_dir.mkdir(parents=True)
        (task_dir / "task.json").write_text(json.dumps(
            {"id": "t-1", "status": "in_progress", "paused": False, "suspended": False}),
            encoding="utf-8")

    def _run_export(self, out):
        args = _Args(target=str(self.target), source=str(self.source),
                     export_deviations=True, out=str(out))
        import io
        import contextlib
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = install.run_upgrade(args, self.manifest, "c0ffee")
        return code, buffer.getvalue()

    def test_export_ignores_upgrade_prerequisites(self):
        # 不同版本 + 在途任务 + 写权被占：只读导出仍应成功（旧实现被升级前置拦住）
        self._write_local(".wf/bin/repair.py", "deviated local")
        self._busy_project()
        before = (self.target / ".wf/install/installation.json").read_text(encoding="utf-8")
        out = self.root / "out-readonly"
        code, text = self._run_export(out)
        self.assertEqual(code, 0, text)
        self.assertTrue((out / "manifest.json").is_file(), text)
        self.assertEqual(before, (self.target / ".wf/install/installation.json").read_text(encoding="utf-8"))
        manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["deviations"][0]["status"], "pending")
        # 五轮 a-1：导出清单的人面路径是**项目相对路径**（与 --keep/--restore 同一 token）
        self.assertEqual(manifest["deviations"][0]["target_path"], ".wf/bin/repair.py")
        self.assertNotIn("path", manifest["deviations"][0])

    def test_export_allows_same_version(self):
        # 同版只读导出：补丁基线就是当前发行 N；不应被“同版非升级”拦住
        installation = self._installation()
        installation["version"] = "0.1.5"
        (self.target / ".wf/install/installation.json").write_text(
            json.dumps(installation, ensure_ascii=False, indent=2), encoding="utf-8")
        self.manifest["version"] = "0.1.5"
        self._write_local(".wf/bin/repair.py", "same-version deviation")
        out = self.root / "out-same"
        code, text = self._run_export(out)
        self.assertEqual(code, 0, text)
        self.assertTrue((out / "manifest.json").is_file(), text)
        self.assertEqual(json.loads((out / "manifest.json").read_text())["release_version"], "0.1.5")

    def test_export_out_inside_symlinked_target_is_rejected(self):
        link = self.root / "proj-link"
        link.symlink_to(self.target, target_is_directory=True)
        out = link / "exports"
        args = _Args(target=str(link), source=str(self.source),
                     export_deviations=True, out=str(out))
        import io
        import contextlib
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = install.run_upgrade(args, self.manifest, "c0ffee")
        self.assertEqual(code, 1)
        self.assertIn("项目树外", buffer.getvalue())
        self.assertFalse((self.target / "exports").exists())

    def test_no_deviation_is_ok_not_blocked(self):
        # 本地与发行一致：没有可导出的偏离是正常结果，不是需要人裁决的冲突
        out = self.root / "out-none"
        code, text = self._run_export(out)
        self.assertEqual(code, 0, text)
        self.assertIn("无本地偏离", text)
        self.assertFalse((out / "manifest.json").exists())

    def test_flag_combinations_are_rejected_before_paths(self):
        cases = [
            (_Args(target="x", upgrade=False, apply=True), "--apply"),
            (_Args(target="x", export_deviations=True, apply=True, out="o"), "--apply"),
            (_Args(target="x", export_deviations=True, out=None), "--out"),
            (_Args(target="x", export_deviations=True, keep=["a"], out="o"), "--keep"),
            (_Args(target="x", out="o"), "--out"),
            (_Args(target="x", keep=["a"], restore=["a"]), "--keep/--restore"),
            (_Args(target="x", confirm=True), "--confirm"),
        ]
        for args, flag in cases:
            problems = install.upgrade_flag_problems(args)
            self.assertTrue(any(item["flag"] == flag for item in problems), (flag, problems))


class ExportPatchHeaderTest(unittest.TestCase):
    """补丁头必须是清单 source_path，才能应用到源仓库发行检出根。"""

    def test_patch_uses_source_path_not_target_path(self):
        import contextlib
        import io

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "proj"
            local = target / ".wf/lib/wflib/scope.py"
            local.parent.mkdir(parents=True)
            local.write_text("local\n", encoding="utf-8")
            out = root / "out"
            plan = {"actions": [{
                "base": str(target), "relative": ".wf/lib/wflib/scope.py",
                "path": ".wf/lib/wflib/scope.py",
                "kind": "deviation-kept", "local": "sha256:local", "upstream": "sha256:old",
                "new": "sha256:new", "decision": "human (upgrade --keep)",
                "asset": {"source_path": "wf-release/lib/wflib/scope.py"},
            }], "deletes": [], "unresolved": []}
            args = _Args(target=str(target), source=str(root), export_deviations=True, out=str(out))
            original = install._committed_bytes
            install._committed_bytes = lambda source, commit, path: b"base\n"
            try:
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    code = install.export_deviations(
                        args, {"version": "0.1.5"}, {"version": "0.1.5"}, plan,
                        str(root), "c0ffee")
            finally:
                install._committed_bytes = original
            self.assertEqual(code, 0, buffer.getvalue())
            patch = (out / "deviations/1-scope.py.patch").read_text(encoding="utf-8")
            self.assertIn("a/wf-release/lib/wflib/scope.py", patch)
            self.assertIn("b/wf-release/lib/wflib/scope.py", patch)
            self.assertNotIn("a/.wf/lib/wflib/scope.py", patch)
            manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["deviations"][0]["source_path"], "wf-release/lib/wflib/scope.py")


class WfPyForwardingTest(unittest.TestCase):
    """引导层必须把 install.py 支持的升级参数原样转交，且不吞未知参数。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.project = self.root / "proj"
        (self.project / ".wf/bin").mkdir(parents=True)
        shutil.copy2(PAYLOAD / "bin/wf.py", self.project / ".wf/bin/wf.py")
        self.release = self.root / "release"
        self.release.mkdir()
        self.marker = self.root / "argv.json"
        (self.release / "install.py").write_text(
            "import json, sys\n"
            f"json.dump(sys.argv, open({str(self.marker)!r}, 'w'))\n",
            encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, *extra):
        return subprocess.run(
            [sys.executable, str(self.project / ".wf/bin/wf.py"), "--project", str(self.project),
             "upgrade", "--release", str(self.release), "--release-ref", "refs/tags/wf-v0.1.6",
             *extra],
            capture_output=True, text=True, timeout=60)

    def test_known_flags_are_forwarded_verbatim(self):
        out = self.root / "out"
        result = self._run("--export-deviations", "--out", str(out),
                           "--keep", "a", "--restore", "b", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        argv = json.loads(self.marker.read_text(encoding="utf-8"))
        self.assertIn("--export-deviations", argv)
        self.assertIn("--out", argv)
        self.assertIn(str(out), argv)
        self.assertIn("--keep", argv)
        self.assertIn("a", argv)
        self.assertIn("--restore", argv)
        self.assertIn("b", argv)
        self.assertIn("--json", argv)
        self.assertIn("refs/tags/wf-v0.1.6", argv)
        self.assertNotIn("--release", argv)          # 引导层自用，不转交 install.py

    def test_unknown_flag_is_rejected_not_swallowed(self):
        result = self._run("--json", "--frobnicate")
        self.assertNotEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["code"], "WF_USAGE_INVALID")
        self.assertEqual(payload["facts"]["unknown"], "--frobnicate")
        self.assertFalse(self.marker.exists())       # 未转交、未执行安装器


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

    def test_install_direct_unknown_flag_is_structured_usage_error(self):
        import contextlib
        import io

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = install.main(["--target", "/tmp", "--release-ref", "refs/tags/wf-v0.1.5",
                                 "--source", "/tmp", "--frobnicate", "--json"])
        self.assertEqual(code, 1)
        payload = json.loads(buffer.getvalue())
        self.assertEqual(payload["code"], "WF_USAGE_INVALID")
        self.assertEqual(payload["facts"]["unknown"], ["--frobnicate"])


if __name__ == "__main__":
    unittest.main()
