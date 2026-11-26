"""W4（五轮，b-P0）：发行 tag 的机械闭环核对。

事实面：`git tag -l` 只有 `wf-v0.1.0`，README 却记载"0.1.5 → 0.1.6 可用 upgrade 升级"；
安装器只认 `refs/tags/wf-vX.Y.Z` 且要 `rev-parse` 成功，于是**文档承诺的升级通道在字段上不可执行**。
根因不是代码缺陷，而是"版本三者同批"这条义务只写在散文里——写不成机械检查的义务不会履行。

本用例逐个核对 `scripts/verify-wf-release.py` 的判定项（合成 git 仓库，hermetic）：
- ref 形态与版本一致性；
- tag 不存在 ⇒ `tag_exists` 失败并列出仓库现有发行 tag；
- tag 提交内的发行树与工作树不一致（内容不同 / 只在一侧存在）⇒ 失败；
- 清单 version / README 目标版本 / rules_digest 与 tag 版本不符 ⇒ 各自失败；
- 全部一致 ⇒ 通过（"源码重建一致"一项可注入桩，因为它调用真实 builder）。
"""

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verify_mod = _load("wf_verify_release", REPO / "scripts" / "verify-wf-release.py")

sys.path.insert(0, str(REPO / "docs/workflows/wf/payload/lib"))
from wflib import assets as wf_assets  # noqa: E402

VERSION = "0.1.7"
REF = f"refs/tags/wf-v{VERSION}"

MANIFEST = {
    "schema_version": 1,
    "version": VERSION,
    "assets": [{"source_path": "wf-release/bin/wf.py", "target_class": "project_wf",
                "target_relative": ".wf/bin/wf.py", "kind": "bin", "required": True}],
    "required_steps": [{"id": "control.task.create", "round": 1}],
    "template_markers": [],
    "gitignore_managed": {"begin_marker": "# wf-managed-v1", "end_marker": "# wf-managed-end",
                          "lines": ["/.wf-lock"]},
    "compatibility": {"python_min": {"major": 3, "minor": 11}},
}
MANIFEST["compatibility"]["rules_digest"] = wf_assets.compute_rules_digest(MANIFEST)

README_TEXT = "# wf 模块源树\n\n| 项 | 值 |\n|---|---|\n| 目标版本 | `%s` |\n" % VERSION
CLI_PYPROJECT_TEXT = r"""[project]
name = "wf-cli"
dynamic = ["version"]
[project.scripts]
wf = "wf_cli.main:entry"
[tool.hatch.version]
path = "../wf-release/wf-release.json"
pattern = '"version"\s*:\s*"(?P<version>[0-9]+\.[0-9]+\.[0-9]+)"'
"""


