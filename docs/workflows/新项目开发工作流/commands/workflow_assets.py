#!/usr/bin/env python3
"""Shared workflow asset definitions for installation, upgrade, and analysis."""

from __future__ import annotations

import os
import re
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
WORKFLOW_VERSION = "0.1.28"
WORKFLOW_SCHEMA_VERSION = "3"  # 安装记录 JSON 的 schema 版本，安装记录结构变化时递增
COMPATIBLE_TRELLIS_VERSION = "0.5.17"

PATCH_BASELINE_COMMANDS = ["continue", "finish-work"]
LEGACY_PATCH_BASELINE_COMMANDS = ["start", "finish-work", "record-session"]
CODEX_PATCH_BASELINE_SKILLS = ["trellis-continue", "trellis-finish-work", "trellis-start"]
LEGACY_CODEX_PATCH_BASELINE_SKILLS = ["start", "finish-work"]
PATCH_BASELINE_SHARED_DOCS = ["workflow.md"]
OVERLAY_BASELINE_COMMANDS = ["brainstorm", "check"]
OPTIONAL_DISABLED_BASELINE_COMMANDS = ["parallel"]
ADDED_COMMANDS = ["feasibility", "design", "plan", "project-audit", "review-gate", "delivery"]
DISTRIBUTED_COMMANDS = [
    "feasibility",
    "brainstorm",
    "design",
    "plan",
    "project-audit",
    "check",
    "review-gate",
    "delivery",
]
HELPER_SCRIPTS = [
    "workflow_common.py",
    "state_utils.py",
    "validators_core.py",
    "validators_gates.py",
    "embed_integrity.py",
    "feasibility-check.py",
    "design-export.py",
    "workflow-state.py",
    "plan-validate.py",
    "check-quality.py",
    "delivery-control-validate.py",
    "ownership-proof-validate.py",
    "source-watermark-guard.py",
    "patch-workflow-phase.py",
    "patch-workflow-phase-strong-gate.py",
    "patch-claude-inject-subagent-context.py",
    "patch-inject-workflow-state.py",
    "patch-opencode-inject-subagent-context.py",
    "patch-session-start-strong-gate.py",
    "patch-task-start-strong-gate.py",
    "patch-task-create-preserve-active.py",
    "patch-task-status-view-strong-gate.py",
]
RETIRED_HELPER_SCRIPTS = [
    "record-session-helper.py",
    "metadata-autocommit-guard.py",
    "state_validators.py",
    "state_collectors.py",
]
LATEST_TRELLIS_VERSION_ENV = "TRELLIS_LATEST_VERSION"
CURRENT_TRELLIS_VERSION_ENV = "TRELLIS_CURRENT_VERSION"
CODEX_SHARED_SKILL_NAMES = [*DISTRIBUTED_COMMANDS, *CODEX_PATCH_BASELINE_SKILLS]
CODEX_SHARED_SKILL_CLEANUP_NAMES = [
    *DISTRIBUTED_COMMANDS,
    *CODEX_PATCH_BASELINE_SKILLS,
    *LEGACY_CODEX_PATCH_BASELINE_SKILLS,
]

_TRELLIS_VERSION_RE = re.compile(
    r"(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:-(?P<label>beta|rc)(?:\.(?P<prenum>\d+))?)?"
)


@dataclass(frozen=True)
class TrellisVersion:
    major: int
    minor: int
    patch: int
    prerelease_label: str | None
    prerelease_number: int

    def sort_key(self) -> tuple[int, int, int, int, int]:
        prerelease_rank = {
            "beta": 0,
            "rc": 1,
            None: 2,
        }[self.prerelease_label]
        return (
            self.major,
            self.minor,
            self.patch,
            prerelease_rank,
            self.prerelease_number,
        )

# ── Profile support ──
VALID_PROFILES = ("personal", "outsourcing")
DEFAULT_PROFILE = "outsourcing"
OUTSOURCING_ONLY_SCRIPTS = [
    "delivery-control-validate.py",
]
CORE_HELPER_SCRIPTS = [s for s in HELPER_SCRIPTS if s not in OUTSOURCING_ONLY_SCRIPTS]

