#!/usr/bin/env bash
# Push a wf release tag and attach the system command release assets.
# Usage: scripts/push-wf-tag.sh wf-vX.Y.Z [remote]
# The pre-push hook verifies the release and builds tmp/wf-cli-dist; this wrapper runs the
# attachment after the tag exists on the remote (git has no post-push hook).
set -euo pipefail

tag="${1:-}"
remote="${2:-backup}"
if ! [[ "$tag" =~ ^wf-v([0-9]+\.[0-9]+\.[0-9]+)$ ]]; then
  echo "usage: $0 wf-vX.Y.Z [remote]" >&2
  exit 1
fi
version="${BASH_REMATCH[1]}"
if ! git rev-parse --verify "refs/tags/$tag" >/dev/null 2>&1; then
  echo "ERROR: tag $tag 不存在；先提交发行树并 git tag $tag" >&2
  exit 1
fi
if [ -n "$(git status --porcelain -- docs/workflows/wf-release docs/workflows/wf-cli)" ]; then
  echo "ERROR: 发行树或 wf-cli 有未提交改动；先提交后再推送 tag" >&2
  git status --short -- docs/workflows/wf-release docs/workflows/wf-cli >&2
  exit 1
fi

git push "$remote" "refs/tags/$tag"

wheel="tmp/wf-cli-dist/wf_cli-$version-py3-none-any.whl"
if [ ! -f "$wheel" ]; then
  python3 scripts/build-wf-cli-wheel.py --version "$version" --out tmp/wf-cli-dist
fi
if ! python3 scripts/attach-wf-cli-asset.py --create-release --tag "$tag" --wheel "$wheel"; then
  echo "ERROR: tag 已推送，但 release 附件未完成；修网络/token 后重跑：" >&2
  echo "ERROR:   python3 scripts/attach-wf-cli-asset.py --create-release --tag $tag --wheel $wheel" >&2
  exit 1
fi
printf 'OK  %s 已推送并附加系统命令 release 资产\n' "$tag"
printf '安装：curl -fsSL "${WF_FORGEJO_BASE:-https://forgejo.xzc.com}/xzc/ai-coding-toolkit/releases/download/latest/install.py" | python3 -\n'
