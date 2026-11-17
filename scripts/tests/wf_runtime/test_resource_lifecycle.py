"""结果身份与 run 生命周期（owner schema2 / run-state schema1 / begin_run 复用矩阵）。

覆盖 AC07/08/09/18 的身份部分：
- owner 精确旧格式、schema2、未知 schema/字段、错 root、plan-only 与 execution 的意图校验；
- run-state active/finished/unknown、证据完整性对复用许可的影响；
- begin_run 只允许 absent/空/精确 plan-only/finished+cleaned，其余拒绝且不删任何内容；
- 三个初始化 checkpoint 只要求“点名 + 总开关 + owned scope”，非法点名在首次写前拒绝；
- finish_run 只改写本代 active 状态。
"""

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

FULL = Path(__file__).resolve().parent / "full"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lifecycle = _load("wf_lifecycle_identity_test", FULL / "resource_lifecycle.py")


class IdentityTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-lifecycle-identity-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "results"
        self.root.mkdir()

    def write_owner(self, payload):
        (self.root / lifecycle.OWNER_NAME).write_text(json.dumps(payload))

    def owner(self, **overrides):
        payload = lifecycle.owner_document(str(self.root), "execution", "run-1")
        payload.update(overrides)
        return payload

    def test_schema2_owner_is_strict(self):
        self.write_owner(self.owner())
        self.assertEqual(lifecycle.classify_owner(str(self.root))["kind"], "schema2")
        for overrides in ({"schema_version": 1}, {"lifecycle_protocol": True},
                          {"extra": "x"}, {"root": "/elsewhere"},
                          {"intent": "execution", "run_id": None},
                          {"intent": "plan-only", "run_id": "run-1"},
                          {"owner": "someone-else"}):
            with self.subTest(overrides=overrides):
                self.write_owner(self.owner(**overrides))
                self.assertEqual(lifecycle.classify_owner(str(self.root))["kind"], "unknown")

    def test_legacy_owner_is_format_only(self):
        self.write_owner({"owner": lifecycle.RESULT_OWNER, "root": str(self.root)})
        self.assertEqual(lifecycle.classify_owner(str(self.root))["kind"], "legacy")

    def test_broken_owner_is_unknown(self):
        (self.root / lifecycle.OWNER_NAME).write_text("{broken")
        self.assertEqual(lifecycle.classify_owner(str(self.root))["kind"], "unknown")

    def test_run_state_requires_identity_and_evidence(self):
        payload = {"schema_version": 1, "run_id": "run-1", "root": str(self.root),
                   "role": "full", "state": "finished", "cleanup_state": "cleaned",
                   "evidence_state": "complete", "status": "ok", "reasons": [],
                   "retained_paths": [], "started_at": "t", "finished_at": "t"}
        (self.root / lifecycle.RUN_STATE_NAME).write_text(json.dumps(payload))
        self.assertEqual(lifecycle.classify_run_state(str(self.root))["kind"], "finished")
        for overrides in ({"role": "other"}, {"run_id": ""}, {"cleanup_state": "maybe"},
                          {"evidence_state": "unknown"}, {"root": "/elsewhere"},
                          {"schema_version": True}):
            with self.subTest(overrides=overrides):
                record = dict(payload, **overrides)
                (self.root / lifecycle.RUN_STATE_NAME).write_text(json.dumps(record))
                self.assertEqual(lifecycle.classify_run_state(str(self.root))["kind"], "unknown")


class ClassificationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-lifecycle-classify-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "results"

    def begin(self, intent="execution", role="full", run_id=None):
        return lifecycle.begin_run(str(self.root), intent, role, run_id)

    def finish(self, run_id, cleanup="cleaned", evidence="complete", retained=()):
        lifecycle.finish_run(str(self.root), run_id, "full", cleanup, "ok", evidence, retained)

    def test_absent_empty_and_plan_only(self):
        self.assertEqual(lifecycle.classify_result(str(self.root))["kind"], "absent")
        out = self.begin("plan-only", "full")
        self.assertEqual(lifecycle.classify_result(str(self.root))["kind"],
                         "empty")
        (self.root / "plan.json").write_text("{}")
        self.assertEqual(lifecycle.classify_result(str(self.root))["kind"], "plan-only")
        (self.root / "commands").mkdir()
        self.assertEqual(lifecycle.classify_result(str(self.root))["kind"], "incomplete-new")
        self.assertIsNone(out["run_id"])

    def test_finished_cleaned_requires_complete_evidence_and_no_retention(self):
        out = self.begin()
        self.finish(out["run_id"])
        self.assertEqual(lifecycle.classify_result(str(self.root))["kind"], "finished-cleaned")
        self.assertTrue(lifecycle.classify_result(str(self.root))["automatic_prune"])

    def test_evidence_incomplete_or_retained_blocks_reuse(self):
        out = self.begin()
        self.finish(out["run_id"], evidence="incomplete")
        self.assertFalse(lifecycle.classify_result(str(self.root))["reusable"])
        with self.assertRaises(lifecycle.LifecycleError):
            self.begin()
        import shutil
        shutil.rmtree(self.root)
        out = self.begin()
        self.finish(out["run_id"], retained=["/tmp/kept"])
        result = lifecycle.classify_result(str(self.root))
        self.assertEqual(result["kind"], "active")
        self.assertFalse(result["reusable"])
        with self.assertRaises(lifecycle.LifecycleError):
            self.begin()

    def test_active_unknown_and_mismatch_refuse_without_deleting(self):
        out = self.begin()
        (self.root / "lines").write_text("x")
        info = lifecycle.classify_result(str(self.root))
        self.assertEqual(info["kind"], "active")
        with self.assertRaises(lifecycle.LifecycleError):
            self.begin()
        self.assertTrue((self.root / "lines").exists())
        # run_id 不匹配：owner 指向本代、state 指向别的代
        record = json.loads((self.root / lifecycle.RUN_STATE_NAME).read_text())
        record["run_id"] = "another-run"
        (self.root / lifecycle.RUN_STATE_NAME).write_text(json.dumps(record))
        self.assertIn(lifecycle.classify_result(str(self.root))["kind"],
                      ("incomplete-new", "unknown"))
        _ = out

    def test_legacy_owner_with_content_is_not_reused(self):
        owner = {"owner": lifecycle.RESULT_OWNER,
                 "root": lifecycle.canonical_root(str(self.root))}
        self.root.mkdir(parents=True)
        (self.root / lifecycle.OWNER_NAME).write_text(json.dumps(owner))
        (self.root / "lines").write_text("x")
        with self.assertRaises(lifecycle.LifecycleError):
            self.begin()
        self.assertTrue((self.root / "lines").exists())

    def test_unknown_top_level_entry_refuses_reuse(self):
        out = self.begin()
        self.finish(out["run_id"])
        (self.root / "user-notes.txt").write_text("keep")
        with self.assertRaises(lifecycle.LifecycleError):
            self.begin()
        self.assertTrue((self.root / "user-notes.txt").exists())

    def test_begin_run_prepares_only_known_artifacts(self):
        out = self.begin()
        (self.root / "lines").write_text("x")
        (self.root / "logs").mkdir(exist_ok=True)
        (self.root / "logs" / "a.log").write_text("x")
        (self.root / "commands").mkdir(exist_ok=True)
        (self.root / "commands" / "c.json").write_text("{}")
        self.finish(out["run_id"])
        second = self.begin()
        self.assertNotEqual(second["run_id"], out["run_id"])
        self.assertFalse((self.root / "lines").exists())
        self.assertFalse((self.root / "logs" / "a.log").exists())
        self.assertFalse((self.root / "commands" / "c.json").exists())
        self.assertTrue((self.root / "logs").is_dir())
        self.assertTrue((self.root / "commands").is_dir())

    def test_run_owned_pycache_is_a_registered_artifact(self):
        out = self.begin()
        (self.root / "pycache").mkdir()
        (self.root / "pycache" / "x.pyc").write_text("bytecode")
        self.finish(out["run_id"])
        info = lifecycle.classify_result(str(self.root))
        self.assertEqual(info["kind"], "finished-cleaned", info["reason"])
        self.begin()
        self.assertFalse((self.root / "pycache").exists())

    def test_finish_run_only_rewrites_this_generation(self):
        out = self.begin()
        with self.assertRaises(lifecycle.LifecycleError):
            lifecycle.finish_run(str(self.root), "other-run", "full", "cleaned", "ok")
        lifecycle.finish_run(str(self.root), out["run_id"], "full", "cleaned", "ok",
                             "complete")
        state = json.loads((self.root / lifecycle.RUN_STATE_NAME).read_text())
        self.assertEqual((state["state"], state["cleanup_state"], state["evidence_state"]),
                         ("finished", "cleaned", "complete"))