# ── Execution cards ──
EXECUTION_CARDS = ["需求变更管理执行卡.md", "源码水印与归属证据链执行卡.md"]
OUTSOURCING_EXECUTION_CARDS: list[str] = []
WORKFLOW_SHARED_DOCS = [*EXECUTION_CARDS, "finish-work-checklist-template.md"]
OUTSOURCING_WORKFLOW_SHARED_DOCS: list[str] = []
WORKFLOW_DOCS_DIR = ".trellis/workflow-docs"
WORKFLOW_DOC_CLEANUP_POLICY = "remove-on-uninstall"
INITIAL_PACK_CLEANUP_POLICY = "retain-imported-assets"
REQUIREMENTS_FOUNDATION_ASSET_IDS = [
    "spec.universal-domains.product-and-requirements.problem-definition",
    "spec.universal-domains.product-and-requirements.scope-boundary",
    "spec.universal-domains.product-and-requirements.requirement-clarification",
    "spec.universal-domains.project-governance.readme-governance",
    "spec.universal-domains.verification.evidence-requirements",
    "spec.universal-domains.product-and-requirements.acceptance-criteria",
    "spec.universal-domains.product-and-requirements.prd-documentation",
    "spec.universal-domains.product-and-requirements.prd-documentation-customer-facing",
    "spec.universal-domains.architecture.system-boundaries",
    "spec.universal-domains.product-and-requirements.prd-documentation-developer-facing",
    "template.universal-domains.product-and-requirements.acceptance-criteria-template",
    "template.universal-domains.product-and-requirements.customer-facing-prd-template",
    "template.universal-domains.product-and-requirements.developer-facing-prd-template",
    "checklist.universal-domains.product-and-requirements.acceptance-quality-checklist",
    "checklist.universal-domains.product-and-requirements.customer-facing-prd-checklist",
    "checklist.universal-domains.product-and-requirements.developer-facing-prd-checklist",
    "example.universal-domains.product-and-requirements.product-and-requirements-examples",
    "spec.scenarios.discovery-and-planning.solution-comparison",
    "example.assembled-packs.requirements-discovery-foundation",
]
REQUIREMENTS_FOUNDATION_TARGET_PATHS = [
    ".trellis/spec/universal-domains/product-and-requirements/problem-definition",
    ".trellis/spec/universal-domains/product-and-requirements/scope-boundary",
    ".trellis/spec/universal-domains/product-and-requirements/requirement-clarification",
    ".trellis/spec/universal-domains/project-governance/readme-governance",
    ".trellis/spec/universal-domains/verification/evidence-requirements",
    ".trellis/spec/universal-domains/product-and-requirements/acceptance-criteria",
    ".trellis/spec/universal-domains/product-and-requirements/prd-documentation",
    ".trellis/spec/universal-domains/product-and-requirements/prd-documentation-customer-facing",
    ".trellis/spec/universal-domains/architecture/system-boundaries",
    ".trellis/spec/universal-domains/product-and-requirements/prd-documentation-developer-facing",
    ".trellis/templates/universal-domains/product-and-requirements/acceptance-criteria-template.md",
    ".trellis/templates/universal-domains/product-and-requirements/customer-facing-prd-template.md",
    ".trellis/templates/universal-domains/product-and-requirements/developer-facing-prd-template.md",
    ".trellis/checklists/universal-domains/product-and-requirements/acceptance-quality-checklist.md",
    ".trellis/checklists/universal-domains/product-and-requirements/customer-facing-prd-checklist.md",
    ".trellis/checklists/universal-domains/product-and-requirements/developer-facing-prd-checklist.md",
    ".trellis/library-assets/examples/universal-domains/product-and-requirements",
    ".trellis/spec/scenarios/discovery-and-planning/solution-comparison",
    ".trellis/library-assets/examples/assembled-packs/requirements-discovery-foundation.md",
]
WORKFLOW_DOC_PATCH_COMPONENTS = [
    "workflow-task-mechanism-projectization",
    "workflow-phase-index-strong-gate",
    "workflow-no-task-strong-gate",
    "workflow-breadcrumb-strong-gate",
    "workflow-legacy-breadcrumb-cleanup",
    "workflow-legacy-phase-router-cleanup",
    "workflow-contract-reference-cleanup",
]
LEGACY_AGENT_NAMES = ["research", "implement", "check"]
# Reserved for legacy install-record compatibility and historical capability
# categories. Fresh installs keep this list empty and do not overlay native
# trellis-* agents anymore.
MANAGED_ENHANCED_AGENT_NAMES: list[str] = []
AGENTS_NL_ROUTING_MARKERS = (
    "<!-- workflow-nl-routing-start -->",
    "<!-- workflow-nl-routing-end -->",
)
CRITICAL_RUNTIME_PATCHES = [
    "inject-workflow-state",
    "claude-inject-subagent-context",
    "opencode-inject-subagent-context",
    "session-start-strong-gate",
    "task-start-strong-gate",
    "task-create-preserve-active",
    "task-status-view-strong-gate",
    "workflow-phase-strong-gate",
]
INJECT_WORKFLOW_STATE_PATCH_MARKER = "# [workflow-embed-patch:prefer-workflow-state-json]"
SESSION_START_STRONG_GATE_PATCH_MARKER = "# strong-gate-session-start-patch-applied"
TASK_START_STRONG_GATE_PATCH_MARKER = "# [workflow-embed-patch:strong-gate-no-status-flip]"
TASK_CREATE_PRESERVE_ACTIVE_PATCH_MARKER = "# [workflow-embed-patch:preserve-parent-active-task]"
TASK_STATUS_VIEW_PATCH_MARKER = "# [workflow-embed-patch:strong-gate-task-status-view]"
WORKFLOW_PHASE_STRONG_GATE_PATCH_MARKER = "# strong-gate-phase-patch-applied"
OPENCODE_INJECT_SUBAGENT_CONTEXT_PATCH_MARKER = "// [workflow-embed-patch:opencode-subagent-gates]"
CLAUDE_INJECT_SUBAGENT_CONTEXT_PATCH_MARKER = "# [workflow-embed-patch:claude-subagent-gates]"


