from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
import json


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
PARALLEL_DISABLED_MARKER = "<!-- workflow-parallel-disabled -->"
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
BASELINE_CHECK_CONTENT = (
    "# /trellis:check\n\n"
    "Check if the code you just wrote follows the development guidelines.\n\n"
    "1. Identify changed files.\n"
)
BASELINE_BRAINSTORM_CONTENT = (
    "# /trellis:brainstorm\n\n"
    "Clarify requirements before implementation.\n"
)
BASELINE_PARALLEL_CONTENT = (
    "# /trellis:parallel\n\n"
    "Run a worktree-based parallel pipeline and finish with a PR.\n"
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
    def run_script(
        self,
        script: Path,
        *args: str,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        return subprocess.run(
            [PYTHON, str(script), *args],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            env=merged_env,
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
        current_branch: str = "main",
        has_local_history: bool = False,
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
            (root / ".git" / "HEAD").write_text(f"ref: refs/heads/{current_branch}\n", encoding="utf-8")
            if has_local_history:
                ref_path = root / ".git" / "refs" / "heads" / current_branch
                ref_path.parent.mkdir(parents=True, exist_ok=True)
                ref_path.write_text("0123456789abcdef0123456789abcdef01234567\n", encoding="utf-8")
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
        (root / ".claude" / "commands" / "trellis" / "brainstorm.md").write_text(
            BASELINE_BRAINSTORM_CONTENT,
            encoding="utf-8",
        )
        (root / ".claude" / "commands" / "trellis" / "check.md").write_text(
            BASELINE_CHECK_CONTENT,
            encoding="utf-8",
        )
        (root / ".claude" / "commands" / "trellis" / "parallel.md").write_text(
            BASELINE_PARALLEL_CONTENT,
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
            (root / ".opencode" / "commands" / "trellis" / "brainstorm.md").write_text(
                BASELINE_BRAINSTORM_CONTENT,
                encoding="utf-8",
            )
            (root / ".opencode" / "commands" / "trellis" / "check.md").write_text(
                BASELINE_CHECK_CONTENT,
                encoding="utf-8",
            )
            (root / ".opencode" / "commands" / "trellis" / "parallel.md").write_text(
                BASELINE_PARALLEL_CONTENT,
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
            (root / ".agents" / "skills" / "brainstorm").mkdir(parents=True)
            (root / ".agents" / "skills" / "brainstorm" / "SKILL.md").write_text(
                BASELINE_BRAINSTORM_CONTENT,
                encoding="utf-8",
            )
            (root / ".agents" / "skills" / "check").mkdir(parents=True)
            (root / ".agents" / "skills" / "check" / "SKILL.md").write_text(
                BASELINE_CHECK_CONTENT,
                encoding="utf-8",
            )
            (root / ".agents" / "skills" / "parallel").mkdir(parents=True)
            (root / ".agents" / "skills" / "parallel" / "SKILL.md").write_text(
                BASELINE_PARALLEL_CONTENT,
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

    def latest_env_for(self, fixture_root: Path) -> dict[str, str]:
        version_path = fixture_root / ".trellis" / ".version"
        return {"TRELLIS_LATEST_VERSION": version_path.read_text(encoding="utf-8").strip()}

    def test_install_deploys_record_session_closure_helper_and_patch(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        brainstorm = fixture / ".claude" / "commands" / "trellis" / "brainstorm.md"
        self.assertTrue(brainstorm.exists(), "brainstorm.md should be deployed")
        project_audit = fixture / ".claude" / "commands" / "trellis" / "project-audit.md"
        self.assertTrue(project_audit.exists(), "project-audit.md should be deployed")
        helper = fixture / ".trellis" / "scripts" / "workflow" / "metadata-autocommit-guard.py"
        self.assertTrue(helper.exists(), "metadata-autocommit-guard.py should be deployed")
        record_helper = fixture / ".trellis" / "scripts" / "workflow" / "record-session-helper.py"
        self.assertTrue(record_helper.exists(), "record-session-helper.py should be deployed")
        workflow_state_helper = fixture / ".trellis" / "scripts" / "workflow" / "workflow-state.py"
        self.assertTrue(workflow_state_helper.exists(), "workflow-state.py should be deployed")
        ownership_helper = fixture / ".trellis" / "scripts" / "workflow" / "ownership-proof-validate.py"
        self.assertTrue(ownership_helper.exists(), "ownership-proof-validate.py should be deployed")
        finish_work = fixture / ".claude" / "commands" / "trellis" / "finish-work.md"
        finish_work_text = finish_work.read_text(encoding="utf-8")
        self.assertIn(FINISH_WORK_MARKER, finish_work_text)
        self.assertNotIn("pnpm lint", finish_work_text)
        # 补丁已条件化：验证质量平台门禁口径，不再硬断言特定 sonar 内容
        self.assertIn("质量平台门禁", finish_work_text)
        record_session = fixture / ".claude" / "commands" / "trellis" / "record-session.md"
        rs_text = record_session.read_text(encoding="utf-8")
        self.assertIn(RECORD_SESSION_MARKER, rs_text)
        # Verify close-out order: record-session-helper must appear before archive
        helper_pos = rs_text.find("record-session-helper.py")
        archive_pos = rs_text.find("task.py archive")
        if helper_pos >= 0 and archive_pos >= 0:
            self.assertLess(
                helper_pos,
                archive_pos,
                "record-session-helper.py must appear before 'task.py archive' in the patch — "
                "close-out order is record-session first, then archive",
            )

        record = fixture / ".trellis" / "workflow-installed.json"
        self.assertTrue(record.exists(), "workflow-installed.json should be created")
        record_data = json.loads(record.read_text(encoding="utf-8"))
        self.assertIn("brainstorm", record_data["commands"])
        self.assertIn("project-audit", record_data["commands"])
        self.assertEqual(record_data["overlay_commands"], ["brainstorm", "check"])
        self.assertEqual(record_data["disabled_commands"], ["parallel"])
        self.assertEqual(
            record_data["patched_baseline_commands"],
            ["start", "finish-work", "record-session"],
        )
        self.assertIn("metadata-autocommit-guard.py", record_data["scripts"])
        self.assertIn("ownership-proof-validate.py", record_data["scripts"])
        self.assertIn("record-session-helper.py", record_data["scripts"])
        self.assertIn("workflow-state.py", record_data["scripts"])
        self.assertEqual(record_data["workflow_version"], "0.1.24")
        self.assertEqual(record_data["workflow_schema_version"], "1")
        self.assertEqual(record_data["initial_pack"], "pack.requirements-discovery-foundation")
        parallel = fixture / ".claude" / "commands" / "trellis" / "parallel.md"
        self.assertIn(PARALLEL_DISABLED_MARKER, parallel.read_text(encoding="utf-8"))

    def test_install_patches_finish_work_for_opencode_and_codex(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        opencode_finish_work = fixture / ".opencode" / "commands" / "trellis" / "finish-work.md"
        codex_finish_work = fixture / ".agents" / "skills" / "finish-work" / "SKILL.md"
        opencode_parallel = fixture / ".opencode" / "commands" / "trellis" / "parallel.md"
        codex_parallel = fixture / ".agents" / "skills" / "parallel" / "SKILL.md"
        opencode_text = opencode_finish_work.read_text(encoding="utf-8")
        codex_text = codex_finish_work.read_text(encoding="utf-8")
        self.assertIn(FINISH_WORK_MARKER, opencode_text)
        self.assertIn(FINISH_WORK_MARKER, codex_text)
        self.assertNotIn("pnpm test", opencode_text)
        self.assertNotIn("pnpm test", codex_text)
        # 补丁已条件化：验证质量平台门禁口径，不再硬断言特定 sonar 内容
        self.assertIn("质量平台门禁", opencode_text)
        self.assertIn("质量平台门禁", codex_text)
        self.assertIn(PARALLEL_DISABLED_MARKER, opencode_parallel.read_text(encoding="utf-8"))
        self.assertIn(PARALLEL_DISABLED_MARKER, codex_parallel.read_text(encoding="utf-8"))

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

    def test_install_requires_main_branch_for_new_project(self) -> None:
        fixture = self.create_fixture(current_branch="master", has_local_history=False)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertNotEqual(install.returncode, 0)
        self.assertIn("主分支和初始分支必须使用 `main`", install.stderr)
        self.assertIn("git branch -M main", install.stderr)

    def test_install_allows_existing_project_to_keep_non_main_branch(self) -> None:
        fixture = self.create_fixture(current_branch="release/1.x", has_local_history=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.assertIn("不强制改为 `main`", install.stdout)

    def test_install_requires_codex_baseline_finish_work_skill(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)
        (fixture / ".agents" / "skills" / "finish-work" / "SKILL.md").unlink()

        install = self.install_workflow(fixture)

        self.assertNotEqual(install.returncode, 0)
        self.assertIn(
            "所有 skills 目录均缺少 finish-work 基线", install.stdout + install.stderr
        )
        self.assertFalse((fixture / ".trellis" / "workflow-installed.json").exists())

    def test_install_codex_syncs_all_skills_dirs_without_requiring_finish_work_everywhere(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)
        codex_parallel = fixture / ".codex" / "skills" / "parallel" / "SKILL.md"
        codex_parallel.parent.mkdir(parents=True, exist_ok=True)
        codex_parallel.write_text(BASELINE_PARALLEL_CONTENT, encoding="utf-8")

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.assertIn(".codex/skills 缺少 finish-work 基线，跳过该项目化补丁", install.stdout)
        self.assertTrue((fixture / ".agents" / "skills" / "delivery" / "SKILL.md").exists())
        self.assertTrue((fixture / ".codex" / "skills" / "delivery" / "SKILL.md").exists())
        self.assertFalse((fixture / ".codex" / "skills" / "finish-work" / "SKILL.md").exists())
        self.assertIn(
            PARALLEL_DISABLED_MARKER,
            (fixture / ".codex" / "skills" / "parallel" / "SKILL.md").read_text(encoding="utf-8"),
        )

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
        self.assertFalse((fixture / ".agents" / "skills" / "review-gate").exists())
        self.assertNotIn("workflow-nl-routing-start", (fixture / "AGENTS.md").read_text(encoding="utf-8"))

    def test_upgrade_check_detects_phase_router_drift_even_when_versions_match(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        backup_start = fixture / ".claude" / "commands" / "trellis" / ".backup-original" / "start.md"
        target_start = fixture / ".claude" / "commands" / "trellis" / "start.md"
        shutil.copy2(backup_start, target_start)

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

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

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("辅助脚本缺失", result.stdout)
        self.assertIn("record-session-helper.py", result.stdout)

    def test_upgrade_check_blocks_when_target_is_not_latest_trellis(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env={"TRELLIS_LATEST_VERSION": "2.1.0"},
        )

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("尚未升级到当前最新 Trellis", result.stdout)
        self.assertIn("禁止执行当前步骤", result.stdout)

    def test_upgrade_check_detects_helper_script_drift_for_opencode_only(self) -> None:
        fixture = self.create_fixture(include_opencode=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        helper = fixture / ".trellis" / "scripts" / "workflow" / "check-quality.py"
        helper.write_text(helper.read_text(encoding="utf-8") + "\n# drift\n", encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--cli",
            "opencode",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("辅助脚本内容漂移", result.stdout)
        self.assertIn("check-quality.py", result.stdout)

    def test_upgrade_check_detects_install_record_schema_drift(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        record_path = fixture / ".trellis" / "workflow-installed.json"
        record_data = json.loads(record_path.read_text(encoding="utf-8"))
        record_data.pop("patched_baseline_commands", None)
        record_data.pop("initial_pack", None)
        record_data.pop("bootstrap_task_removed", None)
        record_path.write_text(json.dumps(record_data, ensure_ascii=False, indent=2), encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("workflow-installed.json 缺少字段", result.stdout)
        self.assertIn("patched_baseline_commands", result.stdout)
        self.assertIn("initial_pack", result.stdout)
        self.assertIn("bootstrap_task_removed", result.stdout)

    def test_upgrade_check_allows_legacy_missing_version_keys(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        record_path = fixture / ".trellis" / "workflow-installed.json"
        record_data = json.loads(record_path.read_text(encoding="utf-8"))
        record_data.pop("workflow_version", None)
        record_data.pop("workflow_schema_version", None)
        record_path.write_text(json.dumps(record_data, ensure_ascii=False, indent=2), encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertNotIn("workflow-installed.json 缺少字段", result.stdout)
        self.assertIn("legacy/unknown", result.stdout)

    def test_upgrade_check_detects_codex_secondary_skills_dir_parallel_drift(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)
        codex_parallel = fixture / ".codex" / "skills" / "parallel" / "SKILL.md"
        codex_parallel.parent.mkdir(parents=True, exist_ok=True)
        codex_parallel.write_text(BASELINE_PARALLEL_CONTENT, encoding="utf-8")

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        codex_parallel.write_text("# drifted parallel\n", encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn(".codex/skills", result.stdout)
        self.assertIn("parallel skill (.codex/skills): 禁用覆盖漂移", result.stdout)

    def test_upgrade_check_detects_record_session_patch_drift(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        record_session = fixture / ".claude" / "commands" / "trellis" / "record-session.md"
        content = record_session.read_text(encoding="utf-8").replace(RECORD_SESSION_MARKER, "## Missing Marker")
        record_session.write_text(content, encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("record-session.md: 元数据闭环说明缺失", result.stdout)

    def test_upgrade_check_detects_brainstorm_command_drift(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        brainstorm = fixture / ".claude" / "commands" / "trellis" / "brainstorm.md"
        brainstorm.write_text("# drifted brainstorm\n", encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("命令内容漂移: /trellis:brainstorm", result.stdout)

    def test_upgrade_check_detects_check_command_drift(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        check = fixture / ".claude" / "commands" / "trellis" / "check.md"
        check.write_text("# drifted check\n", encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("命令内容漂移: /trellis:check", result.stdout)

    def test_upgrade_check_detects_finish_work_patch_drift(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        finish_work = fixture / ".claude" / "commands" / "trellis" / "finish-work.md"
        content = finish_work.read_text(encoding="utf-8").replace(FINISH_WORK_MARKER, "<!-- missing -->")
        finish_work.write_text(content, encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

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

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--force",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

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

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

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

        merge = self.run_script(
            UPGRADE_SCRIPT,
            "--merge",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(merge.returncode, 0, msg=merge.stdout + merge.stderr)
        self.assertIn(PHASE_ROUTER_MARKER, start.read_text(encoding="utf-8"))
        self.assertIn(FINISH_WORK_MARKER, finish_work.read_text(encoding="utf-8"))
        self.assertIn(RECORD_SESSION_MARKER, record_session.read_text(encoding="utf-8"))
        record_data = json.loads((fixture / ".trellis" / "workflow-installed.json").read_text(encoding="utf-8"))
        self.assertEqual(record_data["workflow_version"], "0.1.24")
        self.assertEqual(record_data["previous_version"], "2.0.0")

        followup_check = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )
        self.assertEqual(followup_check.returncode, 0, msg=followup_check.stdout + followup_check.stderr)

    def test_upgrade_merge_updates_codex_secondary_skills_dir(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)
        codex_parallel = fixture / ".codex" / "skills" / "parallel" / "SKILL.md"
        codex_parallel.parent.mkdir(parents=True, exist_ok=True)
        codex_parallel.write_text(BASELINE_PARALLEL_CONTENT, encoding="utf-8")

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        codex_delivery = fixture / ".codex" / "skills" / "delivery" / "SKILL.md"
        codex_delivery.write_text("# drifted delivery\n", encoding="utf-8")
        codex_parallel.write_text("# drifted parallel\n", encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        merge = self.run_script(
            UPGRADE_SCRIPT,
            "--merge",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(merge.returncode, 0, msg=merge.stdout + merge.stderr)
        self.assertIn(
            "# /trellis:delivery",
            codex_delivery.read_text(encoding="utf-8"),
        )
        self.assertIn(
            PARALLEL_DISABLED_MARKER,
            codex_parallel.read_text(encoding="utf-8"),
        )

    def test_upgrade_merge_preserves_bootstrap_cleanup_status(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        record_path = fixture / ".trellis" / "workflow-installed.json"
        record_data = json.loads(record_path.read_text(encoding="utf-8"))
        self.assertEqual(record_data["bootstrap_cleanup_status"], "removed")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        merge = self.run_script(
            UPGRADE_SCRIPT,
            "--merge",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(merge.returncode, 0, msg=merge.stdout + merge.stderr)
        updated_record = json.loads(record_path.read_text(encoding="utf-8"))
        self.assertEqual(updated_record["bootstrap_cleanup_status"], "removed")

    def test_force_restores_codex_secondary_parallel_backup_without_finish_work(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)
        codex_parallel = fixture / ".codex" / "skills" / "parallel" / "SKILL.md"
        codex_parallel.parent.mkdir(parents=True, exist_ok=True)
        codex_parallel.write_text(BASELINE_PARALLEL_CONTENT, encoding="utf-8")

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        backup_parallel = fixture / ".codex" / "skills" / ".backup-original" / "parallel" / "SKILL.md"
        self.assertTrue(backup_parallel.exists())
        codex_parallel.write_text("# drifted parallel\n", encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--force",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn(
            "[Codex] parallel skill 已从 .backup-original 恢复",
            result.stdout,
        )
        self.assertIn(
            PARALLEL_DISABLED_MARKER,
            codex_parallel.read_text(encoding="utf-8"),
        )

    def test_force_restores_finish_work_from_backup_and_reapplies_patch(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        finish_work = fixture / ".claude" / "commands" / "trellis" / "finish-work.md"
        finish_work.write_text("# broken finish-work\n\nmissing expected sections\n", encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--force",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

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

    def test_uninstall_restores_overlapped_baseline_check_command(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        patched_check = fixture / ".claude" / "commands" / "trellis" / "check.md"
        self.assertIn("/trellis:check", patched_check.read_text(encoding="utf-8"))
        self.assertEqual(
            (fixture / ".claude" / "commands" / "trellis" / ".backup-original" / "check.md").read_text(encoding="utf-8"),
            BASELINE_CHECK_CONTENT,
        )

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        restored_text = patched_check.read_text(encoding="utf-8")
        self.assertEqual(restored_text, BASELINE_CHECK_CONTENT)

    def test_uninstall_restores_overlapped_baseline_brainstorm_command(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        patched_brainstorm = fixture / ".claude" / "commands" / "trellis" / "brainstorm.md"
        self.assertIn("/trellis:brainstorm", patched_brainstorm.read_text(encoding="utf-8"))
        self.assertEqual(
            (fixture / ".claude" / "commands" / "trellis" / ".backup-original" / "brainstorm.md").read_text(encoding="utf-8"),
            BASELINE_BRAINSTORM_CONTENT,
        )

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        restored_text = patched_brainstorm.read_text(encoding="utf-8")
        self.assertEqual(restored_text, BASELINE_BRAINSTORM_CONTENT)

    def test_uninstall_restores_disabled_parallel_command(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        patched_parallel = fixture / ".claude" / "commands" / "trellis" / "parallel.md"
        self.assertIn(PARALLEL_DISABLED_MARKER, patched_parallel.read_text(encoding="utf-8"))
        self.assertEqual(
            (fixture / ".claude" / "commands" / "trellis" / ".backup-original" / "parallel.md").read_text(encoding="utf-8"),
            BASELINE_PARALLEL_CONTENT,
        )

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        restored_text = patched_parallel.read_text(encoding="utf-8")
        self.assertEqual(restored_text, BASELINE_PARALLEL_CONTENT)

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
