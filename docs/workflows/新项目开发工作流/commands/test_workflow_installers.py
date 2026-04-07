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
FINISH_WORK_MARKER = "<!-- finish-work-projectization-patch -->"
RECORD_SESSION_MARKER = "## Record-Session Metadata Closure `[AI]`"
DEFAULT_PROJECT_TODO = "文档内容需要和实际当前的代码同步\n"
BASELINE_START_CONTENT = (
    "# /trellis:start\n\n"
    "Original baseline start command for fixture testing.\n\n"
    "## Operation Types\n\n"
    "| Marker | Meaning |\n"
    "|--------|---------|\n"
    "| `[AI]` | tool calls |\n"
    "| `[USER]` | user actions |\n"
)
BASELINE_RECORD_SESSION_CONTENT = (
    "# /trellis:record-session\n\n"
    "## Record Work Progress\n\n"
    "### Step 1: Get Context & Check Tasks\n\n"
    "```bash\n"
    "python3 ./.trellis/scripts/get_context.py --mode record\n"
    "```\n\n"
    "### Step 2: One-Click Add Session\n\n"
    "```bash\n"
    "python3 ./.trellis/scripts/add_session.py --title \"Title\" --commit \"hash\"\n"
    "```\n"
)
BASELINE_OPENCODE_RECORD_SESSION_CONTENT = (
    "# /trellis:record-session\n\n"
    "### Step 2: One-Click Add Session\n\n"
    "```bash\n"
    "python3 ./.trellis/scripts/add_session.py --title \"Title\" --commit \"hash\"\n"
    "```\n"
)
BASELINE_FINISH_WORK_CONTENT = (
    "# Finish Work - Pre-Commit Checklist\n\n"
    "Before submitting or committing, use this checklist to ensure work completeness.\n\n"
    "**Timing**: After code is written and tested, before commit\n\n"
    "---\n\n"
    "## Checklist\n\n"
    "### 1. Code Quality\n\n"
    "```bash\n"
    "# Must pass\n"
    "pnpm lint\n"
    "pnpm type-check\n"
    "pnpm test\n"
    "```\n\n"
    "- [ ] `pnpm lint` passes with 0 errors?\n"
    "- [ ] `pnpm type-check` passes with no type errors?\n"
    "- [ ] Tests pass?\n\n"
    "### 1.5. Test Coverage\n\n"
    "Check if your change needs new or updated tests.\n"
)
BASELINE_FINISH_WORK_WITHOUT_TEST_COVERAGE_CONTENT = (
    "# Finish Work - Pre-Commit Checklist\n\n"
    "Before submitting or committing, use this checklist to ensure work completeness.\n\n"
    "**Timing**: After code is written and tested, before commit\n\n"
    "---\n\n"
    "## Checklist\n\n"
    "### 1. Code Quality\n\n"
    "```bash\n"
    "# Must pass\n"
    "pnpm lint\n"
    "pnpm type-check\n"
    "pnpm test\n"
    "```\n\n"
    "- [ ] `pnpm lint` passes with 0 errors?\n"
    "- [ ] `pnpm type-check` passes with no type errors?\n"
    "- [ ] Tests pass?\n\n"
    "### 2. Code-Spec Sync\n\n"
    "Check code-spec updates.\n"
)


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
        include_multi_origin_push_urls: bool = True,
        include_trellis: bool = True,
        include_trellis_version: bool = True,
        include_bootstrap_task: bool = True,
    ) -> Path:
        root = Path(tempfile.mkdtemp(prefix="workflow-installers-"))
        if include_git:
            (root / ".git").mkdir(parents=True)
            push_urls = [
                "git@github.com:example/project.git",
                "git@gitee.com:example/project.git",
            ]
            if not include_multi_origin_push_urls:
                push_urls = push_urls[:1]
            config_lines = [
                "[core]",
                "\trepositoryformatversion = 0",
                "\tfilemode = true",
                "\tbare = false",
                "\tlogallrefupdates = true",
                '[remote "origin"]',
                "\turl = git@github.com:example/project.git",
                "\tfetch = +refs/heads/*:refs/remotes/origin/*",
            ]
            config_lines.extend(f"\tpushurl = {url}" for url in push_urls)
            (root / ".git" / "config").write_text("\n".join(config_lines) + "\n", encoding="utf-8")
        (root / ".claude" / "commands" / "trellis").mkdir(parents=True)
        if include_trellis:
            (root / ".trellis").mkdir(parents=True)
            if include_bootstrap_task:
                (root / ".trellis" / "tasks" / "00-bootstrap-guidelines").mkdir(parents=True)
                (root / ".trellis" / "tasks" / "00-bootstrap-guidelines" / "task.json").write_text(
                    '{"id":"00-bootstrap-guidelines"}\n',
                    encoding="utf-8",
                )
        (root / ".claude" / "commands" / "trellis" / "start.md").write_text(
            BASELINE_START_CONTENT,
            encoding="utf-8",
        )
        (root / ".claude" / "commands" / "trellis" / "finish-work.md").write_text(
            BASELINE_FINISH_WORK_CONTENT,
            encoding="utf-8",
        )
        (root / ".claude" / "commands" / "trellis" / "record-session.md").write_text(
            BASELINE_RECORD_SESSION_CONTENT,
            encoding="utf-8",
        )
        if include_trellis and include_trellis_version:
            (root / ".trellis" / ".version").write_text("2.0.0\n", encoding="utf-8")
        if include_opencode:
            (root / ".opencode" / "commands" / "trellis").mkdir(parents=True)
            (root / ".opencode" / "commands" / "trellis" / "start.md").write_text(
                BASELINE_START_CONTENT.replace("Original baseline", "Original OpenCode baseline"),
                encoding="utf-8",
            )
            (root / ".opencode" / "commands" / "trellis" / "finish-work.md").write_text(
                BASELINE_FINISH_WORK_CONTENT,
                encoding="utf-8",
            )
            (root / ".opencode" / "commands" / "trellis" / "record-session.md").write_text(
                BASELINE_OPENCODE_RECORD_SESSION_CONTENT,
                encoding="utf-8",
            )
        if include_codex:
            (root / ".agents" / "skills").mkdir(parents=True)
            (root / ".agents" / "skills" / "finish-work").mkdir(parents=True)
            (root / ".agents" / "skills" / "finish-work" / "SKILL.md").write_text(
                BASELINE_FINISH_WORK_CONTENT,
                encoding="utf-8",
            )
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
        finish_work = fixture / ".claude" / "commands" / "trellis" / "finish-work.md"
        finish_work_text = finish_work.read_text(encoding="utf-8")
        self.assertIn(FINISH_WORK_MARKER, finish_work_text)
        self.assertNotIn("pnpm lint", finish_work_text)
        record_session = fixture / ".claude" / "commands" / "trellis" / "record-session.md"
        self.assertIn(RECORD_SESSION_MARKER, record_session.read_text(encoding="utf-8"))

        record = fixture / ".trellis" / "workflow-installed.json"
        self.assertTrue(record.exists(), "workflow-installed.json should be created")
        self.assertIn("brainstorm", record.read_text(encoding="utf-8"))
        self.assertIn("metadata-autocommit-guard.py", record.read_text(encoding="utf-8"))
        self.assertIn("record-session-helper.py", record.read_text(encoding="utf-8"))
        self.assertIn("pack.requirements-discovery-foundation", record.read_text(encoding="utf-8"))

    def test_install_patches_finish_work_for_opencode_and_codex(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        opencode_finish_work = fixture / ".opencode" / "commands" / "trellis" / "finish-work.md"
        codex_finish_work = fixture / ".agents" / "skills" / "finish-work" / "SKILL.md"
        self.assertIn(FINISH_WORK_MARKER, opencode_finish_work.read_text(encoding="utf-8"))
        self.assertIn(FINISH_WORK_MARKER, codex_finish_work.read_text(encoding="utf-8"))
        self.assertNotIn("pnpm test", opencode_finish_work.read_text(encoding="utf-8"))
        self.assertNotIn("pnpm test", codex_finish_work.read_text(encoding="utf-8"))

    def test_install_patches_finish_work_when_test_coverage_heading_is_missing(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)
        finish_work = fixture / ".claude" / "commands" / "trellis" / "finish-work.md"
        finish_work.write_text(BASELINE_FINISH_WORK_WITHOUT_TEST_COVERAGE_CONTENT, encoding="utf-8")

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        patched_text = finish_work.read_text(encoding="utf-8")
        self.assertIn(FINISH_WORK_MARKER, patched_text)
        self.assertIn("### 2. Code-Spec Sync", patched_text)
        self.assertNotIn("pnpm lint", patched_text)

    def test_install_imports_requirements_foundation_and_removes_bootstrap_task(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        lock_path = fixture / ".trellis" / "library-lock.yaml"
        self.assertTrue(lock_path.exists(), "library-lock.yaml should be created during installation")
        lock_text = lock_path.read_text(encoding="utf-8")
        self.assertIn("pack.requirements-discovery-foundation", lock_text)
        self.assertIn("spec.universal-domains.product-and-requirements.problem-definition", lock_text)
        self.assertFalse((fixture / ".trellis" / "tasks" / "00-bootstrap-guidelines").exists())
        self.assertIn("初始 spec 基线已导入", install.stdout)
        self.assertIn("Trellis bootstrap 任务已删除", install.stdout)

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

    def test_install_requires_multiple_origin_push_urls(self) -> None:
        fixture = self.create_fixture(include_multi_origin_push_urls=False)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertNotEqual(install.returncode, 0)
        self.assertIn("origin", install.stderr)
        self.assertIn("至少需要 2 个 push URL", install.stderr)

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

    def test_upgrade_check_detects_finish_work_patch_drift(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        finish_work = fixture / ".claude" / "commands" / "trellis" / "finish-work.md"
        content = finish_work.read_text(encoding="utf-8").replace(FINISH_WORK_MARKER, "<!-- missing -->")
        finish_work.write_text(content, encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(UPGRADE_SCRIPT, "--check", "--project-root", str(fixture))

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("finish-work.md: 项目化补丁缺失", result.stdout)

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

    def test_upgrade_check_reports_missing_record_session_file(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        (fixture / ".claude" / "commands" / "trellis" / "record-session.md").unlink()
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(UPGRADE_SCRIPT, "--check", "--project-root", str(fixture))

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("record-session.md: 文件缺失", result.stdout)

    def test_upgrade_merge_restores_drift_and_followup_check_passes(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        start = fixture / ".claude" / "commands" / "trellis" / "start.md"
        finish_work = fixture / ".claude" / "commands" / "trellis" / "finish-work.md"
        record_session = fixture / ".claude" / "commands" / "trellis" / "record-session.md"
        start.write_text(BASELINE_START_CONTENT, encoding="utf-8")
        finish_work.write_text(BASELINE_FINISH_WORK_CONTENT, encoding="utf-8")
        record_session.write_text(BASELINE_RECORD_SESSION_CONTENT, encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        merge = self.run_script(UPGRADE_SCRIPT, "--merge", "--project-root", str(fixture))

        self.assertEqual(merge.returncode, 0, msg=merge.stdout + merge.stderr)
        self.assertIn(PHASE_ROUTER_MARKER, start.read_text(encoding="utf-8"))
        self.assertIn(FINISH_WORK_MARKER, finish_work.read_text(encoding="utf-8"))
        self.assertIn(RECORD_SESSION_MARKER, record_session.read_text(encoding="utf-8"))

        followup_check = self.run_script(UPGRADE_SCRIPT, "--check", "--project-root", str(fixture))
        self.assertEqual(followup_check.returncode, 0, msg=followup_check.stdout + followup_check.stderr)

    def test_force_restores_finish_work_from_backup_and_reapplies_patch(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        finish_work = fixture / ".claude" / "commands" / "trellis" / "finish-work.md"
        finish_work.write_text("# broken finish-work\n\nmissing expected sections\n", encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(UPGRADE_SCRIPT, "--force", "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        restored_text = finish_work.read_text(encoding="utf-8")
        self.assertIn(FINISH_WORK_MARKER, restored_text)
        self.assertNotIn("pnpm lint", restored_text)

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
        finish_work = (fixture / ".claude" / "commands" / "trellis" / "finish-work.md").read_text(encoding="utf-8")
        self.assertNotIn(FINISH_WORK_MARKER, finish_work)
        self.assertIn("pnpm lint", finish_work)
        self.assertNotIn(
            RECORD_SESSION_MARKER,
            (fixture / ".claude" / "commands" / "trellis" / "record-session.md").read_text(encoding="utf-8"),
        )

    def test_uninstall_restores_codex_finish_work_skill(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        patched_skill = fixture / ".agents" / "skills" / "finish-work" / "SKILL.md"
        self.assertIn(FINISH_WORK_MARKER, patched_skill.read_text(encoding="utf-8"))

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        restored_text = patched_skill.read_text(encoding="utf-8")
        self.assertNotIn(FINISH_WORK_MARKER, restored_text)
        self.assertIn("pnpm lint", restored_text)

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
