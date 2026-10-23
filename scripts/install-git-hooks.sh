#!/usr/bin/env sh
# Install the repository's tracked git hooks into this clone.
#
# The pre-push hook verifies DSH plugins before a push that carries plugin
# changes: plugins that declare `build:client` are rebuilt (git dependencies
# never run `prepack`) and every pushed plugin worktree must be clean. It is
# linked into `.git/hooks/pre-push` rather than replacing `core.hooksPath`, so an
# existing hook manager (for example Sonar's, which chains to
# `.git/hooks/pre-push`) keeps working.
set -eu

fail() {
  echo "ERROR: install-git-hooks: $*" >&2
  exit 1
}

command -v git >/dev/null 2>&1 || fail "git is required"
root=$(git rev-parse --show-toplevel)
cd "$root"

source_path="scripts/git-hooks/pre-push"
# `--git-path hooks` follows core.hooksPath; the chainable local slot is
# always <git-common-dir>/hooks, which Sonar-style managers delegate to.
git_dir=$(git rev-parse --git-common-dir)
case "$git_dir" in
  /*) ;;
  *) git_dir="$root/$git_dir" ;;
esac
hooks_dir="$git_dir/hooks"
mkdir -p "$hooks_dir"
target="$hooks_dir/pre-push"

if [ ! -x "$source_path" ]; then
  chmod +x "$source_path"
fi

if [ -e "$target" ] || [ -L "$target" ]; then
  same_link=0
  if [ -L "$target" ] && [ "$(readlink "$target")" = "$root/$source_path" ]; then
    same_link=1
  fi
  if [ "$same_link" -eq 0 ] && ! grep -q "Verify DSH plugins before a push that carries plugin changes" "$target" 2>/dev/null; then
    fail "refusing to overwrite an existing $target; move it aside and re-run."
  fi
fi

ln -sfn "$root/$source_path" "$target"
echo "OK: installed $target -> $root/$source_path"

active=$(git config --get core.hooksPath || true)
if [ -n "$active" ]; then
  case "$active" in
    /*) active_dir="$active" ;;
    *) active_dir="$root/$active" ;;
  esac
  if [ -x "$active_dir/pre-push" ] && grep -q "hooks/pre-push" "$active_dir/pre-push" 2>/dev/null; then
    echo "OK: core.hooksPath=$active; its pre-push chains to $target (Sonar-style), so both run."
  else
    echo "WARN: core.hooksPath=$active does not chain to .git/hooks/pre-push." >&2
    echo "WARN: install this hook there, or unset core.hooksPath, for it to run." >&2
  fi
fi
