"""五轮复审（第 5 份输入）的四个机制回归：预览内容绑定、首装重入、manual 开工验证、幽灵旗标。

每条都对应一份"看起来正常、实际能骗过门禁"的具体故障：

1. **b-1 预览只比路径集合**：同一路径在确认期间内容变了（L1→L2）仍会继续 `--restore`，
   覆盖确认后新增的修改。锁内重核必须比"逐路径动作 + 本地/上游/新版摘要"。
2. **b-2 首装中断后无法接续**：`writer.json` 存在但 `installation.json` 缺失时，重入被路由到
   "追加平台"，再因缺安装记录被拒；repair 只修 writer，补不出安装记录。路由应按**安装记录**
   判定，并把这次重入当首装重试（沿用既有 writer、递增代次）。
3. **b-3 manual 开工验证必然失败**：规划校验接受 `kind=manual + consume_at=start`，
   开工却按命令通道跑 → `WF_VERIFICATION_UNREADY`，AI 只能回去改已批准的验证声明。
4. **a-1 `task-retrospect --decision` 读了就丢**：帮助承诺"并入复盘记录"，实现里
   `decision` 从未使用。已删旗标；`test_help_contract` 的"读入即算消费"盲区在此新增
   "读入后被丢弃"的定向断言。
"""

