"""W3（三轮 P0-1）：会话身份——`enable --new-session` 轮换与宿主映射四态解析。

断言面（按 implement.md 2.7）：
- new-session：旧对象终态后可轮换（同边界 task-new 绑定新对象成功）；对象在途被拒并给出口；
  旧附件/绑定保留为历史；写权未释放时拒绝；宿主映射条目随轮换移除。
- 四态：①host_resume；②inflight_reuse（在途续用、paused 算在途、archived 不算、
  无绑定文件不算在途走③、instance 回填、实例不符 unresolved）；③host_establish
  （replace_owner 接管、不撞 L1 单主）；④无映射锚点路径。
- status facts 投影 host_mapping（hit/absent/import-error）。
- hook 脚本实跑：写映射、无 .wf 退出、import 失败标记、成功自愈。
- 资产链：安装面向全部平台，.codex/hooks/ 恒投放；hooks.json 合并/幂等/
  只删自己条目、per-asset 平台条件非法组合拒绝。
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import cli, identity_store as store, records, session as session_mod  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


install = _load("w3_install", REPO / "docs/workflows/wf/payload/install.py")
uninstall = _load("w3_uninstall", REPO / "docs/workflows/wf/payload/bin/uninstall.py")


class _Args:
    def __init__(self, argv):
        self.argv = list(argv)

    def value(self, name, default=None):
        if name in self.argv:
            return self.argv[self.argv.index(name) + 1]
        return default

    def flag(self, name):
        return name in self.argv


def _pid_anchor(pid=None):
    return {"kind": "pid", "pid": pid or os.getpid(), "exe": "python3",
            "start": 1000.0, "boot": "b1"}


def _sid_anchor(sid="sid-1"):
    return {"kind": "sid", "sid": sid, "boot": "b1", "sid_start": 900.0}


def _make_ctx(root, anchors, platforms=("codex", "dsh")):
    ctx = cli.Context(str(root), [])
    ctx.command = "enable"

    def _candidates():
        return list(anchors)

    ctx._candidates_patch = mock.patch.object(session_mod, "candidates", _candidates)
    ctx._candidates_patch.start()

    def _platforms(self):
        return list(platforms)

    ctx.platforms = _platforms.__get__(ctx)
    return ctx


class Harness(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".wf").mkdir()
        # 安装记录：platforms 清单
        install_dir = self.root / ".wf" / "install"
        install_dir.mkdir()
        records.write_json(install_dir / "installation.json",
                           {"platforms": list(("codex", "dsh")), "assets": []})
        # 布局检查需要的骨架
        bin_dir = self.root / ".wf" / "bin"
        bin_dir.mkdir()
        (bin_dir / "wf.py").write_text("# stub\n", encoding="utf-8")
        lib_dir = self.root / ".wf" / "lib" / "wflib"
        lib_dir.mkdir(parents=True)
        (lib_dir / "__init__.py").write_text("", encoding="utf-8")
        # 写权空闲
        records.write_json(self.root / ".wf/writer.json",
                           {"schema_version": 1, "id": "writer", "revision": 0,
                            "state": "idle", "generation": 0, "holder": None,
                            "created_at": records.now_str(), "updated_at": records.now_str()})

    def tearDown(self):
        self._tmp.cleanup()

    # ---- 夹具构造 -------------------------------------------------------
    def _establish_wf_session(self, ctx_or_root, anchors):
        root = str(self.root)
        issued = "a" * 32
        key = records.sha256_hex(records.canonical_bytes(
            {"provider": "wf", "identity": {"issued_id": issued}}))
        at = records.now_str()
        attachment = store.new_attachment({"issued_id": issued}, "wf", key,
                                          anchors[-1] if anchors else None,
                                          {"enabled": True, "start_source": "human:enable",
                                           "enabled_at": at}, at)
        store.save_attachment(root, key, attachment)
        routes = store.load_routes(root)
        for item in anchors:
            store.register(routes, session_mod.anchor_key(item), key,
                           "session" if item["kind"] == "sid" else "proc", item["boot"], at)
        store.save_routes(root, routes)
        return key, attachment

    def _bind_task(self, session_key, task_id="t-1", instance_id=None, status="in_progress"):
        directory = self.root / ".wf" / "tasks" / task_id
        directory.mkdir(parents=True, exist_ok=True)
        records.write_json(directory / "task.json",
                           {"id": task_id, "title": "对象", "status": status,
                            "phase": "execute"})
        binding = {"schema_version": 1, "id": session_key,
                   "identity": {"provider": "wf", "value": None},
                   "instance_id": instance_id or "inst-1",
                   "object": {"kind": "task", "id": task_id},
                   "bound_at": records.now_str()}
        store_records_path = self.root / ".wf" / "session-bindings"
        store_records_path.mkdir(parents=True, exist_ok=True)
        records.write_json(store_records_path / f"{session_key}.json", binding)
        return binding

    def _write_mapping(self, session_id="sess-A", host_id="codex"):
        anchor = _pid_anchor()
        key = session_mod.anchor_key(anchor)
        map_dir = self.root / ".wf" / ".runtime" / "host-session-map"
        map_dir.mkdir(parents=True, exist_ok=True)
        records.write_json(map_dir / f"{key}.json",
                           {"provider": "host", "host_id": host_id,
                            "session_id": session_id, "mapped_at": "t",
                            "boot": "b1"})
        return key


class FourStateResolutionTest(Harness):
    """② 在途续用优先：hook 上线/换聊天不夺走在途会话。"""

    def test_state1_host_resume(self):
        anchors = [_pid_anchor()]
        ctx = _make_ctx(self.root, anchors)
        mapping_key = self._write_mapping(session_id="sess-A")
        host_key = session_mod.session_key(
            {"provider": "host", "identity": {"host_id": "codex", "session_id": "sess-A"}})
        at = records.now_str()
        attachment = store.new_attachment({"host_id": "codex", "session_id": "sess-A"},
                                           "host", host_key, anchors[-1],
                                           {"enabled": True, "start_source": "human:enable",
                                            "enabled_at": at}, at)
        store.save_attachment(str(self.root), host_key, attachment)
        resolution = ctx._auto_resolve()
        self.assertEqual(resolution["state"], "host_resume")
        self.assertEqual(resolution["key"], host_key)
        session = ctx.auto_session()
        self.assertEqual(session["provider"], "host")
        facts = cli._identity_facts(ctx, host_key)
        self.assertTrue(facts["host_identity_present"])
        self.assertEqual(facts["session_provider"], "host")
        self.assertNotIn("new_session_indistinguishable", facts)

    def test_state2_inflight_reuse_overrides_host_mapping(self):
        # hook 上线前已有 wf 会话在途：映射命中但 host 无附件 ⇒ 续用在途会话
        anchors = [_pid_anchor()]
        ctx = _make_ctx(self.root, anchors)
        wf_key, _attachment = self._establish_wf_session(ctx, anchors)
        self._bind_task(wf_key, status="in_progress")
        attachment = store.load_attachment(str(self.root), wf_key)
        attachment["instance_expected"] = "inst-1"
        store.save_attachment(str(self.root), wf_key, attachment)
        self._write_mapping(session_id="sess-A")
        resolution = ctx._auto_resolve()
        self.assertEqual(resolution["state"], "inflight_reuse")
        self.assertEqual(resolution["key"], wf_key)
        session = ctx.auto_session()
        self.assertEqual(session["provider"], "wf")   # ②续用时是 wf，不得报 host
        facts = cli._identity_facts(ctx, ctx.key(required=False))
        self.assertEqual(facts["session_provider"], "wf")
        self.assertTrue(facts["host_identity_present"])
        self.assertIn("inflight_reuse", facts)

    def test_state2_paused_counts_as_inflight(self):
        anchors = [_pid_anchor()]
        ctx = _make_ctx(self.root, anchors)
        wf_key, _attachment = self._establish_wf_session(ctx, anchors)
        self._bind_task(wf_key, status="in_progress")
        # 任务 paused ⇒ 仍在途
        task_file = self.root / ".wf" / "tasks" / "t-1" / "task.json"
        task = json.loads(task_file.read_text(encoding="utf-8"))
        task["paused"] = True
        task_file.write_text(json.dumps(task), encoding="utf-8")
        attachment = store.load_attachment(str(self.root), wf_key)
        attachment["instance_expected"] = "inst-1"
        store.save_attachment(str(self.root), wf_key, attachment)
        self._write_mapping(session_id="sess-A")
        resolution = ctx._auto_resolve()
        self.assertEqual(resolution["state"], "inflight_reuse")

    def test_state2_archived_falls_to_state3(self):
        anchors = [_pid_anchor()]
        ctx = _make_ctx(self.root, anchors)
        wf_key, _attachment = self._establish_wf_session(ctx, anchors)
        self._bind_task(wf_key, status="archived")
        self._write_mapping(session_id="sess-A")
        resolution = ctx._auto_resolve()
        self.assertEqual(resolution["state"], "host_establish")

    def test_state2_missing_binding_falls_to_state3(self):
        # 启用未绑定（有附件、无绑定文件）⇒ 不算在途 ⇒ 走③（不卡人裁档）
        anchors = [_pid_anchor()]
        ctx = _make_ctx(self.root, anchors)
        self._establish_wf_session(ctx, anchors)      # 附件在、绑定无
        self._write_mapping(session_id="sess-A")
        resolution = ctx._auto_resolve()
        self.assertEqual(resolution["state"], "host_establish")
        # 接管**启用未绑定**的会话时，enable facts 点明"旧会话路由已让出"
        result = cli.cmd_enable(ctx, _Args(["--json"]))
        established = (result.get("facts") or {}).get("established") or {}
        self.assertIn("route_taken_over_from", established)
        self.assertIn("旧会话路由已让出", json.dumps(established, ensure_ascii=False))

    def test_state2_instance_backfill(self):
        # 历史会话 instance_expected=None：以 binding.instance_id 回填附件
        anchors = [_pid_anchor()]
        ctx = _make_ctx(self.root, anchors)
        wf_key, _attachment = self._establish_wf_session(ctx, anchors)
        self._bind_task(wf_key, instance_id="inst-9")
        self._write_mapping(session_id="sess-A")
        resolution = ctx._auto_resolve()
        self.assertEqual(resolution["state"], "inflight_reuse")
        attachment = store.load_attachment(str(self.root), wf_key)
        self.assertEqual(attachment.get("instance_expected"), "inst-9")   # 回填成功
        session = ctx.auto_session()
        self.assertEqual(session["instance_id"], "inst-9")

    def test_state2_instance_mismatch_is_unresolved(self):
        anchors = [_pid_anchor()]
        ctx = _make_ctx(self.root, anchors)
        wf_key, _attachment = self._establish_wf_session(ctx, anchors)
        self._bind_task(wf_key, instance_id="inst-other")
        attachment = store.load_attachment(str(self.root), wf_key)
        attachment["instance_expected"] = "inst-different"
        store.save_attachment(str(self.root), wf_key, attachment)
        self._write_mapping(session_id="sess-A")
        resolution = ctx._auto_resolve()
        self.assertEqual(resolution["state"], "unresolved")
        self.assertEqual(resolution["evidence"]["reason"], "instance_mismatch")
        # 只读面降级：auto_session 不抛（返回 None），facts 挂 _resolution
        self.assertIsNone(ctx.auto_session())
        self.assertEqual(ctx._resolution["state"], "unresolved")

    def test_state3_clear_new_session_id_takes_over_routes(self):
        # P0-1 目标场景：/clear 换新 session_id，旧对象终态 ⇒ ③建立并接管（不撞 L1 单主）
        anchors = [_sid_anchor("boot-sid"), _pid_anchor()]
        ctx = _make_ctx(self.root, anchors)
        wf_key, _attachment = self._establish_wf_session(ctx, anchors)
        self._bind_task(wf_key, status="archived")
        # 第一次：在途才续用；archived ⇒ 无在途 ⇒ ③
        self._write_mapping(session_id="sess-B")      # /clear 后的新标识
        resolution = ctx._auto_resolve()
        self.assertEqual(resolution["state"], "host_establish")
        # enable 建立并接管：旧 wf owner 被 replace_owner 组更新，无 StoreError
        result = cli.cmd_enable(ctx, _Args(["--json"]))
        facts = result.get("facts") or {}
        host_key = session_mod.session_key(
            {"provider": "host", "identity": {"host_id": "codex", "session_id": "sess-B"}})
        routes = store.load_routes(str(self.root))
        for key in (session_mod.anchor_key(item) for item in anchors):
            self.assertIn(host_key, store.owners_of(routes, key))
            self.assertNotIn(wf_key, store.owners_of(routes, key))
        # 接管事实随 enable 回显可见（established 投影），不静默丢弃
        established = facts.get("established") or {}
        self.assertIn("route_taken_over_from", established)

    def test_state4_no_mapping_anchor_path_unchanged(self):
        anchors = [_pid_anchor()]
        ctx = _make_ctx(self.root, anchors)
        wf_key, _ = self._establish_wf_session(ctx, anchors)
        resolution = ctx._auto_resolve()
        self.assertEqual(resolution["state"], "anchor_resume")
        self.assertEqual(resolution["key"], wf_key)

    def test_mapping_host_id_not_installed_falls_back_to_anchor(self):
        anchors = [_pid_anchor()]
        ctx = _make_ctx(self.root, anchors)
        wf_key, _ = self._establish_wf_session(ctx, anchors)
        self._write_mapping(session_id="sess-A", host_id="unknown-host")
        resolution = ctx._auto_resolve()
        self.assertEqual(resolution["state"], "anchor_resume")   # 回落，不丢会话
        self.assertIn("host_mapping_rejected", resolution["evidence"])


class NewSessionRotationTest(Harness):
    """W3-1：`enable --new-session`。"""

    def test_rotate_after_terminal_then_task_new_binds_new_object(self):
        anchors = [_pid_anchor()]
        ctx = _make_ctx(self.root, anchors)
        wf_key, _ = self._establish_wf_session(ctx, anchors)
        self._bind_task(wf_key, status="archived")
        result = cli.cmd_enable(ctx, _Args(["--new-session", "--json"]))
        facts = result.get("facts") or {}
        self.assertTrue(facts["rotated"])
        self.assertEqual(facts["old_session_key"], wf_key)
        new_key = facts["session_key"]
        self.assertNotEqual(new_key, wf_key)
        # 旧附件/绑定保留为历史
        self.assertTrue((self.root / ".wf/.runtime/attachments" / f"{wf_key}.json").is_file())
        self.assertTrue((self.root / ".wf/session-bindings" / f"{wf_key}.json").is_file())
        # 无映射场景轮换后仍无映射（removed_host_mapping 为空是事实，不伪造）
        self.assertEqual(facts.get("removed_host_mapping"), [])
        # 路由指向新会话：同边界 task-new 解析到新会话（不再绑旧对象）
        ctx2 = _make_ctx(self.root, anchors)
        session = ctx2.auto_session()
        self.assertEqual(session["identity"]["issued_id"], facts["issued_id"])

    def test_rotate_rejected_while_object_inflight(self):
        anchors = [_pid_anchor()]
        ctx = _make_ctx(self.root, anchors)
        wf_key, _ = self._establish_wf_session(ctx, anchors)
        self._bind_task(wf_key, status="in_progress")
        attachment = store.load_attachment(str(self.root), wf_key)
        attachment["instance_expected"] = "inst-1"
        store.save_attachment(str(self.root), wf_key, attachment)
        with self.assertRaises(cli.CliError) as caught:
            cli.cmd_enable(ctx, _Args(["--new-session", "--json"]))
        self.assertEqual(caught.exception.code, "WF_BINDING_MISMATCH")
        self.assertIn("task-abandon", json.dumps(caught.exception.facts, ensure_ascii=False))

    def test_rotate_rejected_when_writer_held(self):
        anchors = [_pid_anchor()]
        ctx = _make_ctx(self.root, anchors)
        wf_key, _ = self._establish_wf_session(ctx, anchors)
        self._bind_task(wf_key, status="archived")
        records.write_json(self.root / ".wf/writer.json",
                           {"state": "held", "generation": 3,
                            "holder": {"kind": "session", "id": wf_key}})
        with self.assertRaises(cli.CliError) as caught:
            cli.cmd_enable(ctx, _Args(["--new-session", "--json"]))
        self.assertEqual(caught.exception.code, "WF_WRITER_BUSY")
        self.assertIn("writer release", caught.exception.next or "")


class HostMappingVisibilityTest(Harness):
    def test_status_projects_hit_absent_import_error(self):
        anchors = [_pid_anchor()]
        ctx = _make_ctx(self.root, anchors)
        self._establish_wf_session(ctx, anchors)
        # absent
        result = cli.cmd_status(ctx, _Args(["--json"]))
        self.assertEqual(result["facts"]["host_mapping"]["status"], "absent")
        # hit
        self._write_mapping(session_id="sess-A")
        result = cli.cmd_status(ctx, _Args(["--json"]))
        self.assertEqual(result["facts"]["host_mapping"]["status"], "hit")
        self.assertEqual(result["facts"]["host_mapping"]["session_id"], "sess-A")
        # import-error（删掉映射、写标记）
        anchor = _pid_anchor()
        key = session_mod.anchor_key(anchor)
        (self.root / ".wf/.runtime/host-session-map" / f"{key}.json").unlink()
        records.write_json(self.root / ".wf/.runtime/host-session-map" / "import-error",
                           {"at": "t", "error": "ImportError"})
        result = cli.cmd_status(ctx, _Args(["--json"]))
        self.assertEqual(result["facts"]["host_mapping"]["status"], "import-error")
        self.assertEqual(result["facts"]["host_mapping"]["import_error"], "ImportError")

    def test_store_remove_host_map_clears_entries_and_marker(self):
        anchors = [_pid_anchor()]
        keys = [session_mod.anchor_key(a) for a in anchors]
        self._write_mapping()
        map_dir = self.root / ".wf/.runtime/host-session-map"
        records.write_json(map_dir / "import-error", {"at": "t"})
        removed = store.remove_host_map(str(self.root), keys)
        self.assertEqual(len(removed), 1)
        self.assertFalse((map_dir / "import-error").is_file())
        self.assertEqual(store.load_host_map(str(self.root), keys)["status"], "absent")


class HookScriptTest(Harness):
    """hook 实跑：部署落点、映射写入、非 wf 项目退出、import 失败标记、成功自愈。"""

    def _deploy_hook(self, project, with_lib=True):
        hooks_dir = project / ".codex" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        script = hooks_dir / "wf-session-identity.py"
        shutil_src = REPO / "docs/workflows/wf/payload/hooks/codex-session-identity.py"
        script.write_text(shutil_src.read_text(encoding="utf-8"), encoding="utf-8")
        if with_lib:
            lib = project / ".wf" / "lib"
            if not lib.exists():
                lib.symlink_to(REPO / "docs/workflows/wf/payload/lib", target_is_directory=True)
        return script

    def test_hook_writes_mapping_and_selfheals(self):
        project = self.root / "proj"
        project.mkdir()
        (project / ".wf").mkdir()
        script = self._deploy_hook(project)
        # 先制造 import-error：移走 lib 再跑 → 写标记
        (project / ".wf/lib").unlink()
        (project / ".wf").rmdir()
        (project / ".wf").mkdir()
        # 没有 .wf/lib 也能跑：hook import wflib 失败 → import-error 标记
        proc = subprocess.run(
            [sys.executable, "-I", str(script)],
            input=json.dumps({"session_id": "sess-X"}),
            capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        map_dir = project / ".wf/.runtime/host-session-map"
        self.assertTrue((map_dir / "import-error").is_file(), "失败必须可见")
        # 恢复 lib 再跑：成功写映射 ⇒ 标记消失（恢复即自愈）
        (project / ".wf/lib").symlink_to(REPO / "docs/workflows/wf/payload/lib",
                                         target_is_directory=True)
        proc = subprocess.run(
            [sys.executable, "-I", str(script)],
            input=json.dumps({"session_id": "sess-Y"}),
            capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse((map_dir / "import-error").is_file(), "成功后标记必须消失")
        payloads = [json.loads((map_dir / name).read_text(encoding="utf-8"))
                    for name in os.listdir(map_dir) if name.endswith(".json")]
        self.assertTrue(payloads)
        for payload in payloads:
            self.assertEqual(payload["host_id"], "codex")
            self.assertEqual(payload["session_id"], "sess-Y")

    def test_hook_exits_silently_without_wf(self):
        project = self.root / "plain"
        project.mkdir()
        hooks_dir = project / ".codex" / "hooks"
        hooks_dir.mkdir(parents=True)
        script = hooks_dir / "wf-session-identity.py"
        script.write_text((REPO / "docs/workflows/wf/payload/hooks/codex-session-identity.py")
                          .read_text(encoding="utf-8"), encoding="utf-8")
        proc = subprocess.run([sys.executable, "-I", str(script)],
                               input=json.dumps({"session_id": "s"}),
                               capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(os.listdir(project), [".codex"], "非 wf 项目不写任何文件")


class HostHookAssetChainTest(Harness):
    """资产链：per-asset 平台条件投放 + hooks.json 合并/幂等/只删自己。"""

    HOOK_ASSET = {"source_path": "payload/hooks/codex-session-identity.py",
                  "target_class": "host_hook",
                  "target_relative": ".codex/hooks/wf-session-identity.py",
                  "kind": "hook", "required": True, "file_kind": "file",
                  "executable": True, "digest": "sha256:" + "0" * 64,
                  "platform": "codex"}

    def test_plan_deploys_every_hook_asset(self):
        """安装面向全部平台：清单里的 hook 资产一律投放（platform 键只表示归属，不是筛选）。"""
        manifest_payload = {"assets": [dict(self.HOOK_ASSET)]}
        skill_root = str(self.root / ".agents/skills")
        writes, problems = install.plan_writes(str(self.root), [skill_root], manifest_payload)
        self.assertEqual(problems, [])
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0][2], ".codex/hooks/wf-session-identity.py")

    def test_illegal_platform_combinations_rejected(self):
        skill_root = str(self.root / ".agents/skills")
        # platform 出现在非 host_hook 资产 → 拒
        bad = {"assets": [dict(self.HOOK_ASSET, target_class="project_wf",
                               target_relative=".wf/x.py")]}
        writes, problems = install.plan_writes(str(self.root), [skill_root], bad)
        self.assertEqual(writes, [])
        self.assertTrue(any("only allowed on host_hook" in json.dumps(p) for p in problems))
        # host_hook 缺 platform → 拒
        bad2 = {"assets": [dict(self.HOOK_ASSET)]}
        bad2["assets"][0].pop("platform")
        writes, problems = install.plan_writes(str(self.root), [skill_root], bad2)
        self.assertEqual(writes, [])
        self.assertTrue(any("requires a platform" in json.dumps(p) for p in problems))
        # host_hook 平台名不在 PLATFORMS → 拒
        bad3 = {"assets": [dict(self.HOOK_ASSET, platform="no-such-platform")]}
        writes, problems = install.plan_writes(str(self.root), [skill_root], bad3)
        self.assertEqual(writes, [])
        self.assertTrue(any("not a known platform" in json.dumps(p) for p in problems))

    def _hook_plan(self, command=None):
        return install.plan_hooks_json(str(self.root), install.HOOK_SCRIPT_RELATIVE,
                                       command or install.host_hook_command(
                                           install.HOOK_SCRIPT_RELATIVE))

    def test_hooks_json_plan_apply_idempotent_and_conflict(self):
        """2026-11-23 五轮：`merge_hooks_json` 已删除（升级/首装/追加平台共用
        `plan_hooks_json` + `apply_hooks_json`），本断言随之锚到真实路径。"""
        applied = install.apply_hooks_json(str(self.root), self._hook_plan())
        self.assertEqual(applied, "created")
        self.assertEqual(install.apply_hooks_json(str(self.root), self._hook_plan()), "unchanged")
        data = json.loads((self.root / ".codex/hooks.json").read_text(encoding="utf-8"))
        entries = data["hooks"]["SessionStart"]
        self.assertEqual(len(entries), 1)
        # 已有用户条目：保序追加，不动用户内容（重建为只含用户条目的文件）
        user_entry = {"hooks": [{"type": "command", "command": "python3 my.py"}]}
        install._dump_json(install.hooks_json_path(str(self.root)),
                            {"hooks": {"SessionStart": [user_entry]}})
        self.assertEqual(install.apply_hooks_json(str(self.root), self._hook_plan()), "appended")
        data = json.loads((self.root / ".codex/hooks.json").read_text(encoding="utf-8"))
        self.assertEqual(len(data["hooks"]["SessionStart"]), 2)
        self.assertEqual(data["hooks"]["SessionStart"][0], user_entry)   # 用户条目原样
        # 同名脚本被不同命令串占用 → 判定为 conflict（交人，不覆盖）
        data["hooks"]["SessionStart"][-1]["hooks"][0]["command"] = "sh other-runner wf-session-identity.py"
        install._dump_json(install.hooks_json_path(str(self.root)), data)
        plan = self._hook_plan()
        self.assertEqual(plan["action"], "conflict")
        self.assertEqual(install.apply_hooks_json(str(self.root), plan), "conflict")
        unchanged = json.loads((self.root / ".codex/hooks.json").read_text(encoding="utf-8"))
        self.assertEqual(unchanged["hooks"]["SessionStart"][-1]["hooks"][0]["command"],
                         "sh other-runner wf-session-identity.py")

    def test_uninstall_removes_only_own_hooks_json_entry(self):
        target = str(self.root)
        install.apply_hooks_json(str(self.root), self._hook_plan())
        data = json.loads((self.root / ".codex/hooks.json").read_text(encoding="utf-8"))
        data["hooks"]["SessionStart"].insert(
            0, {"hooks": [{"type": "command", "command": "python3 user-own.py"}]})
        data["hooks"]["UserPromptSubmit"] = [
            {"hooks": [{"type": "command", "command": "python3 other.py"}]}]
        install._dump_json(install.hooks_json_path(target), data)
        removed = uninstall.remove_hooks_json_entry(target)
        self.assertEqual(removed, 1)
        data = json.loads((self.root / ".codex/hooks.json").read_text(encoding="utf-8"))
        commands = [h["command"] for e in data["hooks"]["SessionStart"] for h in e["hooks"]]
        self.assertEqual(commands, ["python3 user-own.py"])            # 用户条目保留
        self.assertEqual(len(data["hooks"]["UserPromptSubmit"][0]["hooks"]), 1)
        self.assertTrue((self.root / ".codex/hooks.json").is_file())   # 文件不删

    def test_uninstall_collects_host_hook_as_project_target(self):
        manifest_payload = {"assets": [dict(self.HOOK_ASSET)]}
        installation = {"roots": [], "platforms": ["codex"]}
        project_targets, skill_targets = uninstall.collect_targets(str(self.root),
                                                                   installation, manifest_payload)
        self.assertIn(".codex/hooks/wf-session-identity.py", project_targets)
        self.assertEqual(skill_targets, [])

    def test_self_check_always_checks_hook_assets(self):
        """全部平台安装：hook 未投放就是缺，不再按平台跳过。"""
        manifest_payload = {"assets": [dict(self.HOOK_ASSET)]}
        skill_root = str(self.root / ".agents/skills")
        problems = install.self_check(str(self.root), manifest_payload, [skill_root])
        self.assertTrue(any("digest mismatch" in json.dumps(p)
                            and "wf-session-identity" in json.dumps(p) for p in problems))


if __name__ == "__main__":
    unittest.main()
