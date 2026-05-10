from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
import json

from workflow_assets import HELPER_SCRIPTS


REPO_ROOT = Path(__file__).resolve().parents[4]
PYTHON = (
    "/ops/softwares/python/bin/python3"
    if Path("/ops/softwares/python/bin/python3").exists()
    else shutil.which("python3") or shutil.which("python")
)
COMMANDS_DIR = REPO_ROOT / "docs" / "workflows" / "新项目开发工作流" / "commands"
INSTALL_SCRIPT = COMMANDS_DIR / "install-workflow.py"
DETECT_EMBED_STATE_SCRIPT = COMMANDS_DIR / "detect-embed-state.py"
UPGRADE_SCRIPT = COMMANDS_DIR / "upgrade-compat.py"
UNINSTALL_SCRIPT = COMMANDS_DIR / "uninstall-workflow.py"
EMBED_CONFIRM_ENV = "WORKFLOW_EMBED_EXECUTOR_CONFIRMED"
ATTEMPT_RECORD_NAME = "workflow-embed-attempt.json"
PHASE_ROUTER_MARKER = "## Phase Router `[AI]`"
FINISH_WORK_MARKER = "<!-- finish-work-projectization-patch -->"
PARALLEL_DISABLED_MARKER = "<!-- workflow-parallel-disabled -->"
WORKFLOW_PATCH_MARKER = "<!-- workflow-projectization-patch -->"
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
BASELINE_CONTINUE_CONTENT = (
    "# Continue Current Task\n\n"
    "Original baseline continue command for fixture testing.\n"
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
BASELINE_START_SKILL_CONTENT = (
    "---\n"
    "name: start\n"
    "description: Baseline start skill\n"
    "---\n\n"
    "# Start Session\n\n"
    "Original baseline Codex start skill.\n"
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
BASELINE_WORKFLOW_CONTENT = (
    "## Development Process\n\n"
    "### Task Development Flow\n\n"
    "```\n"
    "1. Create or select task\n"
    "2. Start task\n"
    "3. Write code\n"
    "4. Self-test\n"
    "5. Commit code\n"
    "6. Record session\n"
    "7. Finish task\n"
    "```\n\n"
    "## Session End\n\n"
    "### One-Click Session Recording\n\n"
    "Use add_session.py directly.\n\n"
    "## File Descriptions\n\n"
    "### 1. workspace/ - Developer Workspaces\n"
)
BASELINE_TRELLIS_CONTINUE_SKILL_CONTENT = (
    "---\n"
    "name: trellis-continue\n"
    "description: Baseline continue skill\n"
    "---\n\n"
    "# Continue Current Task\n\n"
    "Original baseline Codex continue skill.\n"
)
BASELINE_TRELLIS_FINISH_WORK_SKILL_CONTENT = (
    "---\n"
    "name: trellis-finish-work\n"
    "description: Baseline finish-work skill\n"
    "---\n\n"
    + BASELINE_FINISH_WORK_CONTENT
)
BASELINE_TRELLIS_BRAINSTORM_SKILL_CONTENT = (
    "---\n"
    "name: trellis-brainstorm\n"
    "description: Baseline brainstorm skill\n"
    "---\n\n"
    + BASELINE_BRAINSTORM_CONTENT
)
BASELINE_TRELLIS_CHECK_SKILL_CONTENT = (
    "---\n"
    "name: trellis-check\n"
    "description: Baseline check skill\n"
    "---\n\n"
    + BASELINE_CHECK_CONTENT
)
BASELINE_AGENT_RESEARCH_MD = (
    "---\n"
    "name: trellis-research\n"
    "description: baseline research\n"
    "---\n\n"
    "# Research Agent\n"
)
BASELINE_AGENT_IMPLEMENT_MD = (
    "---\n"
    "name: trellis-implement\n"
    "description: baseline implement\n"
    "---\n\n"
    "# Implement Agent\n"
)
BASELINE_AGENT_CHECK_MD = (
    "---\n"
    "name: trellis-check\n"
    "description: baseline check\n"
    "---\n\n"
    "# Check Agent\n"
)
BASELINE_CODEX_RESEARCH_TOML = (
    'name = "trellis-research"\n'
    'description = "baseline research"\n'
    'sandbox_mode = "read-only"\n'
)
BASELINE_CODEX_IMPLEMENT_TOML = (
    'name = "trellis-implement"\n'
    'description = "baseline implement"\n'
    'sandbox_mode = "workspace-write"\n'
)
BASELINE_CODEX_CHECK_TOML = (
    'name = "trellis-check"\n'
    'description = "baseline check"\n'
    'sandbox_mode = "read-only"\n'
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
        bootstrap_as_current_task: bool = False,
        current_branch: str = "main",
        has_local_history: bool = False,
        use_latest_trellis_baseline: bool = True,
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
            (root / ".trellis" / "workflow.md").write_text(
                BASELINE_WORKFLOW_CONTENT,
                encoding="utf-8",
            )
            if include_bootstrap_task:
                (root / ".trellis" / "tasks" / "00-bootstrap-guidelines").mkdir(parents=True)
                (root / ".trellis" / "tasks" / "00-bootstrap-guidelines" / "task.json").write_text(
                    '{"id":"00-bootstrap-guidelines"}\n',
                    encoding="utf-8",
                )
                if bootstrap_as_current_task:
                    (root / ".trellis" / ".current-task").write_text(
                        ".trellis/tasks/00-bootstrap-guidelines\n",
                        encoding="utf-8",
                    )
        claude_entry_name = "continue.md" if use_latest_trellis_baseline else "start.md"
        claude_entry_content = BASELINE_CONTINUE_CONTENT if use_latest_trellis_baseline else BASELINE_START_CONTENT
        (root / ".claude" / "commands" / "trellis" / claude_entry_name).write_text(
            claude_entry_content,
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
        (root / ".claude" / "agents").mkdir(parents=True, exist_ok=True)
        claude_agent_prefix = "trellis-" if use_latest_trellis_baseline else ""
        (root / ".claude" / "agents" / f"{claude_agent_prefix}research.md").write_text(BASELINE_AGENT_RESEARCH_MD, encoding="utf-8")
        (root / ".claude" / "agents" / f"{claude_agent_prefix}implement.md").write_text(BASELINE_AGENT_IMPLEMENT_MD, encoding="utf-8")
        (root / ".claude" / "agents" / f"{claude_agent_prefix}check.md").write_text(BASELINE_AGENT_CHECK_MD, encoding="utf-8")
        if include_trellis and include_trellis_version:
            version = "0.5.0-rc.3" if use_latest_trellis_baseline else "2.0.0"
            (root / ".trellis" / ".version").write_text(f"{version}\n", encoding="utf-8")
        if include_opencode:
            (root / ".opencode" / "commands" / "trellis").mkdir(parents=True)
            opencode_entry_name = "continue.md" if use_latest_trellis_baseline else "start.md"
            opencode_entry_content = (
                BASELINE_CONTINUE_CONTENT.replace("Original baseline", "Original OpenCode baseline")
                if use_latest_trellis_baseline
                else BASELINE_START_CONTENT.replace("Original baseline", "Original OpenCode baseline")
            )
            (root / ".opencode" / "commands" / "trellis" / opencode_entry_name).write_text(
                opencode_entry_content,
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
            (root / ".opencode" / "agents").mkdir(parents=True)
            opencode_agent_prefix = "trellis-" if use_latest_trellis_baseline else ""
            (root / ".opencode" / "agents" / f"{opencode_agent_prefix}research.md").write_text(BASELINE_AGENT_RESEARCH_MD, encoding="utf-8")
            (root / ".opencode" / "agents" / f"{opencode_agent_prefix}implement.md").write_text(BASELINE_AGENT_IMPLEMENT_MD, encoding="utf-8")
            (root / ".opencode" / "agents" / f"{opencode_agent_prefix}check.md").write_text(BASELINE_AGENT_CHECK_MD, encoding="utf-8")
        if include_codex:
            (root / ".agents" / "skills").mkdir(parents=True)
            (root / ".agents" / "skills" / "trellis-continue").mkdir(parents=True)
            (root / ".agents" / "skills" / "trellis-continue" / "SKILL.md").write_text(
                BASELINE_TRELLIS_CONTINUE_SKILL_CONTENT,
                encoding="utf-8",
            )
            (root / ".agents" / "skills" / "trellis-finish-work").mkdir(parents=True)
            (root / ".agents" / "skills" / "trellis-finish-work" / "SKILL.md").write_text(
                BASELINE_TRELLIS_FINISH_WORK_SKILL_CONTENT,
                encoding="utf-8",
            )
            (root / ".agents" / "skills" / "trellis-brainstorm").mkdir(parents=True)
            (root / ".agents" / "skills" / "trellis-brainstorm" / "SKILL.md").write_text(
                BASELINE_TRELLIS_BRAINSTORM_SKILL_CONTENT,
                encoding="utf-8",
            )
            (root / ".agents" / "skills" / "trellis-check").mkdir(parents=True)
            (root / ".agents" / "skills" / "trellis-check" / "SKILL.md").write_text(
                BASELINE_TRELLIS_CHECK_SKILL_CONTENT,
                encoding="utf-8",
            )
            (root / ".agents" / "skills" / "parallel").mkdir(parents=True)
            (root / ".agents" / "skills" / "parallel" / "SKILL.md").write_text(
                BASELINE_PARALLEL_CONTENT,
                encoding="utf-8",
            )
            (root / ".codex" / "hooks").mkdir(parents=True)
            (root / ".codex" / "agents").mkdir(parents=True)
            (root / ".codex" / "hooks.json").write_text("{}", encoding="utf-8")
            (root / ".codex" / "hooks" / "session-start.py").write_text("# hook\n", encoding="utf-8")
            codex_agent_prefix = "trellis-" if use_latest_trellis_baseline else ""
            (root / ".codex" / "agents" / f"{codex_agent_prefix}research.toml").write_text(BASELINE_CODEX_RESEARCH_TOML, encoding="utf-8")
            (root / ".codex" / "agents" / f"{codex_agent_prefix}implement.toml").write_text(BASELINE_CODEX_IMPLEMENT_TOML, encoding="utf-8")
            (root / ".codex" / "agents" / f"{codex_agent_prefix}check.toml").write_text(BASELINE_CODEX_CHECK_TOML, encoding="utf-8")
        if include_agents_md:
            (root / "AGENTS.md").write_text("# Project Rules\n", encoding="utf-8")
        return root

    def install_workflow(self, fixture_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return self.run_script(
            INSTALL_SCRIPT,
            "--project-root",
            str(fixture_root),
            *args,
            env={EMBED_CONFIRM_ENV: "1"},
        )

    def detect_embed_state(self, fixture_root: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return self.run_script(DETECT_EMBED_STATE_SCRIPT, "--project-root", str(fixture_root), *args, env=env)

    def latest_env_for(self, fixture_root: Path) -> dict[str, str]:
        version_path = fixture_root / ".trellis" / ".version"
        return {"TRELLIS_LATEST_VERSION": version_path.read_text(encoding="utf-8").strip()}

    def mark_legacy_codex_installed(self, fixture_root: Path) -> None:
        record_path = fixture_root / ".trellis" / "workflow-installed.json"
        record_data = json.loads(record_path.read_text(encoding="utf-8"))
        cli_types = list(record_data.get("cli_types", []))
        if "codex" not in cli_types:
            cli_types.append("codex")
        record_data["cli_types"] = cli_types
        record_data["patched_codex_skills"] = ["start", "finish-work"]
        record_path.write_text(json.dumps(record_data, ensure_ascii=False, indent=2), encoding="utf-8")

    def apply_legacy_codex_workflow_state(self, fixture_root: Path) -> None:
        self.mark_legacy_codex_installed(fixture_root)
        commands_root = COMMANDS_DIR
        start_skill = fixture_root / ".agents" / "skills" / "start" / "SKILL.md"
        finish_work_skill = fixture_root / ".agents" / "skills" / "finish-work" / "SKILL.md"
        start_backup = fixture_root / ".agents" / "skills" / ".backup-original" / "start" / "SKILL.md"
        finish_backup = fixture_root / ".agents" / "skills" / ".backup-original" / "finish-work" / "SKILL.md"
        start_backup.parent.mkdir(parents=True, exist_ok=True)
        finish_backup.parent.mkdir(parents=True, exist_ok=True)
        start_backup.write_text(BASELINE_START_SKILL_CONTENT, encoding="utf-8")
        finish_backup.write_text(BASELINE_FINISH_WORK_CONTENT, encoding="utf-8")

        install_module = self.run_script  # suppress linter-like unused concerns by local aliasing? no
        _ = install_module
        import importlib.util
        module_path = COMMANDS_DIR / "install-workflow.py"
        spec = importlib.util.spec_from_file_location("workflow_install_workflow_test", module_path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        patched_start = module.build_codex_start_skill_content(
            BASELINE_START_SKILL_CONTENT,
            module.prepare_command_content(commands_root / "start-skill-patch-phase-router.md"),
        )
        assert patched_start is not None
        start_skill.parent.mkdir(parents=True, exist_ok=True)
        start_skill.write_text(patched_start, encoding="utf-8")

        patched_finish = module.build_finish_work_content(
            BASELINE_FINISH_WORK_CONTENT,
            module.prepare_command_content(commands_root / "finish-work-patch-projectization.md"),
        )
        assert patched_finish is not None
        finish_work_skill.parent.mkdir(parents=True, exist_ok=True)
        finish_work_skill.write_text(patched_finish, encoding="utf-8")

        agents_backup_dir = fixture_root / ".trellis" / ".backup-original" / "codex-agents"
        agents_backup_dir.mkdir(parents=True, exist_ok=True)
        (agents_backup_dir / "trellis-research.toml").write_text(BASELINE_CODEX_RESEARCH_TOML, encoding="utf-8")
        (agents_backup_dir / "trellis-implement.toml").write_text(BASELINE_CODEX_IMPLEMENT_TOML, encoding="utf-8")
        (agents_backup_dir / "trellis-check.toml").write_text(BASELINE_CODEX_CHECK_TOML, encoding="utf-8")

    def test_install_deploys_record_session_closure_helper_and_patch(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        brainstorm = fixture / ".claude" / "commands" / "trellis" / "brainstorm.md"
        self.assertTrue(brainstorm.exists(), "brainstorm.md should be deployed")
        project_audit = fixture / ".claude" / "commands" / "trellis" / "project-audit.md"
        self.assertTrue(project_audit.exists(), "project-audit.md should be deployed")
        workflow_state_helper = fixture / ".trellis" / "scripts" / "workflow" / "workflow-state.py"
        self.assertTrue(workflow_state_helper.exists(), "workflow-state.py should be deployed")
        ownership_helper = fixture / ".trellis" / "scripts" / "workflow" / "ownership-proof-validate.py"
        self.assertTrue(ownership_helper.exists(), "ownership-proof-validate.py should be deployed")
        watermark_guard = fixture / ".trellis" / "scripts" / "workflow" / "source-watermark-guard.py"
        self.assertTrue(watermark_guard.exists(), "source-watermark-guard.py should be deployed")
        workflow_doc = fixture / ".trellis" / "workflow.md"
        workflow_doc_text = workflow_doc.read_text(encoding="utf-8")
        self.assertIn(WORKFLOW_PATCH_MARKER, workflow_doc_text)
        self.assertIn("task.py start <name>", workflow_doc_text)
        self.assertIn("python3 ./.trellis/scripts/add_session.py", workflow_doc_text)
        self.assertIn("finish-work-checklist.md", workflow_doc_text)
        self.assertIn("child task", workflow_doc_text)
        self.assertIn("parent coordinator records", workflow_doc_text)
        self.assertIn("does not automatically authorize", workflow_doc_text)
        start_text = (fixture / ".claude" / "commands" / "trellis" / "continue.md").read_text(encoding="utf-8")
        self.assertIn(
            ".trellis/scripts/workflow/workflow-state.py route <task-dir> --project-root <project-root>",
            start_text,
        )
        self.assertNotIn("docs/workflows/新项目开发工作流/commands/shell", start_text)
        finish_work = fixture / ".claude" / "commands" / "trellis" / "finish-work.md"
        finish_work_text = finish_work.read_text(encoding="utf-8")
        self.assertIn(FINISH_WORK_MARKER, finish_work_text)
        self.assertNotIn("pnpm lint", finish_work_text)
        # 补丁已条件化：验证质量平台门禁口径，不再硬断言特定 sonar 内容
        self.assertIn("质量平台门禁", finish_work_text)
        record = fixture / ".trellis" / "workflow-installed.json"
        self.assertTrue(record.exists(), "workflow-installed.json should be created")
        record_data = json.loads(record.read_text(encoding="utf-8"))
        self.assertIn("brainstorm", record_data["commands"])
        self.assertIn("project-audit", record_data["commands"])
        self.assertEqual(record_data["overlay_commands"], ["brainstorm", "check"])
        self.assertEqual(record_data["disabled_commands"], ["parallel"])
        self.assertEqual(
            record_data["patched_baseline_commands"],
            ["continue", "finish-work"],
        )
        self.assertEqual(record_data["patched_shared_docs"], ["workflow.md"])
        self.assertEqual(record_data["profile"], "outsourcing")
        self.assertEqual(record_data["scripts"], HELPER_SCRIPTS)
        self.assertEqual(
            record_data["execution_cards"],
            ["需求变更管理执行卡.md", "源码水印与归属证据链执行卡.md"],
        )
        for helper_name in HELPER_SCRIPTS:
            helper_path = fixture / ".trellis" / "scripts" / "workflow" / helper_name
            self.assertTrue(helper_path.exists(), f"{helper_name} should be deployed")
        change_card = fixture / ".trellis" / "workflow-docs" / "需求变更管理执行卡.md"
        ownership_card = fixture / ".trellis" / "workflow-docs" / "源码水印与归属证据链执行卡.md"
        self.assertTrue(change_card.exists(), "需求变更管理执行卡.md should be deployed")
        self.assertTrue(ownership_card.exists(), "源码水印与归属证据链执行卡.md should be deployed")
        ownership_card_text = ownership_card.read_text(encoding="utf-8")
        self.assertIn(".trellis/scripts/workflow/ownership-proof-validate.py", ownership_card_text)
        self.assertIn(".trellis/scripts/workflow/source-watermark-guard.py", ownership_card_text)
        self.assertNotIn("docs/workflows/新项目开发工作流/commands/shell", ownership_card_text)
        self.assertNotIn("<WORKFLOW_DIR>/commands/shell", ownership_card_text)
        self.assertEqual(record_data["workflow_version"], "0.1.27")
        self.assertEqual(record_data["workflow_schema_version"], "2")
        self.assertEqual(record_data["initial_pack"], "pack.requirements-discovery-foundation")
        parallel = fixture / ".claude" / "commands" / "trellis" / "parallel.md"
        self.assertFalse(parallel.exists())
        self.assertTrue((fixture / ".claude" / "commands" / "trellis" / ".backup-original" / "parallel.md").exists())
        deployed_feasibility = (fixture / ".claude" / "commands" / "trellis" / "feasibility.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(".trellis/scripts/workflow/feasibility-check.py", deployed_feasibility)
        self.assertNotIn("docs/workflows/新项目开发工作流/commands/shell", deployed_feasibility)
        self.assertIn("OpenCode 入口见目标项目 AGENTS.md 路由表", deployed_feasibility)
        self.assertNotIn("[阶段状态机与强门禁协议](", deployed_feasibility)
        self.assertNotIn("../源码水印与归属证据链执行卡.md", deployed_feasibility)
        self.assertIn(
            "[源码水印与归属证据链执行卡](.trellis/workflow-docs/源码水印与归属证据链执行卡.md)",
            deployed_feasibility,
        )

    def test_install_personal_profile_keeps_ownership_cards_and_helpers(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture, "--profile", "personal")

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        record_data = json.loads((fixture / ".trellis" / "workflow-installed.json").read_text(encoding="utf-8"))
        self.assertEqual(record_data["profile"], "personal")
        self.assertEqual(
            record_data["scripts"],
            [name for name in HELPER_SCRIPTS if name not in {"delivery-control-validate.py"}],
        )
        self.assertEqual(
            record_data["execution_cards"],
            ["需求变更管理执行卡.md", "源码水印与归属证据链执行卡.md"],
        )

        workflow_scripts = fixture / ".trellis" / "scripts" / "workflow"
        self.assertTrue((workflow_scripts / "workflow-state.py").exists())
        self.assertFalse((workflow_scripts / "delivery-control-validate.py").exists())
        self.assertTrue((workflow_scripts / "ownership-proof-validate.py").exists())
        self.assertTrue((workflow_scripts / "source-watermark-guard.py").exists())

        workflow_docs = fixture / ".trellis" / "workflow-docs"
        self.assertTrue((workflow_docs / "需求变更管理执行卡.md").exists())
        self.assertTrue((workflow_docs / "源码水印与归属证据链执行卡.md").exists())

        deployed_delivery = (fixture / ".claude" / "commands" / "trellis" / "delivery.md").read_text(encoding="utf-8")
        self.assertIn("源码水印与归属证据链执行卡", deployed_delivery)
        self.assertIn("ownership-proof-validate.py", deployed_delivery)
        self.assertIn("source-watermark-guard.py", deployed_delivery)

    def test_upgrade_merge_respects_personal_profile_for_commands_and_codex_skills(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture, "--profile", "personal")
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        merge = self.run_script(
            UPGRADE_SCRIPT,
            "--merge",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(merge.returncode, 0, msg=merge.stdout + merge.stderr)
        delivery_cmd = (fixture / ".claude" / "commands" / "trellis" / "delivery.md").read_text(encoding="utf-8")
        delivery_skill = (fixture / ".agents" / "skills" / "delivery" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("源码水印与归属证据链执行卡", delivery_cmd)
        self.assertIn("ownership-proof-validate.py", delivery_cmd)
        self.assertIn("source-watermark-guard.py", delivery_cmd)
        self.assertIn("源码水印与归属证据链执行卡", delivery_skill)
        self.assertIn("ownership-proof-validate.py", delivery_skill)
        self.assertIn("source-watermark-guard.py", delivery_skill)

    def test_install_patches_finish_work_for_opencode_and_codex(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        opencode_finish_work = fixture / ".opencode" / "commands" / "trellis" / "finish-work.md"
        codex_finish_work = fixture / ".agents" / "skills" / "trellis-finish-work" / "SKILL.md"
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
        self.assertFalse(opencode_parallel.exists())
        self.assertFalse(codex_parallel.exists())

    def test_install_patches_codex_continue_skill_phase_router(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        start_skill = fixture / ".agents" / "skills" / "trellis-continue" / "SKILL.md"
        start_text = start_skill.read_text(encoding="utf-8")
        self.assertIn("## Workflow Phase Router Patch `[AI]`", start_text)
        self.assertIn("Use the `feasibility` skill", start_text)
        self.assertNotIn("docs/workflows/新项目开发工作流/commands/shell", start_text)
        self.assertNotIn("<WORKFLOW_DIR>/commands/shell", start_text)
        self.assertEqual(
            (fixture / ".agents" / "skills" / ".backup-original" / "trellis-continue" / "SKILL.md").read_text(
                encoding="utf-8"
            ),
            BASELINE_TRELLIS_CONTINUE_SKILL_CONTENT,
        )

    def test_install_migrates_legacy_agents_to_trellis_naming(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True, use_latest_trellis_baseline=False)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.assertTrue((fixture / ".claude" / "agents" / "trellis-research.md").exists())
        self.assertFalse((fixture / ".claude" / "agents" / "research.md").exists())
        self.assertTrue((fixture / ".opencode" / "agents" / "trellis-research.md").exists())
        self.assertFalse((fixture / ".opencode" / "agents" / "research.md").exists())
        self.assertTrue((fixture / ".codex" / "agents" / "trellis-research.toml").exists())
        self.assertFalse((fixture / ".codex" / "agents" / "research.toml").exists())

    def test_install_keeps_codex_native_implement_check_but_enhances_research(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        codex_trellis_agents = fixture / ".codex" / "agents"
        self.assertIn(
            "Resolve the active task path. Try in order:",
            (codex_trellis_agents / "trellis-research.toml").read_text(encoding="utf-8"),
        )
        self.assertEqual(
            (codex_trellis_agents / "trellis-implement.toml").read_text(encoding="utf-8"),
            BASELINE_CODEX_IMPLEMENT_TOML,
        )
        self.assertEqual(
            (codex_trellis_agents / "trellis-check.toml").read_text(encoding="utf-8"),
            BASELINE_CODEX_CHECK_TOML,
        )
        self.assertFalse((fixture / ".trellis" / ".backup-original" / "codex-agents").exists())

    def test_install_deploys_enhanced_research_agents_to_target_project(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        claude_research = (fixture / ".claude" / "agents" / "trellis-research.md").read_text(encoding="utf-8")
        opencode_research = (fixture / ".opencode" / "agents" / "trellis-research.md").read_text(encoding="utf-8")
        codex_research = (fixture / ".codex" / "agents" / "trellis-research.toml").read_text(encoding="utf-8")

        self.assertIn("mcp__ace__search_context", claude_research)
        self.assertIn("mcp__grok-search__web_search", claude_research)
        self.assertIn("mcp__deepwiki__read_wiki_structure", claude_research)
        self.assertIn("mcp__Context7__resolve-library-id", claude_research)

        self.assertIn("mcp__ace__search_context: allow", opencode_research)
        self.assertIn("mcp__grok-search__*: allow", opencode_research)
        self.assertIn("mcp__deepwiki__*: allow", opencode_research)
        self.assertIn("mcp__Context7__*: allow", opencode_research)

        self.assertIn("Resolve the active task path. Try in order:", codex_research)
        self.assertIn("Choose tools by search type:", codex_research)
        self.assertIn("ace.search_context", codex_research)
        self.assertIn("grok-search", codex_research)

    def test_upgrade_check_detects_managed_research_agent_drift(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        claude_research = fixture / ".claude" / "agents" / "trellis-research.md"
        claude_research.write_text("# drifted research\n", encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("agent 内容漂移", result.stdout)

    def test_upgrade_merge_restores_managed_research_agent(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        claude_research = fixture / ".claude" / "agents" / "trellis-research.md"
        claude_research.write_text("# drifted research\n", encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--merge",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        updated = claude_research.read_text(encoding="utf-8")
        self.assertIn("mcp__ace__search_context", updated)
        self.assertIn("mcp__grok-search__web_search", updated)

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
        self.assertIn("spec.universal-domains.project-governance.readme-governance", lock_text)
        readme_governance = (
            fixture
            / ".trellis"
            / "spec"
            / "universal-domains"
            / "project-governance"
            / "readme-governance"
            / "normative-rules.md"
        )
        self.assertTrue(readme_governance.exists(), "README governance spec should be imported during installation")
        readme_governance_text = readme_governance.read_text(encoding="utf-8")
        self.assertIn("README.md", readme_governance_text)
        self.assertIn("README.en.md", readme_governance_text)
        self.assertIn("default Simplified Chinese entry", readme_governance_text)
        self.assertFalse((fixture / ".trellis" / "tasks" / "00-bootstrap-guidelines").exists())
        self.assertIn("初始 spec 基线已导入", install.stdout)
        self.assertIn("Trellis bootstrap 任务已删除", install.stdout)
        self.assertIn("README.en.md", install.stdout)

    def test_install_clears_stale_current_task_when_bootstrap_task_is_removed(self) -> None:
        fixture = self.create_fixture(bootstrap_as_current_task=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        current_task_file = fixture / ".trellis" / ".current-task"
        if current_task_file.exists():
            self.assertEqual(current_task_file.read_text(encoding="utf-8").strip(), "")
        self.assertFalse((fixture / ".trellis" / "tasks" / "00-bootstrap-guidelines").exists())
        self.assertIn("已清理 bootstrap current-task 引用", install.stdout)

    def test_install_clears_bootstrap_current_task_when_reference_uses_short_name(self) -> None:
        fixture = self.create_fixture(bootstrap_as_current_task=True)
        self.addCleanup(shutil.rmtree, fixture)
        (fixture / ".trellis" / ".current-task").write_text("00-bootstrap-guidelines\n", encoding="utf-8")

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        current_task_file = fixture / ".trellis" / ".current-task"
        if current_task_file.exists():
            self.assertEqual(current_task_file.read_text(encoding="utf-8").strip(), "")
        self.assertIn("已清理 bootstrap current-task 引用", install.stdout)

    def test_install_dry_run_previews_bootstrap_current_task_cleanup(self) -> None:
        fixture = self.create_fixture(bootstrap_as_current_task=True)
        self.addCleanup(shutil.rmtree, fixture)

        result = self.run_script(INSTALL_SCRIPT, "--project-root", str(fixture), "--dry-run")

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("将清理 bootstrap current-task 引用", result.stdout)
        self.assertEqual(
            (fixture / ".trellis" / ".current-task").read_text(encoding="utf-8").strip(),
            ".trellis/tasks/00-bootstrap-guidelines",
        )

    def test_install_does_not_clear_special_current_task_values(self) -> None:
        fixture = self.create_fixture(bootstrap_as_current_task=True)
        self.addCleanup(shutil.rmtree, fixture)
        (fixture / ".trellis" / ".current-task").write_text(".\n", encoding="utf-8")

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.assertEqual((fixture / ".trellis" / ".current-task").read_text(encoding="utf-8").strip(), ".")
        self.assertNotIn("已清理 bootstrap current-task 引用", install.stdout)

    def test_uninstall_restores_workflow_doc(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        workflow_doc = fixture / ".trellis" / "workflow.md"
        self.assertIn(WORKFLOW_PATCH_MARKER, workflow_doc.read_text(encoding="utf-8"))

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertEqual(workflow_doc.read_text(encoding="utf-8"), BASELINE_WORKFLOW_CONTENT)

    def test_upgrade_check_detects_workflow_doc_patch_drift(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        workflow_doc = fixture / ".trellis" / "workflow.md"
        workflow_doc.write_text(
            workflow_doc.read_text(encoding="utf-8").replace(WORKFLOW_PATCH_MARKER, "<!-- missing -->"),
            encoding="utf-8",
        )
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("workflow.md", result.stdout + result.stderr)

    def test_upgrade_check_detects_workflow_doc_content_drift_while_marker_intact(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        workflow_doc = fixture / ".trellis" / "workflow.md"
        workflow_doc.write_text(
            workflow_doc.read_text(encoding="utf-8").replace(
                "archive runs first, then add_session",
                "archive runs second, then add_session",
            ),
            encoding="utf-8",
        )
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("workflow.md", result.stdout + result.stderr)
        self.assertIn("内容漂移", result.stdout + result.stderr)

    def test_upgrade_check_detects_embed_attempt_record_conflict(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        (fixture / ".trellis" / ATTEMPT_RECORD_NAME).write_text(
            json.dumps({"status": "failed"}, ensure_ascii=False),
            encoding="utf-8",
        )
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(ATTEMPT_RECORD_NAME, result.stdout + result.stderr)
        self.assertIn("status=failed", result.stdout + result.stderr)

    def test_upgrade_check_allows_attempt_record_during_installer_self_check_env(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        (fixture / ".trellis" / ATTEMPT_RECORD_NAME).write_text(
            json.dumps({"status": "failed", "last_step": "post-install-check"}, ensure_ascii=False),
            encoding="utf-8",
        )
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        env = self.latest_env_for(fixture)
        env["WORKFLOW_IGNORE_EMBED_ATTEMPT"] = "1"
        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=env,
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_upgrade_check_detects_agents_md_routing_drift(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True, include_agents_md=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        agents_md = fixture / "AGENTS.md"
        content = agents_md.read_text(encoding="utf-8")
        start_idx = content.index("<!-- workflow-nl-routing-start -->")
        end_idx = content.index("<!-- workflow-nl-routing-end -->") + len("<!-- workflow-nl-routing-end -->")
        agents_md.write_text(content[:start_idx] + content[end_idx:], encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("AGENTS.md: NL 路由表缺失", result.stdout + result.stderr)

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

    def test_codex_secondary_skills_docs_do_not_claim_parallel_as_fresh_baseline_default(self) -> None:
        cli_matrix = (REPO_ROOT / "docs" / "workflows" / "新项目开发工作流" / "CLI原生适配边界矩阵.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("不应再把 `.codex/skills/parallel` 当作必然出现的默认现象", cli_matrix)
        self.assertIn("test -d .agents/skills", cli_matrix)
        self.assertIn("test -d .codex/skills || true", cli_matrix)
        self.assertNotIn(
            "本仓库实际观察到的例子是：主体 skills 落在 `.agents/skills/`，`parallel` 落在 `.codex/skills/`。",
            cli_matrix,
        )

        codex_readme = (
            REPO_ROOT / "docs" / "workflows" / "新项目开发工作流" / "commands" / "codex" / "README.md"
        ).read_text(encoding="utf-8")
        self.assertIn("当前 fresh `0.5.10` 基线默认可稳定观察到的是 `.agents/skills/`", codex_readme)
        self.assertNotIn(
            "本仓库实际观察到的例子是：主体 skills 落在 `.agents/skills/`，而 `parallel` 落在 `.codex/skills/`。",
            codex_readme,
        )

        hidden_boundary = (
            REPO_ROOT / "docs" / "workflows" / "新项目开发工作流" / "装后隐藏目录与托管边界核对清单.md"
        ).read_text(encoding="utf-8")
        self.assertIn("当前 fresh baseline 不应默认假定它存在", hidden_boundary)
        self.assertIn("仅在 `.codex/skills/` 实际存在时才纳入核对", hidden_boundary)
        self.assertIn("仅在该目录真实存在时才继续检查其条件性影响面", hidden_boundary)

        command_map = (REPO_ROOT / "docs" / "workflows" / "新项目开发工作流" / "命令映射.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("只应视为共享承载面与漂移核对范围", command_map)

        workflow_overview = (REPO_ROOT / "docs" / "workflows" / "新项目开发工作流" / "工作流总纲.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("install-only 的协作提醒产物", workflow_overview)
        self.assertIn("不是卸载时必须恢复/清理的目标", workflow_overview)

    def test_install_creates_and_clears_attempt_record_on_success(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True, include_agents_md=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.assertFalse((fixture / ".trellis" / ATTEMPT_RECORD_NAME).exists())
        self.assertIn("装后自检通过", install.stdout)

    def test_install_leaves_failed_attempt_record_when_cli_deployment_fails(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)
        (fixture / ".agents" / "skills" / "trellis-finish-work" / "SKILL.md").unlink()

        install = self.install_workflow(fixture)

        self.assertNotEqual(install.returncode, 0)
        attempt_record = fixture / ".trellis" / ATTEMPT_RECORD_NAME
        self.assertTrue(attempt_record.exists(), "workflow-embed-attempt.json should remain after failed install")
        attempt_data = json.loads(attempt_record.read_text(encoding="utf-8"))
        self.assertEqual(attempt_data["status"], "failed")
        self.assertEqual(attempt_data["last_step"], "deploy-cli-assets")
        self.assertFalse((fixture / ".trellis" / "workflow-installed.json").exists())

    def test_install_blocks_when_target_is_not_initial_baseline(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True, include_agents_md=True)
        self.addCleanup(shutil.rmtree, fixture)

        first_install = self.install_workflow(fixture)
        self.assertEqual(first_install.returncode, 0, msg=first_install.stdout + first_install.stderr)

        second_install = self.install_workflow(fixture)

        self.assertNotEqual(second_install.returncode, 0)
        self.assertIn("不是可执行首次嵌入的初始态", second_install.stderr)
        self.assertIn("workflow-installed.json", second_install.stderr)

    def test_detect_embed_state_reports_initial_baseline_ready(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True, include_agents_md=True)
        self.addCleanup(shutil.rmtree, fixture)

        result = self.detect_embed_state(fixture, "--json")

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "INITIAL_BASELINE_READY")
        self.assertEqual(payload["traces"], [])

    def test_detect_embed_state_reports_already_valid_embedded(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True, include_agents_md=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        result = self.detect_embed_state(fixture, "--json", env=self.latest_env_for(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "ALREADY_VALID_EMBEDDED")
        self.assertTrue(payload["upgrade_check_passed"])

    def test_detect_embed_state_blocks_failed_attempt_record(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True, include_agents_md=True)
        self.addCleanup(shutil.rmtree, fixture)
        attempt_record = fixture / ".trellis" / ATTEMPT_RECORD_NAME
        attempt_record.write_text(
            json.dumps(
                {
                    "status": "failed",
                    "workflow_version": "0.1.27",
                    "workflow_root": "/tmp/workflow",
                    "workflow_spec_path": "/tmp/workflow/工作流嵌入执行规范.md",
                    "target_project_root": str(fixture),
                    "last_step": "deploy-cli-assets",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        result = self.detect_embed_state(fixture, "--json", env=self.latest_env_for(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "BLOCKED_NON_INITIAL_STATE")
        self.assertIn("embed-attempt-record", "\n".join(payload["traces"]))
        self.assertEqual(payload["attempt_details"]["status"], "failed")
        self.assertEqual(payload["attempt_details"]["last_step"], "deploy-cli-assets")

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
        self.assertIn("git remote add origin <你的第一个远程仓库URL>", install.stderr)
        self.assertIn("git remote set-url --add --push origin <第一个仓库URL>", install.stderr)
        self.assertIn("git remote set-url --add --push origin <第二个仓库URL>", install.stderr)

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
        (fixture / ".agents" / "skills" / "trellis-finish-work" / "SKILL.md").unlink()

        install = self.install_workflow(fixture)

        self.assertNotEqual(install.returncode, 0)
        self.assertIn(
            "活动 skills 目录缺少 trellis-finish-work 基线", install.stdout + install.stderr
        )
        self.assertFalse((fixture / ".trellis" / "workflow-installed.json").exists())

    def test_install_codex_uses_agents_skills_for_shared_assets_only(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)
        codex_parallel = fixture / ".codex" / "skills" / "parallel" / "SKILL.md"
        codex_parallel.parent.mkdir(parents=True, exist_ok=True)
        codex_parallel.write_text(BASELINE_PARALLEL_CONTENT, encoding="utf-8")

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.assertTrue((fixture / ".agents" / "skills" / "delivery" / "SKILL.md").exists())
        self.assertFalse((fixture / ".codex" / "skills" / "delivery" / "SKILL.md").exists())
        self.assertFalse((fixture / ".codex" / "skills" / "trellis-finish-work" / "SKILL.md").exists())
        self.assertFalse((fixture / ".codex" / "skills" / "trellis-continue" / "SKILL.md").exists())
        self.assertFalse((fixture / ".codex" / "skills" / "parallel" / "SKILL.md").exists())
        self.assertTrue((fixture / ".codex" / "skills" / ".backup-original" / "parallel" / "SKILL.md").exists())

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
        self.assertIn("调研、研究、查资料", agents_md)
        self.assertIn("trellis-research", agents_md)

    def test_install_dry_run_reports_preview_without_writing_files(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True, include_agents_md=True)
        self.addCleanup(shutil.rmtree, fixture)

        result = self.run_script(INSTALL_SCRIPT, "--project-root", str(fixture), "--dry-run")

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("将写入安装记录", result.stdout)
        self.assertIn("将注入 AGENTS.md NL 路由表", result.stdout)
        self.assertIn("将执行装后自检", result.stdout)
        self.assertNotIn("✅ 安装记录 → workflow-installed.json", result.stdout)
        self.assertNotIn("✅ AGENTS.md NL 路由表已注入", result.stdout)
        self.assertFalse((fixture / ".trellis" / "workflow-installed.json").exists())
        self.assertFalse((fixture / ".trellis" / ATTEMPT_RECORD_NAME).exists())
        self.assertFalse((fixture / ".agents" / "skills" / "review-gate").exists())
        self.assertNotIn("workflow-nl-routing-start", (fixture / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertIn("[codex] 命令: 9/9, 补丁: 3, agents: 1, 脚本: 0, 手动基线校验: 2".lower(), result.stdout.lower())
        self.assertNotIn("[codex] 命令: 9/9, 补丁: 4".lower(), result.stdout.lower())

    def test_install_dry_run_does_not_migrate_legacy_agents(self) -> None:
        """--dry-run must NOT perform actual file renames on disk."""
        fixture = self.create_fixture(use_latest_trellis_baseline=False)
        self.addCleanup(shutil.rmtree, fixture)

        legacy_research = fixture / ".claude" / "agents" / "research.md"
        trellis_research = fixture / ".claude" / "agents" / "trellis-research.md"
        self.assertTrue(legacy_research.exists())
        self.assertFalse(trellis_research.exists())

        result = self.run_script(
            INSTALL_SCRIPT,
            "--project-root", str(fixture),
            "--dry-run",
            env={EMBED_CONFIRM_ENV: "1"},
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        # Legacy file must still exist (no actual rename)
        self.assertTrue(legacy_research.exists(), "dry-run must not rename legacy agents on disk")
        # trellis-* must NOT exist (no actual creation)
        self.assertFalse(trellis_research.exists(), "dry-run must not create trellis-* agents on disk")

    def test_install_requires_embed_executor_confirmation(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        result = self.run_script(INSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("无法在 Codex 中嵌入成功", result.stderr)
        self.assertIn(EMBED_CONFIRM_ENV, result.stderr)

    def test_install_proceeds_after_embed_executor_confirmation(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        result = self.run_script(
            INSTALL_SCRIPT,
            "--project-root",
            str(fixture),
            env={EMBED_CONFIRM_ENV: "1"},
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_install_filters_supported_clis_when_codex_is_requested_with_others(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True, include_agents_md=True)
        self.addCleanup(shutil.rmtree, fixture)

        result = self.run_script(
            INSTALL_SCRIPT,
            "--project-root",
            str(fixture),
            "--cli",
            "claude,opencode",
            env={EMBED_CONFIRM_ENV: "1"},
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        record_data = json.loads((fixture / ".trellis" / "workflow-installed.json").read_text(encoding="utf-8"))
        self.assertEqual(record_data["cli_types"], ["claude", "opencode"])
        self.assertIn("patched_codex_skills", record_data)

    def test_upgrade_check_detects_phase_router_drift_even_when_versions_match(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        backup_start = fixture / ".claude" / "commands" / "trellis" / ".backup-original" / "continue.md"
        target_start = fixture / ".claude" / "commands" / "trellis" / "continue.md"
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

        helper = fixture / ".trellis" / "scripts" / "workflow" / "workflow-state.py"
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
        self.assertIn("workflow-state.py", result.stdout)

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

    def test_upgrade_check_detects_obsolete_helper_script_residue(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        stale_helper = fixture / ".trellis" / "scripts" / "workflow" / "record-session-helper.py"
        stale_helper.write_text("# obsolete helper residue\n", encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("废弃辅助脚本残留", result.stdout)
        self.assertIn("record-session-helper.py", result.stdout)

    def test_upgrade_merge_removes_obsolete_helper_script_residue(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        stale_helper = fixture / ".trellis" / "scripts" / "workflow" / "record-session-helper.py"
        stale_helper.write_text("# obsolete helper residue\n", encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--merge",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertFalse(stale_helper.exists())

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
        record_data.pop("patched_codex_skills", None)
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
        self.assertNotIn("patched_codex_skills", result.stdout)

    def test_upgrade_check_allows_legacy_missing_version_keys(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        record_path = fixture / ".trellis" / "workflow-installed.json"
        record_data = json.loads(record_path.read_text(encoding="utf-8"))
        record_data.pop("workflow_version", None)
        record_data.pop("workflow_schema_version", None)
        record_data.pop("patched_codex_skills", None)
        record_data.pop("bootstrap_cleanup_status", None)
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

    def test_upgrade_merge_backfills_legacy_missing_version_keys_even_without_conflicts(self) -> None:
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
            "--merge",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        updated = json.loads(record_path.read_text(encoding="utf-8"))
        self.assertEqual(updated["workflow_version"], "0.1.27")
        self.assertEqual(updated["workflow_schema_version"], "2")

    def test_upgrade_check_warns_when_bootstrap_cleanup_record_conflicts_with_filesystem(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        bootstrap_dir = fixture / ".trellis" / "tasks" / "00-bootstrap-guidelines"
        bootstrap_dir.mkdir(parents=True, exist_ok=True)
        (bootstrap_dir / "task.json").write_text('{"id":"00-bootstrap-guidelines"}\n', encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("bootstrap_cleanup_status=removed", result.stdout + result.stderr)

    def test_upgrade_check_warns_when_bootstrap_dry_run_removed_conflicts_with_filesystem(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        record_path = fixture / ".trellis" / "workflow-installed.json"
        record_data = json.loads(record_path.read_text(encoding="utf-8"))
        record_data["bootstrap_cleanup_status"] = "dry-run-removed"
        record_path.write_text(json.dumps(record_data, ensure_ascii=False, indent=2), encoding="utf-8")

        bootstrap_dir = fixture / ".trellis" / "tasks" / "00-bootstrap-guidelines"
        bootstrap_dir.mkdir(parents=True, exist_ok=True)
        (bootstrap_dir / "task.json").write_text('{"id":"00-bootstrap-guidelines"}\n', encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("bootstrap_cleanup_status=dry-run-removed", result.stdout + result.stderr)

    def test_upgrade_force_backfills_legacy_missing_codex_patch_record(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        self.apply_legacy_codex_workflow_state(fixture)
        record_path = fixture / ".trellis" / "workflow-installed.json"
        record_data = json.loads(record_path.read_text(encoding="utf-8"))
        record_data.pop("patched_codex_skills", None)
        record_path.write_text(json.dumps(record_data, ensure_ascii=False, indent=2), encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--force",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        updated_record = json.loads(record_path.read_text(encoding="utf-8"))
        self.assertEqual(updated_record["patched_codex_skills"], ["trellis-continue", "trellis-finish-work"])

    def test_upgrade_merge_clears_residual_attempt_record_after_success(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        attempt_record = fixture / ".trellis" / ATTEMPT_RECORD_NAME
        attempt_record.write_text(json.dumps({"status": "failed"}, ensure_ascii=False), encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--merge",
            "--project-root",
            str(fixture),
            env={**self.latest_env_for(fixture), "WORKFLOW_IGNORE_EMBED_ATTEMPT": "1"},
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertFalse(attempt_record.exists(), "successful merge should clear residual attempt record")

    def test_upgrade_check_detects_codex_start_skill_patch_drift(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.apply_legacy_codex_workflow_state(fixture)

        start_skill = fixture / ".agents" / "skills" / "start" / "SKILL.md"
        start_skill.write_text(BASELINE_START_SKILL_CONTENT, encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("start skill (.agents/skills): Phase Router 补丁缺失", result.stdout)

    def test_upgrade_check_detects_codex_secondary_skills_dir_parallel_drift(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)
        codex_parallel = fixture / ".codex" / "skills" / "parallel" / "SKILL.md"
        codex_parallel.parent.mkdir(parents=True, exist_ok=True)
        codex_parallel.write_text(BASELINE_PARALLEL_CONTENT, encoding="utf-8")

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.apply_legacy_codex_workflow_state(fixture)

        codex_parallel.parent.mkdir(parents=True, exist_ok=True)
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
        self.assertIn("parallel skill (.codex/skills): 应已从嵌入面移除", result.stdout)

    def test_upgrade_check_no_longer_checks_agent_drift(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.mark_legacy_codex_installed(fixture)

        codex_check = fixture / ".codex" / "agents" / "trellis-check.toml"
        codex_check.write_text('name = "trellis-check"\nsandbox_mode = "read-only"\n', encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_upgrade_check_still_ignores_non_research_claude_agent_drift(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        claude_check = fixture / ".claude" / "agents" / "trellis-check.md"
        claude_check.write_text("# drifted check\n", encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_upgrade_check_still_ignores_non_research_opencode_agent_drift(self) -> None:
        fixture = self.create_fixture(include_opencode=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        opencode_check = fixture / ".opencode" / "agents" / "trellis-check.md"
        opencode_check.write_text("# drifted check\n", encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_upgrade_merge_no_longer_restores_codex_managed_agent(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.mark_legacy_codex_installed(fixture)

        codex_check = fixture / ".codex" / "agents" / "trellis-check.toml"
        codex_check.write_text('name = "trellis-check"\nsandbox_mode = "read-only"\n', encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--merge",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        updated = codex_check.read_text(encoding="utf-8")
        self.assertIn('sandbox_mode = "read-only"', updated)

    def test_upgrade_merge_still_ignores_non_research_claude_agent_drift(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        claude_check = fixture / ".claude" / "agents" / "trellis-check.md"
        claude_check.write_text("# drifted check\n", encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--merge",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        updated = claude_check.read_text(encoding="utf-8")
        self.assertEqual(updated, "# drifted check\n")

    def test_upgrade_merge_still_ignores_non_research_opencode_agent_drift(self) -> None:
        fixture = self.create_fixture(include_opencode=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        opencode_check = fixture / ".opencode" / "agents" / "trellis-check.md"
        opencode_check.write_text("# drifted check\n", encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--merge",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        updated = opencode_check.read_text(encoding="utf-8")
        self.assertEqual(updated, "# drifted check\n")

    def test_uninstall_migrates_legacy_agents_and_restores_backups(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.mark_legacy_codex_installed(fixture)

        merge = self.run_script(
            UPGRADE_SCRIPT,
            "--merge",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )
        self.assertEqual(merge.returncode, 0, msg=merge.stdout + merge.stderr)

        codex_check = fixture / ".codex" / "agents" / "trellis-check.toml"

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("[Codex]", result.stdout)
        if codex_check.exists():
            restored = codex_check.read_text(encoding="utf-8")
            self.assertIn('sandbox_mode = "read-only"', restored)

    def test_uninstall_preserves_native_trellis_agents_no_backup(self) -> None:
        """Post-0.5: workflow no longer overlays agents; uninstall must NOT
        delete Trellis-native trellis-*.md files when no backup exists."""
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        claude_research = fixture / ".claude" / "agents" / "trellis-research.md"
        self.assertTrue(claude_research.exists(), "trellis-research.md should exist before uninstall")

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        # Native agents must survive uninstall
        self.assertTrue(claude_research.exists(), "native trellis-research.md must NOT be deleted by uninstall")

    def test_uninstall_removes_legacy_bare_name_agents(self) -> None:
        """Legacy bare-name agent files (research.md) are leftovers from
        pre-0.5 installs and should be cleaned up by uninstall."""
        fixture = self.create_fixture(use_latest_trellis_baseline=False)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        # After install, legacy bare-name should be migrated to trellis-*
        legacy_research = fixture / ".claude" / "agents" / "research.md"
        trellis_research = fixture / ".claude" / "agents" / "trellis-research.md"
        self.assertFalse(legacy_research.exists(), "legacy research.md should be migrated by install")
        self.assertTrue(trellis_research.exists(), "trellis-research.md should exist after migration")

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

        # trellis-* is native, must survive uninstall even without backup
        self.assertTrue(trellis_research.exists(), "native trellis-research.md must survive uninstall")

    def test_uninstall_restores_agents_from_backup(self) -> None:
        """When a workflow backup exists, uninstall restores the backup
        content for both Claude and OpenCode agents."""
        fixture = self.create_fixture(include_opencode=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        claude_research = fixture / ".claude" / "agents" / "trellis-research.md"
        opencode_check = fixture / ".opencode" / "agents" / "trellis-check.md"

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        if claude_research.exists():
            restored = claude_research.read_text(encoding="utf-8")
            self.assertEqual(restored, BASELINE_AGENT_RESEARCH_MD)
        if opencode_check.exists():
            restored = opencode_check.read_text(encoding="utf-8")
            self.assertEqual(restored, BASELINE_AGENT_CHECK_MD)

    def test_uninstall_removes_agents_created_by_legacy_migration(self) -> None:
        fixture = self.create_fixture(include_codex=True, use_latest_trellis_baseline=False)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

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

        broken_start = fixture / ".claude" / "commands" / "trellis" / "continue.md"
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

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_upgrade_merge_restores_drift_and_followup_check_passes(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        start = fixture / ".claude" / "commands" / "trellis" / "continue.md"
        finish_work = fixture / ".claude" / "commands" / "trellis" / "finish-work.md"
        record_session = fixture / ".claude" / "commands" / "trellis" / "record-session.md"
        start.write_text(BASELINE_CONTINUE_CONTENT, encoding="utf-8")
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
        record_data = json.loads((fixture / ".trellis" / "workflow-installed.json").read_text(encoding="utf-8"))
        self.assertEqual(record_data["workflow_version"], "0.1.27")
        self.assertEqual(record_data["previous_version"], "0.5.0-rc.3")

        followup_check = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )
        self.assertEqual(followup_check.returncode, 0, msg=followup_check.stdout + followup_check.stderr)

    def test_upgrade_merge_preserves_legacy_entry_command_while_migrating_agent_names(self) -> None:
        fixture = self.create_fixture(include_codex=True, use_latest_trellis_baseline=False)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        legacy_start = fixture / ".claude" / "commands" / "trellis" / "start.md"
        self.assertTrue(legacy_start.exists())

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
            PHASE_ROUTER_MARKER,
            (fixture / ".claude" / "commands" / "trellis" / "start.md").read_text(encoding="utf-8"),
        )
        self.assertTrue((fixture / ".claude" / "commands" / "trellis" / "start.md").exists())
        self.assertTrue((fixture / ".claude" / "agents" / "trellis-research.md").exists())
        self.assertFalse((fixture / ".claude" / "agents" / "research.md").exists())

    def test_upgrade_merge_restores_agents_md_routing(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True, include_agents_md=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        agents_md = fixture / "AGENTS.md"
        content = agents_md.read_text(encoding="utf-8")
        start_idx = content.index("<!-- workflow-nl-routing-start -->")
        end_idx = content.index("<!-- workflow-nl-routing-end -->") + len("<!-- workflow-nl-routing-end -->")
        agents_md.write_text(content[:start_idx] + content[end_idx:], encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        merge = self.run_script(
            UPGRADE_SCRIPT,
            "--merge",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(merge.returncode, 0, msg=merge.stdout + merge.stderr)
        updated_agents = agents_md.read_text(encoding="utf-8")
        self.assertIn("workflow-nl-routing-start", updated_agents)
        self.assertIn("自然语言命令路由", updated_agents)

        followup_check = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )
        self.assertEqual(followup_check.returncode, 0, msg=followup_check.stdout + followup_check.stderr)

    def test_upgrade_merge_removes_codex_secondary_duplicate_shared_skills(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)
        codex_parallel = fixture / ".codex" / "skills" / "parallel" / "SKILL.md"
        codex_parallel.parent.mkdir(parents=True, exist_ok=True)
        codex_parallel.write_text(BASELINE_PARALLEL_CONTENT, encoding="utf-8")

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.apply_legacy_codex_workflow_state(fixture)

        codex_delivery = fixture / ".codex" / "skills" / "delivery" / "SKILL.md"
        codex_delivery.parent.mkdir(parents=True, exist_ok=True)
        codex_delivery.write_text("# drifted delivery\n", encoding="utf-8")
        codex_parallel.parent.mkdir(parents=True, exist_ok=True)
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
        self.assertFalse(codex_delivery.exists())
        self.assertFalse(codex_parallel.exists())

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
        self.apply_legacy_codex_workflow_state(fixture)

        backup_parallel = fixture / ".codex" / "skills" / ".backup-original" / "parallel" / "SKILL.md"
        backup_parallel.parent.mkdir(parents=True, exist_ok=True)
        backup_parallel.write_text(BASELINE_PARALLEL_CONTENT, encoding="utf-8")
        self.assertTrue(backup_parallel.exists())
        codex_parallel.parent.mkdir(parents=True, exist_ok=True)
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
        self.assertFalse(codex_parallel.exists())

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

    def test_force_restores_codex_start_skill_from_backup_and_reapplies_patch(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.apply_legacy_codex_workflow_state(fixture)

        start_skill = fixture / ".agents" / "skills" / "start" / "SKILL.md"
        start_skill.write_text("# broken start skill\n", encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--force",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        restored_text = start_skill.read_text(encoding="utf-8")
        self.assertIn("Original baseline Codex start skill", restored_text)
        self.assertIn("Workflow Phase Router Patch", restored_text)

    def test_force_fails_when_codex_active_baseline_backup_is_missing(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.apply_legacy_codex_workflow_state(fixture)

        start_backup = fixture / ".agents" / "skills" / ".backup-original" / "start" / "SKILL.md"
        if start_backup.exists():
            start_backup.unlink()
        current_backup = fixture / ".agents" / "skills" / ".backup-original" / "trellis-continue" / "SKILL.md"
        if current_backup.exists():
            current_backup.unlink()
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--force",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("缺少 .backup-original/trellis-continue 或 start", result.stdout + result.stderr)

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
        self.assertTrue((fixture / ".claude" / "commands" / "trellis" / "continue.md").exists())
        finish_work = (fixture / ".claude" / "commands" / "trellis" / "finish-work.md").read_text(encoding="utf-8")
        self.assertNotIn(FINISH_WORK_MARKER, finish_work)
        self.assertIn("pnpm lint", finish_work)

    def test_uninstall_restores_codex_start_and_finish_work_skills(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.apply_legacy_codex_workflow_state(fixture)
        start_skill = fixture / ".agents" / "skills" / "start" / "SKILL.md"
        self.assertIn("Workflow Phase Router Patch", start_skill.read_text(encoding="utf-8"))
        patched_skill = fixture / ".agents" / "skills" / "finish-work" / "SKILL.md"
        self.assertIn(FINISH_WORK_MARKER, patched_skill.read_text(encoding="utf-8"))

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        start_text = start_skill.read_text(encoding="utf-8")
        self.assertNotIn("Workflow Phase Router Patch", start_text)
        self.assertIn("Original baseline Codex start skill", start_text)
        restored_text = patched_skill.read_text(encoding="utf-8")
        self.assertNotIn(FINISH_WORK_MARKER, restored_text)
        self.assertIn("pnpm lint", restored_text)

    def test_uninstall_restores_codex_skills_when_record_lacks_patched_codex_skills(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.apply_legacy_codex_workflow_state(fixture)
        record_path = fixture / ".trellis" / "workflow-installed.json"
        record_data = json.loads(record_path.read_text(encoding="utf-8"))
        record_data.pop("patched_codex_skills", None)
        record_path.write_text(json.dumps(record_data, ensure_ascii=False, indent=2), encoding="utf-8")

        start_skill = fixture / ".agents" / "skills" / "start" / "SKILL.md"
        patched_skill = fixture / ".agents" / "skills" / "finish-work" / "SKILL.md"
        self.assertIn("Workflow Phase Router Patch", start_skill.read_text(encoding="utf-8"))
        self.assertIn(FINISH_WORK_MARKER, patched_skill.read_text(encoding="utf-8"))

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertNotIn("Workflow Phase Router Patch", start_skill.read_text(encoding="utf-8"))
        self.assertNotIn(FINISH_WORK_MARKER, patched_skill.read_text(encoding="utf-8"))

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
        self.assertFalse(patched_parallel.exists())
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

    def test_uninstall_leaves_default_todo_file_untouched(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.assertTrue((fixture / "todo.txt").exists())

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertNotIn("todo.txt 已删除", result.stdout)
        self.assertEqual((fixture / "todo.txt").read_text(encoding="utf-8"), DEFAULT_PROJECT_TODO)

    def test_uninstall_leaves_modified_todo_file_untouched(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        todo_path = fixture / "todo.txt"
        todo_path.write_text("自定义提醒\n", encoding="utf-8")

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertNotIn("todo.txt 已被修改，保留现有内容", result.stdout)
        self.assertEqual(todo_path.read_text(encoding="utf-8"), "自定义提醒\n")


if __name__ == "__main__":
    unittest.main()