class UnitExecutionTest(unittest.TestCase):
    """unit_execution schema1：本次 invocation 的阶段引用、prep 失败终态与写失败。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-unit-exec-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.results = self.root / "results"
        self.results.mkdir()
        self.unit_result = self.results / "u.test.log.json"

    def receipt(self, command_id, phase="test", run_id=None, state="finished",
                local="none"):
        path = self.results / "logs" / f"{phase}.{command_id}.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps({"schema_version": 1, "command_id": command_id,
                                    "run_id": run_id, "evidence_scope": "managed-child",
                                    "state": state, "local_cleanup": local,
                                    "retained_paths": []}))
        return path

    def result(self, path, command_id, phase="test", status="passed", run_id=None):
        payload = {"schema_version": 2, "name": "u", "status": status, "rc": 0 if status == "passed" else 1,
                   "evidence_path": str(path)}
        if phase == "test":
            payload["supervision"] = {"cleanup_state": "cleaned", "infrastructure_error": False,
                                      "target_rc": 0 if status == "passed" else 1}
        (self.results / "logs" / f"{phase}.result.json").write_text(json.dumps(payload))
        return self.results / "logs" / f"{phase}.result.json"

    def run_cli(self, *args):
        import subprocess
        import sys
        return subprocess.run([sys.executable, str(FULL / "resource_lifecycle.py"),
                               "unit-execution", *args],
                              capture_output=True, text=True, timeout=30)

    def test_passed_unit_appends_evidence_for_this_invocation(self):
        receipt = self.receipt("c1", run_id="run-1")
        test_result = self.result(receipt, "c1", run_id="run-1")
        self.unit_result.write_text(json.dumps({"schema_version": 2, "name": "u",
                                                "status": "passed"}))
        proc = self.run_cli("--unit-result", str(self.unit_result), "--unit", "u",
                            "--invocation", "inv-1", "--run-id", "run-1", "--state", "passed",
                            "--result-row", "u\t0\t1\tok\tx",
                            "--phase", f"test:{test_result}")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        record = json.loads(self.unit_result.read_text())
        execution = record["unit_execution"]
        self.assertEqual((execution["invocation_id"], execution["run_id"],
                          execution["state"]), ("inv-1", "run-1", "passed"))
        self.assertEqual(execution["command_evidence"][0]["command_id"], "c1")
        self.assertEqual(execution["result_row"][0], "u")

    def test_prep_failure_without_commands_writes_a_preflight_record(self):
        proc = self.run_cli("--create-unit-result", str(self.unit_result), "--unit", "u",
                            "--invocation", "inv-2", "--state", "prep-failed",
                            "--result-row", "u\t1\t0\tbad\tFIXTURE-FAILED",
                            "--failure-reason", "FIXTURE-FAILED")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        record = json.loads(self.unit_result.read_text())
        self.assertEqual(record["unit_execution"]["state"], "prep-failed")
        self.assertTrue(record["unit_execution"]["preflight_failed"])
        self.assertNotIn("supervision", record, "prep 失败不得伪造 test 的 supervision")
        self.assertNotIn("assertion_result", record)

    def test_invalid_evidence_is_refused(self):
        (self.results / "logs").mkdir(exist_ok=True)
        test_result = self.results / "logs" / "missing-result.json"
        test_result.write_text(json.dumps({"schema_version": 2, "status": "passed"}))
        self.unit_result.write_text(json.dumps({"schema_version": 2, "name": "u",
                                                "status": "passed"}))
        proc = self.run_cli("--unit-result", str(self.unit_result), "--unit", "u",
                            "--invocation", "inv-3", "--state", "passed",
                            "--result-row", "u\t0\t1\tok\tx",
                            "--phase", f"test:{test_result}")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("缺 evidence_path", proc.stderr)
        receipt = self.receipt("c2", run_id="run-2", local="pending")
        test_result = self.result(receipt, "c2", run_id="run-2")
        proc = self.run_cli("--unit-result", str(self.unit_result), "--unit", "u",
                            "--invocation", "inv-3", "--run-id", "run-2", "--state", "passed",
                            "--result-row", "u\t0\t1\tok\tx",
                            "--phase", f"test:{test_result}")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("本地清理未确认", proc.stderr)
        receipt = self.receipt("c3", run_id="run-3")
        test_result = self.result(receipt, "c3", run_id="run-3")
        proc = self.run_cli("--unit-result", str(self.unit_result), "--unit", "u",
                            "--invocation", "inv-3", "--run-id", "other-run",
                            "--state", "passed", "--result-row", "u\t0\t1\tok\tx",
                            "--phase", f"test:{test_result}")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("run_id 与本次不符", proc.stderr)

    def test_duplicate_unit_execution_is_refused(self):
        receipt = self.receipt("c4", run_id="run-1")
        test_result = self.result(receipt, "c4", run_id="run-1")
        self.unit_result.write_text(json.dumps({"schema_version": 2, "name": "u",
                                                "unit_execution": {"schema_version": 1}}))
        proc = self.run_cli("--unit-result", str(self.unit_result), "--unit", "u",
                            "--invocation", "inv-4", "--run-id", "run-1", "--state", "passed",
                            "--result-row", "u\t0\t1\tok\tx",
                            "--phase", f"test:{test_result}")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("拒绝重复写", proc.stderr)


class InitCheckpointTest(unittest.TestCase):
    """三个初始化点只在 helper 内 os._exit(97)：必须由真实子进程观察退出码。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-lifecycle-init-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "results"

    def run_begin(self, *, intent="execution", point=None, switch="1", scope=True,
                  extra_env=None):
        import subprocess
        import sys
        env = {key: value for key, value in os.environ.items() if not key.startswith("WF_")}
        env.update(extra_env or {})
        if switch is not None:
            env["WF_TEST_FAULT_INJECTION"] = switch
        if point is not None:
            env["WF_RESULTS_INIT_STOP_AFTER"] = point
        command = [sys.executable, str(FULL / "resource_lifecycle.py"), "begin-run",
                   "--results-root", str(self.root), "--role", "full", "--intent", intent,
                   "--format", "json"]
        if scope:
            # 真实 owned scope：checkpoint 准入要求它存在且可读。
            import fixture_scope
            scope_root = fixture_scope.create_test_scope()
            env["WF_TEST_SCOPE_ROOT"] = str(scope_root)
            self.addCleanup(lambda: __import__("shutil").rmtree(scope_root, ignore_errors=True))
        return subprocess.run(command, capture_output=True, text=True, env=env, timeout=60)

    def test_each_checkpoint_exits_97_at_its_own_window(self):
        for checkpoint in lifecycle.INIT_CHECKPOINTS:
            with self.subTest(checkpoint=checkpoint):
                import shutil
                if self.root.exists():
                    shutil.rmtree(self.root)
                proc = self.run_begin(point=checkpoint)
                self.assertEqual(proc.returncode, 97, proc.stdout + proc.stderr)
                self.assertIn("WF-RESULTS-INIT-STOP", proc.stderr)
                self.assertNotIn('"run_id"', proc.stdout, "死亡前不得给出成功 run_id")
                # 每点只写一半：下一次 begin_run 必须拒绝而非吞掉（保留现场）。
                if checkpoint != "after-prepare-before-controller":
                    with self.assertRaises(lifecycle.LifecycleError):
                        lifecycle.begin_run(str(self.root), "execution", "full")

    def test_first_plan_only_and_reuse_all_reach_the_checkpoint(self):
        def complete():
            out = lifecycle.begin_run(str(self.root), "execution", "full")
            lifecycle.finish_run(str(self.root), out["run_id"], "full", "cleaned", "ok",
                                 "complete")
            import shutil
            shutil.rmtree(self.root)
            out = lifecycle.begin_run(str(self.root), "execution", "full")
            lifecycle.finish_run(str(self.root), out["run_id"], "full", "cleaned", "ok",
                                 "complete")

        for intent in ("execution", "plan-only"):
            with self.subTest(intent=intent):
                import shutil
                if self.root.exists():
                    shutil.rmtree(self.root)
                out = lifecycle.begin_run(str(self.root), "execution", "full")
                lifecycle.finish_run(str(self.root), out["run_id"], "full", "cleaned", "ok",
                                     "complete")
                proc = self.run_begin(intent=intent, point="after-owner-intent")
                self.assertEqual(proc.returncode, 97, proc.stdout + proc.stderr)
                self.assertFalse(lifecycle.classify_result(str(self.root))["reusable"],
                                 "死亡窗口的意图不得被下一次运行当作可复用")
                with self.assertRaises(lifecycle.LifecycleError):
                    lifecycle.begin_run(str(self.root), "execution", "full")

    def test_invalid_selector_or_missing_gates_are_refused_before_writing(self):
        proc = self.run_begin(point="bogus")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("未知初始化 checkpoint", proc.stderr)
        self.assertFalse(self.root.exists(), "非法点名必须在首次写前拒绝")
        proc = self.run_begin(point="after-owner-intent", switch="0")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("只在 WF_TEST_FAULT_INJECTION=1", proc.stderr)
        self.assertFalse(self.root.exists())
        proc = self.run_begin(point="after-owner-intent", scope=False)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("owned test scope", proc.stderr)
        self.assertFalse(self.root.exists(), "没有 owned scope 时不得进入 checkpoint")