import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
PAYLOAD = REPO / "docs/workflows/wf/payload"
sys.path.insert(0, str(PAYLOAD / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from wflib import cli, tasks  # noqa: E402
import command_introspection as ci  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


install = _load("w5_review5_install", PAYLOAD / "install.py")
RELEASED = json.loads(
    (REPO / "docs/workflows/wf-release/wf-release.json").read_text(encoding="utf-8"))
HOOK_REL = ".codex/hooks/wf-session-identity.py"


class PlanFingerprintTest(unittest.TestCase):
    """b-1：触发旧实现的最小差异是"同一路径的本地摘要变了"。"""

    def _plan(self, local):
        return {"actions": [{"kind": "deviation", "path": ".wf/bin/x.py", "local": local,
                             "upstream": "sha256:o", "new": "sha256:n", "restore": True}]}

    def test_same_paths_different_content_differ(self):
        self.assertNotEqual(install._plan_fingerprint(self._plan("sha256:L1")),
                            install._plan_fingerprint(self._plan("sha256:L2")))

    def test_identical_plan_is_stable(self):
        self.assertEqual(install._plan_fingerprint(self._plan("sha256:L1")),
                         install._plan_fingerprint(self._plan("sha256:L1")))

    def test_kind_change_is_visible(self):
        first = self._plan("sha256:L1")
        second = self._plan("sha256:L1")
        second["actions"][0]["kind"] = "update"
        self.assertNotEqual(install._plan_fingerprint(first),
                            install._plan_fingerprint(second))


class FirstInstallRetryTest(unittest.TestCase):
    """b-2：`writer.json` 在、`installation.json` 不在 ⇒ 仍走首装（重试），不转追加平台。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="wf-w5-retry-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.target = self.root / "proj"
        self.target.mkdir()
        self.source = self.root / "checkout"
        (self.source / "wf-release/skills/wf-start").mkdir(parents=True)
        (self.source / "wf-release/skills/wf-start/SKILL.md").write_text(
            "---\nname: wf-start\ndescription: x\n---\nbody\n", encoding="utf-8")
        self.manifest = {
            "version": "0.1.7",
            "compatibility": {"rules_digest": "sha256:rules"},
            "required_steps": [], "delivery_round": RELEASED["delivery_round"],
            "template_markers": [],
            "gitignore_managed": {"begin_marker": "# wf-managed-v1",
                                  "end_marker": "# wf-managed-end",
                                  "lines": ["/.wf-lock"]},
            "assets": [{"source_path": "wf-release/skills/wf-start/SKILL.md",
                        "target_class": "skill_root", "target_relative": "wf-start/SKILL.md",
                        "kind": "skill", "required": True, "file_kind": "file",
                        "executable": False,
                        "digest": install.file_digest(
                            str(self.source / "wf-release/skills/wf-start/SKILL.md"))}]}
        (self.source / "wf-release.json").write_text(
            json.dumps(self.manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        for patch in (
            mock.patch.object(install, "load_manifest",
                              lambda src: (self.manifest, str(self.source / "wf-release.json"))),
            mock.patch.object(install, "verify_assets", lambda *a, **k: []),
            mock.patch.object(install, "resolve_tag", lambda *a, **k: "c0ffee"),
            mock.patch.object(install, "_worktree_clean", lambda *a, **k: (True, [])),
            mock.patch.object(install, "branch_source_findings", lambda *a, **k: []),
            mock.patch.object(install, "trellis_clues", lambda *a, **k: []),
            mock.patch.object(install, "self_check", lambda *a, **k: []),
        ):
            patch.start()
            self.addCleanup(patch.stop)

    def _run(self, argv):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = install.main(argv)
        text = buffer.getvalue()
        payload = None
        decoder = json.JSONDecoder()
        for index, char in enumerate(text):
            if char != "{":
                continue
            try:
                payload, _end = decoder.raw_decode(text[index:])
            except ValueError:
                continue
            break
        return code, payload, text

    def _argv(self):
        return ["--target", str(self.target), "--release-ref", "refs/tags/wf-v0.1.7",
                "--source", str(self.source), "--confirm", "--json"]

    def test_interrupted_first_install_can_be_retried(self):
        # 模拟上一次首装中途失败：writer.json 在（recovering），无 installation.json
        (self.target / ".wf").mkdir(parents=True)
        (self.target / ".wf/writer.json").write_text(json.dumps(
            {"schema_version": 1, "id": "writer", "revision": 3, "state": "recovering",
             "generation": 7, "holder": None, "created_at": "t", "updated_at": "t",
             "maintenance_results": [{"operation": "install-old", "result": "failed"}]}),
            encoding="utf-8")
        code, payload, text = self._run(self._argv())
        self.assertEqual(payload["code"], "WF_OK", text)
        self.assertTrue((self.target / ".wf/install/installation.json").is_file())
        writer = json.loads((self.target / ".wf/writer.json").read_text(encoding="utf-8"))
        self.assertEqual(writer["state"], "idle")
        self.assertGreater(writer["generation"], 7, "重入不得重置代次")
        self.assertGreaterEqual(writer["revision"], 3)
        # 既有的维护回执不能被覆盖
        self.assertIn("install-old", json.dumps(writer["maintenance_results"]))

    def test_installed_project_still_routes_to_add_platforms(self):
        (self.target / ".wf/install").mkdir(parents=True)
        (self.target / ".wf/install/installation.json").write_text(json.dumps({
            "schema_version": 1, "version": "0.1.7", "release_ref": "refs/tags/wf-v0.1.7",
            "source_commit": "c0ffee", "rules_digest": "sha256:rules", "platforms": ["dsh"],
            "roots": [".agents/skills"], "assets": [], "host_hook_entries": []}),
            encoding="utf-8")
        (self.target / ".wf/writer.json").write_text(json.dumps(
            {"schema_version": 1, "id": "writer", "revision": 0, "state": "idle",
             "generation": 2, "holder": None, "created_at": "t", "updated_at": "t"}),
            encoding="utf-8")
        code, payload, text = self._run(self._argv())
        self.assertEqual(payload["code"], "WF_OK", text)
        installation = json.loads(
            (self.target / ".wf/install/installation.json").read_text(encoding="utf-8"))
        self.assertEqual(installation["install_id"] if "install_id" in installation else "absent",
                         "absent", "已安装项目不得被当成首装覆盖")


class ManualStartVerificationTest(unittest.TestCase):
    """b-3：manual + consume_at=start 只登记"待人判"，不执行、不报 UNREADY。"""

    def test_manual_start_verification_is_recorded_not_executed(self):
        plan = {"verifications": [
            {"id": "v-human", "invocation": {"kind": "manual", "criterion": "人确认环境可用"},
             "required": True, "consume_at": "start"},
            {"id": "v-cmd", "invocation": {"kind": "argv", "argv": [sys.executable, "-c", "pass"]},
             "required": True, "consume_at": "start"},
            {"id": "v-check", "invocation": {"kind": "manual", "criterion": "文档可读"},
             "required": True, "consume_at": "check"}]}
        ctx = type("C", (), {"root": "/tmp"})()
        results = tasks._run_start_verifications(ctx, {"plan": plan})
        self.assertEqual([item["verification_id"] for item in results], ["v-human", "v-cmd"])
        manual = results[0]
        self.assertEqual(manual["kind"], "manual")
        self.assertEqual(manual["status"], "human_required")
        self.assertEqual(manual["criterion"], "人确认环境可用")
        self.assertNotIn("exit_code", manual)
        self.assertEqual(results[1]["kind"], "argv")
        self.assertEqual(results[1]["exit_code"], 0)



class PhantomFlagTest(unittest.TestCase):
    """a-1：`task-retrospect --decision` 读入即丢弃——已删；这里防它复活。"""

    def test_retrospect_has_no_decision_flag(self):
        documented = {key for key in cli.COMMAND_HELP["task-retrospect"]["args"]
                      if key.startswith("--")}
        self.assertNotIn("--decision", documented)
        self.assertNotIn("--decision", cli.COMMAND_FLAGS["task-retrospect"])

    def test_handler_does_not_read_decision(self):
        sources = ci.handler_sources(cli, "task-retrospect",
                                     ci.example_argv(cli, "task-retrospect"))
        self.assertTrue(sources)
        for text in sources:
            self.assertNotIn('args.value("--decision")', text)

    def test_help_contract_reads_but_discards_is_caught_by_design(self):
        """盲区登记：`ConsumptionTest` 只保证"被读取"。这里用**行为**补一层：
        给了 `--decision` 必须被拒绝（未知参数），而不是 успех 后静默丢弃。"""
        ctx = cli.Context(tempfile.mkdtemp(prefix="wf-w5-phantom-"), [])
        ctx.command = "task-retrospect"
        with self.assertRaises(cli.CliError) as caught:
            cli.validate_usage("task-retrospect",
                               ["--task", "t1", "--evidence", "e.json", "--decision", "d.json"])
        self.assertEqual(caught.exception.code, "WF_USAGE_INVALID")


if __name__ == "__main__":
    unittest.main()


class PreviewContentBindingTest(unittest.TestCase):
    """b-1 行为面：预览→确认之间本地内容变了，必须 `WF_PREVIEW_STALE`（不只路径集合相等）。

    旧实现只比路径集合：同一路径的本地摘要从 L1 变 L2 仍会继续 `--restore`，
    覆盖确认后新增的修改。这里在**锁内重核那一次**改动文件，断言被拒。
    """

    ASSET = ".wf/bin/repair.py"

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="wf-w5-preview-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.target = self.root / "proj"
        (self.target / ".wf/install").mkdir(parents=True)
        self.local = self.target / self.ASSET
        self.local.parent.mkdir(parents=True)
        self.local.write_text("L1\n", encoding="utf-8")
        (self.target / ".wf/writer.json").write_text(json.dumps(
            {"schema_version": 1, "id": "writer", "revision": 0, "state": "idle",
             "generation": 3, "holder": None, "created_at": "t", "updated_at": "t"}),
            encoding="utf-8")
        (self.target / ".wf/install/installation.json").write_text(json.dumps(
            {"schema_version": 1, "version": "0.1.6", "release_ref": "refs/tags/wf-v0.1.6",
             "source_commit": "c0ffee", "platforms": ["dsh"], "roots": [],
             "assets": [{"target": self.ASSET, "root_ref": "project",
                         "digest": "sha256:" + "0" * 64,
                         "source_path": "wf-release/bin/repair.py",
                         "upstream_version": "0.1.6",
                         "upstream_fingerprint": "sha256:" + "0" * 64}]},
            ensure_ascii=False), encoding="utf-8")
        self.source = self.root / "checkout"
        (self.source / "wf-release/bin").mkdir(parents=True)
        (self.source / "wf-release/bin/repair.py").write_text("N\n", encoding="utf-8")
        self.manifest = {"version": "0.1.7",
                         "compatibility": {"rules_digest": "sha256:rules"},
                         "gitignore_managed": {"begin_marker": "# wf-managed-v1",
                                               "end_marker": "# wf-managed-end",
                                               "lines": ["/.wf-lock"]},
                         "assets": [{"source_path": "wf-release/bin/repair.py",
                                     "target_class": "project_wf",
                                     "target_relative": self.ASSET, "kind": "bin",
                                     "required": True, "file_kind": "file",
                                     "executable": False,
                                     "digest": install.file_digest(
                                         str(self.source / "wf-release/bin/repair.py"))}]}
        (self.source / "wf-release.json").write_text(
            json.dumps(self.manifest, ensure_ascii=False), encoding="utf-8")

    def test_content_change_between_preview_and_apply_is_stale(self):
        real = install.three_way_plan
        calls = {"n": 0}

        def wrapper(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 2:          # 锁内重核之前：有人改了本地文件
                self.local.write_text("L2\n", encoding="utf-8")
            return real(*args, **kwargs)

        args = type("A", (), {
            "target": str(self.target), "source": str(self.source),
            "release_ref": "refs/tags/wf-v0.1.7", "apply": True, "keep": [],
            "restore": [self.ASSET], "json": True, "upgrade": True,
            "platform": [], "confirm": False, "export_deviations": False, "out": None})()
        fake_stdin = mock.Mock(isatty=lambda: True, readline=lambda: "token\n")
        buffer = io.StringIO()
        with mock.patch.object(install, "three_way_plan", wrapper), \
                mock.patch.object(install.PreviewToken, "confirm", return_value=True), \
                mock.patch.object(install, "upgrade_prerequisites",
                                  return_value=([], {}, {"state": "idle"})), \
                mock.patch("sys.stdin", fake_stdin), \
                contextlib.redirect_stdout(buffer):
            code = install.run_upgrade(args, self.manifest, "c0ffee")
        text = buffer.getvalue()
        self.assertNotEqual(code, 0, text)
        self.assertIn("WF_PREVIEW_STALE", text)
        self.assertEqual(self.local.read_text(encoding="utf-8"), "L2\n",
                         "内容已变时必须不写入")


class FirstInstallTakeoverBoundaryTest(FirstInstallRetryTest):
    """六轮复审 a-1：首装重入不得越过 §4.4 的持有边界。

    旧实现把"缺 installation.json"直接当成首装中断，**只要 writer.json 能解析就覆盖其
    持有者**；已安装项目一旦丢失安装记录，正在工作的会话会被 maintenance 接管
    （holder=session → maintenance，代次 9→10），等于绕过写权边界。
    只有"无持有者"或"本框架安装维护留下的检查点"才可按首装重试。
    """

    def _seed_writer(self, holder, phase="installing", state="held", generation=9):
        (self.target / ".wf").mkdir(parents=True, exist_ok=True)
        (self.target / ".wf/writer.json").write_text(json.dumps(
            {"schema_version": 1, "id": "writer", "revision": 5, "state": state,
             "generation": generation, "holder": holder, "created_at": "t", "updated_at": "t",
             "checkpoint": {"operation": "op-old", "phase": phase},
             "maintenance_results": []}), encoding="utf-8")

    def test_session_holder_is_not_taken_over(self):
        self._seed_writer({"kind": "session", "id": "sess-1",
                           "scope": {"object": {"kind": "task", "id": "t-1"}}, "generation": 9})
        code, payload, text = self._run(self._argv())
        self.assertNotEqual(code, 0, text)
        self.assertEqual(payload["code"], "WF_WRITER_BUSY")
        writer = json.loads((self.target / ".wf/writer.json").read_text(encoding="utf-8"))
        self.assertEqual(writer["holder"]["kind"], "session", "会话持有不得被接管")
        self.assertEqual(writer["generation"], 9)
        self.assertFalse((self.target / ".wf/install/installation.json").exists())

    def test_maintenance_holder_of_other_phase_is_not_taken_over(self):
        self._seed_writer({"kind": "maintenance", "id": "op-other", "generation": 9},
                          phase="upgrading", state="held")
        code, payload, text = self._run(self._argv())
        self.assertNotEqual(code, 0, text)
        self.assertEqual(payload["code"], "WF_WRITER_BUSY")
        self.assertIn("不是安装阶段", json.dumps(payload["facts"], ensure_ascii=False))

    def test_crashed_install_maintenance_holder_is_takeable(self):
        self._seed_writer({"kind": "maintenance", "id": "op-install", "generation": 9},
                          phase="installing", state="held")
        code, payload, text = self._run(self._argv())
        self.assertEqual(payload["code"], "WF_OK", text)
        writer = json.loads((self.target / ".wf/writer.json").read_text(encoding="utf-8"))
        self.assertEqual(writer["state"], "idle")
        self.assertGreater(writer["generation"], 9)

    def test_handover_middle_state_is_not_taken_over(self):
        self._seed_writer({"kind": "session", "id": "sess-1", "generation": 9},
                          phase="handover", state="handover")
        code, payload, text = self._run(self._argv())
        self.assertEqual(payload["code"], "WF_WRITER_BUSY", text)


class StartVerificationRedactionTest(unittest.TestCase):
    """六轮复审 a-2：开工验证失败的命令输出必须走同一份遮罩。

    同一验证命令在 Check 阶段有遮罩（`check.redact_text`），开工阶段却把 stdout/stderr
    原样塞进错误事实——凭据会随错误回显进会话日志。这里用虚构 Bearer 值锁定。
    """

    def test_failure_output_is_redacted(self):
        token = "Bearer sk-live-ABC123SECRET"
        plan = {"verifications": [{"id": "v", "consume_at": "start", "required": True,
                                   "invocation": {"kind": "argv",
                                                  "argv": ["/bin/sh", "-c",
                                                           f"echo '{token}'; exit 3"]}}]}
        ctx = type("C", (), {"root": "/tmp"})()
        with self.assertRaises(tasks.TaskError) as caught:
            tasks._run_start_verifications(ctx, {"plan": plan})
        facts = json.dumps(caught.exception.__dict__.get("facts") or {}, ensure_ascii=False)
        output = json.dumps(json.loads(facts), ensure_ascii=False)
        self.assertNotIn("sk-live-ABC123SECRET", output)
        self.assertIn("***", output)
        self.assertEqual(caught.exception.code, "WF_CHECK_FAILED")


class LongCredentialMaskTest(unittest.TestCase):
    """七轮复审 a-1：长凭据必须整体遮罩，且顺序是"先遮罩、后截断"。

    断言用**唯一哨兵串**而不是某几个字母：遮罩会保留键/前缀（`Bearer `、`password:`），
    拿字母集合作判据会把头部词自身算成"残留"（上一版就栽在这：`Bearer` 里的 B）。
    """

    def test_redact_text_masks_whole_long_values(self):
        from wflib import check

        marker = "S3NT1NEL"
        cases = {
            "bearer": "Bearer " + marker * 200,
            "json-quoted": '{"token": "' + marker * 150 + '"}',
            "key-suffix": '{"access_token_value": "' + marker * 150 + '"}',
            "key-suffix-api": '{"api_key_primary": "' + marker * 150 + '"}',
            "cli": "--token " + marker * 150,
            "cli-quoted": 'run --token "' + marker * 150 + '"',
            "chinese": "口令：" + marker * 150,
        }
        for name, text in cases.items():
            masked = check.redact_text(text)
            self.assertNotIn(marker, masked, name)
            self.assertIn("***", masked, name)

    def test_plain_text_is_untouched(self):
        from wflib import check

        self.assertEqual(check.redact_text("hello world"), "hello world")

    def test_start_failure_output_masks_before_truncating(self):
        token = "Bearer " + "A" * 1090
        plan = {"verifications": [{"id": "v", "consume_at": "start", "required": True,
                                   "invocation": {"kind": "argv",
                                                  "argv": ["/bin/sh", "-c",
                                                           f"echo '{token}'; exit 3"]}}]}
        ctx = type("C", (), {"root": "/tmp"})()
        with self.assertRaises(tasks.TaskError) as caught:
            tasks._run_start_verifications(ctx, {"plan": plan})
        output = json.dumps(caught.exception.facts, ensure_ascii=False)
        self.assertEqual(output.count("A"), 0, output[:200])
        self.assertIn("***", output)


class ConcurrentInstallTest(FirstInstallRetryTest):
    """七轮复审 a-2：锁外判断"未安装"后，另一个进程可能刚装完。

    锁内不重判时，后拿到锁的进程会把既有安装记录当首装重试：重新生成安装身份、
    用自己的平台/技能根覆盖原记录，已有副本随即脱离升级/卸载管理。
    修法：锁内重判，发现已安装则释放锁并交回追加平台分支（不覆盖、不改身份）。
    """

    def test_install_completed_while_waiting_is_not_overwritten(self):
        installer = self
        real_lock = install.Lock

        class RacingLock:
            """进入锁的瞬间模拟"另一个安装进程刚写完安装记录"。"""

            def __init__(self, path, root=None):
                self._inner = real_lock(path, root=root)

            def __enter__(self):
                installed = {
                    "schema_version": 1, "install_id": "winner-install",
                    "version": "0.1.7", "release_ref": "refs/tags/wf-v0.1.7",
                    "source_commit": "c0ffee",
                    "rules_digest": "sha256:" + "9" * 64,      # 不同来源 ⇒ 追加平台会拒
                    "platforms": ["claudecode"], "roots": [".claude/skills"],
                    "assets": [], "host_hook_entries": []}
                install_dir = installer.target / ".wf/install"
                install_dir.mkdir(parents=True, exist_ok=True)
                (install_dir / "installation.json").write_text(
                    json.dumps(installed, ensure_ascii=False), encoding="utf-8")
                return self._inner.__enter__()

            def __exit__(self, *exc_info):
                return self._inner.__exit__(*exc_info)

        with mock.patch.object(install, "Lock", RacingLock):
            code, payload, text = self._run(self._argv())
        self.assertNotEqual(code, 0, text)
        installation = json.loads(
            (self.target / ".wf/install/installation.json").read_text(encoding="utf-8"))
        self.assertEqual(installation["install_id"], "winner-install", "不得重建安装身份")
        self.assertEqual(installation["platforms"], ["claudecode"], "不得被自己的平台覆盖")
        self.assertEqual(installation["roots"], [".claude/skills"])


class NoopSelfCheckTest(FirstInstallRetryTest):
    """八轮复审 b-2：首装自检失败 → repair 清写权 → 重跑，不能只回 OK 而不复核。

    旧实现走"无任何变化"幂等分支直接返回成功：既不重跑自检、也不报状态，
    AI 无法通过现有入口确认安装是否真正恢复。这里断言 noop 分支按同一 `self_check` 复核：
    有 problem 就阻断并列出，干净才回 OK 且事实里标 `self_check: clean`。
    """

    def _seed_installed(self):
        (self.target / ".wf/install").mkdir(parents=True)
        assets = [{"target": "wf-start/SKILL.md", "root_ref": str(self.target / root),
                   "digest": self.manifest["assets"][0]["digest"],
                   "source_path": "wf-release/skills/wf-start/SKILL.md",
                   "upstream_version": "0.1.7"}
                  for root in (".agents/skills", ".claude/skills")]
        (self.target / ".wf/install/installation.json").write_text(json.dumps({
            "schema_version": 1, "install_id": "install-1", "version": "0.1.7",
            "release_ref": "refs/tags/wf-v0.1.7", "source_commit": "c0ffee",
            "rules_digest": "sha256:rules",
            # 记录也要与"全部平台已装"一致：否则重跑会按陈旧元数据触发一次补齐
            "platforms": install.all_platforms(),
            "roots": [".agents/skills", ".claude/skills"],
            "assets": assets, "host_hook_entries": []}),
            encoding="utf-8")
        (self.target / ".wf/writer.json").write_text(json.dumps(
            {"schema_version": 1, "id": "writer", "revision": 0, "state": "idle",
             "generation": 4, "holder": None, "created_at": "t", "updated_at": "t"}),
            encoding="utf-8")
        source_text = (self.source / "wf-release/skills/wf-start/SKILL.md").read_text(
            encoding="utf-8")
        for root in (".agents/skills", ".claude/skills"):
            deployed = self.target / root / "wf-start/SKILL.md"
            deployed.parent.mkdir(parents=True, exist_ok=True)
            deployed.write_text(source_text, encoding="utf-8")

    def test_noop_reports_self_check_problems(self):
        """没有缺失可补、但自检不通过时必须报出来——不能"不做事却报绿"。"""
        self._seed_installed()
        with mock.patch.object(install, "self_check",
                               lambda *a, **k: [{"target": "x", "reason": "hook entry missing"}]):
            code, payload, text = self._run(self._argv())
        self.assertNotEqual(code, 0, text)
        self.assertEqual(payload["code"], "WF_CAPABILITY_UNAVAILABLE")
        self.assertEqual(payload["facts"]["self_check"], "problems")
        self.assertEqual(payload["facts"]["problems"], [{"target": "x",
                                                         "reason": "hook entry missing"}])
        self.assertIn("hook entry missing", text, "问题必须出现在人的可见输出里")

    def test_noop_with_clean_self_check_is_ok(self):
        self._seed_installed()
        with mock.patch.object(install, "self_check", lambda *a, **k: []):
            code, payload, text = self._run(self._argv())
        self.assertEqual(payload["code"], "WF_OK", text)
        self.assertEqual(payload["facts"]["self_check"], "clean")

    def test_noop_does_not_take_the_writer(self):
        self._seed_installed()
        with mock.patch.object(install, "self_check", lambda *a, **k: []):
            self._run(self._argv())
        writer = json.loads((self.target / ".wf/writer.json").read_text(encoding="utf-8"))
        self.assertEqual(writer["state"], "idle")
        self.assertEqual(writer["generation"], 4, "无写入不得递增代次")


class UrlCredentialMaskTest(unittest.TestCase):
    """八轮复审 b-1：URL 内凭据必须遮 password 段（脱敏协议 `secret-mask` 点名）。"""

    def test_url_password_is_masked_but_user_and_host_kept(self):
        from wflib import check

        masked = check.redact_text("https://alice:Sup3rS3cret@db.internal/x")
        self.assertNotIn("Sup3rS3cret", masked)
        self.assertIn("alice", masked)
        self.assertIn("@db.internal/x", masked)

    def test_url_without_password_is_untouched(self):
        from wflib import check

        self.assertEqual(check.redact_text("https://alice@db.internal/x"),
                         "https://alice@db.internal/x")

    def test_url_inside_log_line(self):
        from wflib import check

        masked = check.redact_text("clone failed: https://bob:hunter2@git.example.com/repo.git\n")
        self.assertNotIn("hunter2", masked)
        self.assertIn("git.example.com/repo.git", masked)

    def test_scp_style_remote_is_not_touched(self):
        from wflib import check

        self.assertEqual(check.redact_text("git@github.com:org/repo.git"),
                         "git@github.com:org/repo.git")


class RedactionLinearCostTest(unittest.TestCase):
    """八轮复审 b-3：长值里反复出现触发词不能退化成平方（100KB 曾 43s）。"""

    def test_repeated_triggers_in_one_value_are_linear(self):
        import time

        from wflib import check

        text = "Bearer " + "token" * 200000        # ≈1MB，全部同一行同一值
        started = time.perf_counter()
        masked = check.redact_text(text)
        elapsed = time.perf_counter() - started
        self.assertLess(elapsed, 5.0, f"redact_text took {elapsed:.2f}s on {len(text)} bytes")
        self.assertNotIn("token", masked)


class QuotedCredentialMaskTest(unittest.TestCase):
    """九轮复审 a-P0：引号值形态（Bearer "…"、--flag "多词"）此前完全漏遮。

    窗口扩展到值是对的，但**模式集没跟上**：`Bearer\\s+[^\\s"',;]+` 排除引号、flag 形态的
    `\\S+` 只吃到 `"my`。窗口算到了 ≠ 窗口掩掉了。
    """

    def test_bearer_with_quoted_value(self):
        from wflib import check

        masked = check.redact_text('Authorization: Bearer "eyJhbGciOiJIUzI1NiJ9.payload.sig"')
        self.assertNotIn("eyJhbGci", masked)
        self.assertIn("***", masked)

    def test_flag_with_quoted_multiword_value(self):
        from wflib import check

        for quote in ('"', "'"):
            text = f"run --token {quote}my secret value here{quote}"
            masked = check.redact_text(text)
            self.assertNotIn("secret value", masked, quote)
            self.assertNotIn("here", masked, quote)

    def test_adjacent_fields_both_masked(self):
        from wflib import check

        text = '{"token":"ab","password":"' + "P" * 300 + '"}'
        masked = check.redact_text(text)
        self.assertNotIn('"ab"', masked)
        self.assertNotIn("P" * 20, masked)

    def test_quoted_multiword_value(self):
        from wflib import check

        masked = check.redact_text('password: "FIRST SECOND THIRD"')
        self.assertNotIn("SECOND", masked)
        self.assertNotIn("THIRD", masked)

    def test_private_key_block(self):
        from wflib import check

        text = "-----BEGIN RSA PRIVATE KEY-----\nMIIEow\nAAAA\n-----END RSA PRIVATE KEY-----"
        masked = check.redact_text(text)
        self.assertNotIn("MIIEow", masked)
        self.assertIn("***", masked)


class MaterialsRedactionTest(unittest.TestCase):
    """九轮复审 b-2：审查材料是外发物，生成时必须脱敏（日志已脱敏推不出材料已脱敏）。"""

    def test_diff_and_prd_are_redacted(self):
        import sys as _sys

        _sys.path.insert(0, str(PAYLOAD / "lib"))
        from wflib import review, tasks

        material_text = 'diff --git a/x b/x\n+api_key = "sk-live-abcdefghijklmnop"\n'
        prd_text = "验收：password: hunter2 不得入库\n"
        with tempfile.TemporaryDirectory(prefix="wf-w9-mat-") as tmp:
            out = os.path.join(tmp, "materials")
            os.makedirs(out)
            ctx = type("C", (), {"root": tmp})()
            delivery = {"paths": ["x"], "buckets": {"e": ["x"], "f": [], "covered_f": [],
                                                    "uncovered_f": []}}
            material_facts = {"text": material_text, "files": [], "problems": [],
                              "empty": False, "diff_base": "HEAD"}
            with mock.patch.object(review, "materialize_delivery",
                                   lambda *a, **k: material_facts), \
                    mock.patch.object(tasks, "read_prd", lambda *a, **k: prd_text,
                                      create=True):
                facts = review.write_materials(ctx, {"id": "t1"}, 1, {"check_anchor": "x"},
                                               out, paths=["x"], delivery=delivery)
            diff = Path(out, "diff.patch").read_text(encoding="utf-8")
            prd = Path(out, "prd.md").read_text(encoding="utf-8")
            status = json.loads(Path(out, "status.json").read_text(encoding="utf-8"))
        self.assertNotIn("sk-live-abcdefghijklmnop", diff)
        self.assertNotIn("hunter2", prd)
        self.assertTrue(status["redacted"])
        self.assertIsNotNone(facts)


class UninstallHookMembersTest(unittest.TestCase):
    """九轮复审 b-3：卸载只摘掉 entry 内**本脚本成员**，同组用户命令必须保留。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="wf-w9-uninstall-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        (self.root / ".codex").mkdir()
        self.hooks = self.root / ".codex/hooks.json"
        sys.path.insert(0, str(PAYLOAD / "bin"))
        import uninstall as uninstall_mod
        self.uninstall = uninstall_mod

    def _write(self, payload):
        self.hooks.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def test_user_member_in_same_entry_survives(self):
        ours = {"type": "command", "command": install.host_hook_command(HOOK_REL), "timeout": 15}
        user = {"type": "command", "command": "user-owned-session-hook", "timeout": 5}
        self._write({"hooks": {"SessionStart": [{"hooks": [ours, user]}]}})
        removed = self.uninstall.remove_hooks_json_entry(str(self.root))
        data = json.loads(self.hooks.read_text(encoding="utf-8"))
        members = data["hooks"]["SessionStart"][0]["hooks"]
        self.assertEqual(removed, 1)
        self.assertEqual([m["command"] for m in members], ["user-owned-session-hook"])

    def test_entry_with_only_ours_is_dropped(self):
        ours = {"type": "command", "command": install.host_hook_command(HOOK_REL), "timeout": 15}
        self._write({"hooks": {"SessionStart": [{"hooks": [ours]}]}})
        removed = self.uninstall.remove_hooks_json_entry(str(self.root))
        data = json.loads(self.hooks.read_text(encoding="utf-8"))
        self.assertEqual(removed, 1)
        self.assertEqual(data["hooks"]["SessionStart"], [])


class HookMatcherTest(unittest.TestCase):
    """九轮复审 b-4：matcher 也是触发条件，限定成 compact 等于会话启动不触发。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="wf-w9-matcher-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        (self.root / ".codex/hooks").mkdir(parents=True)
        (self.root / ".codex/hooks/wf-session-identity.py").write_text("# hook\n", encoding="utf-8")

    def _hooks_path(self):
        return self.root / ".codex/hooks.json"

    def _command(self):
        return install.host_hook_command(install.HOOK_SCRIPT_RELATIVE)

    def test_matcher_restricted_entry_is_conflict(self):
        command = self._command()
        self._hooks_path().write_text(json.dumps(
            {"hooks": {"SessionStart": [{"matcher": "compact",
                                          "hooks": [{"type": "command", "command": command,
                                                     "timeout": 15}]}]}}), encoding="utf-8")
        plan = install.plan_hooks_json(str(self.root), install.HOOK_SCRIPT_RELATIVE, command)
        self.assertEqual(plan["action"], "conflict")
        self.assertEqual(plan["matcher"], "compact")

    def test_matcher_restricted_entry_fails_self_check(self):
        command = self._command()
        self._hooks_path().write_text(json.dumps(
            {"hooks": {"SessionStart": [{"matcher": "compact",
                                          "hooks": [{"type": "command", "command": command,
                                                     "timeout": 15}]}]}}), encoding="utf-8")
        manifest = {"assets": [{"source_path": "x", "target_class": "host_hook",
                                "target_relative": install.HOOK_SCRIPT_RELATIVE,
                                "platform": "codex", "kind": "hook", "required": True,
                                "file_kind": "file", "executable": False,
                                "digest": install.file_digest(
                                    str(self.root / ".codex/hooks/wf-session-identity.py"))}]}
        problems = install.self_check(str(self.root), manifest, [])
        self.assertTrue(any(item.get("reason") == "host hook entry missing or drifted"
                            for item in problems), problems)


class ReleaseTagHintTest(unittest.TestCase):
    """九轮复审 b-6：修复命令必须是 `git tag <名字>`，不是 `git tag refs/tags/<名字>`。"""

    def test_hint_uses_tag_name_only(self):
        import importlib.util as _ilu

        spec = _ilu.spec_from_file_location("verify_release",
                                            REPO / "scripts" / "verify-wf-release.py")
        module = _ilu.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.verify(str(REPO), "0.1.7", "refs/tags/wf-v0.1.7",
                               source_check=lambda *a: {"name": "x", "ok": True, "facts": {}})
        exits = result["checks"][0].get("exits") or []
        joined = " ".join(exits)
        self.assertIn("git tag wf-v0.1.7", joined)
        self.assertNotIn("git tag refs/tags/", joined)


class HumanSignListTest(unittest.TestCase):
    """九轮复审：人签封闭清单要覆盖既有的人判对象（manual 验证、工作流人判点）。"""

    def test_design_lists_manual_verification_and_human_points(self):
        design = (REPO / "docs/workflows/wf-framework-design.md").read_text(encoding="utf-8")
        self.assertIn("手工验证结论", design)
        self.assertIn("human_points", design)

    def test_mechanical_revision_boundary_is_stated(self):
        design = (REPO / "docs/workflows/wf-framework-design.md").read_text(encoding="utf-8")
        self.assertIn("首次批准本身", design)
        self.assertIn("只是排版/转义", design)


class RedactionPropertyMatrixTest(unittest.TestCase):
    """十轮复审 a-P1：遮罩测试改为**由规则集派生的性质矩阵**，不再手挑样例。

    手挑样例的失败模式已连续五轮验证：每轮都能找到一个"没被样例覆盖"的分隔符/引号/长度变体。
    这里对每个文档化形态 × 分隔符变体 × 值长 × 引号形态做笛卡尔积，断言"值不出现在输出里"；
    新增一条规则时，把形态加进 `FORMS` 就会被自动覆盖。

    生成的值都带唯一哨兵（`ZK9`），因此断言不依赖字母集合，也不会被键/前缀自身的字符干扰。
    """

    MARKER = "ZK9SECRETVALUE"

    def _value(self, length):
        return (self.MARKER * ((length // len(self.MARKER)) + 2))[:length]

    def _forms(self, value):
        q = '"' + value + '"'
        sq = "'" + value + "'"
        return {
            "bearer-space": f"Bearer {value}",
            "bearer-eq": f"Bearer = {value}",
            "bearer-colon": f"Bearer: {value}",
            "bearer-quoted": f"Bearer {q}",
            "authorization": f"Authorization: Bearer {value}",
            "authorization-quoted": f"Authorization: Bearer {q}",
            "token-eq": f"token={value}",
            "token-space": f"token {value}",
            "token-colon-spaced": f"token : {value}",
            "token-tab": f"token\t=\t{value}",
            "token-json": '{"token": "' + value + '"}',
            "token-quoted-space": f'token = "{value}"',
            "token-single-quoted": f"token = {sq}",
            "api-key-flag": f"--api-key {value}",
            "api-key-flag-eq": f"--api-key={value}",
            "client-secret": f"client_secret: {value}",
            "access-token-suffix": '{"access_token_value": "' + value + '"}',
            "private-key-name": f"private_key = {value}",
            "chinese": f"口令：{value}",
            "url-userinfo": f"https://user:{value}@host/path",
        }

    def test_every_documented_form_hides_the_value(self):
        from wflib import check

        failures = []
        for length in (12, 40, 1200):
            value = self._value(length)
            for name, text in self._forms(value).items():
                masked = check.redact_text(text)
                if value in masked:
                    failures.append(f"{name} (len={length}) -> {masked[:60]!r}")
        self.assertFalse(failures, "\n".join(failures))

    def _expression_forms(self):
        """非字面量的赋值形态：材料档必须保留（reviewer 要能判断"取的是哪个值"）。"""
        return {
            "token-call": "token = read_from_store()",
            "password-attr": "password = self.secret",
            "api-key-index": "api_key = os.environ['X']",
            "password-const": "password = DEFAULT_PASSWORD",
            "token-version": "api_key_version = 2",
        }

    def test_every_documented_form_hides_the_value_in_materials(self):
        """材料档：字面量形态**必须遮**，表达式形态**必须保留**——两边都是有用断言。

        上一版这段是恒真断言：`assertEqual(material, material)`，材料档零防护，
        白名单还与实现脱节（十三轮 b-P0）。
        """
        from wflib import check

        value = self._value(40)
        failures = []
        for name, text in self._forms(value).items():
            full = check.redact_text(text)
            material = check.redact_material(text)
            if value in full:
                failures.append(f"全量档未遮：{name} -> {full[:60]!r}")
            if value in material:
                failures.append(f"材料档漏遮：{name} -> {material[:60]!r}")
        self.assertFalse(failures, "\n".join(failures))

    def test_expression_forms_stay_readable_in_materials(self):
        from wflib import check

        for name, text in self._expression_forms().items():
            self.assertEqual(check.redact_material(text), text, name)
            self.assertNotEqual(check.redact_text(text), text, f"全量档应遮：{name}")

    def test_material_level_keeps_code_calls_readable(self):
        """b-3：材料要能审代码——`password = read_from_store()` 不是凭据，不能被掩。"""
        from wflib import check

        for line in ("password = read_from_store()",
                     "token = request.headers.get('X-Token')",
                     "secret = os.environ['APP_SECRET']",
                     "the token in this sentence"):
            self.assertEqual(check.redact_material(line), line)

    def test_escaped_quotes_do_not_leak_the_tail(self):
        from wflib import check

        text = 'password: "abc\\"def' + self.MARKER + '"'
        masked = check.redact_text(text)
        self.assertNotIn(self.MARKER, masked)

    def test_separator_is_not_consumed_as_value(self):
        """a-P0 的回归形态：`token = value` 不得只掩掉 `=`。"""
        from wflib import check

        for text in ("token = abc123secret", "token : abc123secret",
                     "--token = abc123secret", "Bearer = eyJabc.payload.sig"):
            masked = check.redact_text(text)
            self.assertNotIn("abc123secret", masked, text)
            self.assertNotIn("eyJabc", masked, text)

    def test_prose_is_not_over_masked(self):
        """裸前缀只遮"看起来像凭据"的不透明串，散文不能被掩成 `***`。"""
        from wflib import check

        for line in ("the token in this sentence", "the bearer of bad news",
                     "digest of the report"):
            self.assertEqual(check.redact_text(line), line)


class ManualDecisionContentBindingTest(unittest.TestCase):
    """十轮复审 b-1（人工验证）：决定必须绑定人看到的**交付内容**，不能只绑规划版本。"""

    def _manual(self, content_digest, decisions):
        from wflib import check

        verification = {"id": "v1", "invocation": {"kind": "manual"}, "required": True}
        plan = {"version": 3, "approval": {"object_digest": "sha256:prd"}}
        return check._manual_command(verification, decisions, "sha256:anchor", plan, 3,
                                     content_digest)

    def test_stale_digest_does_not_satisfy(self):
        entry = self._manual("sha256:content-new", [{
            "choice": "passed", "subject": "v1", "plan_version": 3,
            "content_digest": "sha256:content-old", "source": "human"}])
        self.assertEqual(entry["status"], "not_run")
        self.assertIn("not bound to current content", entry["summary"])
        self.assertEqual(entry["stale_decision"]["current_content_digest"], "sha256:content-new")

    def test_matching_digest_satisfies(self):
        entry = self._manual("sha256:content-new", [{
            "choice": "passed", "subject": "v1", "plan_version": 3,
            "content_digest": "sha256:content-new", "source": "human"}])
        self.assertEqual(entry["status"], "passed")
        self.assertEqual(entry["decision"]["choice"], "passed")

    def test_missing_digest_does_not_satisfy(self):
        entry = self._manual("sha256:content-new", [{
            "choice": "passed", "subject": "v1", "plan_version": 3, "source": "human"}])
        self.assertEqual(entry["status"], "not_run")


class MechanicalRevisionDigestTest(unittest.TestCase):
    """十轮复审 b-1（机械修订）：草稿预填的 object_digest 必须在入口被核对。"""

    def test_stale_object_digest_is_rejected(self):
        from wflib import records, tasks

        with tempfile.TemporaryDirectory(prefix="wf-w10-mech-") as tmp:
            task_dir = Path(tmp, ".wf/tasks/11-01-t-1")
            task_dir.mkdir(parents=True)
            Path(task_dir, "prd.md").write_text("current prd\n", encoding="utf-8")
            Path(task_dir, "task.json").write_text(json.dumps({"id": "11-01-t-1"}),
                                                   encoding="utf-8")
            ctx = type("C", (), {"root": tmp})()
            task = {"id": "11-01-t-1", "status": "in_progress", "phase": "plan",
                    "plan": {"approval": {"object_digest": "sha256:old"},
                             "approved_version": 1, "version": 1}}
            with self.assertRaises(tasks.TaskError) as caught:
                tasks._mechanical_revision(ctx, str(task_dir), task, {"kind": "session"},
                                           {"object_digest": "sha256:stale", "reason": "排版"},
                                           [])
            self.assertEqual(caught.exception.code, "WF_SEMANTIC_DECISION")
            facts = caught.exception.facts
            self.assertEqual(facts["declared_object_digest"], "sha256:stale")
            self.assertIn("current_object_digest", facts)


class MaterialLogIdentityTest(unittest.TestCase):
    """十轮复审 b-2：日志必须**先核身份再进材料包**（外发面不允许"事后标注"）。"""

    def test_unreferenced_and_tampered_logs_never_reach_the_package(self):
        import sys as _sys

        _sys.path.insert(0, str(PAYLOAD / "lib"))
        from wflib import records, review

        with tempfile.TemporaryDirectory(prefix="wf-w10-logs-") as tmp:
            root = Path(tmp)
            task_dir = root / ".wf/tasks/t-1"
            log_dir = task_dir / "check-logs/2026-01-01T000000"
            log_dir.mkdir(parents=True)
            good = log_dir / "good.log"
            good.write_text("ok output\n", encoding="utf-8")
            (log_dir / "tampered.log").write_text("changed\n", encoding="utf-8")
            (log_dir / "stray.log").write_text("never referenced\n", encoding="utf-8")
            (task_dir / "task.json").write_text(json.dumps({"id": "t-1"}), encoding="utf-8")
            materials = root / "materials"
            materials.mkdir()
            ctx = type("C", (), {"root": str(root)})()
            task = {"id": "t-1", "baseline_head": None,
                    "check": {"id": "c1", "started_at": "2026-01-01T00:00:00", "commands": [
                        {"verification_id": "a", "evidence_ref": "check-logs/2026-01-01T000000/good.log",
                         "log_digest": records.file_digest(str(good))},
                        {"verification_id": "b", "evidence_ref": "check-logs/2026-01-01T000000/tampered.log",
                         "log_digest": "sha256:" + "0" * 64}]}}
            with mock.patch.object(review, "materialize_delivery",
                                   lambda *a, **k: {"text": "", "files": [], "problems": [],
                                                    "empty": True, "diff_base": "HEAD"}), \
                    mock.patch.object(sys.modules["wflib.tasks"], "read_prd",
                                      lambda *a, **k: "", create=True):
                review.write_materials(ctx, task, 1, {"check_anchor": "x"}, str(materials),
                                       paths=[], delivery={"paths": [],
                                                           "buckets": {"e": [], "f": [],
                                                                       "covered_f": [],
                                                                       "uncovered_f": []}})
            copied = sorted(item.name for item in (materials / "check-logs").iterdir())
            status = json.loads((materials / "status.json").read_text(encoding="utf-8"))
        self.assertEqual(copied, ["good.log"])
        reasons = [item["reason"] for item in status["problems"]]
        self.assertTrue(any("not referenced" in reason for reason in reasons), reasons)
        self.assertTrue(any("digest mismatch" in reason for reason in reasons), reasons)


class ReviewBindingByAnchorTest(unittest.TestCase):
    """十轮复审 b-5：重跑 Check 得到同内容锚点时，不必整轮重审。"""

    def _task(self, review_anchor, check_anchor, tmp):
        from wflib import records

        report = Path(tmp, "report.md")
        report.write_text("report\n", encoding="utf-8")
        digest = records.file_digest(str(report))
        return {"check": {"id": "c2", "anchor": {"check_anchor": check_anchor}},
                "reviews": {"result": {"check_id": "c1", "round": 1,
                                       "anchor": {"check_id": "c1",
                                                  "check_anchor": review_anchor},
                                       "imported": [{"slot": "a", "report_digest": digest}]},
                            "imported": [{"round": 1, "slot": "a", "report_digest": digest,
                                          "report_path": "report.md"}],
                            "launches": []}}

    def test_same_anchor_survives_new_check_id(self):
        from wflib import gates

        with tempfile.TemporaryDirectory(prefix="wf-w10-bind-") as tmp:
            ctx = type("C", (), {"root": tmp})()
            judgment = gates.review_binding(ctx, self._task("sha256:same", "sha256:same", tmp))
        self.assertTrue(judgment["binding"], judgment)

    def test_different_anchor_still_rejects(self):
        from wflib import gates

        with tempfile.TemporaryDirectory(prefix="wf-w10-bind2-") as tmp:
            ctx = type("C", (), {"root": tmp})()
            judgment = gates.review_binding(ctx, self._task("sha256:old", "sha256:new", tmp))
        self.assertFalse(judgment["binding"])
        self.assertEqual(judgment["code"], "WF_REVIEW_INVALID")


class MaterialLevelLiteralTest(unittest.TestCase):
    """十一轮复审 a-P0/b-3：材料级要**接进生产路径**且遮住最常见的字面凭据形态。

    早前 `redact_material` 只有测试在用（`write_materials` 仍调全量档），而材料档本身
    又把非引号键值整条排除——`.env` 里的 `API_KEY=abcdefgh123456` 会明文外发。
    """

    def test_env_style_literal_is_masked(self):
        from wflib import check

        for text in ("API_KEY=abcdefgh123456", "password: hunter2",
                     "DB_PASSWORD=s3cr3t-value", "--api-key abc123secret"):
            self.assertNotIn("abcdefgh123456", check.redact_material(text))
            self.assertIn("***", check.redact_material(text), text)

    def test_expressions_stay_readable_in_materials(self):
        from wflib import check

        for text in ("password = read_from_store()", "password = self.secret",
                     "token = os.environ['X']", "password = load_default()"):
            self.assertEqual(check.redact_material(text), text)

    def test_materials_use_the_material_level(self):
        """生产路径按**文件类型**选档：代码文件用材料级（调用可审）、配置类用全量（不泄漏）。

        b-3 的"调用要能读"与 a-1 的"config.yaml 裸凭据必须遮"只能靠分片同时满足；
        这里断言生产路径走的是分片实现，而不是某单一档位。
        """
        source = (PAYLOAD / "lib/wflib/review.py").read_text(encoding="utf-8")
        self.assertIn("redact_patch(diff_text)", source)
        self.assertNotIn("redact_text(diff_text)", source)
        helper = (PAYLOAD / "lib/wflib/check.py").read_text(encoding="utf-8")
        self.assertIn("def redact_for_path(path, text):", helper)
        self.assertIn('"diff": "per-file', source)


class MaterialsReviewRecordRedactionTest(unittest.TestCase):
    """十一轮复审 b-2：tests.json 里的命令记录（含人工验证的 decision 理由）也要遮。"""

    def test_decision_text_in_commands_is_redacted(self):
        import sys as _sys

        _sys.path.insert(0, str(PAYLOAD / "lib"))
        from wflib import review

        with tempfile.TemporaryDirectory(prefix="wf-w11-mat-") as tmp:
            root = Path(tmp)
            task_dir = root / ".wf/tasks/t-1"
            task_dir.mkdir(parents=True)
            (task_dir / "task.json").write_text(json.dumps({"id": "t-1"}), encoding="utf-8")
            materials = root / "materials"
            materials.mkdir()
            ctx = type("C", (), {"root": str(root)})()
            task = {"id": "t-1", "baseline_head": None,
                    "check": {"id": "c1", "started_at": "2026-01-01T00:00:00", "commands": [
                        {"verification_id": "v1", "status": "passed", "summary": "manual decision",
                         "decision": {"choice": "passed", "reason": "人确认 API_KEY=abcdefgh123456"}}]}}
            with mock.patch.object(review, "materialize_delivery",
                                   lambda *a, **k: {"text": "", "files": [], "problems": [],
                                                    "empty": True, "diff_base": "HEAD"}), \
                    mock.patch.object(sys.modules["wflib.tasks"], "read_prd",
                                      lambda *a, **k: "", create=True):
                review.write_materials(ctx, task, 1, {"check_anchor": "x"}, str(materials),
                                       paths=[], delivery={"paths": [],
                                                           "buckets": {"e": [], "f": [],
                                                                       "covered_f": [],
                                                                       "uncovered_f": []}})
            tests = (materials / "tests.json").read_text(encoding="utf-8")
        self.assertNotIn("abcdefgh123456", tests)
        self.assertIn("***", tests)


class StaleMaterialLogCleanupTest(unittest.TestCase):
    """十一轮复审 b-2（第二处）：重生成材料时，上次复制的日志不得留在新包。"""

    def test_previous_copy_is_removed_when_no_longer_eligible(self):
        import sys as _sys

        _sys.path.insert(0, str(PAYLOAD / "lib"))
        from wflib import review

        with tempfile.TemporaryDirectory(prefix="wf-w11-stale-") as tmp:
            root = Path(tmp)
            task_dir = root / ".wf/tasks/t-1"
            (task_dir / "check-logs/2026-01-01T000000").mkdir(parents=True)
            (task_dir / "task.json").write_text(json.dumps({"id": "t-1"}), encoding="utf-8")
            (task_dir / "check-logs/2026-01-01T000000/good.log").write_text(
                "tampered\n", encoding="utf-8")
            materials = root / "materials"
            (materials / "check-logs").mkdir(parents=True)
            (materials / "check-logs/good.log").write_text("old copy\n", encoding="utf-8")
            ctx = type("C", (), {"root": str(root)})()
            task = {"id": "t-1", "baseline_head": None,
                    "check": {"id": "c1", "started_at": "2026-01-01T00:00:00", "commands": [
                        {"verification_id": "v1", "evidence_ref": "check-logs/2026-01-01T000000/good.log",
                         "log_digest": "sha256:" + "0" * 64}]}}
            with mock.patch.object(review, "materialize_delivery",
                                   lambda *a, **k: {"text": "", "files": [], "problems": [],
                                                    "empty": True, "diff_base": "HEAD"}), \
                    mock.patch.object(sys.modules["wflib.tasks"], "read_prd",
                                      lambda *a, **k: "", create=True):
                review.write_materials(ctx, task, 1, {"check_anchor": "x"}, str(materials),
                                       paths=[], delivery={"paths": [],
                                                           "buckets": {"e": [], "f": [],
                                                                       "covered_f": [],
                                                                       "uncovered_f": []}})
            leftovers = list((materials / "check-logs").iterdir())
        self.assertEqual(leftovers, [], "旧副本必须清掉")


class DirectHumanAcceptanceBindingTest(unittest.TestCase):
    """十一轮复审 b-1（第二处）：直接人判验收项也要绑定交付内容。"""

    def test_stale_direct_acceptance_is_not_covered(self):
        from wflib import check

        plan = {"version": 2, "approval": {"object_digest": "sha256:prd"},
                "acceptance": [{"id": "a1", "verification_ids": []}]}
        decisions = [{"choice": "passed", "subject": "a1", "plan_version": 2,
                      "content_digest": "sha256:old", "source": "human"}]
        results = check._acceptance_results(type("C", (), {"root": "/tmp"})(),
                                            {"plan": plan}, [], decisions, "sha256:a",
                                            "sha256:new")
        self.assertNotEqual(results[0]["conclusion"], "passed")

    def test_matching_content_is_covered(self):
        from wflib import check

        plan = {"version": 2, "approval": {"object_digest": "sha256:prd"},
                "acceptance": [{"id": "a1", "verification_ids": []}]}
        decisions = [{"choice": "passed", "subject": "a1", "plan_version": 2,
                      "content_digest": "sha256:new", "source": "human"}]
        results = check._acceptance_results(type("C", (), {"root": "/tmp"})(),
                                            {"plan": plan}, [], decisions, "sha256:a",
                                            "sha256:new")
        self.assertEqual(results[0]["conclusion"], "passed")


class EmptyCommandsValidityTest(unittest.TestCase):
    """十一轮复审 b-6：纯人判验收（无验证项）不是"commands 缺失"。"""

    def _check(self, verifications):
        return {"result": "pass", "anchor": {"rule_version": "v", "check_anchor": "sha256:x"},
                "commands": [], "acceptance_results": [], "plan_version": 1,
                "internal_review": {"standard": {"conclusion": "pass"},
                                    "requirement": {"conclusion": "pass"}}}

    def test_empty_commands_allowed_without_declared_verifications(self):
        from wflib import check

        problems = check.validate_check_result({"plan": {"verifications": []}},
                                              self._check([]))
        command_problems = [item for item in problems if item.get("field") == "commands"]
        self.assertFalse(command_problems)

    def test_empty_commands_still_rejected_when_verifications_declared(self):
        from wflib import check

        problems = check.validate_check_result(
            {"plan": {"verifications": [{"id": "v1", "required": True}]}}, self._check(None))
        command_problems = [item for item in problems if item.get("field") == "commands"]
        self.assertTrue(command_problems, problems)


class MaterialLevelChineseAndAssignmentTest(unittest.TestCase):
    """十二轮 a-P0：中文键与 `Bearer =`/`Basic =` 赋值必须与键值形态同口径（材料级也遮）。"""

    def test_chinese_key_masked_in_materials(self):
        from wflib import check

        for text in ("口令：abcdef12345678", "密码 = abc12345678", "令牌：tok1234567890"):
            self.assertNotIn("abc12345678", check.redact_material(text))
            self.assertNotIn("tok1234567890", check.redact_material(text))
            self.assertIn("***", check.redact_material(text), text)

    def test_bearer_assignment_masked_in_materials(self):
        from wflib import check

        for text in ("Bearer = eyJhbGciOiJIUzI1NiJ9.payload.sig",
                     "Basic = dXNlcjpwYXNzd29yZA==",
                     "token: abc123def456"):
            self.assertNotIn("eyJhbGci", check.redact_material(text))
            self.assertNotIn("dXNlcjpw", check.redact_material(text))
            self.assertNotIn("abc123def456", check.redact_material(text))

    def test_constant_reference_and_version_not_masked(self):
        from wflib import check

        for text in ("password = DEFAULT_PASSWORD", "api_key_version = 2",
                     "token = some_identifier"):
            self.assertEqual(check.redact_material(text), text)


class MaterialsSingleWriteRedactionTest(unittest.TestCase):
    """十二轮 b-1：材料只写一次脱敏结果——不得"先写原文再覆写"。"""

    def test_quote_bearing_decision_is_redacted_and_json_stays_valid(self):
        import sys as _sys

        _sys.path.insert(0, str(PAYLOAD / "lib"))
        from wflib import review

        with tempfile.TemporaryDirectory(prefix="wf-w12-mat-") as tmp:
            root = Path(tmp)
            task_dir = root / ".wf/tasks/t-1"
            task_dir.mkdir(parents=True)
            (task_dir / "task.json").write_text(json.dumps({"id": "t-1"}), encoding="utf-8")
            materials = root / "materials"
            materials.mkdir()
            ctx = type("C", (), {"root": str(tmp)})()
            task = {"id": "t-1", "baseline_head": None,
                    "check": {"id": "c1", "started_at": "2026-01-01T00:00:00", "commands": [
                        {"verification_id": "v1", "status": "passed", "summary": "manual decision",
                         "decision": {"choice": "passed",
                                      "reason": '人确认 "口令：abcdef12345678" 与 API_KEY=abc12345678 匹配'}}]}}
            with mock.patch.object(review, "materialize_delivery",
                                   lambda *a, **k: {"text": "", "files": [], "problems": [],
                                                    "empty": True, "diff_base": "HEAD"}), \
                    mock.patch.object(sys.modules["wflib.tasks"], "read_prd",
                                      lambda *a, **k: "", create=True):
                review.write_materials(ctx, task, 1, {"check_anchor": "x"}, str(materials),
                                       paths=[], delivery={"paths": [],
                                                           "buckets": {"e": [], "f": [],
                                                                       "covered_f": [],
                                                                       "uncovered_f": []}})
            text = (materials / "tests.json").read_text(encoding="utf-8")
            payload = json.loads(text)          # 结构必须仍是合法 JSON
        self.assertNotIn("abcdef12345678", text)
        self.assertNotIn("abc12345678", text)
        self.assertEqual(payload["commands"][0]["verification_id"], "v1")

    def test_source_has_no_second_write_path(self):
        source = (PAYLOAD / "lib/wflib/review.py").read_text(encoding="utf-8")
        self.assertIn("redact_commands(commands)", source)
        self.assertNotIn("redact_material(json.dumps", source)


class RoundIdentitySameAnchorTest(unittest.TestCase):
    """十二轮 b-3：同锚点重跑 Check 时，轮次身份与 next 提示都不该要求重开一轮。"""

    def test_round_anchor_identity_accepts_same_anchor_new_check_id(self):
        from wflib import review

        task = {"check": {"id": "c2", "anchor": {"check_anchor": "sha256:same"}}}
        problems = review.anchor_identity_problems(
            {"check_id": "c1", "check_anchor": "sha256:same"}, task)
        self.assertEqual(problems, [])

    def test_round_anchor_identity_rejects_different_anchor(self):
        from wflib import review

        task = {"check": {"id": "c2", "anchor": {"check_anchor": "sha256:new"}}}
        problems = review.anchor_identity_problems(
            {"check_id": "c1", "check_anchor": "sha256:old"}, task)
        self.assertTrue(problems)

    def test_next_hint_recognises_reusable_review(self):
        import sys as _sys

        _sys.path.insert(0, str(PAYLOAD / "lib"))
        from wflib import tasks

        task = {"plan": {"complexity": "complex"},
                "check": {"id": "c2", "result": "pass",
                          "anchor": {"check_anchor": "sha256:same"}},
                "reviews": {"result": {"verdict": "pass",
                                       "anchor": {"check_id": "c1",
                                                  "check_anchor": "sha256:same"}}}}
        # 门禁不认绑定时（无导入报告）不能请人收工：要给"重新导入/换一轮"的出口
        hint = tasks.check_next_hint(task, task["check"], ctx=None)
        self.assertIn("不再绑定", hint)
        self.assertNotIn("可请人直接 finish", hint)


class OptionalVerificationOnlyTest(unittest.TestCase):
    """十二轮 b-4：只有可选且未被引用的验证项时，空 commands 不是缺陷。"""

    def test_optional_only_plan_allows_empty_commands(self):
        from wflib import check

        check_record = {"result": "pass",
                        "anchor": {"rule_version": "v", "check_anchor": "sha256:x"},
                        "commands": [], "acceptance_results": [], "plan_version": 1,
                        "internal_review": {"standard": {"conclusion": "pass"},
                                            "requirement": {"conclusion": "pass"}}}
        task = {"plan": {"verifications": [{"id": "v0", "required": False}],
                         "acceptance": [{"id": "a1", "verification_ids": []}]}}
        problems = check.validate_check_result(task, check_record)
        self.assertFalse([item for item in problems if item.get("field") == "commands"])

    def test_referenced_optional_verification_still_requires_run(self):
        from wflib import check

        check_record = {"result": "pass",
                        "anchor": {"rule_version": "v", "check_anchor": "sha256:x"},
                        "commands": [], "acceptance_results": [], "plan_version": 1,
                        "internal_review": {"standard": {"conclusion": "pass"},
                                            "requirement": {"conclusion": "pass"}}}
        task = {"plan": {"verifications": [{"id": "v0", "required": False}],
                         "acceptance": [{"id": "a1", "verification_ids": ["v0"]}]}}
        problems = check.validate_check_result(task, check_record)
        self.assertTrue([item for item in problems if item.get("field") == "commands"])


class MaterialResidualRiskBoundaryTest(unittest.TestCase):
    """十三轮 b-P1：材料档的**残余风险边界**必须有显式断言 + 协议登记。

    判据要求裸值"含至少一个数字"，于是纯字母裸凭据（`token = mysecretpassword`）
    在材料档不遮。这是声明取舍（保 `DEFAULT_PASSWORD` 这类常量引用可读），不是疏忽——
    所以它必须被**测试固定**并被 `redaction.json` 登记，而不是只写在实现注释里。
    """

    def test_pure_alpha_bare_value_is_not_masked_in_materials(self):
        from wflib import check

        text = "token = mysecretpassword"
        self.assertEqual(check.redact_material(text), text)     # 声明面
        self.assertNotEqual(check.redact_text(text), text)      # 全量档仍然遮

    def test_residual_risk_is_registered_in_protocol(self):
        import json as _json

        protocol = _json.loads((PAYLOAD / "protocol/redaction.json").read_text(encoding="utf-8"))
        entry = next(item for item in protocol["rules"]
                     if item.get("id") == "material-literal-heuristic")
        self.assertIn("纯字母", entry["residual_risk"])
        # 十四轮后残余面收窄为"仅代码类文件"，且每个外发面的档位必须写明
        self.assertIn("代码类文件", entry["residual_risk"])
        self.assertEqual(set(entry["surfaces"]), {"diff.patch", "prd.md", "tests.json"})


class StructuredFieldNameMaskTest(unittest.TestCase):
    """十三轮 a-2：结构化脱敏不能丢字段名语义（`{"password": "<纯字母>"}` 仍须遮）。"""

    def test_secret_named_field_value_is_masked(self):
        from wflib import check

        redacted = check.redact_object({"password": "purelettershere",
                                        "reason": "人确认 password 为 purelettershere"})
        self.assertEqual(redacted["password"], "***")

    def test_non_secret_fields_are_left_alone(self):
        from wflib import check

        redacted = check.redact_object({"token_count": 3, "token_version": "v2",
                                        "task": "t-1"})
        self.assertEqual(redacted, {"token_count": 3, "token_version": "v2", "task": "t-1"})


class MaterialsWriteCountTest(unittest.TestCase):
    """十三轮 a-1：tests.json 只允许写一次，且必须是脱敏后的内容。"""

    def test_tests_json_is_written_exactly_once_redacted(self):
        import sys as _sys

        _sys.path.insert(0, str(PAYLOAD / "lib"))
        from wflib import review

        writes = []
        real = review.records.write_json

        def spy(path, payload, **kwargs):
            if os.path.basename(str(path)) == "tests.json":
                writes.append(json.dumps(payload, ensure_ascii=False))
            return real(path, payload, **kwargs)

        with tempfile.TemporaryDirectory(prefix="wf-w13-mat-") as tmp:
            root = Path(tmp)
            task_dir = root / ".wf/tasks/t-1"
            task_dir.mkdir(parents=True)
            (task_dir / "task.json").write_text(json.dumps({"id": "t-1"}), encoding="utf-8")
            materials = root / "materials"
            materials.mkdir()
            ctx = type("C", (), {"root": str(root)})()
            task = {"id": "t-1", "baseline_head": None,
                    "check": {"id": "c1", "started_at": "2026-01-01T00:00:00", "commands": [
                        {"verification_id": "v1", "status": "passed",
                         "decision": {"choice": "passed",
                                      "reason": "人确认 API_KEY=abc12345678 与口令：hunter2 匹配"}}]}}
            with mock.patch.object(review, "materialize_delivery",
                                   lambda *a, **k: {"text": "", "files": [], "problems": [],
                                                    "empty": True, "diff_base": "HEAD"}), \
                    mock.patch.object(sys.modules["wflib.tasks"], "read_prd",
                                      lambda *a, **k: "", create=True), \
                    mock.patch.object(review.records, "write_json", spy):
                review.write_materials(ctx, task, 1, {"check_anchor": "x"}, str(materials),
                                       paths=[], delivery={"paths": [],
                                                           "buckets": {"e": [], "f": [],
                                                                       "covered_f": [],
                                                                       "uncovered_f": []}})
        self.assertEqual(len(writes), 1, f"tests.json 被写 {len(writes)} 次")
        self.assertNotIn("abc12345678", writes[0])
        self.assertNotIn("hunter2", writes[0])


class PerFilePatchRedactionTest(unittest.TestCase):
    """十四轮 a-1：材料 diff 按**文件类型**选档——配置类全量，代码类只遮字面量。

    整份 diff 用单档只能二选一：全量档让 `password = read_from_store()` 不可审，
    材料档让 `config.yaml` 里的裸凭据随材料外发（实测过）。
    """

    def _patch(self):
        return (
            "diff --git a/src/app.py b/src/app.py\n"
            "+++ b/src/app.py\n"
            "+password = read_from_store()\n"
            "+API_KEY = \"abcdef123456\"\n"
            "diff --git a/config.yaml b/config.yaml\n"
            "+++ b/config.yaml\n"
            "+api_key: mysecretpassword\n"
            "diff --git a/.env b/.env\n"
            "+++ b/.env\n"
            "+TOKEN=mysecretpassword\n"
        )

    def test_config_files_are_fully_masked(self):
        import sys as _sys

        _sys.path.insert(0, str(PAYLOAD / "lib"))
        from wflib import review

        redacted = review.redact_patch(self._patch())
        self.assertNotIn("mysecretpassword", redacted)
        # 代码文件里的调用保持可审（性质不变）
        self.assertIn("password = read_from_store()", redacted)
        self.assertNotIn("abcdef123456", redacted)

    def test_is_config_path_covers_common_suffixes(self):
        import sys as _sys

        _sys.path.insert(0, str(PAYLOAD / "lib"))
        from wflib import check

        for path in ("config.yaml", "app.ini", "prod.toml", "x.properties", ".env",
                     ".env.local", "terraform.tfvars", "secrets.json", "id_rsa.pem"):
            self.assertTrue(check.is_config_path(path), path)
        for path in ("src/app.py", "README.md", "wf.py", "src/config_loader.py"):
            self.assertFalse(check.is_config_path(path), path)

    def test_status_declares_the_policy(self):
        source = (PAYLOAD / "lib/wflib/review.py").read_text(encoding="utf-8")
        self.assertIn('"redaction": {"diff": "per-file', source)


class DefaultRequestAnchorReuseTest(unittest.TestCase):
    """十四轮 a-2：默认请求必须带 `check_anchor`，否则同锚点复用在真实路径上永不生效。"""

    def test_default_request_includes_check_anchor(self):
        import sys as _sys

        _sys.path.insert(0, str(PAYLOAD / "lib"))
        from wflib import review

        with tempfile.TemporaryDirectory(prefix="wf-w14-req-") as tmp:
            root = Path(tmp)
            task_dir = root / ".wf/tasks/t-1"
            task_dir.mkdir(parents=True)
            (task_dir / "task.json").write_text(json.dumps({"id": "t-1"}), encoding="utf-8")
            (task_dir / "prd.md").write_text("# prd\n", encoding="utf-8")
            ctx = type("C", (), {"root": str(root)})()
            task = {"id": "t-1", "baseline_head": "abc",
                    "entry_snapshot": {"touch_paths": ["src/a.py"]},
                    "plan": {"touch_paths": ["src/a.py"]},
                    "check": {"id": "c9", "anchor": {"check_anchor": "sha256:zzz"},
                              "commands": []}}
            with mock.patch.object(review.scope_mod, "delivery_set",
                                   lambda *a, **k: {"paths": ["src/a.py"],
                                                    "buckets": {"e": [], "f": [],
                                                                "covered_f": [], "uncovered_f": []}}):
                request = review.default_launch_request(ctx, task)
        self.assertEqual(request["submitted_scope"]["test_results"]["check_anchor"],
                         "sha256:zzz")


class StartVerificationTimeoutTest(unittest.TestCase):
    """十四轮 a-3：开工验证在项目锁内跑，必须跟随 `verification_timeout_seconds`。"""

    def test_timeout_is_passed_to_subprocess(self):
        import sys as _sys

        _sys.path.insert(0, str(PAYLOAD / "lib"))
        from wflib import tasks

        calls = {}

        def fake_run(argv, **kwargs):
            calls.update(kwargs)

            class Result:
                returncode = 0
                stdout = ""
                stderr = ""
            return Result()

        ctx = type("C", (), {"root": "/tmp"})()
        plan = {"verifications": [{"id": "v1", "required": True, "consume_at": "start",
                                   "invocation": {"kind": "argv", "argv": ["/bin/true"]}}]}
        with mock.patch.object(tasks.subprocess, "run", fake_run), \
                mock.patch("wflib.check.verification_timeout", return_value=7):
            tasks._run_start_verifications(ctx, {"plan": plan})
        self.assertEqual(calls.get("timeout"), 7)

    def test_timeout_failure_is_reported_not_raised_as_traceback(self):
        import sys as _sys

        _sys.path.insert(0, str(PAYLOAD / "lib"))
        from wflib import tasks

        def fake_run(argv, **kwargs):
            raise tasks.subprocess.TimeoutExpired(argv, kwargs.get("timeout"))

        ctx = type("C", (), {"root": "/tmp"})()
        plan = {"verifications": [{"id": "v1", "required": True, "consume_at": "start",
                                   "invocation": {"kind": "argv", "argv": ["/bin/sleep"]}}]}
        with mock.patch.object(tasks.subprocess, "run", fake_run):
            with self.assertRaises(tasks.TaskError) as caught:
                tasks._run_start_verifications(ctx, {"plan": plan})
        self.assertEqual(caught.exception.code, "WF_CHECK_FAILED")
        self.assertIn("timed out", json.dumps(caught.exception.facts, ensure_ascii=False))


class CommandRecordRedactionTest(unittest.TestCase):
    """十五轮 b-P0：命令记录里 argv 的分离写法凭据不得比入库记录更宽。

    `redact_argv`（入库记录）会把 `--password <值>` 的**下一个参数**遮成 `***`；材料档
    逐值遮罩没有位置语义，于是同一凭据在 tests.json 里明文外发——材料比记录宽，顺序倒置。
    """

    def test_separated_flag_value_is_masked_in_materials(self):
        import sys as _sys

        _sys.path.insert(0, str(PAYLOAD / "lib"))
        from wflib import check

        commands = [{"verification_id": "v", "status": "passed",
                     "invocation": {"kind": "argv",
                                    "argv": ["tool", "--password", "mysecretpassword"]},
                     "summary": "tool --password mysecretpassword"}]
        redacted = check.redact_commands(commands)
        self.assertNotIn("mysecretpassword", json.dumps(redacted, ensure_ascii=False))
        self.assertEqual(redacted[0]["invocation"]["argv"], ["tool", "--password", "***"])

    def test_pure_alpha_bare_value_in_summary_is_masked(self):
        """命令记录走全量档：`API_KEY=<纯字母>` 也该遮（与代码文件的可读判据不同）。"""
        import sys as _sys

        _sys.path.insert(0, str(PAYLOAD / "lib"))
        from wflib import check

        redacted = check.redact_commands([{"summary": "API_KEY=abcdefghijklmnopqrstuvwxyz"}])
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz", redacted[0]["summary"])


class StartTimeoutConfigErrorTest(unittest.TestCase):
    """十五轮 a-1：非法超时配置必须报错，不得静默退成无超时执行。"""

    def test_invalid_config_raises_instead_of_running_without_timeout(self):
        import sys as _sys

        _sys.path.insert(0, str(PAYLOAD / "lib"))
        from wflib import tasks, check as check_mod, records

        calls = []

        def fake_run(argv, **kwargs):
            calls.append(kwargs)

            class Result:
                returncode = 0
                stdout = ""
                stderr = ""
            return Result()

        ctx = type("C", (), {"root": "/tmp"})()
        plan = {"verifications": [{"id": "v1", "required": True, "consume_at": "start",
                                   "invocation": {"kind": "argv", "argv": ["/bin/true"]}}]}
        with mock.patch.object(tasks.subprocess, "run", fake_run), \
                mock.patch("wflib.check.verification_timeout",
                           side_effect=check_mod.CheckError("WF_RECORD_INVALID",
                                                            {"reason": "invalid"})):
            with self.assertRaises(check_mod.CheckError):
                tasks._run_start_verifications(ctx, {"plan": plan})
        self.assertEqual(calls, [], "配置非法时不得执行命令")


class StaleMaterialLogsWithoutSourceTest(unittest.TestCase):
    """十五轮 a-3：源日志目录不存在时，旧材料副本也必须清掉。"""

    def test_stale_copy_removed_even_when_source_missing(self):
        import sys as _sys

        _sys.path.insert(0, str(PAYLOAD / "lib"))
        from wflib import review

        with tempfile.TemporaryDirectory(prefix="wf-w15-logs-") as tmp:
            root = Path(tmp)
            task_dir = root / ".wf/tasks/t-1"
            task_dir.mkdir(parents=True)
            (task_dir / "task.json").write_text(json.dumps({"id": "t-1"}), encoding="utf-8")
            materials = root / "materials"
            (materials / "check-logs").mkdir(parents=True)
            stale = materials / "check-logs/old.log"
            stale.write_text("expired evidence\n", encoding="utf-8")
            ctx = type("C", (), {"root": str(root)})()
            # 源目录 `check-logs/<started>` 不存在（模拟已删除/不可达）
            task = {"id": "t-1", "baseline_head": None,
                    "check": {"id": "c1", "started_at": "2026-01-01T00:00:00", "commands": []}}
            with mock.patch.object(review, "materialize_delivery",
                                   lambda *a, **k: {"text": "", "files": [], "problems": [],
                                                    "empty": True, "diff_base": "HEAD"}), \
                    mock.patch.object(sys.modules["wflib.tasks"], "read_prd",
                                      lambda *a, **k: "", create=True):
                review.write_materials(ctx, task, 1, {"check_anchor": "x"}, str(materials),
                                       paths=[], delivery={"paths": [],
                                                           "buckets": {"e": [], "f": [],
                                                                       "covered_f": [],
                                                                       "uncovered_f": []}})
            self.assertFalse(stale.exists(), "旧副本必须被清掉")


class QuotedPatchPathTest(unittest.TestCase):
    """十六轮 b-1：Git 的引号/八进制路径必须照样识别出配置文件。

    以前只认裸 `a/`，`"a/\350\256\276..."` 形态解析不出 → 落到"代码文件"档 →
    同一份凭据因文件名而外发。解析不确定时按配置类 **fail-closed**。
    """

    def _patch(self, header):
        return header + "+api_key: abcdefghijklmnopqrstuvwxyz\n"

    def test_escaped_non_ascii_config_path_is_detected(self):
        import sys as _sys

        _sys.path.insert(0, str(PAYLOAD / "lib"))
        from wflib import review

        header = ('diff --git "a/\\350\\256\\276\\347\\275\\256.yaml" '
                  '"b/\\350\\256\\276\\347\\275\\256.yaml"\n')
        self.assertEqual(review._patch_path(header[len("diff --git "):].strip()), "设置.yaml")
        redacted = review.redact_patch(self._patch(header))
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz", redacted)

    def test_unparsable_header_fails_closed(self):
        import sys as _sys

        _sys.path.insert(0, str(PAYLOAD / "lib"))
        from wflib import review

        redacted = review.redact_patch(self._patch("diff --git weird-header\n"))
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz", redacted)

    def test_code_path_stays_readable(self):
        import sys as _sys

        _sys.path.insert(0, str(PAYLOAD / "lib"))
        from wflib import review

        redacted = review.redact_patch("diff --git a/app.py b/app.py\n+password = read_from_store()\n")
        self.assertIn("password = read_from_store()", redacted)


class CommandFieldNameMaskTest(unittest.TestCase):
    """十六轮 b-2：命令记录改 argv 语义后，仍须按字段名遮。"""

    def test_decision_password_field_is_masked(self):
        import sys as _sys

        _sys.path.insert(0, str(PAYLOAD / "lib"))
        from wflib import check

        redacted = check.redact_commands([{"verification_id": "v1",
                                           "decision": {"password": "purelettershere"}}])
        self.assertEqual(redacted[0]["decision"]["password"], "***")

    def test_non_secret_fields_survive(self):
        import sys as _sys

        _sys.path.insert(0, str(PAYLOAD / "lib"))
        from wflib import check

        redacted = check.redact_commands([{"verification_id": "v1", "status": "passed",
                                           "token_count": 2}])
        self.assertEqual(redacted[0]["token_count"], 2)
        self.assertEqual(redacted[0]["verification_id"], "v1")


class OpenRoundContinueHintTest(unittest.TestCase):
    """十六轮 b-3：原轮未判定且锚点未变时，提示继续原轮而不是重新发起。"""

    def test_hint_continues_open_round(self):
        import sys as _sys

        _sys.path.insert(0, str(PAYLOAD / "lib"))
        from wflib import tasks

        task = {"plan": {"complexity": "complex"},
                "check": {"id": "c2", "result": "pass",
                          "anchor": {"check_anchor": "sha256:same"}},
                "reviews": {"launches": [{"round": 1, "anchor": {"check_anchor": "sha256:same"}}],
                            "rounds": [], "result": {}}}
        hint = tasks.check_next_hint(task, task["check"], ctx=None)
        self.assertIn("第 1 轮审查仍在进行", hint)
        self.assertIn("不要重新 review-launch", hint)


class StartVerificationOrderTest(unittest.TestCase):
    """十六轮 b-4：前置条件不成立时不得先跑开工验证命令。"""

    def test_verifications_run_after_prerequisites(self):
        source = (PAYLOAD / "lib/wflib/tasks.py").read_text(encoding="utf-8")
        start = source.index("findings = gates.evaluate(ctx, task, \"before_execute\")")
        run = source.index("start_results = _run_start_verifications(ctx, task)")
        snapshot = source.index('task["entry_snapshot"] = entry')
        self.assertLess(start, run, "门禁必须先于开工验证")
        self.assertLess(run, snapshot, "验证结果要进入口快照之后写盘")


class DevDeployHookDeploymentTest(unittest.TestCase):
    """十七轮 b-1：开发态部署也必须投放 `host_hook`（此前 `.codex/hooks*` 从不落地）。"""

    def test_plan_covers_host_hook_and_record_uses_asset_relative_target(self):
        import importlib.util as _ilu
        import sys as _sys

        _sys.path.insert(0, str(REPO / "scripts"))
        spec = _ilu.spec_from_file_location("dev_deploy", REPO / "scripts" / "wf-dev-deploy.py")
        dev = _ilu.module_from_spec(spec)
        spec.loader.exec_module(dev)
        manifest = {"assets": [
            {"target_class": "skill_root", "target_relative": "wf-start/SKILL.md",
             "source_path": "skills/wf-start/SKILL.md", "digest": "sha256:x"},
            {"target_class": "host_hook", "target_relative": ".codex/hooks/wf-session-identity.py",
             "source_path": "payload/hooks/codex-session-identity.py", "digest": "sha256:y",
             "platform": "codex"},
        ]}
        with tempfile.TemporaryDirectory(prefix="wf-w17-dev-") as tmp:
            writes, problems = dev.plan_deployment(tmp, [str(Path(tmp, ".agents/skills"))], manifest)
        self.assertEqual(problems, [])
        classes = sorted(item["target_class"] for item in writes)
        self.assertEqual(classes, ["host_hook", "skill_root"], "host_hook 必须进部署计划")


class RepoHooksJsonClassificationTest(unittest.TestCase):
    """十七轮 b-3：`.codex/hooks.json` 只在**框架独占**时才算控制记录。"""

    def test_user_added_hook_leaves_control_record(self):
        import sys as _sys

        _sys.path.insert(0, str(PAYLOAD / "lib"))
        from wflib import scope

        with tempfile.TemporaryDirectory(prefix="wf-w17-hooks-") as tmp:
            root = Path(tmp)
            (root / ".wf/install").mkdir(parents=True)
            (root / ".codex").mkdir()
            ours = {"hooks": {"SessionStart": [{"hooks": [
                {"type": "command", "command": "python3 .codex/hooks/wf-session-identity.py"}]}]}}
            (root / ".codex/hooks.json").write_text(json.dumps(ours), encoding="utf-8")
            (root / ".wf/install/installation.json").write_text(json.dumps(
                {"schema_version": 1, "assets": [], "platforms": ["codex"],
                 "host_hook_entries": [{"script_relative": ".codex/hooks/wf-session-identity.py",
                                        "hooks_json_path": ".codex/hooks.json"}]}),
                encoding="utf-8")
            self.assertTrue(scope._hooks_json_is_framework_only(str(root), ".codex/hooks.json"))
            data = json.loads((root / ".codex/hooks.json").read_text(encoding="utf-8"))
            data["hooks"]["Stop"] = [{"hooks": [{"type": "command", "command": "user-own.py"}]}]
            (root / ".codex/hooks.json").write_text(json.dumps(data), encoding="utf-8")
            self.assertFalse(scope._hooks_json_is_framework_only(str(root), ".codex/hooks.json"))


class AcceptedDeviationOnRedeployTest(unittest.TestCase):
    """十七轮 b-4：升级时人确认保留（--keep）的偏离，重跑安装不得当成"本地改过"。

    判据只有一处（`accepted_local_digests`）：自检与重复安装核对共用，避免分叉。
    """

    def test_accepted_deviation_is_not_reported_as_drift(self):
        import importlib.util as _ilu
        import sys as _sys

        _sys.path.insert(0, str(PAYLOAD / "lib"))
        spec = _ilu.spec_from_file_location("install_accept_probe", PAYLOAD / "install.py")
        install_mod = _ilu.module_from_spec(spec)
        spec.loader.exec_module(install_mod)
        with tempfile.TemporaryDirectory(prefix="wf-w17-acc-") as tmp:
            target = Path(tmp)
            (target / ".agents/skills/wf-start").mkdir(parents=True)
            local = target / ".agents/skills/wf-start/SKILL.md"
            local.write_text("local edit\n", encoding="utf-8")
            digest = install_mod.file_digest(str(local))
            installation = {"assets": [{"target": "wf-start/SKILL.md",
                                        "root_ref": str(target / ".agents/skills"),
                                        "digest": "sha256:" + "0" * 64,
                                        "decision": "deviation-kept",
                                        "local_fingerprint": digest}]}
            accepted = install_mod.accepted_local_digests(str(target), installation)
        self.assertEqual(accepted[os.path.normpath(str(local))], digest)

    def test_single_acceptance_rule_shared_by_self_check_and_verify(self):
        source = (PAYLOAD / "install.py").read_text(encoding="utf-8")
        self.assertIn("accepted = accepted_local_digests(", source)
        self.assertIn("accepted.get(os.path.normpath(path)) != actual", source)

