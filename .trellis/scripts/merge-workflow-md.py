#!/usr/bin/env python3
"""One-shot producer for the merged .trellis/workflow.md (0.7.0 template + repo-local patches).

Design: the incoming 0.7.0 template is taken verbatim as the content baseline
(the repository's platform routing blocks are upstream-owned), then each
documented repo-local patch is applied as an anchored, exactly-once substitution.

Three guards, all of them fail-closed, make a half-applied merge impossible:
  1. the template baseline is proven byte-identical to the shipped trellis
     0.7.0-beta.4 template, so "theirs" is not a half-rendered file;
  2. every anchor must match exactly one occurrence, and must actually differ
     from its replacement, or the run aborts before writing anything;
  3. the shipped template is located at run time rather than pinned to one
     machine's npm prefix (see `TRELLIS_SHIPPED_TEMPLATE` and
     `discover_shipped_template`), and a machine where none of the probes
     yields one aborts instead of merging. Guard 1 is what proves the recorded
     baseline is the upstream file; downgrading it to a warning would let a
     truncated or hand-edited baseline be rewritten into `.trellis/workflow.md`
     with only the anchor count as evidence. Set `TRELLIS_SHIPPED_TEMPLATE` to
     the workflow.md, its directory, or a trellis package root to supply it
     explicitly (an explicit value that resolves to nothing is an error too).
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TEMPLATE = REPO / ".trellis/scripts/workflow-baselines/workflow-md.v0.7.0-beta.4.md"
TARGET = REPO / ".trellis/workflow.md"
# Base used only to reason about which hunks were local; kept for auditing the
# next upgrade (workflow-md.v0.5.17.md is the last upstream template this fork
# was derived from).
MERGE_BASE = REPO / ".trellis/scripts/workflow-baselines/workflow-md.v0.5.17.md"
# Guard 1 cross-checks the baseline above against the workflow.md shipped by the
# installed trellis package, so the merge must not commit an absolute npm
# prefix: a hard-coded one makes the script unusable on any other machine (it
# aborts before merging at all) and silently rots when the prefix changes.
# The template is located in this order:
#   $TRELLIS_SHIPPED_TEMPLATE — explicit workflow.md, its directory, or a
#                               package root; an explicit value that resolves
#                               to nothing is an error, not a skip;
#   the `trellis` / `tl` executable on PATH, resolved into its own package;
#   `npm root -g` / `pnpm root -g`, for installs whose bin shim does not
#                               resolve into the package directory.
# When none of them yields a template, the run aborts: guard 1 is mandatory, so
# a machine that cannot produce the shipped template must name it through
# `TRELLIS_SHIPPED_TEMPLATE` rather than merge against a baseline nothing
# verified.
SHIPPED_TEMPLATE_ENV = "TRELLIS_SHIPPED_TEMPLATE"
SHIPPED_TEMPLATE_REL = Path("dist/templates/trellis/workflow.md")
PACKAGE_DIR = Path("@mindfoldhq/trellis")
GLOBAL_ROOT_TIMEOUT_SECONDS = 20

# (label, upstream-anchor, local-replacement) — each anchor must occur exactly once.
PATCHES: list[tuple[str, str, str]] = [
    (
        "P2 invariant points at the repo-local regression test",
        "  INVARIANT (test/regression.test.ts):\n",
        "  INVARIANT (.trellis/scripts/common/tests/test_workflow_phase_contracts.py):\n",
    ),
    (
        "P4 TAG<->PHASE table documents the stale pseudo-status",
        "    [workflow-state:no_task]      → no active task; before Phase 1\n"
        "    [workflow-state:task_error]   → active task record is unreadable; repair it before continuing\n",
        "    [workflow-state:no_task]      → no active task; before Phase 1\n"
        "    [workflow-state:stale]        → active-task pointer exists but resolves to\n"
        "                                    a missing task directory; prompts the user\n"
        "                                    to repair or clear the stale pointer\n"
        "    [workflow-state:task_error]   → active task record is unreadable (task.json\n"
        "                                    missing, malformed, or missing a usable\n"
        "                                    status); repair it before continuing\n",
    ),
    (
        "P5 full-contract pointer targets a spec path this repo does not have",
        "    - Full runtime contract:\n"
        "      .trellis/spec/cli/backend/workflow-state-contract.md\n",
        "    - Full runtime contract lives in the live parser/hook implementations\n"
        "      under `.claude/hooks/`, `.codex/hooks/`, and `.agents/`\n"
        "      (`.opencode/`, `.qoder/`, `.kiro/` were retired for this repo)\n",
    ),
    (
        "P1 degraded-mode semantics of task.py start (Trellis System)",
        "If no context key is available from hook input, `TRELLIS_CONTEXT_ID`, or a platform-native session environment variable, there is no active task and `task.py start` fails with a session identity hint.",
        "If no context key is available from hook input, `TRELLIS_CONTEXT_ID`, or a platform-native session environment variable, `task.py start` falls back to degraded mode: it does not persist a session-scoped active-task pointer, but it still advances the task status. AI continues based on conversation context.",
    ),
    (
        "P6 degraded-mode semantics of task.py start (Phase 1.5)",
        "If `task.py start` errors with a session-identity message (no context key from hook input, `TRELLIS_CONTEXT_ID`, or platform-native session env), follow the hint in the error to set up session identity, then retry.",
        "If `task.py start` cannot resolve session identity (no context key from hook input, `TRELLIS_CONTEXT_ID`, or platform-native session env), it falls back to degraded mode: status still flips to `in_progress`, no session-scoped active-task pointer is persisted, and AI continues based on conversation context until the session identity path is restored.",
    ),
    (
        "P4b stale tag block (upstream has no stale state; mutually exclusive with task_error)",
        "<!-- Per-turn breadcrumb: shown when the active task record cannot be read. -->\n",
        "<!-- Per-turn breadcrumb: shown when the active-task pointer resolves to a task directory that no longer exists (stale), as opposed to a directory whose task.json is unreadable (task_error, block below). -->\n"
        "[workflow-state:stale]\n"
        "Active task pointer is stale: the session still points at a task directory that no longer exists.\n"
        "Before continuing implementation flow, repair the task context: run `python3 ./.trellis/scripts/task.py current --source` to inspect the stale pointer, then either `task.py finish` to clear it or `task.py start <task-dir>` to point the session at the correct live task.\n"
        "Do NOT treat this as `no_task` or silently continue Phase 2/3 work against missing context.\n"
        "[/workflow-state:stale]\n"
        "\n"
        "<!-- Per-turn breadcrumb: shown when the active task record cannot be read. -->\n",
    ),
    (
        "P3/P4c Customizing table lists both pseudo-statuses",
        "| No active task (before Phase 1) | `[workflow-state:no_task]` (after the Phase Index ASCII art) |\n"
        "| Active task record unreadable | `[workflow-state:task_error]` (repair the existing task before continuing) |\n",
        "| No active task (before Phase 1) | `[workflow-state:no_task]` (after the Phase Index ASCII art) |\n"
        "| Stale active-task pointer (task directory gone) | `[workflow-state:stale]` (after the `no_task` block) |\n"
        "| Active task record unreadable | `[workflow-state:task_error]` (repair the existing task before continuing) |\n",
    ),
    (
        "P7 1.3 curation instructions match what create actually seeds",
        "Curate `implement.jsonl` and `check.jsonl` so the Phase 2 sub-agents get the right spec/research context. "
        "These files were seeded on `task create` with a single self-describing `_example` line; your job here is to fill in real entries.",
        "Curate `implement.jsonl` and `check.jsonl` so the Phase 2 sub-agents get the right spec/research context. "
        "`task.py create` writes these two files **empty** on sub-agent-capable platforms — there is no seeded "
        "placeholder row to remove. (Only tasks created before the 0.7.0 upgrade carry a legacy `_example` row.) "
        "Your job here is to fill in real entries.",
    ),
    (
        "P7b legacy _example row is a hard validation error, not a skippable extra",
        "Delete the seed `_example` line once real entries exist (optional — it's skipped automatically by consumers).\n",
        "A legacy `_example` row is a hard error, not an ignorable extra: `task.py validate` reports "
        '"Placeholder `_example` row left by an older `task.py create` — delete this line". Remove it if you '
        "are bringing a pre-0.7.0 task forward; new tasks never contain one.\n",
    ),
    (
        "P8 intentionally-empty manifests need the documented start flag",
        "Ready gate: both `implement.jsonl` and `check.jsonl` must contain at least one real "
        '`{"file": "...", "reason": "..."}` entry before `task.py start`. The seed `_example` row alone is not ready.\n',
        "Ready gate: both `implement.jsonl` and `check.jsonl` must contain at least one real "
        '`{"file": "...", "reason": "..."}` entry before `task.py start`. A `_example` row does not satisfy it. '
        "When the manifests are meant to stay empty, `task.py start` refuses until you confirm it explicitly with "
        "`--allow-empty-context`; that flag is the acknowledgement that no sub-agent will consume them.\n",
    ),
    (
        "P9 inline platforms are told how to satisfy the start gate they still hit",
        "Skip this step. Context is loaded directly by the `trellis-before-dev` skill in Phase 2.\n",
        "Skip this step. Context is loaded directly by the `trellis-before-dev` skill in Phase 2.\n"
        "\n"
        "`task.py create` still creates `implement.jsonl` / `check.jsonl` when any sub-agent-capable platform is "
        "deployed (for example a checked-in `.claude/`), and those files stay empty because this step is skipped. "
        "`task.py start` therefore asks for `--allow-empty-context`: pass it to confirm that no sub-agent will "
        "consume the manifests for this task.\n",
    ),
    (
        "P10 the 1.4 start command carries the empty-context acknowledgement",
        "```bash\npython3 ./.trellis/scripts/task.py start <task-dir>\n```\n"
        "\n"
        "For lightweight tasks, `prd.md` can be enough. For complex tasks, `prd.md`, `design.md`, and "
        "`implement.md` must exist and be reviewed before start. On sub-agent-dispatch platforms, "
        "`implement.jsonl` and `check.jsonl` must both have real curated entries before start. Runtime "
        "consumers tolerate missing or seed-only manifests for compatibility, but that tolerance is not a "
        "planning-ready state.\n",
        "```bash\npython3 ./.trellis/scripts/task.py start <task-dir>\n```\n"
        "\n"
        "For lightweight tasks, `prd.md` can be enough. For complex tasks, `prd.md`, `design.md`, and "
        "`implement.md` must exist and be reviewed before start.\n"
        "\n"
        "**Intentionally empty manifests.** `task.py create` writes `implement.jsonl` / `check.jsonl` as "
        "empty files whenever any sub-agent-capable platform is deployed (a checked-in `.claude/` is enough). "
        "`task.py start` refuses to activate a task whose manifests are still empty, because every sub-agent "
        "dispatched for it would run with zero spec context. When those manifests are meant to stay empty, "
        "pass `--allow-empty-context` — it is the acknowledgement that nothing will consume them:\n"
        "\n"
        "```bash\npython3 ./.trellis/scripts/task.py start --allow-empty-context <task-dir>\n```\n"
        "\n"
        "Inline platforms (see 1.3) always land here, because 1.3 is skipped and the manifests are "
        "therefore never curated.\n",
    ),
    (
        "P10b the inline 1.3 note points at the flag on the start command",
        "`task.py start` therefore asks for `--allow-empty-context`: pass it to confirm that no sub-agent will "
        "consume the manifests for this task.\n",
        "`task.py start` therefore asks for `--allow-empty-context`; 1.4 shows the "
        "command carrying it.\n",
    ),
    (
        "P11 degraded-mode start documents how the task is found again",
        "If `task.py start` cannot resolve session identity (no context key from hook input, "
        "`TRELLIS_CONTEXT_ID`, or platform-native session env), it falls back to degraded mode: status still "
        "flips to `in_progress`, no session-scoped active-task pointer is persisted, and AI continues based on "
        "conversation context until the session identity path is restored.\n",
        "If `task.py start` cannot resolve session identity (no context key from hook input, "
        "`TRELLIS_CONTEXT_ID`, or platform-native session env), it falls back to degraded mode: status still "
        "flips to `in_progress`, no session-scoped active-task pointer is persisted, and AI continues based on "
        "conversation context until the session identity path is restored.\n"
        "\n"
        "Because nothing points at the task, a later session will not pick it up on its own. Find it, then "
        "re-establish the pointer with the variant that matches how the task is meant to run:\n"
        "\n"
        "```bash\n"
        "python3 ./.trellis/scripts/task.py list --status in_progress\n"
        "```\n"
        "\n"
        "Task will dispatch sub-agents (or already carries curated entries) — recover it as-is. This is the "
        "normal path, and an active gate is exactly what you want here:\n"
        "\n"
        "```bash\n"
        "python3 ./.trellis/scripts/task.py start <that-task-dir>\n"
        "```\n"
        "\n"
        "Task is intentionally manifest-free — either an inline platform (see 1.3) or a sub-agent task you have "
        "decided will not curate JSONL. Confirm that explicitly; otherwise curate and use the command above:\n"
        "\n"
        "```bash\n"
        "python3 ./.trellis/scripts/task.py start --allow-empty-context <that-task-dir>\n"
        "```\n"
        "\n"
        "Do not reach for `--allow-empty-context` by default: it is the acknowledgement that no sub-agent will "
        "consume the manifests, and using it where sub-agents are expected lets a task with zero spec context "
        "enter `in_progress`.\n"
        "\n"
        "Durable recovery exists only when session identity resolves — either by running inside a shell that "
        "exposes it, or by exporting `TRELLIS_CONTEXT_ID` before `task.py start`.\n",
    ),
    (
        "P5b tail pointer targets a spec path this repo does not have",
        "- `.trellis/spec/cli/backend/workflow-state-contract.md` — runtime contract + writer table + test invariants\n"
        "- `.trellis/scripts/inject-workflow-state.py` — actual parser (reads workflow.md only, no embedded text)\n",
        "- `.claude/hooks/inject-workflow-state.py` — Claude Code parser implementation + stale/task_error normalization\n"
        "- `.codex/hooks/inject-workflow-state.py` — Codex parser implementation (same normalization)\n"
        "- `.trellis/scripts/common/tests/test_workflow_phase_contracts.py` — repo-local regression test for every tag block and the stale/task_error mapping\n",
    ),
    (
        "P12 lifecycle command reference shows the required --description",
        'python3 ./.trellis/scripts/task.py create "<title>" [--slug <name>] [--parent <dir>]\n',
        'python3 ./.trellis/scripts/task.py create "<title>" --description "<summary>" [--slug <name>] [--parent <dir>]\n',
    ),
    (
        "P13 parent/child instruction shows the required --description",
        'Create new children with `task.py create "<title>" --slug <name> --parent <parent-dir>`.',
        'Create new children with `task.py create "<title>" --description "<one-line summary>" --slug <name> --parent <parent-dir>`.',
    ),
    (
        "P14 Phase 1.0 create command carries the required --description",
        'python3 ./.trellis/scripts/task.py create "<task title>" --slug <name>\n',
        'python3 ./.trellis/scripts/task.py create "<task title>" --description "<one-line summary>" --slug <name>\n',
    ),
    (
        "P15 Phase 1.0 states that --description is required, not optional",
        "`--slug` is the human-readable name only. Do **not** include the `MM-DD-` date prefix; `task.py create` adds that prefix automatically.\n",
        "`--description` is required, not optional: `task.py create` rejects a blank or missing value "
        "(a task whose description is empty is refused at archive), so pass it on every `create`. "
        "`--slug` is the human-readable name only. Do **not** include the `MM-DD-` date prefix; `task.py create` adds that prefix automatically.\n",
    ),
]


def _display(path: Path) -> str:
    """Repo-relative when possible, absolute otherwise (never raise)."""
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _template_in(root: Path) -> Path | None:
    """The shipped `workflow.md` inside a trellis package rooted at *root*."""
    candidate = root / SHIPPED_TEMPLATE_REL
    return candidate if candidate.is_file() else None


def _template_from_override(raw: str) -> tuple[Path | None, str]:
    """Resolve `$TRELLIS_SHIPPED_TEMPLATE` into a template path.

    Accepts the template file itself, the directory holding it, or a package
    root. An override that resolves to nothing returns no path, so the caller
    can fail on it: the variable is explicit user intent, and reporting "no
    cross-check" for a typo would hide the mistake.
    """
    candidate = Path(raw).expanduser()
    source = f"${SHIPPED_TEMPLATE_ENV}={candidate}"
    for path in (candidate, candidate / "workflow.md", candidate / SHIPPED_TEMPLATE_REL):
        if path.is_file():
            return path, source
    return None, source


def _template_from_executable(name: str) -> tuple[Path | None, str]:
    """Walk up from a resolved `name` executable to the package it belongs to."""
    executable = shutil.which(name)
    if not executable:
        return None, ""
    resolved = Path(executable).resolve()
    for parent in resolved.parents:
        found = _template_in(parent) or _template_in(
            parent / "lib/node_modules" / PACKAGE_DIR
        )
        if found is not None:
            return found, f"{name} on PATH, package at {_display(parent)}"
    return None, ""


def _template_from_global_root(tool: str) -> tuple[Path | None, str]:
    """`npm root -g` / `pnpm root -g`, for shims that stay outside the package."""
    executable = shutil.which(tool)
    if not executable:
        return None, ""
    try:
        completed = subprocess.run(
            [executable, "root", "-g"],
            capture_output=True,
            text=True,
            timeout=GLOBAL_ROOT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return None, ""
    root = completed.stdout.strip()
    if completed.returncode != 0 or not root:
        return None, ""
    found = _template_in(Path(root) / PACKAGE_DIR)
    if found is None:
        return None, ""
    return found, f"{tool} root -g, package at {_display(Path(root) / PACKAGE_DIR)}"


def discover_shipped_template() -> tuple[Path | None, str]:
    """Locate the shipped template and name its source ("" when not found)."""
    override = os.environ.get(SHIPPED_TEMPLATE_ENV, "").strip()
    if override:
        return _template_from_override(override)
    probes = (
        lambda: _template_from_executable("trellis"),
        lambda: _template_from_executable("tl"),
        lambda: _template_from_global_root("npm"),
        lambda: _template_from_global_root("pnpm"),
    )
    for probe in probes:
        found, source = probe()
        if found is not None:
            return found, source
    return None, ""


def main() -> int:
    override = os.environ.get(SHIPPED_TEMPLATE_ENV, "").strip()
    shipped, source = discover_shipped_template()
    if shipped is None:
        # Guard 1 is mandatory. Both ways of failing it are the same refusal,
        # but the diagnosis differs: an unusable override means the operator
        # named a path that is not a trellis template, while no override at all
        # means the probes found no install and the operator has to point at
        # one. Reporting "check skipped" for either one is how an unverified
        # baseline reaches `.trellis/workflow.md`.
        if override:
            print(
                f"ABORT: ${SHIPPED_TEMPLATE_ENV}={override} is not a workflow.md, "
                "the directory holding one, or a trellis package root",
                file=sys.stderr,
            )
        else:
            print(
                "ABORT: shipped trellis template not found — no trellis/tl on PATH, "
                f"no npm/pnpm global package, and ${SHIPPED_TEMPLATE_ENV} unset; "
                f"refusing to merge without proving {_display(TEMPLATE)} against it. "
                f"Set ${SHIPPED_TEMPLATE_ENV} to the workflow.md, the directory "
                "holding one, or a trellis package root.",
                file=sys.stderr,
            )
        return 1
    if _sha(shipped) != _sha(TEMPLATE):
        print(
            f"ABORT: {_display(TEMPLATE)} is not byte-identical to the "
            f"shipped trellis template ({_display(shipped)}, via {source}); "
            "refusing to merge against an unverified baseline",
            file=sys.stderr,
        )
        return 1
    print(
        f"baseline cross-check OK: {_display(TEMPLATE)} == "
        f"{_display(shipped)} (via {source})"
    )

    template = TEMPLATE.read_text(encoding="utf-8")
    merged = template

    for label, anchor, replacement in PATCHES:
        if anchor == replacement:
            print(f"ABORT: [{label}] anchor equals replacement", file=sys.stderr)
            return 1
        occurrences = merged.count(anchor)
        if occurrences != 1:
            print(
                f"ABORT: anchor for [{label}] matched {occurrences} time(s), expected 1",
                file=sys.stderr,
            )
            return 1
        merged = merged.replace(anchor, replacement, 1)
        print(f"applied: {label}")

    if merged == template:
        print("ABORT: nothing changed", file=sys.stderr)
        return 1

    TARGET.write_text(merged, encoding="utf-8")
    print(f"\nwrote {TARGET} ({len(merged)} chars, {len(merged.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
