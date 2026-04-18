#!/usr/bin/env python3
"""Shared workflow asset definitions for installation, upgrade, and analysis."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


CLI_DIRS = {
    "claude": ".claude",
    "opencode": ".opencode",
    "codex": ".codex",
}
CLI_ALT_DIRS = {
    "codex": ".agents",
}
ALL_CLI_TYPES = ["claude", "opencode", "codex"]
WORKFLOW_VERSION = "0.1.24"
WORKFLOW_SCHEMA_VERSION = "2"  # 安装记录 JSON 的 schema 版本，安装记录结构变化时递增

PATCH_BASELINE_COMMANDS = ["start", "finish-work", "record-session"]
CODEX_PATCH_BASELINE_SKILLS = ["start", "finish-work"]
PATCH_BASELINE_SHARED_DOCS = ["workflow.md"]
OVERLAY_BASELINE_COMMANDS = ["brainstorm", "check"]
OPTIONAL_DISABLED_BASELINE_COMMANDS = ["parallel"]
ADDED_COMMANDS = ["feasibility", "design", "plan", "test-first", "project-audit", "review-gate", "delivery"]
DISTRIBUTED_COMMANDS = [
    "feasibility",
    "brainstorm",
    "design",
    "plan",
    "test-first",
    "project-audit",
    "check",
    "review-gate",
    "delivery",
]
HELPER_SCRIPTS = [
    "feasibility-check.py",
    "design-export.py",
    "workflow-state.py",
    "plan-validate.py",
    "check-quality.py",
    "delivery-control-validate.py",
    "ownership-proof-validate.py",
    "metadata-autocommit-guard.py",
    "record-session-helper.py",
]
MANAGED_IMPLEMENTATION_AGENTS = ["research", "implement", "check"]
LATEST_TRELLIS_VERSION_ENV = "TRELLIS_LATEST_VERSION"
AGENT_SUFFIXES = {
    "claude": ".md",
    "opencode": ".md",
    "codex": ".toml",
}
SHARED_AGENTS_DIR = "shared-agents"


def workflow_managed_agent_source_path(commands_root: Path, cli_type: str, agent_name: str) -> Path:
    """Return the workflow-local shared source path for an implementation agent."""
    return commands_root / SHARED_AGENTS_DIR / agent_name


def workflow_managed_agent_adapter_path(commands_root: Path, cli_type: str, agent_name: str) -> Path:
    """Return the per-CLI workflow adapter path for an implementation agent."""
    suffix = AGENT_SUFFIXES[cli_type]
    return commands_root / cli_type / "agents" / f"{agent_name}{suffix}"


def workflow_managed_agent_target_path(root: Path, cli_type: str, agent_name: str) -> Path:
    """Return the target-project path for a managed implementation agent."""
    suffix = AGENT_SUFFIXES[cli_type]
    return root / CLI_DIRS[cli_type] / "agents" / f"{agent_name}{suffix}"


def _read_shared_agent_text(agent_dir: Path, name: str) -> str:
    path = agent_dir / name
    if not path.exists():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8").strip()


def render_workflow_managed_agent(commands_root: Path, cli_type: str, agent_name: str) -> str:
    """Render a per-CLI workflow-managed agent from the shared workflow-local source."""
    agent_dir = workflow_managed_agent_source_path(commands_root, cli_type, agent_name)
    readme = _read_shared_agent_text(agent_dir, "README.md")
    system = _read_shared_agent_text(agent_dir, "SYSTEM.md")
    tools = _read_shared_agent_text(agent_dir, "TOOLS.md")

    description = ""
    for line in readme.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            description = stripped
            break
    if not description:
        description = f"{agent_name} agent"

    if cli_type == "claude":
        tools_line = {
            "research": "Read, Glob, Grep, mcp__exa__web_search_exa, mcp__exa__get_code_context_exa, mcp__Context7__*, Skill, mcp__chrome-devtools__*",
            "implement": "Read, Write, Edit, Bash, Glob, Grep, mcp__exa__web_search_exa, mcp__exa__get_code_context_exa",
            "check": "Read, Write, Edit, Bash, Glob, Grep, mcp__exa__web_search_exa, mcp__exa__get_code_context_exa",
        }[agent_name]
        return (
            "---\n"
            f"name: {agent_name}\n"
            "description: |\n"
            f"  {description}\n"
            f"tools: {tools_line}\n"
            "model: opus\n"
            "---\n"
            f"{system}\n"
        )

    if cli_type == "opencode":
        permission_block = {
            "research": [
                "  read: allow",
                "  write: deny",
                "  edit: deny",
                "  bash: deny",
                "  glob: allow",
                "  grep: allow",
                "  mcp__exa__*: allow",
                "  mcp__Context7__*: allow",
                "  mcp__chrome-devtools__*: allow",
            ],
            "implement": [
                "  read: allow",
                "  write: allow",
                "  edit: allow",
                "  bash: allow",
                "  glob: allow",
                "  grep: allow",
                "  mcp__exa__*: allow",
            ],
            "check": [
                "  read: allow",
                "  write: allow",
                "  edit: allow",
                "  bash: allow",
                "  glob: allow",
                "  grep: allow",
                "  mcp__exa__*: allow",
            ],
        }[agent_name]
        return (
            "---\n"
            "description: |\n"
            f"  {description}\n"
            "mode: subagent\n"
            "permission:\n"
            + "\n".join(permission_block)
            + "\n---\n"
            f"{system}\n"
        )

    if cli_type == "codex":
        sandbox_mode = {
            "research": "read-only",
            "implement": "workspace-write",
            "check": "workspace-write",
        }[agent_name]
        return (
            f'name = "{agent_name}"\n'
            f'description = "{description}"\n'
            f'sandbox_mode = "{sandbox_mode}"\n\n'
            'developer_instructions = """\n'
            f"{system}\n\n"
            "## Tool Contract\n\n"
            f"{tools}\n"
            '"""\n'
        )

    raise ValueError(f"Unsupported cli_type for managed agent render: {cli_type}")