def critical_runtime_patches_for_cli_types(cli_types: list[str] | tuple[str, ...]) -> list[str]:
    """Return the runtime patch contract actually required for the selected CLIs.

    Codex still relies primarily on the turn-level hook carrier (`hooks.json` ->
    `inject-workflow-state.py`). If a target project also keeps a
    `session-start.py` auxiliary surface, the installer patches it when present,
    but fresh Codex install records do not treat that startup helper as an
    unconditional critical patch unless the target project explicitly wires it.
    """
    selected = {str(item) for item in cli_types}
    patches = ["inject-workflow-state"]
    if selected & {"claude", "opencode"}:
        patches.append("session-start-strong-gate")
    if "claude" in selected:
        patches.append("claude-inject-subagent-context")
    if "opencode" in selected:
        patches.append("opencode-inject-subagent-context")
    patches.extend(
        [
            "task-start-strong-gate",
            "task-create-preserve-active",
            "task-status-view-strong-gate",
            "workflow-phase-strong-gate",
        ]
    )
    return patches


def managed_workflow_docs_for_profile(profile: str = DEFAULT_PROFILE) -> list[str]:
    docs = list(WORKFLOW_SHARED_DOCS)
    if profile == DEFAULT_PROFILE:
        docs.extend(OUTSOURCING_WORKFLOW_SHARED_DOCS)
    return docs


def legacy_agent_target_path(root: Path, cli_type: str, agent_name: str) -> Path:
    """Return legacy target-project path for upgrade migration only.

    Trellis 0.5+ provides trellis-{research,implement,check} natively.
    This function only resolves legacy paths so upgrade-compat can migrate
    old bare-name agent files (research.md → trellis-research.md etc.).
    """
    if cli_type == "codex":
        return root / CLI_DIRS[cli_type] / "agents" / f"{agent_name}.toml"
    return root / CLI_DIRS[cli_type] / "agents" / f"{agent_name}.md"


