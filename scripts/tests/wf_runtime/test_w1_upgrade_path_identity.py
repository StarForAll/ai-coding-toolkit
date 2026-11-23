"""W1（五轮，a-1）：人面路径身份＝项目相对路径。

dogfood 分析报告 a-1 的事实面：三方匹配内部键是 `(base, rel)`，但
`--keep/--restore`、升级预览、导出清单、安装记录处置留痕统一退化为 `rel`——
`claudecode`（`reads_shared=False` → `.claude/skills`）与任一共享平台
（`.agents/skills`）并存时，两根本同 `rel`，人的处置会同时命中两份副本：
`--restore` 可能把人有意保留的另一个根的本地改动静默覆盖掉。

本用例锁定：
- token 形态是项目相对路径，能区分同名副本；
- 给旧形态（资产相对路径）时不再静默套用，而是报"没有对应待决冲突"并列出可用 token；
- 导出清单与安装记录处置留痕同样带 token（导出 `target_path`、记录 `path`+`root_ref`）。
"""

import contextlib
import hashlib
import shutil
import importlib.util
import io
import json
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


install = _load("w5_install", PAYLOAD / "install.py")

SKILL_REL = "wf-review/SKILL.md"
SHARED_ROOT = ".agents/skills"
CLAUDE_ROOT = ".claude/skills"


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
        self.export_deviations = kwargs.get("export_deviations", False)
        self.out = kwargs.get("out")
        self.keep = kwargs.get("keep", [])
        self.restore = kwargs.get("restore", [])