def prepare_command_content(source_path: Path) -> str:
    """Return target-project-facing command content after deployment rewrites."""
    content = source_path.read_text(encoding="utf-8")
    content = content.replace("<WORKFLOW_DIR>/commands/shell/", ".trellis/scripts/workflow/")
    content = content.replace("docs/workflows/新项目开发工作流/commands/shell/", ".trellis/scripts/workflow/")
    content = content.replace("见 `opencode/README.md`", "OpenCode 入口见目标项目 AGENTS.md 路由表")
    content = content.replace("见 `codex/README.md`", "Codex 入口见目标项目 AGENTS.md 路由表")
    content = content.replace("[阶段状态机与强门禁协议](../阶段状态机与强门禁协议.md)", "阶段状态机与强门禁协议")
    content = content.replace("[需求变更管理执行卡](../需求变更管理执行卡.md)", "需求变更管理执行卡")
    content = content.replace("[需求变更管理执行卡](../../需求变更管理执行卡.md)", "需求变更管理执行卡")
    content = content.replace("[源码水印与归属证据链执行卡](../源码水印与归属证据链执行卡.md)", "源码水印与归属证据链执行卡")
    content = content.replace("[源码水印与归属证据链执行卡](../../源码水印与归属证据链执行卡.md)", "源码水印与归属证据链执行卡")
    return content


@dataclass(frozen=True)
class ManagedAssetSpec:
    asset_id: str
    category: str
    cli_type: str
    kind: str
    name: str

    def locate(self, root: Path) -> Path | None:
        """Locate the primary path for this managed asset.

        For Codex skills this preserves the historical "active directory" lookup
        via ``resolve_codex_skills_dir``. Callers that need full multi-directory
        coverage must use ``list_all_codex_skills_dirs`` and expand paths
        themselves.
        """
        if self.kind == "script":
            return root / ".trellis" / "scripts" / "workflow" / self.name
        if self.kind == "doc":
            return root / ".trellis" / self.name
        if self.kind == "command":
            return root / CLI_DIRS[self.cli_type] / "commands" / "trellis" / f"{self.name}.md"
        if self.kind == "skill":
            skills_dir = resolve_codex_skills_dir(root)
            if skills_dir is None:
                return None
            return skills_dir / self.name / "SKILL.md"
        if self.kind == "agent":
            return workflow_managed_agent_target_path(root, self.cli_type, self.name)
        raise ValueError(f"Unsupported asset kind: {self.kind}")


def resolve_codex_skills_dir(root: Path) -> Path | None:
    skills_dir = root / ".agents" / "skills"
    if skills_dir.is_dir():
        return skills_dir
    skills_dir = root / ".codex" / "skills"
    if skills_dir.is_dir():
        return skills_dir
    return None


def list_all_codex_skills_dirs(root: Path) -> list[Path]:
    """返回目标项目中所有存在的 Codex skills 目录（包括 .agents/skills/ 和 .codex/skills/）。

    注意：resolve_codex_skills_dir 只返回"活动目录"（第一个存在的），
    而本函数返回全部。当 trellis init 同时创建了两个目录时，
    需要用本函数避免影子目录残留。
    """
    dirs: list[Path] = []
    for p in [root / ".agents" / "skills", root / ".codex" / "skills"]:
        if p.is_dir():
            dirs.append(p)
    return dirs


def detect_cli_types(*roots: Path) -> list[str]:
    found: list[str] = []
    for cli_type in ALL_CLI_TYPES:
        for root in roots:
            if cli_type in ("claude", "opencode") and (root / CLI_DIRS[cli_type]).is_dir():
                found.append(cli_type)
                break
            if cli_type == "codex":
                if resolve_codex_skills_dir(root) is not None:
                    found.append(cli_type)
                    break
                if (root / CLI_DIRS[cli_type]).is_dir() or (root / CLI_ALT_DIRS[cli_type]).is_dir():
                    found.append(cli_type)
                    break
    return found


