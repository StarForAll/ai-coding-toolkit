"""W3（五轮，b-P1）：升级同批维护宿主 `hooks.json` 条目。

事实面：`host_hook` 是随发行投放的资产类，它的部署面包含宿主 `hooks.json` 条目
（`merge_hooks_json` 在首装与 `add_platforms` 调用）。但升级只替换脚本字节、既不重核
也不合并条目，自检也只核脚本 digest ⇒ 一旦某版改 hook 落点或命令串，已升级项目会带着
失效条目继续跑（退化方向＝会话身份错配），且自检报绿。

本用例锁定：
- 判定顺序：absent / appended / unchanged / updated（上一版登记串）/ conflict（用户改过）/ unreadable；
- 升级在**写入前**拒绝冲突（不先替换脚本字节），预览列出动作；
- 应用段落地并把新命令串写回安装记录 `host_hook_entries`（下一版据此认"我们的旧串"）；
- 自检对"条目缺失/漂移"报 problem（脚本字节对不等于部署面生效）；
- 未声明 codex host_hook 的项目不读不写 hooks.json。
"""

import contextlib
import importlib.util
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
PAYLOAD = REPO / "docs/workflows/wf/payload"
sys.path.insert(0, str(PAYLOAD / "lib"))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


install = _load("w5_install_hooks", PAYLOAD / "install.py")
RELEASED = json.loads((REPO / "docs/workflows/wf-release/wf-release.json").read_text(encoding="utf-8"))

HOOK_REL = ".codex/hooks/wf-session-identity.py"
OLD_COMMAND = "python3 -X utf8 .codex/hooks/wf-session-identity.py"
NEW_REL = ".codex/hooks/wf-session-identity.py"
# "改了命令串"的发行：落点不变、调用形态变化。命令串的唯一来源是
# `host_hook_command()`，所以测试通过替换该函数来模拟"下一版改了调用串"。
CHANGED_COMMAND = "python3 -B -X utf8 .codex/hooks/wf-session-identity.py"


def changed_command(_relative):
    return CHANGED_COMMAND


class _Args:
    def __init__(self, **kwargs):
        self.target = kwargs["target"]
        self.release_ref = "refs/tags/wf-v0.1.7"
        self.source = kwargs.get("source")
        self.json = True
        self.upgrade = True
        self.apply = kwargs.get("apply", False)
        self.platform = []
        self.confirm = False
        self.export_deviations = False
        self.out = None
        self.keep = kwargs.get("keep", [])
        self.restore = []


