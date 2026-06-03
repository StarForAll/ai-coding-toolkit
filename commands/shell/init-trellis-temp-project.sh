#!/usr/bin/env zsh
set -euo pipefail

# --- Parse arguments ---
CUSTOM_PROJECT_PATH=""
INSTALL_PROFILE=""
PROJECT_ID=""

normalize_profile() {
  local raw="${1:l}"
  case "$raw" in
    personal|p)
      echo "personal"
      ;;
    outsourcing|o)
      echo "outsourcing"
      ;;
    *)
      return 1
      ;;
  esac
}

prompt_profile() {
  if [[ ! -t 0 || ! -t 1 ]]; then
    echo "ERROR: --profile is required in non-interactive mode" >&2
    exit 1
  fi

  local input normalized
  while true; do
    printf '请选择安装 profile (personal/outsourcing，或 p/o): ' >&2
    read -r input
    if normalized="$(normalize_profile "$input")"; then
      echo "$normalized"
      return 0
    fi
    echo "ERROR: invalid profile, use personal / outsourcing or p / o" >&2
  done
}

prompt_project_id() {
  if [[ ! -t 0 || ! -t 1 ]]; then
    echo "ERROR: --project-id is required in non-interactive mode" >&2
    exit 1
  fi

  local input
  while true; do
    printf '请输入 project id: ' >&2
    read -r input
    if [[ "$input" =~ ^[A-Za-z]([A-Za-z0-9:_-]*[A-Za-z])?$ ]]; then
      echo "$input"
      return 0
    fi
    echo "ERROR: invalid --project-id (must start/end with letters; middle may contain letters, digits, :, -, _)" >&2
  done
}

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
    --profile)
      if [[ $# -lt 2 ]]; then
        echo "ERROR: --profile requires a value" >&2
        exit 1
      fi
      if ! INSTALL_PROFILE="$(normalize_profile "$2")"; then
        echo "ERROR: invalid --profile value: $2 (use personal / outsourcing or p / o)" >&2
        exit 1
      fi
      shift 2
      ;;
    --project-id)
      if [[ $# -lt 2 ]]; then
        echo "ERROR: --project-id requires a value" >&2
        exit 1
      fi
      PROJECT_ID="$2"
      shift 2
      ;;
    *)
      echo "ERROR: Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "$INSTALL_PROFILE" ]]; then
  INSTALL_PROFILE="$(prompt_profile)"
fi

if [[ -z "$PROJECT_ID" ]]; then
  PROJECT_ID="$(prompt_project_id)"
fi

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
  "$PYTHON_BIN" "$WORKFLOW_ROOT/commands/install-workflow.py" --project-root "$TARGET_PROJECT" --project-id "$PROJECT_ID" --profile "$INSTALL_PROFILE" --dry-run

# --- Step 12: install-workflow ---
echo "人工执行要求: formal embed 只能由人类操作者在交互式系统终端中显式运行并确认。"
echo "请在 shell 中按以下顺序手动执行，并在 formal install 时完成 EMBED 确认："
echo "\"$PYTHON_BIN\" \"$WORKFLOW_ROOT/commands/detect-embed-state.py\" --project-root \"$TARGET_PROJECT\""
echo "\"$PYTHON_BIN\" \"$WORKFLOW_ROOT/commands/install-workflow.py\" --project-root \"$TARGET_PROJECT\" --project-id \"$PROJECT_ID\" --profile \"$INSTALL_PROFILE\" --dry-run"
echo "WORKFLOW_EMBED_HUMAN_CONFIRMED=1 \"$PYTHON_BIN\" \"$WORKFLOW_ROOT/commands/install-workflow.py\" --project-root \"$TARGET_PROJECT\" --project-id \"$PROJECT_ID\" --profile \"$INSTALL_PROFILE\""
echo "\"$PYTHON_BIN\" \"$WORKFLOW_ROOT/commands/upgrade-compat.py\" --project-root \"$TARGET_PROJECT\" --check"
echo "注意: 第 3 条命令执行过程中需要按提示输入: EMBED $PROJECT_ID"
exit 0