def build_managed_asset_specs(cli_types: list[str]) -> list[ManagedAssetSpec]:
    specs: list[ManagedAssetSpec] = []

    for cli_type in cli_types:
        if cli_type in ("claude", "opencode"):
            for name in PATCH_BASELINE_COMMANDS:
                specs.append(
                    ManagedAssetSpec(
                        asset_id=f"{cli_type}:{name}",
                        category="patch-baseline",
                        cli_type=cli_type,
                        kind="command",
                        name=name,
                    )
                )
            for name in DISTRIBUTED_COMMANDS:
                category = "overlay-baseline" if name in OVERLAY_BASELINE_COMMANDS else "added-command"
                specs.append(
                    ManagedAssetSpec(
                        asset_id=f"{cli_type}:{name}",
                        category=category,
                        cli_type=cli_type,
                        kind="command",
                        name=name,
                    )
                )
            for name in MANAGED_IMPLEMENTATION_AGENTS:
                specs.append(
                    ManagedAssetSpec(
                        asset_id=f"{cli_type}:agent:{name}",
                        category="implementation-agent",
                        cli_type=cli_type,
                        kind="agent",
                        name=name,
                    )
                )
        elif cli_type == "codex":
            for name in CODEX_PATCH_BASELINE_SKILLS:
                specs.append(
                    ManagedAssetSpec(
                        asset_id=f"codex:{name}",
                        category="patch-baseline",
                        cli_type="codex",
                        kind="skill",
                        name=name,
                    )
                )
            for name in DISTRIBUTED_COMMANDS:
                category = "overlay-baseline" if name in OVERLAY_BASELINE_COMMANDS else "added-command"
                specs.append(
                    ManagedAssetSpec(
                        asset_id=f"codex:{name}",
                        category=category,
                        cli_type="codex",
                        kind="skill",
                        name=name,
                    )
                )
            for name in OPTIONAL_DISABLED_BASELINE_COMMANDS:
                specs.append(
                    ManagedAssetSpec(
                        asset_id=f"codex:{name}",
                        category="disabled-baseline",
                        cli_type="codex",
                        kind="skill",
                        name=name,
                    )
                )
            for name in MANAGED_IMPLEMENTATION_AGENTS:
                specs.append(
                    ManagedAssetSpec(
                        asset_id=f"codex:agent:{name}",
                        category="implementation-agent",
                        cli_type="codex",
                        kind="agent",
                        name=name,
                    )
                )

    if cli_types:
        for name in PATCH_BASELINE_SHARED_DOCS:
            specs.append(
                ManagedAssetSpec(
                    asset_id=f"shared:{name}",
                    category="patch-baseline",
                    cli_type="shared",
                    kind="doc",
                    name=name,
                )
            )
        for name in HELPER_SCRIPTS:
            specs.append(
                ManagedAssetSpec(
                    asset_id=f"shared:{name}",
                    category="shared-script",
                    cli_type="shared",
                    kind="script",
                    name=name,
                )
            )

    return specs


def read_project_trellis_version(root: Path) -> str | None:
    version_path = root / ".trellis" / ".version"
    if not version_path.exists():
        return None
    try:
        content = version_path.read_text(encoding="utf-8").strip()
    except UnicodeDecodeError:
        return None
    return content or None


def resolve_latest_trellis_version() -> tuple[str | None, str]:
    overridden = os.environ.get(LATEST_TRELLIS_VERSION_ENV, "").strip()
    if overridden:
        return overridden, LATEST_TRELLIS_VERSION_ENV

    try:
        result = subprocess.run(
            ["trellis", "-v"],
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        return None, f"trellis -v failed: {exc}"

    output = (result.stdout or result.stderr).strip()
    if result.returncode != 0:
        detail = output or f"exit {result.returncode}"
        return None, f"trellis -v failed: {detail}"
    if not output:
        return None, "trellis -v returned empty output"
    return output.splitlines()[-1].strip(), "trellis -v"


def check_latest_trellis_prerequisite(target_root: Path) -> tuple[bool, str]:
    target_version = read_project_trellis_version(target_root)
    if target_version is None:
        return (
            False,
            "目标项目缺少 .trellis/.version，无法确认是否已升级到当前最新 Trellis；"
            "禁止执行当前步骤（包含只读 A/B/C 分析与兼容升级）。",
        )

    latest_version, source = resolve_latest_trellis_version()
    if latest_version is None:
        return (
            False,
            "无法解析当前最新 Trellis 版本，不能确认兼容升级前置条件。"
            f"版本来源检查失败：{source}。",
        )

    if target_version != latest_version:
        return (
            False,
            "目标项目尚未升级到当前最新 Trellis。"
            f"目标项目版本: {target_version}；当前最新版本: {latest_version}（来源: {source}）。"
            "必须先完成 Trellis 官方升级；禁止执行当前步骤（包含只读 A/B/C 分析与兼容升级）。",
        )

    return True, f"目标项目已升级到当前最新 Trellis: {target_version}（来源: {source}）。"