class RetirementTest(unittest.TestCase):
    """共用退役写序：报告先建、逐项删除、部分失败停止、幂等重盘点。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-retire-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.entries = []
        for index, name in enumerate(("a", "b", "c")):
            path = self.root / name
            path.mkdir()
            (path / "payload").write_text(name)
            self.entries.append({"root": str(self.root), "path": str(path),
                                 "kind": "template-staging", "provenance": "owned"})
        self.report = self.root / "report.json"

    def test_report_is_created_before_any_delete_and_partial_failure_stops(self):
        deleted = []

        def delete_entry(item):
            if item["path"].endswith("b"):
                raise OSError("injected delete failure")
            deleted.append(item["path"])
            os.unlink(os.path.join(item["path"], "payload"))
            os.rmdir(item["path"])

        with self.assertRaises(lifecycle.RetireError) as caught:
            lifecycle.execute_retirement("template-cache", str(self.root), self.entries,
                                         "safe-legacy", str(self.report), delete_entry,
                                         lambda: None, False)
        self.assertIn("删除失败，已停止", str(caught.exception))
        self.assertEqual(deleted, [self.entries[0]["path"]])
        saved = json.loads(self.report.read_text())
        self.assertEqual([item["state"] for item in saved["results"]], ["removed", "failed"])
        self.assertEqual(saved["failed_at"], self.entries[1]["path"])
        self.assertTrue(self.entries[1]["path"] and Path(self.entries[1]["path"]).exists())
        self.assertTrue(Path(self.entries[2]["path"]).exists(), "后续项不得被继续删除")

    def test_existing_report_or_missing_report_is_refused_before_delete(self):
        self.report.write_text("{}")
        with self.assertRaises(lifecycle.RetireError) as caught:
            lifecycle.execute_retirement("template-cache", str(self.root), self.entries,
                                         "safe-legacy", str(self.report),
                                         lambda item: None, lambda: None, False)
        self.assertIn("报告已存在", str(caught.exception))
        with self.assertRaises(lifecycle.RetireError):
            lifecycle.execute_retirement("template-cache", str(self.root), self.entries,
                                         "safe-legacy", None, lambda item: None,
                                         lambda: None, False)

    def test_selection_format_is_strict(self):
        for document in ({"schema_version": 1, "domain": "other",
                          "entries": self.entries},
                         {"schema_version": 1, "domain": "template-cache", "entries": []},
                         {"schema_version": 1, "domain": "template-cache",
                          "entries": [{"path": "relative", "kind": "marker"}]}):
            with self.subTest(document=document), self.assertRaises(lifecycle.RetireError):
                lifecycle.selection_entries(document, "template-cache")

    def test_live_references_detects_same_uid_cwd(self):
        import subprocess
        import sys
        target = self.entries[0]["path"]
        proc = subprocess.Popen([sys.executable, "-c",
                                 "import os,time; os.chdir(%r); time.sleep(30)" % target])
        try:
            import time
            deadline = time.monotonic() + 5
            found = []
            while time.monotonic() < deadline:
                found = lifecycle.live_references(target)
                if found:
                    break
                time.sleep(0.05)
            self.assertTrue(found, "同 UID 的 cwd 引用必须被发现")
            self.assertEqual(found[0]["kind"], "cwd")
        finally:
            proc.kill()
            proc.wait(timeout=5)

    def test_selection_digest_is_order_independent(self):
        reversed_entries = list(reversed(self.entries))
        self.assertEqual(lifecycle.selection_digest(self.entries),
                         lifecycle.selection_digest(reversed_entries))



if __name__ == "__main__":
    unittest.main()