class MultiRootHarness(unittest.TestCase):
    """一个装了共享根 + claude 根的项目；两个根下的同名技能副本各有本地改动。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="wf-w1-multiroot-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.target = self.root / "proj"
        for relative in (f"{SHARED_ROOT}/{SKILL_REL}", f"{CLAUDE_ROOT}/{SKILL_REL}"):
            path = self.target / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"local edit in {relative}\n", encoding="utf-8")
        self.shared_digest = self._digest(f"{SHARED_ROOT}/{SKILL_REL}")
        self.claude_digest = self._digest(f"{CLAUDE_ROOT}/{SKILL_REL}")
        # 安装记录：两根本各自登记同一 rel；O（上游旧模板）与 L 不同 ⇒ 两处都冲突
        self.installation = {
            "schema_version": 1, "version": "0.1.6", "release_ref": "refs/tags/wf-v0.1.6",
            "source_commit": "c0ffee", "platforms": ["claudecode", "dsh"],
            "roots": [SHARED_ROOT, CLAUDE_ROOT],
            "assets": [
                {"target": SKILL_REL, "root_ref": SHARED_ROOT, "digest": "sha256:" + "0" * 64,
                 "source_path": f"wf-release/skills/{SKILL_REL}", "upstream_version": "0.1.6",
                 "upstream_fingerprint": "sha256:" + "0" * 64},
                {"target": SKILL_REL, "root_ref": CLAUDE_ROOT, "digest": "sha256:" + "0" * 64,
                 "source_path": f"wf-release/skills/{SKILL_REL}", "upstream_version": "0.1.6",
                 "upstream_fingerprint": "sha256:" + "0" * 64},
            ],
        }
        install_dir = self.target / ".wf/install"
        install_dir.mkdir(parents=True)
        (install_dir / "installation.json").write_text(
            json.dumps(self.installation, indent=2, ensure_ascii=False), encoding="utf-8")
        (self.target / ".wf/writer.json").write_text(json.dumps(
            {"schema_version": 1, "id": "writer", "revision": 0, "state": "idle",
             "generation": 0, "holder": None, "created_at": "t", "updated_at": "t"}),
            encoding="utf-8")
        # 应用段末尾的自检会导入目标项目自己的运行时（`.wf/lib` → `wflib`）并把
        # `required_steps` 与 `gates.supported_keys()` 对齐；夹具直接复制真实运行时与
        # 已发行清单的 required_steps，避免为了断言一个记录字段而伪造自检结果。
        shutil.copytree(PAYLOAD / "lib", self.target / ".wf/lib")
        shutil.copytree(PAYLOAD / "protocol", self.target / ".wf/protocol")
        (self.target / ".wf/bin").mkdir(parents=True)
        for name in ("wf.py", "repair.py", "uninstall.py"):
            shutil.copyfile(PAYLOAD / "bin" / name, self.target / ".wf/bin" / name)
        self.source = self.root / "checkout"
        (self.source / "wf-release").mkdir(parents=True)
        released = json.loads((REPO / "docs/workflows/wf-release/wf-release.json")
                              .read_text(encoding="utf-8"))
        self.manifest = {"version": "0.1.7",
                         "compatibility": {"rules_digest": "sha256:rules"},
                         "required_steps": released["required_steps"],
                         "delivery_round": released["delivery_round"],
                         "gitignore_managed": {"begin_marker": "# wf-managed-v1",
                                               "end_marker": "# wf-managed-end",
                                               "lines": ["/.wf/.runtime/", "/.wf-lock"]},
                         "assets": [
                             {"source_path": f"wf-release/skills/{SKILL_REL}",
                              "target_class": "skill_root", "target_relative": SKILL_REL,
                              "kind": "skill", "required": False, "file_kind": "file",
                              "executable": False, "digest": "sha256:" + "1" * 64},
                         ]}
        (self.source / "wf-release.json").write_text(
            json.dumps(self.manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    def _digest(self, relative):
        return "sha256:" + hashlib.sha256(
            (self.target / relative).read_bytes()).hexdigest()

    def _installation(self):
        return json.loads(
            (self.target / ".wf/install/installation.json").read_text(encoding="utf-8"))

    def _plan(self, keep=(), restore=()):
        return install.three_way_plan(str(self.target), self._installation(), self.manifest,
                                      str(self.source), list(keep), list(restore))

    def _run(self, args, commit="deadbeef"):
        """跑 upgrade 入口并解析它写到 stdout 的 JSON（入口返回的是退出码）。"""
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
        """走真实应用段：令牌确认用桩（令牌本身另有 `--verify-token-parity` 覆盖）。"""
        fake_stdin = mock.Mock()
        fake_stdin.isatty.return_value = True
        fake_stdin.readline.return_value = "token\n"
        with mock.patch.object(install.PreviewToken, "confirm", return_value=True), \
                mock.patch("sys.stdin", fake_stdin):
            return self._run(args, commit)


class PathTokenTest(MultiRootHarness):
    def test_token_is_project_relative_path(self):
        self.assertEqual(install._asset_token(str(self.target), str(self.target),
                                              ".wf/bin/wf.py"), ".wf/bin/wf.py")
        self.assertEqual(
            install._asset_token(str(self.target), str(self.target / SHARED_ROOT), SKILL_REL),
            f"{SHARED_ROOT}/{SKILL_REL}")

    def test_two_roots_are_distinguishable_in_plan(self):
        plan, unresolved = self._plan()
        paths = {item["path"] for item in unresolved}
        self.assertEqual(paths, {f"{SHARED_ROOT}/{SKILL_REL}", f"{CLAUDE_ROOT}/{SKILL_REL}"})
        # 内部身份仍是 (base, rel)：同一 rel 两条记录，不可合并
        self.assertEqual({item["relative"] for item in unresolved}, {SKILL_REL})

    def test_keep_hits_only_the_named_copy(self):
        plan, unresolved = self._plan(keep=[f"{SHARED_ROOT}/{SKILL_REL}"])
        kept = [item for item in plan["actions"] if item["kind"] == "deviation"]
        self.assertEqual([item["path"] for item in kept], [f"{SHARED_ROOT}/{SKILL_REL}"])
        self.assertTrue(kept[0].get("decision", "").endswith("--keep)"))
        # 另一个根仍在等待人裁决，没有被连带处置
        self.assertEqual([item["path"] for item in unresolved], [f"{CLAUDE_ROOT}/{SKILL_REL}"])

    def test_restore_hits_only_the_named_copy(self):
        plan, unresolved = self._plan(restore=[f"{CLAUDE_ROOT}/{SKILL_REL}"])
        restored = [item for item in plan["actions"]
                    if item["kind"] == "deviation" and item.get("restore")]
        self.assertEqual([item["path"] for item in restored], [f"{CLAUDE_ROOT}/{SKILL_REL}"])
        self.assertEqual([item["path"] for item in unresolved], [f"{SHARED_ROOT}/{SKILL_REL}"])

    def test_asset_relative_token_no_longer_matches(self):
        """旧形态（资产相对路径）不再静默套用到所有副本——出口给 token 清单。"""
        plan, unresolved = self._plan(keep=[SKILL_REL])
        kept = [item for item in plan["actions"] if item["kind"] == "deviation"]
        self.assertEqual(kept, [])
        self.assertEqual({item["path"] for item in unresolved},
                         {f"{SHARED_ROOT}/{SKILL_REL}", f"{CLAUDE_ROOT}/{SKILL_REL}"})
        exits = {exit_ for item in unresolved for exit_ in item["exits"]}
        self.assertTrue(any(f"--keep {SHARED_ROOT}/{SKILL_REL}" in item for item in exits))


class UpgradeUnknownTokenTest(MultiRootHarness):
    def test_old_style_token_is_an_asset_decision_with_token_list(self):
        args = _Args(target=str(self.target), source=str(self.source), apply=False,
                     keep=[SKILL_REL])
        code, payload, _text = self._run(args)
        self.assertNotEqual(code, 0)
        self.assertEqual(payload["code"], "WF_ASSET_DECISION")
        paths = {item.get("path") for item in payload["facts"].get("unresolved") or []}
        # 旧形态没有静默套用：两处冲突仍在，且给出的是项目相对 token
        self.assertEqual(paths, {f"{SHARED_ROOT}/{SKILL_REL}", f"{CLAUDE_ROOT}/{SKILL_REL}"})

    def test_preview_lists_project_relative_paths(self):
        args = _Args(target=str(self.target), source=str(self.source), apply=False,
                     keep=[f"{SHARED_ROOT}/{SKILL_REL}"])
        code, payload, _text = self._run(args)
        # 只裁决一处 ⇒ 仍有一处待决；预览里给的应是 token
        self.assertEqual(payload["code"], "WF_ASSET_DECISION")
        unresolved = payload["facts"]["unresolved"]
        self.assertEqual([item["path"] for item in unresolved], [f"{CLAUDE_ROOT}/{SKILL_REL}"])
        self.assertIn(f"--keep {CLAUDE_ROOT}/{SKILL_REL}", " ".join(unresolved[0]["exits"]))

    def test_selected_paths_are_tokens(self):
        args = _Args(target=str(self.target), source=str(self.source), apply=False,
                     keep=[f"{SHARED_ROOT}/{SKILL_REL}", f"{CLAUDE_ROOT}/{SKILL_REL}"])
        code, payload, text = self._run(args)
        self.assertEqual(payload["code"], "WF_OK", text)
        preview = payload["facts"]["preview"]
        self.assertEqual(sorted(preview["selected_paths"]),
                         [f"{SHARED_ROOT}/{SKILL_REL}", f"{CLAUDE_ROOT}/{SKILL_REL}"] if
                         f"{SHARED_ROOT}/{SKILL_REL}" < f"{CLAUDE_ROOT}/{SKILL_REL}" else
                         [f"{CLAUDE_ROOT}/{SKILL_REL}", f"{SHARED_ROOT}/{SKILL_REL}"])
        self.assertEqual({item["path"] for item in preview["before_states"]},
                         {f"{CLAUDE_ROOT}/{SKILL_REL}", f"{SHARED_ROOT}/{SKILL_REL}"})
        # 两处都是"冲突后按人决定保留" ⇒ 预览 risks 逐副本列出（不再合并成一条）
        self.assertEqual(sorted(preview["risks"]),
                         sorted([f"deviation kept: {SHARED_ROOT}/{SKILL_REL}",
                                 f"deviation kept: {CLAUDE_ROOT}/{SKILL_REL}"]))


class ExportManifestTest(MultiRootHarness):
    def test_export_uses_target_path(self):
        out = self.root / "exported"
        args = _Args(target=str(self.target), source=str(self.source),
                     export_deviations=True, out=str(out))
        code, payload, text = self._run(args)
        self.assertEqual(payload["code"], "WF_OK", text)
        data = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(data["deviations"])
        for item in data["deviations"]:
            self.assertIn("target_path", item)
            self.assertTrue(item["target_path"].startswith((f"{SHARED_ROOT}/",
                                                             f"{CLAUDE_ROOT}/")), item)
            self.assertNotIn("path", item)
        paths = [item["target_path"] for item in data["deviations"]]
        self.assertEqual(len(paths), len(set(paths)), "同名副本被压成同一条")


class UpstreamRemovedTest(MultiRootHarness):
    """上游删除 + 本地有改动 + 人 keep ⇒ `unmanaged`（退出托管），走的是删除/退出分支。"""

    def _drop_asset(self, required):
        self.manifest["assets"] = []
        self.manifest["assets"] = []
        installation = self._installation()
        for item in installation["assets"]:
            item["required"] = required
        (self.target / ".wf/install/installation.json").write_text(
            json.dumps(installation, ensure_ascii=False, indent=2), encoding="utf-8")

    def test_unmanaged_decision_records_token_and_root_ref(self):
        """应用段把人的 keep 决定写进安装记录：同一 rel 的两份副本必须各留一条。"""
        self._drop_asset(required=False)
        args = _Args(target=str(self.target), source=str(self.source), apply=True,
                     keep=[f"{SHARED_ROOT}/{SKILL_REL}", f"{CLAUDE_ROOT}/{SKILL_REL}"])
        code, payload, text = self._apply(args)
        self.assertEqual(payload["code"], "WF_OK", text)
        records = [item for item in self._installation().get("decisions") or []
                   if item.get("kind") == "unmanaged-keep"]
        self.assertEqual({item["path"] for item in records},
                         {f"{SHARED_ROOT}/{SKILL_REL}", f"{CLAUDE_ROOT}/{SKILL_REL}"})
        # root_ref 与安装记录 assets 同一约定：项目根外的技能根记绝对路径
        self.assertEqual({item["root_ref"] for item in records},
                         {str(self.target / SHARED_ROOT), str(self.target / CLAUDE_ROOT)})
        self.assertEqual({item["target"] for item in records}, {SKILL_REL})

    def test_required_asset_cannot_be_kept_deleted(self):
        self._drop_asset(required=True)
        args = _Args(target=str(self.target), source=str(self.source), apply=False,
                     keep=[f"{SHARED_ROOT}/{SKILL_REL}", f"{CLAUDE_ROOT}/{SKILL_REL}"])
        code, payload, _text = self._run(args)
        self.assertNotEqual(code, 0)
        self.assertEqual(payload["code"], "WF_SEMANTIC_DECISION")
        self.assertEqual({item for item in payload["facts"]["required_deleted"]},
                         {f"{SHARED_ROOT}/{SKILL_REL}", f"{CLAUDE_ROOT}/{SKILL_REL}"})


if __name__ == "__main__":
    unittest.main()