def codex_phase_router_skill_candidates() -> list[str]:
    """Prefer the new Trellis 0.5 carrier, but keep legacy fallback names."""
    return [CODEX_PATCH_BASELINE_SKILLS[0], LEGACY_CODEX_PATCH_BASELINE_SKILLS[0]]


def codex_finish_work_skill_candidates() -> list[str]:
    """Prefer the new Trellis 0.5 carrier, but keep legacy fallback names."""
    return [CODEX_PATCH_BASELINE_SKILLS[1], LEGACY_CODEX_PATCH_BASELINE_SKILLS[1]]


def codex_patch_baseline_skill_candidates() -> list[str]:
    """Return all known Codex baseline patch skill names in preference order."""
    return [*codex_phase_router_skill_candidates(), *codex_finish_work_skill_candidates()]


def command_phase_router_candidates() -> list[str]:
    """Prefer the current Trellis command carrier, but keep legacy fallback names."""
    return [PATCH_BASELINE_COMMANDS[0], LEGACY_PATCH_BASELINE_COMMANDS[0]]


def command_finish_work_candidates() -> list[str]:
    """Prefer the current Trellis command carrier, but keep legacy fallback names."""
    return [PATCH_BASELINE_COMMANDS[1], LEGACY_PATCH_BASELINE_COMMANDS[1]]


def command_record_session_candidates() -> list[str]:
    """Record-session is kept only for legacy target-project compatibility."""
    return [LEGACY_PATCH_BASELINE_COMMANDS[2]]


def _strip_conditional_blocks(content: str, tag: str) -> str:
    """Remove <!-- if:TAG --> ... <!-- endif:TAG --> blocks including markers."""
    import re
    pattern = re.compile(
        rf"^\s*<!--\s*if:{re.escape(tag)}\s*-->\s*\n"
        rf"(.*?)"
        rf"^\s*<!--\s*endif:{re.escape(tag)}\s*-->\s*\n?",
        re.MULTILINE | re.DOTALL,
    )
    return pattern.sub("", content)


def _clean_conditional_markers(content: str, tag: str) -> str:
    """Remove marker lines but keep the wrapped content."""
    import re
    content = re.sub(rf"^\s*<!--\s*if:{re.escape(tag)}\s*-->\s*\n", "", content, flags=re.MULTILINE)
    content = re.sub(rf"^\s*<!--\s*endif:{re.escape(tag)}\s*-->\s*\n?", "", content, flags=re.MULTILINE)
    return content


def source_repo_root() -> Path:
    """Return the authoring-repo root that owns the workflow product."""
    return Path(__file__).resolve().parents[4]


def trellis_library_root() -> Path:
    """Return the host-side trellis-library directory used by workflow tooling."""
    return source_repo_root() / "trellis-library"


def trellis_library_cli_path() -> Path:
    """Return the host-side trellis-library CLI path used by workflow tooling."""
    return trellis_library_root() / "cli.py"


