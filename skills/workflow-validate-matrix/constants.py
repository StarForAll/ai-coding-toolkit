"""Constants and configuration for workflow-validate-matrix."""

from pathlib import Path

# Workflow source location (relative to repo root)
WORKFLOW_SOURCE_REL = "docs/workflows/新项目开发工作流"

# Python interpreter
PYTHON_BIN = "/ops/softwares/python/bin/python3"

# Scenario definitions (MVP: 3 scenarios)
SCENARIOS = [
    {
        "name": "clean",
        "description": "Empty directory with git init only",
        "profile": "outsourcing",
        "cli": "claude,opencode,codex",
    },
    {
        "name": "existing-trellis",
        "description": "After trellis init",
        "profile": "outsourcing",
        "cli": "claude,opencode,codex",
    },
    {
        "name": "existing-workflow",
        "description": "With old workflow installed (upgrade scenario)",
        "profile": "outsourcing",
        "cli": "claude,opencode,codex",
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

# Temp directory pattern
TEMP_DIR_PATTERN = "/tmp/trellis-matrix-{timestamp}-{scenario}"
