#!/usr/bin/env bash
# Create a throwaway Trellis target project under /tmp for manual verification.
#
# Scope: version probe + directory hygiene + `trellis init -y` with the platforms
# you ask for. It does NOT install, upgrade, or know about any workflow module —
# workflow assets are a separate concern (see docs/workflows/workflow-implementation.md).
#
# Usage: init-trellis-temp-project.sh [options]

set -euo pipefail

usage() {
  cat <<'EOF'
Usage: init-trellis-temp-project.sh [options]

Options:
  --path <dir>        Target directory (default: /tmp/trellis-<version>-<n>, first free n)
  --force             Remove an existing target directory first
  --platform <name>   Repeatable; passed to `trellis init` as --<name>
                      (claude, codex, zcode, pi, dsh, cursor, opencode, ...)
  --no-init           Only prepare the directory; do not run `trellis init`
  --dry-run           Print what would run; create nothing
  -h, --help          Show this help

Exit codes: 0 ok · 1 environment/usage error · 2 `trellis init` failed
EOF
}

log() { printf '[init-trellis-temp-project] %s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

TARGET=""
FORCE=0
NO_INIT=0
DRY_RUN=0
PLATFORMS=()

while [ $# -gt 0 ]; do
  case "$1" in
    --path)
      [ $# -ge 2 ] || die "--path requires a value"
      TARGET="$2"; shift 2 ;;
    --platform)
      [ $# -ge 2 ] || die "--platform requires a value"
      PLATFORMS+=("$2"); shift 2 ;;
    --force) FORCE=1; shift ;;
    --no-init) NO_INIT=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1 (try --help)" ;;
  esac
done

command -v trellis >/dev/null 2>&1 || die "trellis not found on PATH"
VERSION="$(trellis --version 2>/dev/null | head -1 | tr -d '[:space:]')"
[ -n "$VERSION" ] || die "could not read \`trellis --version\` output"

if [ -z "$TARGET" ]; then
  n=2
  while [ -e "/tmp/trellis-${VERSION}-${n}" ]; do n=$((n + 1)); done
  TARGET="/tmp/trellis-${VERSION}-${n}"
fi

if [ -e "$TARGET" ]; then
  if [ "$FORCE" -eq 1 ]; then
    log "removing existing target: $TARGET"
    [ "$DRY_RUN" -eq 1 ] || rm -rf -- "$TARGET"
  else
    die "target already exists: $TARGET (pass --force to recreate)"
  fi
fi

INIT_ARGS=(init -y)
for platform in ${PLATFORMS[@]+"${PLATFORMS[@]}"}; do
  INIT_ARGS+=("--${platform}")
done

log "target : $TARGET"
log "trellis: $VERSION"
[ "$DRY_RUN" -eq 1 ] || mkdir -p -- "$TARGET"

if [ "$NO_INIT" -eq 1 ]; then
  log "prepared only (--no-init)"
  exit 0
fi

if [ "$DRY_RUN" -eq 1 ]; then
  log "would run: (cd $TARGET && trellis ${INIT_ARGS[*]})"
  exit 0
fi

if ! ( cd "$TARGET" && trellis "${INIT_ARGS[@]}" ); then
  printf 'ERROR: `trellis init` failed in %s\n' "$TARGET" >&2
  exit 2
fi

log "ready. Next: (cd $TARGET && git status && python3 .trellis/scripts/get_context.py)"
