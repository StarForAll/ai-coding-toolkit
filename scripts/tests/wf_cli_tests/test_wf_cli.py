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
            record_writer=lambda *args, **kwargs: None,
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
            record_writer=lambda *args, **kwargs: None,
        )
        self.assertEqual(facts["target_kind"], "git")
        self.assertEqual(facts["asset_state"], "missing")
        self.assertNotIn("asset_error", facts)
        self.assertTrue(facts["asset_missing"].endswith("wf_cli-0.0.9-py3-none-any.whl"))
        # 私有仓库没导出 token 时资产必然 404：结论里要说出这个原因，而不是只说"附件缺失"
        self.assertEqual(facts["asset_missing_hint"], "私有仓库需要在环境中提供 FORGEJO_TOKEN")
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


class SelfUninstallTest(unittest.TestCase):
    def test_uninstall_command_for_managers(self):
        which = lambda name: "/usr/bin/" + name
        self.assertEqual(wf_selfupdate.uninstall_command("uv", which=which),
                         ["/usr/bin/uv", "tool", "uninstall", "wf-cli"])
        self.assertEqual(wf_selfupdate.uninstall_command("pipx", which=which),
                         ["/usr/bin/pipx", "uninstall", "wf-cli"])
        self.assertEqual(wf_selfupdate.uninstall_command("pip", executable="/usr/bin/python3", which=which),
                         ["/usr/bin/python3", "-m", "pip", "uninstall", "-y", "wf-cli"])

    def test_apply_runs_the_manager_command(self):
        calls = {}

        def runner(command, **kwargs):
            calls["command"] = command
            class Result:
                returncode = 0
                stdout = "uninstalled"
                stderr = ""
            return Result()

        result = wf_selfupdate.perform_uninstall(
            manager="uv", runner=runner,
            executable="/home/u/.local/share/uv/tools/wf-cli/bin/python",
            which=lambda name: "/usr/bin/" + name,
        )
        self.assertEqual(result["manager"], "uv")
        self.assertEqual(calls["command"], ["/usr/bin/uv", "tool", "uninstall", "wf-cli"])

    def test_main_preview_does_not_uninstall_and_apply_does(self):
        old = wf_main.selfupdate.perform_uninstall
        called = []
        wf_main.selfupdate.perform_uninstall = lambda *args, **kwargs: called.append(True) or {
            "manager": "uv", "command": ["uv", "tool", "uninstall", "wf-cli"], "output": "uninstalled"}
        self.addCleanup(lambda: setattr(wf_main.selfupdate, "perform_uninstall", old))
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = wf_main.main(["self-uninstall", "--manager", "uv", "--json"])
        self.assertEqual(code, 0)
        self.assertFalse(called)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = wf_main.main(["self-uninstall", "--manager", "uv", "--apply", "--json"])
        self.assertEqual(code, 0)
        self.assertTrue(called)


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

    def _in_project(self, path):
        """临时把 cwd 切到目标目录（命令缺省用当前目录定位项目）。"""
        previous = os.getcwd()

        @contextlib.contextmanager
        def _swap():
            os.chdir(path)
            try:
                yield
            finally:
                os.chdir(previous)

        return _swap()

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

    def test_project_flag_is_optional_from_inside_the_project(self):
        # `--project` 可选：缺省取当前目录（向上找 .wf/），维护命令照样拿到同一个项目根。
        _write(self.project / ".wf/bin/uninstall.py", "print('uninstall')\n")
        _write(self.project / ".wf/bin/wf.py", "print('wf')\n")
        self._install_record("0.0.8")
        with self._in_project(self.project):
            code, out = self._run(["version", "--json"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["facts"]["project"],
                             str(self.project.resolve()))
            code, _out = self._run(["uninstall", "--json"])
            self.assertEqual(code, 0)
            _path, argv, _env = self.exec_calls[0]
            self.assertIn(str(self.project.resolve()), argv)
            code, _out = self._run(["task-new", "--title", "x", "--json"])
            self.assertEqual(code, 0)

    def test_missing_project_reports_optional_flag_exit(self):
        outside = self.root / "outside"
        outside.mkdir()
        with self._in_project(outside):
            code, out = self._run(["repair", "--json"])
        self.assertEqual(code, 1)
        payload = json.loads(out)
        self.assertEqual(payload["code"], "WF_PATH_INVALID")
        self.assertIn("--project", payload["next"])


class AssetBaseTest(unittest.TestCase):
    """资产基址的单一事实：安装与自升级取同一个 URL 来源。

    2026-11-26 实测：`wf self-upgrade` 用从 git 源地址推出的 `https://forgejo.xzc.com/...`
    （缺 `:13785`）下载 wheel → Connection refused，随后静默降级成 git 安装并只打印 OK。
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name)
        self._env = mock.patch.dict(os.environ, {"HOME": str(self.home)})
        self._env.start()
        self.addCleanup(self._env.stop)
        for name in ("WF_FORGEJO_BASE", "WF_GIT_URL"):
            patcher = mock.patch.dict(os.environ)
            patcher.start()
            self.addCleanup(patcher.stop)
            os.environ.pop(name, None)

    def test_default_base_carries_the_registered_web_port(self):
        self.assertEqual(wf_release.http_base(), wf_release.DEFAULT_HTTP_BASE)
        self.assertTrue(wf_release.DEFAULT_HTTP_BASE.endswith(":13785"))

    def test_asset_url_is_under_the_instance_root(self):
        # 实例根 + 仓库段 + 发行附件名；安装时 bootstrap 取到的正是这一形状的地址
        url = wf_release.release_asset_url("0.0.15", wf_release.DEFAULT_HTTP_BASE)
        self.assertEqual(
            url,
            "https://forgejo.xzc.com:13785/xzc/ai-coding-toolkit/releases/download/"
            "wf-v0.0.15/wf_cli-0.0.15-py3-none-any.whl")

    def test_git_source_host_is_never_used_to_guess_the_http_base(self):
        os.environ["WF_GIT_URL"] = "ssh://git@forgejo.example:13768/xzc/repo.git"
        self.assertEqual(wf_release.http_base(), wf_release.DEFAULT_HTTP_BASE)

    def test_environment_override_wins(self):
        os.environ["WF_FORGEJO_BASE"] = "https://forgejo.example:8443/"
        self.assertEqual(wf_release.http_base(), "https://forgejo.example:8443")

    def test_install_record_is_reused_by_the_upgrade(self):
        record_path = wf_release.install_record_path()
        wf_release.write_install_record("https://forgejo.example:13785", repo="xzc/repo",
                                        path=record_path)
        self.assertEqual(Path(record_path).parent, self.home / ".wf")
        self.assertEqual(wf_release.http_base(), "https://forgejo.example:13785")
        payload = json.loads(Path(record_path).read_text(encoding="utf-8"))
        self.assertEqual(payload["schema_version"], wf_release.INSTALL_RECORD_SCHEMA)
        self.assertNotIn("tag", payload, "记录不承载发行身份：版本/tag 会过期")
        self.assertEqual(Path(record_path).stat().st_mode & 0o777, 0o600)

    def test_corrupt_record_is_reported_and_not_used(self):
        record_path = Path(wf_release.install_record_path())
        record_path.parent.mkdir(parents=True)
        record_path.write_text("{not json", encoding="utf-8")
        record, problem = wf_release.read_install_record()
        self.assertIsNone(record)
        self.assertIn("已忽略", problem)
        self.assertEqual(wf_release.http_base(), wf_release.DEFAULT_HTTP_BASE)

    def test_bootstrap_and_package_agree_on_record_path_and_schema(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("wf_cli_bootstrap",
                                                      CLI_DIR / "install.py")
        bootstrap = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bootstrap)
        self.assertEqual(tuple(bootstrap.INSTALL_RECORD_REL), wf_release.INSTALL_RECORD_REL)
        self.assertEqual(bootstrap.INSTALL_RECORD_SCHEMA, wf_release.INSTALL_RECORD_SCHEMA)
        self.assertEqual(bootstrap.DEFAULT_BASE, wf_release.DEFAULT_HTTP_BASE)

        recorded = {}

        def fake_now():
            return None

        bootstrap_record = bootstrap.write_install_record("https://forgejo.example:13785",
                                                          "xzc/repo")
        package_record = Path(self._tmp.name) / "package-record.json"
        wf_release.write_install_record("https://forgejo.example:13785", repo="xzc/repo",
                                        path=package_record)
        recorded["bootstrap"] = json.loads(Path(bootstrap_record).read_text(encoding="utf-8"))
        recorded["package"] = json.loads(package_record.read_text(encoding="utf-8"))
        for payload in recorded.values():
            self.assertEqual(sorted(payload),
                             ["http_base", "repo", "schema_version", "written_at"])


    def test_bootstrap_writes_the_record_the_upgrade_reads(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("wf_cli_bootstrap_run",
                                                      CLI_DIR / "install.py")
        bootstrap = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bootstrap)
        release = ("2026-11-26T00:00:00Z", "wf-v0.0.15", "0.0.15", {})
        patches = {
            "latest_release": lambda *args, **kwargs: release,
            "wheel_asset": lambda *args, **kwargs: ("https://forgejo.example:13785/a.whl",
                                                    "wf-v0.0.15", "0.0.15", "a.whl"),
            "download": lambda url, destination, token: Path(destination).write_bytes(b"wheel"),
            "manager_for": lambda requested=None, which=None: "uv",
            "install": lambda manager, wheel: "installed",
        }
        for name, value in patches.items():
            old = getattr(bootstrap, name)
            setattr(bootstrap, name, value)
            self.addCleanup(lambda name=name, old=old: setattr(bootstrap, name, old))
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = bootstrap.main(["--base", "https://forgejo.example:13785"])
        output = buffer.getvalue()
        self.assertEqual(code, 0, output)
        record, problem = wf_release.read_install_record()
        self.assertIsNone(problem)
        self.assertEqual(record["http_base"], "https://forgejo.example:13785")
        self.assertIn("资产基址已记录", output)
        # 自升级读同一条记录 → 得到安装实际用过的基址
        self.assertEqual(wf_release.http_base(), "https://forgejo.example:13785")


class SelfUpgradeReportTest(unittest.TestCase):
    """自升级的成功口径：用 wheel 就是 wheel，降级成 git 必须写明降级与原因。"""

    def release(self, version="0.0.15"):
        return Release(version=version, tag="wf-v" + version, commit="c" * 40, repo="/repo")

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name)
        env = mock.patch.dict(os.environ, {"HOME": str(self.home)})
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("WF_FORGEJO_BASE", None)
        old = wf_selfupdate.validate_cli_tag
        wf_selfupdate.validate_cli_tag = lambda *args: True
        self.addCleanup(lambda: setattr(wf_selfupdate, "validate_cli_tag", old))

    def _runner(self):
        calls = {}

        def runner(command, **kwargs):
            calls["command"] = command

            class Result:
                returncode = 0
                stdout = ""
                stderr = ""
            return Result()

        return runner, calls

    def test_unreachable_asset_is_reported_as_degradation(self):
        runner, calls = self._runner()

        def download(url, destination, token):
            raise wf_selfupdate.SelfUpgradeError(
                "WF_CAPABILITY_UNAVAILABLE", "无法连接系统 wf 发行资产",
                {"url": url, "detail": "<urlopen error [Errno 111] Connection refused>"})

        record_calls = []
        facts = wf_selfupdate.perform(
            "0.0.14", self.release(), manager="uv", token=None,
            download=download, runner=runner,
            executable="/home/u/.local/share/uv/tools/wf-cli/bin/python",
            which=lambda name: "/usr/bin/" + name,
            record_writer=lambda base, **kwargs: record_calls.append(base),
        )
        self.assertEqual(facts["target_kind"], "git")
        self.assertEqual(facts["asset_state"], "unreachable")
        self.assertEqual(facts["asset_base"], wf_release.DEFAULT_HTTP_BASE)
        self.assertEqual(facts["asset_base_source"], "default")
        self.assertIn("asset_error", facts)
        self.assertEqual(record_calls, [], "降级没证明基址可用，不写安装记录")
        self.assertTrue(any("wf-v0.0.15#subdirectory=docs/workflows/wf-cli" in item
                            for item in calls["command"]))

        # 命令层的输出：写明降级、给出的地址与原因，而不是一句 OK
        old_version, old_latest = wf_main.cli_version, wf_main.latest_release
        wf_main.cli_version = lambda: "0.0.14"
        wf_main.latest_release = lambda: self.release()
        old_perform = wf_main.selfupdate.perform
        wf_main.selfupdate.perform = lambda *args, **kwargs: facts
        self.addCleanup(lambda: setattr(wf_main, "cli_version", old_version))
        self.addCleanup(lambda: setattr(wf_main, "latest_release", old_latest))
        self.addCleanup(lambda: setattr(wf_main.selfupdate, "perform", old_perform))
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = wf_main.main(["self-upgrade"])
        text = buffer.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("从 git 安装", text)
        self.assertIn("资产基址", text)
        self.assertIn("被拒绝的资产地址", text)
        self.assertIn("Connection refused", text)
        self.assertFalse(any(line.lstrip().startswith("{'")
                             for line in text.splitlines()),
                         f"事实行不得把 dict 打成 repr：{text}")

    def test_env_base_is_reported_as_its_own_source(self):
        os.environ["WF_FORGEJO_BASE"] = "https://forgejo.example:8443/"
        calls = {}

        def download(url, destination, token):
            calls["url"] = url
            Path(destination).write_bytes(b"wheel")
            return destination

        runner, _calls = self._runner()
        facts = wf_selfupdate.perform(
            "0.0.14", self.release(), manager="uv", token=None,
            download=download, runner=runner,
            executable="/home/u/.local/share/uv/tools/wf-cli/bin/python",
            which=lambda name: "/usr/bin/" + name,
            record_writer=lambda *args, **kwargs: None,
        )
        self.assertEqual(facts["asset_base_source"], "env")
        self.assertTrue(calls["url"].startswith("https://forgejo.example:8443/xzc/"))
        self.assertEqual(facts["asset_base"], "https://forgejo.example:8443")

    def test_corrupt_record_is_surfaced_in_the_upgrade_facts(self):
        record_path = Path(wf_release.install_record_path())
        record_path.parent.mkdir(parents=True)
        record_path.write_text("{not json", encoding="utf-8")
        runner, _calls = self._runner()
        facts = wf_selfupdate.perform(
            "0.0.14", self.release(), manager="uv", token="t",
            download=lambda *args: None, runner=runner,
            executable="/home/u/.local/share/uv/tools/wf-cli/bin/python",
            which=lambda name: "/usr/bin/" + name,
            record_writer=lambda *args, **kwargs: None,
        )
        self.assertEqual(facts["asset_base_source"], "default")
        self.assertIn("已忽略", facts["record_problem"])

    def test_wheel_install_records_the_proven_base(self):
        runner, _calls = self._runner()

        def download(url, destination, token):
            Path(destination).write_bytes(b"wheel")
            return destination

        record_calls = []
        facts = wf_selfupdate.perform(
            "0.0.14", self.release(), manager="uv", token=None,
            base="https://forgejo.example:13785/",
            download=download, runner=runner,
            executable="/home/u/.local/share/uv/tools/wf-cli/bin/python",
            which=lambda name: "/usr/bin/" + name,
            record_writer=lambda base, **kwargs: record_calls.append(base),
        )
        self.assertEqual(facts["target_kind"], "wheel")
        self.assertEqual(record_calls, ["https://forgejo.example:13785"])
        self.assertNotIn("asset_error", facts)

    def test_passed_renders_structured_facts_as_json(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            wf_main.passed("x", {"asset_error": {"url": "u", "detail": "d"}})
        text = buffer.getvalue()
        self.assertIn('asset_error: {"detail": "d", "url": "u"}', text)
        self.assertNotIn("{'url'", text)


class HelpTextTest(unittest.TestCase):
    """`wf help` 必须是唯一一份说明来源：用法与作用不能各写一处。"""

    def setUp(self):
        self.commands = wf_main.COMMAND_HELP
        self.descriptions = wf_main.COMMAND_DESC

    def test_every_command_has_a_description(self):
        self.assertEqual(sorted(self.commands), sorted(self.descriptions))

    def test_overview_is_rendered_from_the_single_source(self):
        for name, description in self.descriptions.items():
            self.assertIn(description, wf_main.HELP, name)

    def test_repair_help_states_what_is_repaired(self):
        text = wf_main.command_text("repair")
        self.assertIn(self.commands["repair"], text)
        self.assertIn("writer.json", text)
        self.assertIn("维护回执", text)
        self.assertIn("--dispose", text)
        self.assertNotIn("nonexistent-marker", text)

    def test_overview_states_the_optional_project_flag(self):
        self.assertIn("--project 可选，缺省用当前目录", wf_main.HELP)

    def test_help_subcommand_prints_the_same_text_for_a_command(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            wf_main.main(["help", "repair"], exec_fn=lambda *_a: 0)
        self.assertEqual(buffer.getvalue(), wf_main.command_text("repair"))


if __name__ == "__main__":
    unittest.main()