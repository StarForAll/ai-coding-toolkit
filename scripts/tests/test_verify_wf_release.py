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


class PrePushHookTest(unittest.TestCase):
    """pre-push 只对 `refs/tags/wf-v*` 的推送行调用发行核对。"""

    def setUp(self):
        self.hook = (REPO / "scripts" / "git-hooks" / "pre-push").read_text(encoding="utf-8")

    def test_hook_calls_verify_for_tag_pushes(self):
        self.assertIn("refs/tags/wf-v*)", self.hook)
        self.assertIn("scripts/verify-wf-release.py", self.hook)
        self.assertIn("scripts/build-wf-cli-wheel.py", self.hook)
        self.assertIn('tag_version=${tag_ref#refs/tags/wf-v}', self.hook)
        self.assertIn('tag_name="wf-v$tag_version"', self.hook)

    def test_hook_does_not_run_verify_outside_tag_lines(self):
        # 核对只挂在 tag 行收集到的变量上：普通分支推送不进这个分支
        self.assertIn('if [ -n "$wf_tags" ]; then', self.hook)
        self.assertNotIn('while read -r _local_ref', self.hook)


if __name__ == "__main__":
    unittest.main()