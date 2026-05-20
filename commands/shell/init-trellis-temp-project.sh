#!/usr/bin/env zsh
set -euo pipefail

# --- Parse arguments ---
CUSTOM_PROJECT_PATH=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-path)
      if [[ $# -lt 2 ]]; then
        echo "ERROR: --project-path requires a value" >&2
        exit 1
      fi
      CUSTOM_PROJECT_PATH="$2"
      shift 2
      ;;
    *)
      echo "ERROR: Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

VERSION="$(trellis -v 2>/dev/null | head -1)"
if [[ -z "$VERSION" ]]; then
  echo "ERROR: trellis -v failed" >&2
  exit 1
fi

TMPDIR_PREFIX="/tmp/trellis-${VERSION}"
WORKFLOW_ROOT="/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流"
PYTHON_BIN="/ops/softwares/python/bin/python3"

if [[ -n "$CUSTOM_PROJECT_PATH" ]]; then
  TARGET_PROJECT="$CUSTOM_PROJECT_PATH"
else
  TARGET_PROJECT="${TMPDIR_PREFIX}-2"
fi

run_cmd() {
  local desc="$1"; shift
  local out
  out="$("$@" 2>&1)" && return 0
  echo "FAILED: ${desc}" >&2
  echo "$out" >&2
  return 1
}

# --- Step 1: clean old dirs (only in default /tmp mode) ---
if [[ -z "$CUSTOM_PROJECT_PATH" ]]; then
  run_cmd "rm -rf ${TMPDIR_PREFIX}*" rm -rf "${TMPDIR_PREFIX}"*
else
  if [[ -e "$TARGET_PROJECT" ]]; then
    echo "ERROR: --project-path target already exists: ${TARGET_PROJECT}" >&2
    exit 1
  fi
fi

# --- Step 2: mkcd ---
mkdir -p "$TARGET_PROJECT"
cd "$TARGET_PROJECT"

# --- Step 3: git init ---
run_cmd "git init" git init

# --- Step 4: git remote add ---
run_cmd "git remote add origin" git remote add origin git@gitee.com:AllstarsBelongToMe/xxx.git

# --- Step 5: git remote set-url push (gitee) ---
run_cmd "git remote set-url --add --push origin (gitee)" \
  git remote set-url --add --push origin git@gitee.com:AllstarsBelongToMe/xxx.git

# --- Step 6: git remote set-url push (github) ---
run_cmd "git remote set-url --add --push origin (github)" \
  git remote set-url --add --push origin git@github.com:StarForAll/xxx.git

# --- Step 7: git remote -v ---
run_cmd "git remote -v" git remote -v

# --- Step 8: trellis init ---
run_cmd "trellis init" trellis init --claude --opencode --codex -y -u xzc

# --- Step 9: sed config ---
run_cmd "sed .codex/config.toml" \
  sed -i '/min_wait_timeout_ms = 480000/a default_wait_timeout_ms = 480000' .codex/config.toml

# --- Step 10: detect-embed-state ---
run_cmd "detect-embed-state" \
  "$PYTHON_BIN" "$WORKFLOW_ROOT/commands/detect-embed-state.py" --project-root "$TARGET_PROJECT"

# --- Step 11: install-workflow --dry-run ---
run_cmd "install-workflow --dry-run" \
  "$PYTHON_BIN" "$WORKFLOW_ROOT/commands/install-workflow.py" --project-root "$TARGET_PROJECT" --dry-run

# --- Step 12: install-workflow ---
run_cmd "install-workflow" \
  env WORKFLOW_EMBED_EXECUTOR_CONFIRMED=1 "$PYTHON_BIN" "$WORKFLOW_ROOT/commands/install-workflow.py" --project-root "$TARGET_PROJECT"

# --- Step 13: upgrade-compat --check ---
run_cmd "upgrade-compat --check" \
  "$PYTHON_BIN" "$WORKFLOW_ROOT/commands/upgrade-compat.py" --project-root "$TARGET_PROJECT" --check

echo "trellis工作流临时项目新建成功: ${TARGET_PROJECT}"