def prepare_command_content(source_path: Path, *, profile: str = DEFAULT_PROFILE) -> str:
    """Return target-project-facing command content after deployment rewrites."""
    content = source_path.read_text(encoding="utf-8")
    trellis_library_cli = trellis_library_cli_path().as_posix()
    trellis_library_dir = trellis_library_root().as_posix()
    content = content.replace("<WORKFLOW_DIR>/commands/shell/", ".trellis/scripts/workflow/")
    content = content.replace("docs/workflows/新项目开发工作流/commands/shell/", ".trellis/scripts/workflow/")
    content = content.replace("见 `opencode/README.md`", "OpenCode 入口见目标项目 AGENTS.md 路由表")
    content = content.replace("见 `codex/README.md`", "Codex 入口见目标项目 AGENTS.md 路由表")
    content = content.replace("[阶段状态机与强门禁协议](../阶段状态机与强门禁协议.md)", "阶段状态机与强门禁协议")
    content = content.replace("`trellis-library/cli.py assemble`", f"`{trellis_library_cli} assemble`")
    content = content.replace("python3 trellis-library/cli.py ", f"python3 {trellis_library_cli} ")
    content = content.replace("从 `trellis-library` 选择并导入", f"从宿主仓库中的 `{trellis_library_dir}` 选择并导入")
    # Distributed commands and shared stage skills both live three directories
    # below the target-project root, so execution-card links must climb back to
    # the root before resolving .trellis/workflow-docs/.
    _docs_dir = f"../../../{WORKFLOW_DOCS_DIR}"
    content = content.replace(
        "[需求变更管理执行卡](../需求变更管理执行卡.md)",
        f"[需求变更管理执行卡]({_docs_dir}/需求变更管理执行卡.md)",
    )
    content = content.replace(
        "[需求变更管理执行卡](../../需求变更管理执行卡.md)",
        f"[需求变更管理执行卡]({_docs_dir}/需求变更管理执行卡.md)",
    )
    content = content.replace(
        "[源码水印与归属证据链执行卡](../源码水印与归属证据链执行卡.md)",
        f"[源码水印与归属证据链执行卡]({_docs_dir}/源码水印与归属证据链执行卡.md)",
    )
    content = content.replace(
        "[源码水印与归属证据链执行卡](../../源码水印与归属证据链执行卡.md)",
        f"[源码水印与归属证据链执行卡]({_docs_dir}/源码水印与归属证据链执行卡.md)",
    )
    if profile == "personal":
        content = _strip_conditional_blocks(content, "outsourcing")
    else:
        content = _clean_conditional_markers(content, "outsourcing")
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
            return codex_shared_skills_dir(root) / self.name / "SKILL.md"
        raise ValueError(f"Unsupported asset kind: {self.kind}")


@dataclass(frozen=True)
class ManagedAuditExtraSpec:
    capability: str
    mechanism: str
    claude_paths: tuple[str, ...] = ()
    opencode_paths: tuple[str, ...] = ()
    codex_paths: tuple[str, ...] = ()
    required_substrings: tuple[str, ...] = ()


def codex_shared_skills_dir(root: Path) -> Path:
    """Canonical shared skills directory for Codex/OpenCode shared skills."""
    return root / ".agents" / "skills"


def codex_secondary_skills_dir(root: Path) -> Path:
    """Codex-local skills directory reserved for Codex-only skills."""
    return root / ".codex" / "skills"


def resolve_codex_skills_dir(root: Path) -> Path | None:
    skills_dir = codex_shared_skills_dir(root)
    if skills_dir.is_dir():
        return skills_dir
    skills_dir = codex_secondary_skills_dir(root)
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
    for p in [codex_shared_skills_dir(root), codex_secondary_skills_dir(root)]:
        if p.is_dir():
            dirs.append(p)
    return dirs


