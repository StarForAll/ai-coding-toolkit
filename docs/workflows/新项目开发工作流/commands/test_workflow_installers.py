from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
PYTHON = (
    "/ops/softwares/python/bin/python3"
    if Path("/ops/softwares/python/bin/python3").exists()
    else shutil.which("python3") or shutil.which("python")
)
COMMANDS_DIR = REPO_ROOT / "docs" / "workflows" / "新项目开发工作流" / "commands"
INSTALL_SCRIPT = COMMANDS_DIR / "install-workflow.py"
UPGRADE_SCRIPT = COMMANDS_DIR / "upgrade-compat.py"
UNINSTALL_SCRIPT = COMMANDS_DIR / "uninstall-workflow.py"
PHASE_ROUTER_MARKER = "## Phase Router `[AI]`"
RECORD_SESSION_MARKER = "## Record-Session Metadata Closure `[AI]`"
DEFAULT_PROJECT_TODO = "文档内容需要和实际当前的代码同步\n"


class WorkflowInstallerTests(unittest.TestCase):
    def run_script(self, script: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [PYTHON, str(script), *args],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def create_fixture(
        self,
        *,
        include_opencode: bool = False,
        include_codex: bool = False,
        include_agents_md: bool = False,
        include_git: bool = True,
        include_trellis: bool = True,
        include_trellis_version: bool = True,
    ) -> Path:
        root = Path(tempfile.mkdtemp(prefix="workflow-installers-"))
        if include_git:
            (root / ".git").mkdir(parents=True)
        (root / ".claude" / "commands" / "trellis").mkdir(parents=True)
        if include_trellis:
            (root / ".trellis").mkdir(parents=True)
        (root / ".claude" / "commands" / "trellis" / "start.md").write_text(
            "# /trellis:start\n\n"
            "Original baseline start command for fixture testing.\n\n"
            "## Operation Types\n\n"
            "| Marker | Meaning |\n"
            "|--------|---------|\n"
            "| `[AI]` | tool calls |\n"
            "| `[USER]` | user actions |\n",
            encoding="utf-8",
        )
        (root / ".claude" / "commands" / "trellis" / "record-session.md").write_text(
            "# /trellis:record-session\n\n"
            "## Record Work Progress\n\n"
            "### Step 1: Get Context & Check Tasks\n\n"
            "```bash\n"
            "python3 ./.trellis/scripts/get_context.py --mode record\n"
            "```\n\n"
            "### Step 2: One-Click Add Session\n\n"
            "```bash\n"
            "python3 ./.trellis/scripts/add_session.py --title \"Title\" --commit \"hash\"\n"
            "```\n",
            encoding="utf-8",
        )
        if include_trellis and include_trellis_version:
            (root / ".trellis" / ".version").write_text("2.0.0\n", encoding="utf-8")
        if include_opencode:
            (root / ".opencode" / "commands" / "trellis").mkdir(parents=True)
            (root / ".opencode" / "commands" / "trellis" / "start.md").write_text(
                "# /trellis:start\n\n"
                "Original OpenCode baseline start command for fixture testing.\n\n"
                "## Operation Types\n\n"
                "| Marker | Meaning |\n"
                "|--------|---------|\n"
                "| `[AI]` | tool calls |\n"
                "| `[USER]` | user actions |\n",
                encoding="utf-8",
            )
            (root / ".opencode" / "commands" / "trellis" / "record-session.md").write_text(
                "# /trellis:record-session\n\n"
                "### Step 2: One-Click Add Session\n\n"
                "```bash\n"
                "python3 ./.trellis/scripts/add_session.py --title \"Title\" --commit \"hash\"\n"
                "```\n",
                encoding="utf-8",
            )
        if include_codex:
            (root / ".agents" / "skills").mkdir(parents=True)
            (root / ".codex" / "hooks").mkdir(parents=True)
            (root / ".codex" / "hooks.json").write_text("{}", encoding="utf-8")
            (root / ".codex" / "hooks" / "session-start.py").write_text("# hook\n", encoding="utf-8")
        if include_agents_md:
            (root / "AGENTS.md").write_text("# Project Rules\n", encoding="utf-8")
        return root

    def install_workflow(self, fixture_root: Path) -> subprocess.CompletedProcess[str]:
        return self.run_script(INSTALL_SCRIPT, "--project-root", str(fixture_root))

    def test_install_deploys_record_session_closure_helper_and_patch(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        brainstorm = fixture / ".claude" / "commands" / "trellis" / "brainstorm.md"
        self.assertTrue(brainstorm.exists(), "brainstorm.md should be deployed")
        helper = fixture / ".trellis" / "scripts" / "workflow" / "metadata-autocommit-guard.py"
        self.assertTrue(helper.exists(), "metadata-autocommit-guard.py should be deployed")
        record_helper = fixture / ".trellis" / "scripts" / "workflow" / "record-session-helper.py"
        self.assertTrue(record_helper.exists(), "record-session-helper.py should be deployed")
        record_session = fixture / ".claude" / "commands" / "trellis" / "record-session.md"
        self.assertIn(RECORD_SESSION_MARKER, record_session.read_text(encoding="utf-8"))

        record = fixture / ".trellis" / "workflow-installed.json"
        self.assertTrue(record.exists(), "workflow-installed.json should be created")
        self.assertIn("brainstorm", record.read_text(encoding="utf-8"))
        self.assertIn("metadata-autocommit-guard.py", record.read_text(encoding="utf-8"))
        self.assertIn("record-session-helper.py", record.read_text(encoding="utf-8"))

    def test_install_initializes_project_todo_file(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        todo_path = fixture / "todo.txt"
        self.assertTrue(todo_path.exists(), "todo.txt should be created during installation")
        self.assertEqual(todo_path.read_text(encoding="utf-8"), DEFAULT_PROJECT_TODO)

    def test_install_preserves_existing_project_todo_file(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)
        todo_path = fixture / "todo.txt"
        todo_path.write_text("已有内容\n", encoding="utf-8")

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.assertEqual(todo_path.read_text(encoding="utf-8"), "已有内容\n")
        self.assertIn("todo.txt 已存在", install.stdout)

    def test_install_requires_git_repository(self) -> None:
        fixture = self.create_fixture(include_git=False)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertNotEqual(install.returncode, 0)
        self.assertIn("目标项目不是 Git 仓库", install.stderr)

    def test_install_requires_trellis_init(self) -> None:
        fixture = self.create_fixture(include_trellis=False)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertNotEqual(install.returncode, 0)
        self.assertIn("目标项目未执行 trellis init", install.stderr)

    def test_install_requires_trellis_version_marker(self) -> None:
        fixture = self.create_fixture(include_trellis=True, include_trellis_version=False)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertNotEqual(install.returncode, 0)
        self.assertIn("缺少 .trellis/.version", install.stderr)

    def test_install_injects_agents_md_routing_and_multi_cli_assets(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True, include_agents_md=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.assertTrue((fixture / ".opencode" / "commands" / "trellis" / "brainstorm.md").exists())
        self.assertTrue((fixture / ".agents" / "skills" / "brainstorm" / "SKILL.md").exists())

        agents_md = (fixture / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("Claude / OpenCode 入口 | Codex 入口", agents_md)
        self.assertIn("Codex：通过 `AGENTS.md` 自然语言路由或显式触发对应 skill", agents_md)

    def test_install_dry_run_reports_preview_without_writing_files(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True, include_agents_md=True)
        self.addCleanup(shutil.rmtree, fixture)

        result = self.run_script(INSTALL_SCRIPT, "--project-root", str(fixture), "--dry-run")

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("将写入安装记录", result.stdout)
        self.assertIn("将注入 AGENTS.md NL 路由表", result.stdout)
        self.assertNotIn("✅ 安装记录 → workflow-installed.json", result.stdout)
        self.assertNotIn("✅ AGENTS.md NL 路由表已注入", result.stdout)
        self.assertFalse((fixture / ".trellis" / "workflow-installed.json").exists())
        self.assertFalse((fixture / ".agents" / "skills" / "brainstorm").exists())
        self.assertNotIn("workflow-nl-routing-start", (fixture / "AGENTS.md").read_text(encoding="utf-8"))

    def test_upgrade_check_detects_phase_router_drift_even_when_versions_match(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        backup_start = fixture / ".claude" / "commands" / "trellis" / ".backup-original" / "start.md"
        target_start = fixture / ".claude" / "commands" / "trellis" / "start.md"
        shutil.copy2(backup_start, target_start)

        result = self.run_script(UPGRADE_SCRIPT, "--check", "--project-root", str(fixture))

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("Phase Router 丢失", result.stdout)

    def test_upgrade_check_detects_missing_helper_scripts(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        helper = fixture / ".trellis" / "scripts" / "workflow" / "record-session-helper.py"
        helper.unlink()
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(UPGRADE_SCRIPT, "--check", "--project-root", str(fixture))

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("辅助脚本缺失", result.stdout)
        self.assertIn("record-session-helper.py", result.stdout)

    def test_upgrade_check_detects_record_session_patch_drift(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        record_session = fixture / ".claude" / "commands" / "trellis" / "record-session.md"
        content = record_session.read_text(encoding="utf-8").replace(RECORD_SESSION_MARKER, "## Missing Marker")
        record_session.write_text(content, encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(UPGRADE_SCRIPT, "--check", "--project-root", str(fixture))

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("record-session.md: 元数据闭环说明缺失", result.stdout)

    def test_force_recovers_start_from_backup_when_injection_marker_is_missing(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        broken_start = fixture / ".claude" / "commands" / "trellis" / "start.md"
        broken_start.write_text(
            "# broken start\n\n"
            "This file intentionally lacks the expected injection marker.\n",
            encoding="utf-8",
        )
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(UPGRADE_SCRIPT, "--force", "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn(PHASE_ROUTER_MARKER, broken_start.read_text(encoding="utf-8"))
        self.assertNotIn("无法自动注入", result.stdout)

    def test_uninstall_tolerates_corrupted_install_record(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        record = fixture / ".trellis" / "workflow-installed.json"
        record.write_text("{ invalid json", encoding="utf-8")

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("workflow-installed.json", result.stdout)
        self.assertFalse(record.exists())
        self.assertFalse((fixture / ".trellis" / "scripts" / "workflow").exists())
        self.assertTrue((fixture / ".claude" / "commands" / "trellis" / "start.md").exists())
        self.assertNotIn(
            RECORD_SESSION_MARKER,
            (fixture / ".claude" / "commands" / "trellis" / "record-session.md").read_text(encoding="utf-8"),
        )

    def test_uninstall_removes_agents_md_routing_section(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True, include_agents_md=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.assertIn("workflow-nl-routing-start", (fixture / "AGENTS.md").read_text(encoding="utf-8"))

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("AGENTS.md NL 路由表已删除", result.stdout)
        self.assertNotIn("workflow-nl-routing-start", (fixture / "AGENTS.md").read_text(encoding="utf-8"))

    def test_uninstall_removes_default_todo_file(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.assertTrue((fixture / "todo.txt").exists())

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("todo.txt 已删除", result.stdout)
        self.assertFalse((fixture / "todo.txt").exists())

    def test_uninstall_preserves_modified_todo_file(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        todo_path = fixture / "todo.txt"
        todo_path.write_text("自定义提醒\n", encoding="utf-8")

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("todo.txt 已被修改，保留现有内容", result.stdout)
        self.assertEqual(todo_path.read_text(encoding="utf-8"), "自定义提醒\n")


if __name__ == "__main__":
    unittest.main()