class GitCase(unittest.TestCase):
    """一个最小合成仓库：发行树 + README + tag 都由用例自己控制。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="wf-verify-release-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self._git("init", "-q")
        self._git("config", "user.email", "t@example.com")
        self._git("config", "user.name", "t")
        self._git("config", "commit.gpgsign", "false")
        self.write_release(manifest=MANIFEST, readme=README_TEXT)
        self.commit("release 0.1.7")

    # --- helpers ---------------------------------------------------------
    def _git(self, *argv):
        return subprocess.run(["git", "-C", str(self.root), *argv], check=True,
                              capture_output=True, text=True).stdout

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def write_release(self, manifest=None, readme=None):
        self.write("docs/workflows/wf-release/wf-release.json",
                   json.dumps(manifest if manifest is not None else MANIFEST,
                              ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        self.write("docs/workflows/wf-release/wf-release/bin/wf.py", "print('wf')\n")
        self.write("docs/workflows/wf-cli/pyproject.toml", CLI_PYPROJECT_TEXT)
        self.write("docs/workflows/wf-cli/wf_cli/main.py", "def entry():\n    return 0\n")
        self.write("docs/workflows/wf-cli/install.py", "print('bootstrap')\n")
        self.write("docs/workflows/wf/README.md",
                   readme if readme is not None else README_TEXT)

    def commit(self, message):
        self._git("add", "-A")
        self._git("commit", "-q", "-m", message)

    def tag(self, ref=REF):
        self._git("tag", ref[len("refs/tags/"):] if ref.startswith("refs/tags/") else ref)

    def verify(self, version=VERSION, ref=REF, source_ok=True):
        def source_check(_repo, _version):
            return {"name": "release_tree_matches_source", "ok": source_ok,
                    "facts": {"version": _version}, "exits": [] if source_ok else ["重建"]}
        return verify_mod.verify(str(self.root), version, ref, source_check=source_check)

    def check(self, result, name):
        for item in result["checks"]:
            if item["name"] == name:
                return item
        self.fail(f"缺核对项 {name}: {[i['name'] for i in result['checks']]}")


class PassingCase(GitCase):
    def test_matching_release_passes(self):
        self.tag()
        result = self.verify()
        self.assertTrue(result["ok"], json.dumps(result, ensure_ascii=False, indent=2))

    def test_missing_tag_is_reported_with_present_tags(self):
        result = self.verify()
        item = self.check(result, "tag_exists")
        self.assertFalse(item["ok"])
        self.assertEqual(item["facts"]["present_tags"], [])
        self.assertFalse(result["ok"])

    def test_other_release_tags_are_listed(self):
        self.tag("refs/tags/wf-v0.1.0")
        result = self.verify()
        self.assertEqual(self.check(result, "tag_exists")["facts"]["present_tags"],
                         ["wf-v0.1.0"])

    def test_ref_shape_and_version_must_agree(self):
        self.tag()
        result = self.verify(ref="refs/tags/wf-v0.1.7", version="0.1.8")
        self.assertFalse(result["ok"])
        self.assertFalse(self.check(result, "ref_matches_version")["ok"])
        result = self.verify(ref="refs/heads/wf-v0.1.7")
        self.assertFalse(self.check(result, "ref_shape")["ok"])


class CliPackageCase(GitCase):
    def test_missing_cli_entry_is_reported(self):
        os.remove(self.root / "docs/workflows/wf-cli/wf_cli/main.py")
        self.commit("remove cli entry")
        self.tag()
        result = self.verify()
        item = self.check(result, "cli_package")
        self.assertFalse(item["ok"])
        self.assertFalse(item["facts"]["main"])
        self.assertTrue(item["facts"]["bootstrap"])


class TreeDriftCase(GitCase):
    def test_worktree_release_file_differs_from_tag(self):
        self.tag()
        self.write("docs/workflows/wf-release/wf-release/bin/wf.py", "print('changed')\n")
        result = self.verify()
        item = self.check(result, "tag_tree_matches_worktree")
        self.assertFalse(item["ok"])
        self.assertEqual(item["facts"]["mismatched"],
                         ["docs/workflows/wf-release/wf-release/bin/wf.py"])

    def test_file_only_in_worktree_is_reported(self):
        self.tag()
        self.write("docs/workflows/wf-release/wf-release/bin/extra.py", "x\n")
        result = self.verify()
        item = self.check(result, "tag_tree_matches_worktree")
        self.assertEqual(item["facts"]["not_in_tag"],
                         ["docs/workflows/wf-release/wf-release/bin/extra.py"])

    def test_file_only_in_tag_is_reported(self):
        self.tag()
        os.remove(self.root / "docs/workflows/wf-release/wf-release/bin/wf.py")
        result = self.verify()
        item = self.check(result, "tag_tree_matches_worktree")
        self.assertEqual(item["facts"]["missing_in_worktree"],
                         ["docs/workflows/wf-release/wf-release/bin/wf.py"])


class VersionDriftCase(GitCase):
    def test_manifest_version_mismatch(self):
        manifest = dict(MANIFEST, version="0.1.8")
        self.write_release(manifest=manifest)
        self.commit("release 0.1.7 with wrong manifest version")
        self.tag()
        result = self.verify()
        item = self.check(result, "manifest_version")
        self.assertFalse(item["ok"])
        self.assertEqual(item["facts"]["declared"], "0.1.8")

    def test_readme_version_mismatch(self):
        self.write_release(readme="# wf\n\n| 目标版本 | `0.1.8` |\n")
        self.commit("readme drift")
        self.tag()
        result = self.verify()
        item = self.check(result, "readme_version")
        self.assertFalse(item["ok"])
        self.assertEqual(item["facts"]["declared"], "0.1.8")

    def test_rules_digest_mismatch(self):
        manifest = json.loads(json.dumps(MANIFEST))
        manifest["compatibility"]["rules_digest"] = "sha256:" + "0" * 64
        self.write_release(manifest=manifest)
        self.commit("rules digest drift")
        self.tag()
        result = self.verify()
        item = self.check(result, "rules_digest")
        self.assertFalse(item["ok"])
        self.assertEqual(item["facts"]["recomputed"], MANIFEST["compatibility"]["rules_digest"])

    def test_source_rebuild_check_is_injected_not_stubbed_away(self):
        self.tag()
        result = self.verify(source_ok=False)
        self.assertFalse(self.check(result, "release_tree_matches_source")["ok"])
        self.assertFalse(result["ok"])


class RealRepoGuardTest(unittest.TestCase):
    """真实仓库：核对脚本对不存在的 tag 必须失败，且不创建/修改任何 ref。"""

    def test_nonexistent_tag_fails_without_touching_refs(self):
        before = subprocess.run(["git", "-C", str(REPO), "tag", "--list"],
                                capture_output=True, text=True, check=True).stdout
        result = verify_mod.verify(str(REPO), "9.9.9", "refs/tags/wf-v9.9.9",
                                   source_check=lambda _r, _v: {"name": "release_tree_matches_source",
                                                               "ok": True, "facts": {}})
        self.assertFalse(result["ok"])
        after = subprocess.run(["git", "-C", str(REPO), "tag", "--list"],
                               capture_output=True, text=True, check=True).stdout
        self.assertEqual(before, after, "核对脚本不得创建或删除 tag")

    def test_render_mentions_exits(self):
        result = verify_mod.verify(str(REPO), "9.9.9", "refs/tags/wf-v9.9.9",
                                   source_check=lambda _r, _v: {"name": "release_tree_matches_source",
                                                               "ok": False, "facts": {},
                                                               "exits": ["重建"]})
        text = verify_mod._render(result)
        self.assertIn("FAIL", text)
        self.assertIn("出口", text)


class ReleaseScriptTest(unittest.TestCase):
    """wf 发行由一次性 Python 脚本完成；pre-push 只管插件构建，不处理 wf tag。"""

    def setUp(self):
        import importlib.util
        path = REPO / "scripts" / "release-wf.py"
        spec = importlib.util.spec_from_file_location("release_wf", path)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.script = path.read_text(encoding="utf-8")
        self.hook = (REPO / "scripts" / "git-hooks" / "pre-push").read_text(encoding="utf-8")

    def test_prune_keeps_newest_three_tags_in_creation_order(self):
        ordered = ["wf-v0.0.13", "wf-v0.0.12", "wf-v0.1.7", "wf-v0.1.0"]
        self.assertEqual(self.module.prune_candidates(ordered), ["wf-v0.1.0"])
        self.assertEqual(self.module.prune_candidates(ordered, protect={"wf-v0.1.0"}), [])
        self.assertEqual(self.module.prune_candidates(ordered[:3]), [])

    def test_version_bumps(self):
        self.assertEqual(self.module.next_version("0.0.9", "patch"), "0.0.10")
        self.assertEqual(self.module.next_version("0.0.9", "minor"), "0.1.0")
        self.assertEqual(self.module.next_version("0.0.9", "major"), "1.0.0")
        self.assertEqual(self.module.next_version("1.2.3", "patch"), "1.2.4")

    def test_script_does_verify_tag_push_and_attach(self):
        for marker in ("build-wf-release.py", "verify-wf-release.py",
                       "build-wf-cli-wheel.py", "git", "tag",
                       "attach-wf-cli-asset.py", "release-wf",
                       "project_remotes", "HEAD:refs/heads/",
                       "ls-remote", ":refs/tags/", "--prune-local-tags", "--prune-tags"):
            self.assertIn(marker, self.script)

    def test_pending_version_is_not_skipped_by_default(self):
        self.assertEqual(self.module.select_version("0.0.9", "patch",
                                                    explicit=False, already_tagged=False), "0.0.9")
        self.assertEqual(self.module.select_version("0.0.9", "patch",
                                                    explicit=False, already_tagged=True), "0.0.10")
        self.assertEqual(self.module.select_version("0.0.9", "minor",
                                                    explicit=True, already_tagged=False), "0.1.0")

    def test_update_docs_replaces_target_and_current_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            readme = Path(tmp) / "README.md"
            cli = Path(tmp) / "CLI.md"
            readme.write_text(
                "| 目标版本 | `0.0.9`（只有人主动要求时才改）。**0.0.9**：说明。 |\n"
                "当前 0.0.9 仍属预正式发行。\n", encoding="utf-8")
            cli.write_text("python3 scripts/release-wf.py wf-v0.0.9 wf_cli-0.0.9\n",
                           encoding="utf-8")
            old_readme, old_cli = self.module.README, self.module.CLI_README
            self.module.README, self.module.CLI_README = readme, cli
            self.addCleanup(lambda: (setattr(self.module, "README", old_readme),
                                     setattr(self.module, "CLI_README", old_cli)))
            self.assertTrue(self.module.update_docs("0.0.9", "0.0.10"))
            text = readme.read_text(encoding="utf-8")
            self.assertIn("`0.0.10`", text)
            self.assertIn("**0.0.10**", text)
            self.assertIn("当前 0.0.10", text)
            self.assertNotIn("0.0.9", text)
            self.assertIn("wf-v0.0.10", cli.read_text(encoding="utf-8"))

    def test_missing_environment_fails_when_non_interactive(self):
        old_base = os.environ.pop("WF_FORGEJO_BASE", None)
        old_token = os.environ.pop("FORGEJO_TOKEN", None)
        self.addCleanup(lambda: (os.environ.__setitem__("WF_FORGEJO_BASE", old_base)
                                 if old_base is not None else None,
                                 os.environ.__setitem__("FORGEJO_TOKEN", old_token)
                                 if old_token is not None else None))
        with self.assertRaises(self.module.ReleaseError):
            self.module.resolve_environment()

    def test_script_reads_manifest_and_environment(self):
        self.assertIn("wf-release.json", self.script)
        self.assertIn("FORGEJO_TOKEN", self.script)
        self.assertIn("WF_FORGEJO_BASE", self.script)
        self.assertIn("getpass", self.script)

    def test_script_compiles(self):
        subprocess.run([sys.executable, "-m", "py_compile",
                        str(REPO / "scripts" / "release-wf.py")], check=True)

    def test_prune_flags_are_additive_not_standalone(self):
        self.assertNotIn("if args.prune_tags:", self.script)
        self.assertNotIn("只清理旧 tag", self.script)

    def test_historical_releases_are_pruned_before_tags(self):
        # tag 与 release 是 Forgejo 上两类对象：只删 tag 会留下 release 页与附件，
        # 所以发布成功后先删历史 release，再删旧 tag。
        self.assertIn("prune-wf-releases.py", self.script)
        body = self.script.split("def main(argv=None):", 1)[1]
        self.assertLess(body.index("prune_remote_releases(tag, env)"),
                        body.index("prune_remote_tags(tag, env)"))
        self.assertIn('"--keep", str(KEEP_TAGS)', self.script)
        self.assertIn('"--protect", current_tag', self.script)

    def test_first_install_hint_is_the_local_python_entry(self):
        # 收尾提示曾指向 releases/download/latest/install.py；当前首次安装入口是本地脚本
        self.assertIn("python3 scripts/install-wf.py", self.script)
        self.assertNotIn("releases/download/latest", self.script)

    def test_pre_push_no_longer_handles_wf_release(self):
        self.assertNotIn("refs/tags/wf-v", self.hook)
        self.assertNotIn("verify-wf-release.py", self.hook)
        self.assertNotIn("build-wf-cli-wheel.py", self.hook)


if __name__ == "__main__":
    unittest.main()