def find_first_existing_codex_skill_path(
    root: Path,
    skill_names: list[str],
    *,
    skills_dir: Path | None = None,
) -> Path | None:
    """Return the first existing Codex skill path for the given candidate names."""
    resolved_dir = skills_dir or resolve_codex_skills_dir(root)
    if resolved_dir is None:
        return None
    for skill_name in skill_names:
        path = resolved_dir / skill_name / "SKILL.md"
        if path.exists():
            return path
    return None


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
                specs.append(
                    ManagedAssetSpec(
                        asset_id=f"codex:{name}",
                        category="added-command",
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


def build_managed_audit_extra_specs(cli_types: list[str]) -> list[ManagedAuditExtraSpec]:
    if not cli_types:
        return []

    execution_card_paths = tuple(
        f"{WORKFLOW_DOCS_DIR}/{name}" for name in [*EXECUTION_CARDS, *OUTSOURCING_EXECUTION_CARDS]
    )
    finish_work_template_paths = (f"{WORKFLOW_DOCS_DIR}/finish-work-checklist-template.md",)
    requirements_foundation_paths = (
        ".trellis/library-lock.yaml",
        *REQUIREMENTS_FOUNDATION_TARGET_PATHS,
    )

    return [
        ManagedAuditExtraSpec(
            capability="shared-artifact:workflow-installed-record",
            mechanism="Workflow writes .trellis/workflow-installed.json as the install/upgrade/uninstall contract record.",
            claude_paths=(".trellis/workflow-installed.json",),
            opencode_paths=(".trellis/workflow-installed.json",),
            codex_paths=(".trellis/workflow-installed.json",),
        ),
        ManagedAuditExtraSpec(
            capability="shared-doc:execution-cards",
            mechanism="Workflow deploys execution cards under .trellis/workflow-docs/ and references them from distributed commands/skills.",
            claude_paths=execution_card_paths,
            opencode_paths=execution_card_paths,
            codex_paths=execution_card_paths,
        ),
        ManagedAuditExtraSpec(
            capability="shared-doc:finish-work-checklist-template",
            mechanism="Workflow deploys a finish-work checklist template under .trellis/workflow-docs/ for close-out evidence scaffolding.",
            claude_paths=finish_work_template_paths,
            opencode_paths=finish_work_template_paths,
            codex_paths=finish_work_template_paths,
        ),
        ManagedAuditExtraSpec(
            capability="shared-pack:requirements-discovery-foundation-import",
            mechanism="Workflow auto-imports pack.requirements-discovery-foundation, producing .trellis/library-lock.yaml and foundational spec/checklist assets.",
            claude_paths=requirements_foundation_paths,
            opencode_paths=requirements_foundation_paths,
            codex_paths=requirements_foundation_paths,
        ),
        ManagedAuditExtraSpec(
            capability="shared-doc:agents-nl-routing-block",
            mechanism="Workflow injects an AGENTS.md natural-language routing block for non-hook command discovery.",
            claude_paths=("AGENTS.md",),
            opencode_paths=("AGENTS.md",),
            codex_paths=("AGENTS.md",),
            required_substrings=AGENTS_NL_ROUTING_MARKERS,
        ),
        ManagedAuditExtraSpec(
            capability="shared-state:backup-original-preservation",
            mechanism="Workflow preserves replaced baseline assets in .backup-original directories to support uninstall and upgrade-compat restoration.",
            claude_paths=(
                ".trellis/.backup-original",
                ".claude/commands/trellis/.backup-original",
            ),
            opencode_paths=(
                ".trellis/.backup-original",
                ".opencode/commands/trellis/.backup-original",
            ),
            codex_paths=(
                ".trellis/.backup-original",
                ".agents/skills/.backup-original",
                ".codex/skills/.backup-original",
            ),
        ),
        ManagedAuditExtraSpec(
            capability="shared-artifact:todo-reminder-file",
            mechanism="Workflow creates a root-level todo.txt reminder file as an intentional low-stakes collaboration artifact during installation.",
            claude_paths=("todo.txt",),
            opencode_paths=("todo.txt",),
            codex_paths=("todo.txt",),
        ),
    ]


def read_project_trellis_version(root: Path) -> str | None:
    version_path = root / ".trellis" / ".version"
    if not version_path.exists():
        return None
    try:
        content = version_path.read_text(encoding="utf-8").strip()
    except UnicodeDecodeError:
        return None
    return content or None


def parse_trellis_version(value: str | None) -> TrellisVersion | None:
    if not value:
        return None
    match = _TRELLIS_VERSION_RE.fullmatch(value.strip())
    if not match:
        return None
    label = match.group("label")
    prerelease_number = int(match.group("prenum") or 0)
    return TrellisVersion(
        major=int(match.group("major")),
        minor=int(match.group("minor")),
        patch=int(match.group("patch")),
        prerelease_label=label,
        prerelease_number=prerelease_number,
    )


def compare_trellis_versions(left: str, right: str) -> int | None:
    left_version = parse_trellis_version(left)
    right_version = parse_trellis_version(right)
    if left_version is None or right_version is None:
        return None
    if left_version.sort_key() < right_version.sort_key():
        return -1
    if left_version.sort_key() > right_version.sort_key():
        return 1
    return 0


def resolve_current_trellis_version() -> tuple[str | None, str]:
    overridden = os.environ.get(CURRENT_TRELLIS_VERSION_ENV, "").strip()
    if overridden:
        return overridden, CURRENT_TRELLIS_VERSION_ENV
    return resolve_latest_trellis_version()


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
