#!/usr/bin/env bash
# Install the system wf command from the newest wf-v* tag over SSH.
#
# This is the fallback when the Forgejo HTTP/API (release assets) is unavailable but git over
# SSH works. It resolves the newest tag by tag/commit date (not by semver maximum), then installs
# the wf-cli package from that tag. It does not accept a version argument.
set -euo pipefail

SOURCE_URL="${WF_GIT_URL:-ssh://git@forgejo.xzc.com:13768/xzc/ai-coding-toolkit.git}"
if ! command -v git >/dev/null 2>&1; then
  echo "BLOCKED  WF_CAPABILITY_UNAVAILABLE: 缺少 git" >&2
  exit 1
fi

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
repo="$tmp/repo"

clone() {
  git clone --quiet --no-checkout "$@" "$SOURCE_URL" "$repo"
}
if ! clone --filter=blob:none; then
  rm -rf "$repo"
  clone
fi

tag="$(git -C "$repo" for-each-ref --sort=-creatordate --format='%(refname:short)' 'refs/tags/wf-v*' | head -1)"
if ! [[ "$tag" =~ ^wf-v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "BLOCKED  WF_CAPABILITY_UNAVAILABLE: 默认分支上没有 wf-vX.Y.Z tag（tag=$tag）" >&2
  echo "出口: 先创建/推送 wf-vX.Y.Z tag，再重试" >&2
  exit 1
fi

case "$SOURCE_URL" in
  git+ssh://*) vcs="$SOURCE_URL" ;;
  ssh://*) vcs="git+ssh://${SOURCE_URL#ssh://}" ;;
  *) echo "BLOCKED  WF_CAPABILITY_UNAVAILABLE: WF_GIT_URL 必须是 ssh:// 或 git+ssh://" >&2; exit 1 ;;
esac
spec="${vcs}@${tag}#subdirectory=docs/workflows/wf-cli"

if command -v uv >/dev/null 2>&1; then
  uv tool install --force "$spec"
elif command -v pipx >/dev/null 2>&1; then
  pipx install --force "$spec"
else
  echo "BLOCKED  WF_CAPABILITY_UNAVAILABLE: 没有 uv 或 pipx" >&2
  exit 1
fi

printf 'OK  system wf installed from %s\n' "$tag"
printf '下一步: wf version\n'