class HookFixture(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="wf-w3-hooks-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.target = self.root / "proj"
        (self.target / ".wf").mkdir(parents=True)
        shutil.copytree(PAYLOAD / "lib", self.target / ".wf/lib")
        shutil.copytree(PAYLOAD / "protocol", self.target / ".wf/protocol")
        (self.target / ".wf/bin").mkdir(parents=True)
        for name in ("wf.py", "repair.py", "uninstall.py"):
            shutil.copyfile(PAYLOAD / "bin" / name, self.target / ".wf/bin" / name)
        hook = self.target / HOOK_REL
        hook.parent.mkdir(parents=True)
        hook.write_text("# hook body v1\n", encoding="utf-8")
        (self.target / ".wf/writer.json").write_text(json.dumps(
            {"schema_version": 1, "id": "writer", "revision": 0, "state": "idle",
             "generation": 0, "holder": None, "created_at": "t", "updated_at": "t"}),
            encoding="utf-8")
        self.installation = {
            "schema_version": 1, "version": "0.1.6", "release_ref": "refs/tags/wf-v0.1.6",
            "source_commit": "c0ffee", "platforms": ["codex"], "roots": [],
            "host_hook_entries": [{"platform": "codex", "script_relative": HOOK_REL,
                                   "command": OLD_COMMAND, "updated_at": "t"}],
            "assets": [{"target": HOOK_REL, "root_ref": "project",
                        "digest": install.file_digest(str(hook)), "source_path": "wf-release/hooks/x",
                        "upstream_version": "0.1.6"}],
        }
        install_dir = self.target / ".wf/install"
        install_dir.mkdir()
        (install_dir / "installation.json").write_text(
            json.dumps(self.installation, ensure_ascii=False, indent=2), encoding="utf-8")
        (self.target / ".gitignore").write_text("", encoding="utf-8")
        self.source = self.root / "checkout"
        (self.source / "wf-release/hooks").mkdir(parents=True)
        self.source_hook = self.source / "wf-release/hooks/wf-session-identity.py"
        self.source_hook.write_text("# hook body v2\n", encoding="utf-8")
        self.manifest = {
            "version": "0.1.7",
            "compatibility": {"rules_digest": "sha256:rules"},
            "required_steps": RELEASED["required_steps"],
            "delivery_round": RELEASED["delivery_round"],
            "gitignore_managed": {"begin_marker": "# wf-managed-v1",
                                  "end_marker": "# wf-managed-end",
                                  "lines": ["/.wf-lock"]},
            "assets": [{"source_path": "wf-release/hooks/wf-session-identity.py",
                        "target_class": "host_hook", "target_relative": HOOK_REL,
                        "platform": "codex", "kind": "hook", "required": True,
                        "file_kind": "file", "executable": True,
                        "digest": install.file_digest(str(self.source_hook))}],
        }
        (self.source / "wf-release.json").write_text(
            json.dumps(self.manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # --- helpers ---------------------------------------------------------
    def _hooks_path(self):
        return self.target / ".codex/hooks.json"

    def _write_hooks(self, command, extra=None):
        entry = {"hooks": [{"type": "command", "command": command, "timeout": 15}]}
        data = {"hooks": {"SessionStart": [entry] + list(extra or [])}}
        self._hooks_path().parent.mkdir(parents=True, exist_ok=True)
        self._hooks_path().write_text(json.dumps(data, ensure_ascii=False, indent=2),
                                      encoding="utf-8")

    def _commands(self):
        data = json.loads(self._hooks_path().read_text(encoding="utf-8"))
        return [hook.get("command")
                for entry in data["hooks"].get("SessionStart") or []
                for hook in entry.get("hooks") or []]

    def _run(self, args, commit="deadbeef"):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = install.run_upgrade(args, self.manifest, commit)
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

    def _apply(self, args, commit="deadbeef"):
        fake_stdin = mock.Mock()
        fake_stdin.isatty.return_value = True
        fake_stdin.readline.return_value = "token\n"
        with mock.patch.object(install.PreviewToken, "confirm", return_value=True), \
                mock.patch("sys.stdin", fake_stdin):
            return self._run(args, commit)


class PlanTest(HookFixture):
    def test_absent_when_no_file(self):
        self.assertFalse(self._hooks_path().exists())
        plan = install.plan_hooks_json(str(self.target), HOOK_REL, OLD_COMMAND)
        self.assertEqual(plan["action"], "absent")

    def test_unchanged_when_command_matches(self):
        self._write_hooks(OLD_COMMAND)
        plan = install.plan_hooks_json(str(self.target), HOOK_REL, OLD_COMMAND)
        self.assertEqual(plan["action"], "unchanged")

    def test_updated_when_command_is_previous_release(self):
        self._write_hooks(OLD_COMMAND)
        plan = install.plan_hooks_json(str(self.target), HOOK_REL, CHANGED_COMMAND,
                                       previous_command=OLD_COMMAND)
        self.assertEqual(plan["action"], "updated")

    def test_conflict_when_user_changed_command(self):
        user_command = "python3 -X utf8 .codex/hooks/wf-session-identity.py --extra"
        self._write_hooks(user_command)
        plan = install.plan_hooks_json(str(self.target), HOOK_REL,
                                       install.host_hook_command(NEW_REL),
                                       previous_command=OLD_COMMAND)
        self.assertEqual(plan["action"], "conflict")
        self.assertEqual(plan["observed"], [user_command])

    def test_conflict_without_previous_record_is_not_silently_updated(self):
        """旧安装记录没有上一版串时，条目非当前值一律交人——不猜"那是我们的旧串"。"""
        self._write_hooks("python3 -X utf8 .codex/hooks/wf-session-identity.py --legacy")
        plan = install.plan_hooks_json(str(self.target), HOOK_REL,
                                       install.host_hook_command(NEW_REL))
        self.assertEqual(plan["action"], "conflict")

    def test_unreadable_file_is_reported(self):
        self._hooks_path().parent.mkdir(parents=True, exist_ok=True)
        self._hooks_path().write_text("{not json", encoding="utf-8")
        plan = install.plan_hooks_json(str(self.target), HOOK_REL, OLD_COMMAND)
        self.assertEqual(plan["action"], "unreadable")

    def test_apply_appends_without_touching_user_entries(self):
        user_entry = {"hooks": [{"type": "command", "command": "echo user", "timeout": 5}]}
        self._write_hooks(OLD_COMMAND, extra=[user_entry])
        plan = install.plan_hooks_json(str(self.target), HOOK_REL, CHANGED_COMMAND,
                                       previous_command=OLD_COMMAND)
        applied = install.apply_hooks_json(str(self.target), plan)
        self.assertEqual(applied, "updated")
        data = json.loads(self._hooks_path().read_text(encoding="utf-8"))
        entries = data["hooks"]["SessionStart"]
        self.assertEqual(entries[1], user_entry, "用户条目必须原样保留")
        self.assertEqual(self._commands()[0], CHANGED_COMMAND)


class UpgradeIntegrationTest(HookFixture):
    def test_preview_lists_hooks_action(self):
        self._write_hooks(OLD_COMMAND)
        with mock.patch.object(install, "host_hook_command", changed_command):
            code, payload, text = self._run(_Args(target=str(self.target),
                                                 source=str(self.source)))
        self.assertEqual(payload["code"], "WF_OK", text)
        hooks = payload["facts"]["preview"]["hooks_json"]
        self.assertEqual([item["action"] for item in hooks], ["updated"])
        self.assertIn(".codex/hooks.json updated", text)

    def test_unchanged_command_previews_noop(self):
        self._write_hooks(OLD_COMMAND)
        code, payload, text = self._run(_Args(target=str(self.target), source=str(self.source)))
        self.assertEqual(payload["code"], "WF_OK", text)
        self.assertEqual([item["action"] for item in payload["facts"]["preview"]["hooks_json"]],
                         ["unchanged"])

    def test_conflict_blocks_before_writing_assets(self):
        user_command = "python3 -X utf8 .codex/hooks/wf-session-identity.py --mine"
        self._write_hooks(user_command)
        before = (self.target / HOOK_REL).read_text(encoding="utf-8")
        with mock.patch.object(install, "host_hook_command", changed_command):
            code, payload, text = self._run(_Args(target=str(self.target),
                                                 source=str(self.source), apply=True))
        self.assertNotEqual(code, 0)
        self.assertEqual(payload["code"], "WF_ASSET_DECISION")
        self.assertEqual(payload["tier"], "needs_decision")
        self.assertEqual((self.target / HOOK_REL).read_text(encoding="utf-8"), before,
                         "冲突必须在替换脚本字节之前拦住")
        self.assertEqual(self._commands(), [user_command])

    def test_apply_updates_entry_and_records_command(self):
        self._write_hooks(OLD_COMMAND)
        with mock.patch.object(install, "host_hook_command", changed_command):
            code, payload, text = self._apply(_Args(target=str(self.target),
                                                   source=str(self.source), apply=True))
        self.assertEqual(payload["code"], "WF_OK", text)
        self.assertEqual(self._commands(), [CHANGED_COMMAND])
        installation = json.loads(
            (self.target / ".wf/install/installation.json").read_text(encoding="utf-8"))
        self.assertEqual(installation["version"], "0.1.7")
        recorded = installation["host_hook_entries"]
        self.assertEqual(recorded[0]["command"], CHANGED_COMMAND)

    def test_apply_creates_entry_when_missing(self):
        code, payload, text = self._apply(_Args(target=str(self.target), source=str(self.source),
                                               apply=True))
        self.assertEqual(payload["code"], "WF_OK", text)
        self.assertEqual(self._commands(), [install.host_hook_command(NEW_REL)])

    def test_apply_is_idempotent(self):
        self._write_hooks(OLD_COMMAND)
        self._apply(_Args(target=str(self.target), source=str(self.source), apply=True))
        # 第二版：命令串不变 ⇒ unchanged；条目不被重复追加
        self.manifest["version"] = "0.1.8"
        (self.source / "wf-release.json").write_text(
            json.dumps(self.manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        code, payload, text = self._apply(_Args(target=str(self.target), source=str(self.source),
                                               apply=True))
        self.assertEqual(payload["code"], "WF_OK", text)
        self.assertEqual(self._commands(), [install.host_hook_command(NEW_REL)])

    def test_user_owned_hooks_json_entries_are_preserved(self):
        """安装面向全部平台：升级会确保本框架条目存在，但**不动用户自己的条目**。"""
        user_entry = {"hooks": [{"type": "command", "command": "user-own-hook", "timeout": 5}]}
        self._hooks_path().write_text(json.dumps({"hooks": {"Stop": [user_entry]}}), encoding="utf-8")
        self.installation["host_hook_entries"] = []
        (self.target / ".wf/install/installation.json").write_text(
            json.dumps(self.installation, ensure_ascii=False, indent=2), encoding="utf-8")
        code, payload, text = self._apply(_Args(target=str(self.target), source=str(self.source),
                                               apply=True))
        self.assertEqual(payload["code"], "WF_OK", text)
        data = json.loads(self._hooks_path().read_text(encoding="utf-8"))
        self.assertEqual(data["hooks"]["Stop"], [user_entry], "用户条目必须原样保留")
        self.assertTrue(data["hooks"].get("SessionStart"), "全部平台安装应写入本框架条目")


class SelfCheckTest(HookFixture):
    def setUp(self):
        super().setUp()
        # 自检要求"脚本字节 = 发行字节"，否则先报 digest mismatch，测不到条目核对
        shutil.copyfile(self.source_hook, self.target / HOOK_REL)

    def _self_check(self):
        return install.self_check(str(self.target), self.manifest, [],
                                 installation=self.installation)

    def test_missing_entry_is_reported(self):
        problems = self._self_check()
        self.assertTrue(any(item.get("reason") == "host hook entry missing or drifted"
                            for item in problems), problems)

    def test_drifted_entry_is_reported(self):
        self._write_hooks("python3 -X utf8 .codex/hooks/wf-session-identity.py --mine")
        with mock.patch.object(install, "host_hook_command", changed_command):
            problems = self._self_check()
        drifted = [item for item in problems
                   if item.get("reason") == "host hook entry missing or drifted"]
        self.assertEqual(len(drifted), 1, problems)
        self.assertEqual(drifted[0]["action"], "conflict")
        self.assertEqual(drifted[0]["expected_command"], CHANGED_COMMAND)

    def test_matching_entry_passes(self):
        self._write_hooks(install.host_hook_command(NEW_REL))
        problems = self._self_check()
        self.assertFalse([item for item in problems
                          if item.get("reason") == "host hook entry missing or drifted"], problems)


if __name__ == "__main__":
    unittest.main()


class HalfInstallStateTest(unittest.TestCase):
    """五轮复审 P1：hooks.json 冲突不得留下半安装态。

    旧顺序：先置 `held`、先写资产，再判 hooks——冲突时直接 return，于是
    ① 首装留下「.wf/ 已建 + 资产已投放 + 无安装记录 + 写权 held」；
    ② 追加平台留下「新资产已写 + 平台/安装记录未更新 + 写权 held」，后续入口全被
       `WF_WRITER_BUSY` 挡住。
    修法：判定（只读）先于任何写入；需要落地的 hook 动作并入"是否还有事要做"，
    使"重跑同一条安装命令"能补齐缺失条目；写入之后才失败的地方统一走
    `maintenance_abort`（recovering 检查点 + 出口），不留 held。
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="wf-w3-halfinstall-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.target = self.root / "proj"
        self.target.mkdir()
        (self.target / ".codex/hooks").mkdir(parents=True)
        (self.target / HOOK_REL).write_text("# hook body\n", encoding="utf-8")
        self.source = self.root / "checkout"
        (self.source / "wf-release/skills/wf-start").mkdir(parents=True)
        (self.source / "wf-release/skills/wf-start/SKILL.md").write_text(
            "---\nname: wf-start\ndescription: x\n---\nbody\n", encoding="utf-8")
        (self.source / "wf-release/hooks").mkdir(parents=True)
        shutil.copyfile(self.target / HOOK_REL, self.source / "wf-release/hooks/x.py")
        self.manifest = {
            "version": "0.1.7",
            "compatibility": {"rules_digest": "sha256:rules"},
            "required_steps": [], "delivery_round": 3,
            "template_markers": [],
            "gitignore_managed": {"begin_marker": "# wf-managed-v1",
                                  "end_marker": "# wf-managed-end",
                                  "lines": ["/.wf-lock"]},
            "assets": [
                {"source_path": "wf-release/skills/wf-start/SKILL.md",
                 "target_class": "skill_root", "target_relative": "wf-start/SKILL.md",
                 "kind": "skill", "required": True, "file_kind": "file", "executable": False,
                 "digest": install.file_digest(str(self.source / "wf-release/skills/wf-start/SKILL.md"))},
                {"source_path": "wf-release/hooks/x.py", "target_class": "host_hook",
                 "target_relative": HOOK_REL, "platform": "codex", "kind": "hook",
                 "required": True, "file_kind": "file", "executable": True,
                 "digest": install.file_digest(str(self.source / "wf-release/hooks/x.py"))},
            ],
        }
        (self.source / "wf-release.json").write_text(
            json.dumps(self.manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        import wflib
        self._patches = [
            mock.patch.object(install, "load_manifest",
                              lambda src: (self.manifest, str(self.source / "wf-release.json"))),
            mock.patch.object(install, "verify_assets", lambda *a, **k: []),
            mock.patch.object(install, "resolve_tag", lambda *a, **k: "c0ffee"),
            mock.patch.object(install, "_worktree_clean", lambda *a, **k: (True, [])),
            mock.patch.object(install, "branch_source_findings", lambda *a, **k: []),
            mock.patch.object(install, "trellis_clues", lambda *a, **k: []),
            mock.patch.object(install, "self_check", lambda *a, **k: []),
        ]
        for patch in self._patches:
            patch.start()
            self.addCleanup(patch.stop)

    def _hooks(self):
        return self.target / ".codex/hooks.json"

    def _run(self, argv):
        buffer = io.StringIO()
        with mock.patch("sys.stdin", mock.Mock(isatty=lambda: True, readline=lambda: "t\n")), \
                contextlib.redirect_stdout(buffer):
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

    def test_first_install_conflict_writes_nothing(self):
        user_command = "python3 -X utf8 .codex/hooks/wf-session-identity.py --mine"
        self._hooks().write_text(json.dumps(
            {"hooks": {"SessionStart": [{"hooks": [
                {"type": "command", "command": user_command, "timeout": 15}]}]}}),
            encoding="utf-8")
        code, payload, text = self._run([
            "--target", str(self.target), "--release-ref", "refs/tags/wf-v0.1.7",
            "--source", str(self.source), "--confirm", "--json"])
        self.assertNotEqual(code, 0)
        self.assertEqual(payload["code"], "WF_ASSET_DECISION")
        self.assertEqual(payload["tier"], "needs_decision")
        # 决定性事实：一个文件都没写（.wf/ 未建、技能副本未投放、hooks.json 未被改）
        self.assertFalse((self.target / ".wf").exists(), "首装冲突不得创建 .wf/")
        self.assertFalse((self.target / ".agents").exists(), "首装冲突不得投放技能副本")
        self.assertEqual(json.loads(self._hooks().read_text(encoding="utf-8"))["hooks"]["SessionStart"][0]
                         ["hooks"][0]["command"], user_command)

    def test_add_platforms_conflict_keeps_writer_idle(self):
        # 已安装（dsh），追加 codex，但 hooks.json 被用户改过
        (self.target / ".wf").mkdir(parents=True)
        (self.target / ".wf/install").mkdir()
        rules = "sha256:rules"
        (self.target / ".wf/install/installation.json").write_text(json.dumps(
            {"schema_version": 1, "version": "0.1.7", "release_ref": "refs/tags/wf-v0.1.7",
             "source_commit": "c0ffee", "rules_digest": rules, "platforms": ["dsh"],
             "roots": [".agents/skills"], "assets": [], "host_hook_entries": []},
            ensure_ascii=False), encoding="utf-8")
        (self.target / ".wf/writer.json").write_text(json.dumps(
            {"schema_version": 1, "id": "writer", "revision": 0, "state": "idle",
             "generation": 4, "holder": None, "created_at": "t", "updated_at": "t"}),
            encoding="utf-8")
        user_command = "python3 -X utf8 .codex/hooks/wf-session-identity.py --mine"
        self._hooks().write_text(json.dumps(
            {"hooks": {"SessionStart": [{"hooks": [
                {"type": "command", "command": user_command, "timeout": 15}]}]}}),
            encoding="utf-8")
        code, payload, text = self._run([
            "--target", str(self.target), "--release-ref", "refs/tags/wf-v0.1.7",
            "--source", str(self.source), "--confirm", "--json"])
        self.assertNotEqual(code, 0)
        self.assertEqual(payload["code"], "WF_ASSET_DECISION")
        self.assertEqual(payload["tier"], "needs_decision")
        writer = json.loads((self.target / ".wf/writer.json").read_text(encoding="utf-8"))
        self.assertEqual(writer["state"], "idle", "冲突不得把写权留在 held")
        self.assertFalse((self.target / ".agents/skills/wf-start/SKILL.md").exists(),
                         "冲突不得先投放新资产")
        installation = json.loads(
            (self.target / ".wf/install/installation.json").read_text(encoding="utf-8"))
        self.assertEqual(installation["platforms"], ["dsh"])

    def test_rerun_repairs_missing_hooks_entry(self):
        """安装后 hooks.json 丢了条目：自检报错且重跑同一条命令能补（hooks 动作并入变更集）。"""
        (self.target / ".wf").mkdir(parents=True)
        (self.target / ".wf/install").mkdir()
        (self.target / ".wf/install/installation.json").write_text(json.dumps(
            {"schema_version": 1, "version": "0.1.7", "release_ref": "refs/tags/wf-v0.1.7",
             "source_commit": "c0ffee", "rules_digest": "sha256:rules",
             "platforms": ["codex"], "roots": [".agents/skills"],
             "host_hook_entries": [{"platform": "codex", "script_relative": HOOK_REL,
                                    "command": install.host_hook_command(HOOK_REL),
                                    "updated_at": "t"}],
             "assets": [{"target": HOOK_REL, "root_ref": "project",
                         "digest": install.file_digest(str(self.target / HOOK_REL)),
                         "source_path": "wf-release/hooks/x.py",
                         "upstream_version": "0.1.7"}]},
            ensure_ascii=False), encoding="utf-8")
        (self.target / ".wf/writer.json").write_text(json.dumps(
            {"schema_version": 1, "id": "writer", "revision": 0, "state": "idle",
             "generation": 4, "holder": None, "created_at": "t", "updated_at": "t"}),
            encoding="utf-8")
        self.assertFalse(self._hooks().exists())
        code, payload, text = self._run([
            "--target", str(self.target), "--release-ref", "refs/tags/wf-v0.1.7",
            "--source", str(self.source), "--confirm", "--json"])
        self.assertEqual(payload["code"], "WF_OK", text)
        commands = [hook["command"]
                    for entry in json.loads(self._hooks().read_text(encoding="utf-8"))
                    ["hooks"]["SessionStart"] for hook in entry["hooks"]]
        self.assertEqual(commands, [install.host_hook_command(HOOK_REL)])


class PreviewAndReceiptTest(HalfInstallStateTest):
    """五轮复审第 2 轮 a-P2：`.codex/hooks.json` 是**用户共享文件**。

    它既不属发行资产、也不在 `.wf/` 下——安装预览不列、维护回执不记，人既看不到这次
    确认会改宿主的配置文件，事后也无法核对/持久化它（项目迁移后 Codex 会话身份 hook
    可能就此失效）。同类一并收口：`.gitignore` 托管段也在预览与回执里可见，且冲突
    **不写入**而先报。
    """

    def test_preview_lists_host_hook_and_gitignore(self):
        code, payload, text = self._run([
            "--target", str(self.target), "--release-ref", "refs/tags/wf-v0.1.7",
            "--source", str(self.source), "--json"])
        self.assertEqual(payload["code"], "WF_OK", text)
        self.assertTrue(payload["facts"].get("preview"), "应为预览（未带 --confirm）")
        self.assertIn("宿主 hook 配置（用户共享文件 .codex/hooks.json）", text)
        self.assertIn(".codex/hooks.json absent", text)
        self.assertIn("托管段（.gitignore）：appended", text)
        self.assertFalse(self._hooks().exists())
        self.assertFalse((self.target / ".gitignore").exists())

    def test_preview_blocks_on_hooks_conflict_before_confirm(self):
        user = "python3 -X utf8 .codex/hooks/wf-session-identity.py --mine"
        self._hooks().write_text(json.dumps(
            {"hooks": {"SessionStart": [{"hooks": [
                {"type": "command", "command": user, "timeout": 15}]}]}}), encoding="utf-8")
        code, payload, text = self._run([
            "--target", str(self.target), "--release-ref", "refs/tags/wf-v0.1.7",
            "--source", str(self.source), "--json"])
        self.assertNotEqual(code, 0)
        self.assertEqual(payload["code"], "WF_ASSET_DECISION")
        self.assertEqual(payload["tier"], "needs_decision")

    def test_preview_blocks_on_gitignore_segment_conflict(self):
        (self.target / ".gitignore").write_text(
            "# wf-managed-v1\n/stale-line\n# wf-managed-end\n", encoding="utf-8")
        code, payload, text = self._run([
            "--target", str(self.target), "--release-ref", "refs/tags/wf-v0.1.7",
            "--source", str(self.source), "--json"])
        self.assertNotEqual(code, 0)
        self.assertEqual(payload["code"], "WF_ASSET_DECISION")
        self.assertEqual(payload["tier"], "needs_decision")
        self.assertEqual((self.target / ".gitignore").read_text(encoding="utf-8"),
                         "# wf-managed-v1\n/stale-line\n# wf-managed-end\n",
                         "冲突时不得改写用户文件")
        self.assertFalse((self.target / ".wf").exists())

    def test_first_install_receipt_records_user_shared_files(self):
        code, payload, text = self._run([
            "--target", str(self.target), "--release-ref", "refs/tags/wf-v0.1.7",
            "--source", str(self.source), "--confirm", "--json"])
        self.assertEqual(payload["code"], "WF_OK", text)
        writer = json.loads((self.target / ".wf/writer.json").read_text(encoding="utf-8"))
        receipt = writer["maintenance_results"][-1]
        paths = {item["path"] for item in receipt["changes"]}
        self.assertIn(".codex/hooks.json", paths, "首装回执必须逐路径记宿主 hook 配置")
        self.assertIn(".gitignore", paths, "首装回执必须记托管段变更")
        for item in receipt["changes"]:
            if item["path"] in (".codex/hooks.json", ".gitignore"):
                # 新建文件的 before 就是 None（与既有 `deployed` 条目同口径），
                # 关键是**键存在且 after 有值**：回执要能逐路径核对前后状态。
                self.assertIn("before", item, f"{item['path']} 需要落地前状态字段")
                self.assertTrue(item["after"], f"{item['path']} 需要落地后摘要")

    def test_add_platforms_receipt_records_hooks_json(self):
        (self.target / ".wf").mkdir(parents=True)
        (self.target / ".wf/install").mkdir()
        (self.target / ".wf/install/installation.json").write_text(json.dumps(
            {"schema_version": 1, "version": "0.1.7", "release_ref": "refs/tags/wf-v0.1.7",
             "source_commit": "c0ffee", "rules_digest": "sha256:rules", "platforms": ["dsh"],
             "roots": [".agents/skills"], "assets": [], "host_hook_entries": []},
            ensure_ascii=False), encoding="utf-8")
        (self.target / ".wf/writer.json").write_text(json.dumps(
            {"schema_version": 1, "id": "writer", "revision": 0, "state": "idle",
             "generation": 4, "holder": None, "created_at": "t", "updated_at": "t"}),
            encoding="utf-8")
        code, payload, text = self._run([
            "--target", str(self.target), "--release-ref", "refs/tags/wf-v0.1.7",
            "--source", str(self.source), "--confirm", "--json"])
        self.assertEqual(payload["code"], "WF_OK", text)
        writer = json.loads((self.target / ".wf/writer.json").read_text(encoding="utf-8"))
        paths = {item["path"] for item in writer["maintenance_results"][-1]["changes"]}
        self.assertIn(".codex/hooks.json", paths)


class HookEventTest(HookFixture):
    """五轮复审 b-4：命令串挂在非 SessionStart 事件下 ≠ 会话启动适配生效。

    `plan_hooks_json` 原来扫所有事件，只要找到同一个命令就报 `unchanged`——把条目搬到
    `Stop` 下自检仍绿，但会话启动时根本不会生成/刷新身份映射（退化方向＝新会话沿用旧绑定）。
    """

    def test_entry_under_other_event_is_conflict(self):
        self._hooks_path().write_text(json.dumps(
            {"hooks": {"Stop": [{"hooks": [
                {"type": "command", "command": install.host_hook_command(NEW_REL)}]}]}}),
            encoding="utf-8")
        plan = install.plan_hooks_json(str(self.target), HOOK_REL,
                                       install.host_hook_command(NEW_REL),
                                       previous_command=OLD_COMMAND)
        self.assertEqual(plan["action"], "conflict")
        self.assertEqual(plan["observed_events"], ["Stop"])
        self.assertIn("其它事件", plan["reason"])

    def test_session_start_entry_still_unchanged(self):
        self._write_hooks(install.host_hook_command(NEW_REL))
        plan = install.plan_hooks_json(str(self.target), HOOK_REL,
                                       install.host_hook_command(NEW_REL))
        self.assertEqual(plan["action"], "unchanged")

    def test_append_creates_entry_under_session_start(self):
        self._write_hooks("python3 user.py")
        plan = install.plan_hooks_json(str(self.target), HOOK_REL,
                                       install.host_hook_command(NEW_REL))
        self.assertEqual(plan["action"], "appended")
        install.apply_hooks_json(str(self.target), plan)
        data = json.loads(self._hooks_path().read_text(encoding="utf-8"))
        session_start = data["hooks"]["SessionStart"]
        self.assertEqual(len(session_start), 2)
        self.assertEqual(session_start[1]["hooks"][0]["command"],
                         install.host_hook_command(NEW_REL))

    def test_self_check_reports_misplaced_entry(self):
        shutil.copyfile(self.source_hook, self.target / HOOK_REL)
        self._hooks_path().write_text(json.dumps(
            {"hooks": {"Stop": [{"hooks": [
                {"type": "command", "command": install.host_hook_command(NEW_REL)}]}]}}),
            encoding="utf-8")
        problems = install.self_check(str(self.target), self.manifest, [],
                                      installation=self.installation)
        drifted = [item for item in problems
                   if item.get("reason") == "host hook entry missing or drifted"]
        self.assertEqual(len(drifted), 1, problems)
        self.assertEqual(drifted[0]["action"], "conflict")

