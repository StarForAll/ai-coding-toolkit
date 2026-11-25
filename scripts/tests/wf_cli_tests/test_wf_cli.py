"""System-level wf command tests.

The tests use a local git fixture as the registered source and a temporary cache root. They do
not install the package or touch the real Forgejo remote.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
CLI_DIR = REPO / "docs" / "workflows" / "wf-cli"
sys.path.insert(0, str(CLI_DIR))

import wf_cli.main as wf_main  # noqa: E402
import wf_cli.release as wf_release  # noqa: E402
from wf_cli.project import ProjectError, discover_project, normalize_project  # noqa: E402
from wf_cli.release import Release, ReleaseError  # noqa: E402
from wf_cli.version import source_version  # noqa: E402
import wf_cli.selfupdate as wf_selfupdate  # noqa: E402

INSTALLATION = {
    "schema_version": 1,
    "version": "0.0.8",
    "release_ref": "refs/tags/wf-v0.0.8",
    "source_commit": "deadbeef",
}


def _git(repo, *argv, env=None):
    command = ["git", "-C", str(repo), *argv]
    return subprocess.run(command, capture_output=True, text=True, check=True, env=env)


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _release_tree(repo, version):
    _write(repo / "docs/workflows/wf-release/wf-release.json",
           json.dumps({"version": version, "assets": [],
                       "compatibility": {"rules_digest": "sha256:fixture"}},
                      ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    _write(repo / "docs/workflows/wf-release/install.py", "print('installer')\n")
    _write(repo / "docs/workflows/wf-release/wf-release/bin/repair.py", "print('repair')\n")
    _write(repo / "docs/workflows/wf-release/wf-release/bin/uninstall.py", "print('uninstall')\n")


def _commit(repo, version, date):
    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = date
    env["GIT_COMMITTER_DATE"] = date
    _release_tree(repo, version)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", f"release {version}", env=env)
    _git(repo, "tag", f"wf-v{version}")


class GitFixture(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.repo = self.root / "source"
        self.repo.mkdir()
        _git(self.repo, "init", "-q", "-b", "main")
        _git(self.repo, "config", "user.email", "t@example.com")
        _git(self.repo, "config", "user.name", "t")
        self.url = "file://" + str(self.repo)
        self.cache = self.root / "cache"
        self._old_cache = os.environ.get("XDG_CACHE_HOME")
        os.environ["XDG_CACHE_HOME"] = str(self.cache)
        self.addCleanup(self._restore_cache)
        self._old_url = wf_release.SOURCE_URL
        wf_release.SOURCE_URL = self.url
        self.addCleanup(self._restore_url)

    def _restore_cache(self):
        if self._old_cache is None:
            os.environ.pop("XDG_CACHE_HOME", None)
        else:
            os.environ["XDG_CACHE_HOME"] = self._old_cache

    def _restore_url(self):
        wf_release.SOURCE_URL = self._old_url

    def make_releases(self):
        _commit(self.repo, "0.0.8", "2026-11-20T10:00:00+0000")
        _commit(self.repo, "0.0.9", "2026-11-25T10:00:00+0000")
        return self.url


class VersionTest(unittest.TestCase):
    def test_source_version_matches_release_manifest(self):
        manifest = json.loads((REPO / "docs/workflows/wf-release/wf-release.json").read_text(encoding="utf-8"))
        self.assertEqual(source_version(), str(manifest["version"]))

    def test_pyproject_dynamic_version_points_at_manifest(self):
        import tomllib

        pyproject = tomllib.loads((CLI_DIR / "pyproject.toml").read_text(encoding="utf-8"))
        tool = pyproject["tool"]["hatch"]["version"]
        self.assertEqual(tool["path"], "../wf-release/wf-release.json")
        manifest_text = (REPO / "docs/workflows/wf-release/wf-release.json").read_text(encoding="utf-8")
        import re

        match = re.search(tool["pattern"], manifest_text)
        self.assertIsNotNone(match)
        self.assertEqual(match.group("version"), source_version())


class SelfUpgradeTest(unittest.TestCase):
    def release(self, version="0.0.9"):
        return Release(version=version, tag="wf-v" + version, commit="c" * 40, repo="/repo")

    def test_release_asset_is_preferred_and_installed(self):
        calls = {}

        def download(url, destination, token):
            calls["url"] = url
            calls["token"] = token
            Path(destination).write_bytes(b"wheel")
            return destination

        def runner(command, **kwargs):
            calls["command"] = command
            class Result:
                returncode = 0
                stdout = "installed"
                stderr = ""
            return Result()

        old = wf_selfupdate.validate_cli_tag
        wf_selfupdate.validate_cli_tag = lambda *args: True
        self.addCleanup(lambda: setattr(wf_selfupdate, "validate_cli_tag", old))
        facts = wf_selfupdate.perform(
            "0.0.8", self.release(), manager="uv", token="secret",
            base="https://forgejo.example/xzc/repo", source_url="ssh://git@forgejo.example/xzc/repo.git",
            download=download, runner=runner,
            executable="/home/u/.local/share/uv/tools/wf-cli/bin/python",
            which=lambda name: "/usr/bin/" + name,
        )
        self.assertEqual(facts["target_kind"], "wheel")
        self.assertIn("wf_cli-0.0.9-py3-none-any.whl", calls["url"])
        self.assertEqual(calls["token"], "secret")
        self.assertIn("--force", calls["command"])
        self.assertTrue(calls["command"][-1].endswith("wf_cli-0.0.9-py3-none-any.whl"))

    def test_missing_asset_falls_back_to_git_tag(self):
        calls = {}

        def runner(command, **kwargs):
            calls["command"] = command
            class Result:
                returncode = 0
                stdout = ""
                stderr = ""
            return Result()

        old = wf_selfupdate.validate_cli_tag
        wf_selfupdate.validate_cli_tag = lambda *args: True
        self.addCleanup(lambda: setattr(wf_selfupdate, "validate_cli_tag", old))
        facts = wf_selfupdate.perform(
            "0.0.8", self.release(), manager="uv", token=None,
            base="https://forgejo.example/xzc/repo", source_url="ssh://git@forgejo.example/xzc/repo.git",
            download=lambda *args: None, runner=runner,
            executable="/home/u/.local/share/uv/tools/wf-cli/bin/python",
            which=lambda name: "/usr/bin/" + name,
        )
        self.assertEqual(facts["target_kind"], "git")
        self.assertTrue(any("wf-v0.0.9#subdirectory=docs/workflows/wf-cli" in item
                            for item in calls["command"]))

    def test_manager_detection(self):
        self.assertEqual(wf_selfupdate.manager_for("/home/u/.local/share/uv/tools/wf-cli/bin/python",
                                                   which=lambda name: None), "uv")
        self.assertEqual(wf_selfupdate.manager_for("/home/u/.local/pipx/venvs/wf-cli/bin/python",
                                                   which=lambda name: None), "pipx")
        self.assertEqual(wf_selfupdate.manager_for("/usr/bin/python3",
                                                   which=lambda name: "/usr/bin/uv" if name == "uv" else None), "uv")
        self.assertIsNone(wf_selfupdate.manager_for("/usr/bin/python3", which=lambda name: None))

    def test_command_reports_latest(self):
        latest = self.release()
        old_version, old_latest = wf_main.cli_version, wf_main.latest_release
        wf_main.cli_version = lambda: "0.0.8"
        wf_main.latest_release = lambda: latest
        old_perform = wf_main.selfupdate.perform
        wf_main.selfupdate.perform = lambda *args, **kwargs: {
            "from": "0.0.8", "to": "0.0.9", "tag": "wf-v0.0.9",
            "manager": "uv", "target_kind": "wheel",
        }
        self.addCleanup(lambda: setattr(wf_main, "cli_version", old_version))
        self.addCleanup(lambda: setattr(wf_main, "latest_release", old_latest))
        self.addCleanup(lambda: setattr(wf_main.selfupdate, "perform", old_perform))
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = wf_main.main(["self-upgrade", "--json"])
        self.assertEqual(code, 0)
        self.assertIn("wf-v0.0.9", buffer.getvalue())

    def test_same_version_is_noop(self):
        latest = self.release()
        old_version, old_latest = wf_main.cli_version, wf_main.latest_release
        wf_main.cli_version = lambda: "0.0.9"
        wf_main.latest_release = lambda: latest
        called = []
        old_perform = wf_main.selfupdate.perform
        wf_main.selfupdate.perform = lambda *args, **kwargs: called.append(True)
        self.addCleanup(lambda: setattr(wf_main, "cli_version", old_version))
        self.addCleanup(lambda: setattr(wf_main, "latest_release", old_latest))
        self.addCleanup(lambda: setattr(wf_main.selfupdate, "perform", old_perform))
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = wf_main.main(["self-upgrade", "--json"])
        self.assertEqual(code, 0)
        self.assertFalse(called)
        self.assertIn("已是最新", buffer.getvalue())


class BootstrapTest(unittest.TestCase):
    def setUp(self):
        import importlib.util

        path = REPO / "docs/workflows/wf-cli/install.py"
        spec = importlib.util.spec_from_file_location("wf_cli_install_bootstrap", path)
        self.bootstrap = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.bootstrap)

    def test_latest_release_ignores_draft_and_prerelease(self):
        payload = [
            {"tag_name": "wf-v0.0.9", "draft": True, "assets": []},
            {"tag_name": "wf-v0.0.8", "draft": False, "prerelease": False,
             "published_at": "2026-11-25T10:00:00Z", "assets": []},
            {"tag_name": "not-wf", "draft": False, "assets": []},
            {"tag_name": "wf-v0.0.10", "draft": False, "prerelease": True, "assets": []},
        ]
        old = self.bootstrap._json
        self.bootstrap._json = lambda url, token=None: payload
        self.addCleanup(lambda: setattr(self.bootstrap, "_json", old))
        release = self.bootstrap.latest_release("https://forgejo.example", "xzc/repo")
        self.assertEqual(release[1], "wf-v0.0.8")
        self.assertEqual(release[2], "0.0.8")

    def test_wheel_asset_requires_matching_version(self):
        entry = {"tag_name": "wf-v0.0.8", "assets": [
            {"name": "wf_cli-0.0.8-py3-none-any.whl",
             "browser_download_url": "https://forgejo.example/xzc/repo/releases/download/wf-v0.0.8/wf_cli-0.0.8-py3-none-any.whl"},
            {"name": "other.txt", "browser_download_url": "https://forgejo.example/other.txt"},
        ]}
        release = ("2026-11-25", "wf-v0.0.8", "0.0.8", entry)
        url, tag, version, name = self.bootstrap.wheel_asset(release, "https://forgejo.example", "xzc/repo")
        self.assertEqual(tag, "wf-v0.0.8")
        self.assertEqual(version, "0.0.8")
        self.assertEqual(name, "wf_cli-0.0.8-py3-none-any.whl")
        self.assertTrue(url.endswith(name))

    def test_missing_asset_is_an_error(self):
        release = ("2026-11-25", "wf-v0.0.8", "0.0.8", {"assets": []})
        with self.assertRaises(self.bootstrap.BootstrapError) as caught:
            self.bootstrap.wheel_asset(release, "https://forgejo.example", "xzc/repo")
        self.assertIn("缺少系统 wf 安装 wheel", str(caught.exception))


class ProjectDiscoveryTest(unittest.TestCase):
    def test_discover_from_nested_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / ".wf/bin/wf.py", "print('wf')\n")
            nested = root / "a/b/c"
            nested.mkdir(parents=True)
            self.assertEqual(Path(discover_project(nested)).resolve(), root.resolve())

    def test_installation_record_alone_is_a_project_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / ".wf/install/installation.json", "{}\n")
            self.assertEqual(Path(discover_project(root)).resolve(), root.resolve())

    def test_relative_project_is_rejected(self):
        with self.assertRaises(ProjectError) as caught:
            normalize_project("relative/path")
        self.assertEqual(caught.exception.code, "WF_PATH_INVALID")


class ReleaseResolutionTest(GitFixture):
    def test_latest_uses_newest_tag_on_default_branch(self):
        self.make_releases()
        release = wf_release.latest_release()
        self.assertEqual(release.version, "0.0.9")
        self.assertEqual(release.tag, "wf-v0.0.9")

    def test_unmerged_newer_tag_is_not_latest(self):
        _commit(self.repo, "0.0.8", "2026-11-20T10:00:00+0000")
        _commit(self.repo, "0.0.9", "2026-11-25T10:00:00+0000")
        _git(self.repo, "checkout", "-q", "-b", "side", "wf-v0.0.8")
        _commit(self.repo, "0.1.0", "2026-11-26T10:00:00+0000")
        _git(self.repo, "checkout", "-q", "main")
        release = wf_release.latest_release()
        self.assertEqual(release.version, "0.0.9")

    def test_worktree_is_created_and_reused(self):
        self.make_releases()
        root = wf_release.ensure_release("0.0.8")
        self.assertTrue(root.endswith("docs/workflows/wf-release"))
        self.assertTrue(os.path.isfile(os.path.join(root, "install.py")))
        again = wf_release.ensure_release("0.0.8")
        self.assertEqual(root, again)

    def test_missing_tag_is_reported(self):
        self.make_releases()
        with self.assertRaises(ReleaseError) as caught:
            wf_release.ensure_release("0.0.7")
        self.assertEqual(caught.exception.code, "WF_RELEASE_CONFLICT")
        self.assertIn("wf-v0.0.7", json.dumps(caught.exception.facts, ensure_ascii=False))

    def test_manifest_version_must_match_tag(self):
        _release_tree(self.repo, "0.0.8")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-q", "-m", "wrong version")
        _git(self.repo, "tag", "wf-v0.0.9")
        with self.assertRaises(ReleaseError) as caught:
            wf_release.ensure_release("0.0.9")
        self.assertEqual(caught.exception.code, "WF_RELEASE_CONFLICT")

    def test_dirty_worktree_is_replaced(self):
        self.make_releases()
        root = wf_release.ensure_release("0.0.8")
        _write(Path(root) / "install.py", "tampered\n")
        again = wf_release.ensure_release("0.0.8")
        self.assertEqual(Path(root), Path(again))
        self.assertEqual((Path(again) / "install.py").read_text(encoding="utf-8"), "print('installer')\n")


class CliDispatchTest(GitFixture):
    def setUp(self):
        super().setUp()
        self.project = self.root / "project"
        self.project.mkdir()
        self._old_version = wf_main.cli_version
        wf_main.cli_version = lambda: "0.0.8"
        self.addCleanup(self._restore_version)
        self.exec_calls = []

    def _restore_version(self):
        wf_main.cli_version = self._old_version

    def _exec(self, path, argv, env):
        self.exec_calls.append((path, list(argv), dict(env)))
        return 0

    def _run(self, argv):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = wf_main.main(argv, exec_fn=self._exec)
        return code, buffer.getvalue()

    def _install_record(self, version="0.0.8"):
        _write(self.project / ".wf/install/installation.json",
               json.dumps(dict(INSTALLATION, version=version), ensure_ascii=False, indent=2) + "\n")

    def test_install_uses_command_version_and_no_release_flags(self):
        self.make_releases()
        code, _out = self._run(["install", "--project", str(self.project), "--confirm", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(len(self.exec_calls), 1)
        _path, argv, _env = self.exec_calls[0]
        self.assertIn("--target", argv)
        self.assertIn(str(self.project.resolve()), argv)
        self.assertIn("--confirm", argv)
        self.assertIn("--strict-source", argv)
        self.assertNotIn("--release-ref", argv)
        self.assertNotIn("--source", argv)

    def test_install_rejects_version_mismatch_before_running_installer(self):
        self.make_releases()
        self._install_record("0.0.7")
        code, out = self._run(["install", "--project", str(self.project), "--json"])
        self.assertEqual(code, 1)
        self.assertIn("WF_RELEASE_CONFLICT", out)
        self.assertEqual(self.exec_calls, [])

    def test_retired_flags_are_structured(self):
        code, out = self._run(["install", "--release-ref", "refs/tags/wf-v0.0.8", "--json"])
        self.assertEqual(code, 1)
        payload = json.loads(out)
        self.assertEqual(payload["code"], "WF_USAGE_INVALID")
        self.assertEqual(payload["facts"]["retired"], "--release-ref")
        self.assertEqual(self.exec_calls, [])

    def test_upgrade_uses_latest_release(self):
        self.make_releases()
        self._install_record("0.0.8")
        code, _out = self._run(["upgrade", "--project", str(self.project), "--apply", "--json"])
        self.assertEqual(code, 0)
        _path, argv, _env = self.exec_calls[0]
        self.assertIn("--upgrade", argv)
        self.assertIn("--apply", argv)
        self.assertNotIn("--release-ref", argv)
        self.assertNotIn("--source", argv)

    def test_upgrade_is_noop_at_latest(self):
        self.make_releases()
        self._install_record("0.0.9")
        code, out = self._run(["upgrade", "--project", str(self.project), "--json"])
        self.assertEqual(code, 0)
        self.assertIn("WF_OK", out)
        self.assertEqual(self.exec_calls, [])

    def test_export_deviations_runs_installer_at_same_version(self):
        self.make_releases()
        self._install_record("0.0.9")
        code, _out = self._run(["upgrade", "--project", str(self.project),
                                "--export-deviations", "--out", str(self.root / "out"), "--json"])
        self.assertEqual(code, 0)
        _path, argv, _env = self.exec_calls[0]
        self.assertIn("--export-deviations", argv)
        self.assertIn("--out", argv)

    def test_uninstall_forwards_to_installed_entry(self):
        _write(self.project / ".wf/bin/uninstall.py", "print('uninstall')\n")
        self._install_record("0.0.8")
        code, _out = self._run(["uninstall", "--project", str(self.project), "--purge", "--json"])
        self.assertEqual(code, 0)
        _path, argv, _env = self.exec_calls[0]
        self.assertIn(str(self.project.resolve()), argv)
        self.assertIn("--purge", argv)
        self.assertTrue(argv[1].endswith(".wf/bin/uninstall.py"))

    def test_repair_falls_back_to_installed_release(self):
        self.make_releases()
        self._install_record("0.0.8")
        code, _out = self._run(["repair", "--project", str(self.project), "--json"])
        self.assertEqual(code, 0)
        _path, argv, _env = self.exec_calls[0]
        self.assertTrue(argv[1].endswith("wf-release/bin/repair.py"))

    def test_runtime_command_is_forwarded_to_bootstrap(self):
        _write(self.project / ".wf/bin/wf.py", "print('wf')\n")
        code, _out = self._run(["--project", str(self.project), "task-new", "--title", "x", "--json"])
        self.assertEqual(code, 0)
        _path, argv, _env = self.exec_calls[0]
        self.assertEqual(Path(argv[1]).resolve(), (self.project / ".wf/bin/wf.py").resolve())
        self.assertIn("task-new", argv)
        self.assertIn("--title", argv)

    def test_version_reports_installed_version(self):
        self._install_record("0.0.7")
        code, out = self._run(["--project", str(self.project), "version", "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["facts"]["version"], "0.0.8")
        self.assertEqual(payload["facts"]["installed"], "0.0.7")


if __name__ == "__main__":
    unittest.main()