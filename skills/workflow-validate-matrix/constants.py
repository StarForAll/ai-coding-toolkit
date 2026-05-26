"""Constants and configuration for workflow-validate-matrix."""

import os

# Python interpreter (allow override for local environments)
PYTHON_BIN = os.environ.get("PYTHON_BIN", "/ops/softwares/python/bin/python3")

# Trellis user (allow override via environment)
TRELLIS_USER = os.environ.get("TRELLIS_USER", "xzc")

# Embed-state values emitted by detect-embed-state.py --json
EMBED_STATE_INITIAL = "INITIAL_BASELINE_READY"
EMBED_STATE_VALID = "ALREADY_VALID_EMBEDDED"
EMBED_STATE_BLOCKED = "BLOCKED_NON_INITIAL_STATE"

# workflow-state.py route actions that indicate an unusable installed workflow
BLOCKING_ROUTE_ACTIONS = {
    "blocked",
    "embed_invalid",
    "repair_needed",
}

# Relative files that must exist after a successful install.
REQUIRED_POST_INSTALL_PATHS = (
    ".trellis/workflow-installed.json",
    ".trellis/workflow.md",
    ".trellis/library-lock.yaml",
    ".trellis/scripts/workflow/workflow-state.py",
    ".trellis/scripts/workflow/embed_integrity.py",
)

# Scenario definitions. Keep this small enough for pre-commit use, but diverse
# enough that "matrix" covers state/profile/CLI/upgrade boundaries.
SCENARIOS = [
    {
        "name": "clean-outsourcing-all-cli",
        "setup": "clean",
        "description": "Fresh Trellis baseline, outsourcing profile, all supported CLI adapters",
        "profile": "outsourcing",
        "cli": "claude,opencode,codex",
        "mode": "fresh-install",
        "expected_pre_status": EMBED_STATE_INITIAL,
        "expected_post_status": EMBED_STATE_VALID,
        "run_install": True,
        "run_upgrade_compat": False,
        "run_post_checks": True,
    },
    {
        "name": "clean-personal-claude",
        "setup": "clean",
        "description": "Fresh Trellis baseline, personal profile, Claude-only adapter",
        "profile": "personal",
        "cli": "claude",
        "mode": "fresh-install",
        "expected_pre_status": EMBED_STATE_INITIAL,
        "expected_post_status": EMBED_STATE_VALID,
        "run_install": True,
        "run_upgrade_compat": False,
        "run_post_checks": True,
    },
    {
        "name": "existing-customized-all-cli",
        "setup": "existing-customized",
        "description": "Existing Trellis project with task history and pre-existing CLI customizations",
        "profile": "outsourcing",
        "cli": "claude,opencode,codex",
        "mode": "fresh-install",
        "expected_pre_status": EMBED_STATE_INITIAL,
        "expected_post_status": EMBED_STATE_VALID,
        "run_install": True,
        "run_upgrade_compat": False,
        "run_post_checks": True,
    },
    {
        "name": "partial-failed-attempt",
        "setup": "failed-attempt",
        "description": "Project with a failed workflow-embed-attempt record; expected to be blocked before install",
        "profile": "outsourcing",
        "cli": "claude,opencode,codex",
        "mode": "blocked-state",
        "expected_pre_status": EMBED_STATE_BLOCKED,
        "run_install": False,
        "run_upgrade_compat": False,
        "run_post_checks": False,
    },
    {
        "name": "preinstalled-upgrade-check",
        "setup": "preinstalled-workflow",
        "description": "Already embedded workflow with legacy version metadata, validating upgrade-compat on an installed target",
        "profile": "outsourcing",
        "cli": "claude,opencode,codex",
        "mode": "upgrade-check",
        "expected_pre_status": EMBED_STATE_VALID,
        "expected_post_status": EMBED_STATE_VALID,
        "run_install": False,
        "run_upgrade_compat": True,
        "run_post_checks": True,
    },
]

# Validation commands
VALIDATION_STEPS = [
    "detect-embed-state",
    "install-workflow",
    "upgrade-compat",
    "workflow-state",
]

# Timeouts (seconds)
STEP_TIMEOUT = 300  # 5 minutes per step
TOTAL_TIMEOUT = 1800  # 30 minutes total

# Disk space requirement (bytes)
MIN_DISK_SPACE = 500 * 1024 * 1024  # 500MB

# Report protocol
PROTOCOL_VERSION = "workflow-scan-repair-v3"
DOCUMENT_TYPE = "workflow-questions"

# Temp directory pattern. Each scenario is a child of the same matrix root so a
# single temp-project-root can reference all finding locations.
TEMP_DIR_PATTERN = "/tmp/trellis-matrix-{timestamp}/{scenario}"
