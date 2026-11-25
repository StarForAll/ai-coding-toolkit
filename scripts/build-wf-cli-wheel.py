#!/usr/bin/env python3
"""Build the system-level wf command wheel for a Forgejo release.

The wheel is a release attachment, not a target-project asset and not a member of
`wf-release.json`. It is built from the same version source as the release manifest, then attached
to the matching `wf-vX.Y.Z` release so `install.py` / `wf self-upgrade` can install the system
command without a version argument.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLI_ROOT = REPO_ROOT / "docs" / "workflows" / "wf-cli"
MANIFEST = REPO_ROOT / "docs" / "workflows" / "wf-release" / "wf-release.json"
WHEEL_RE = re.compile(r"^wf_cli-(\d+\.\d+\.\d+)-py3-none-any\.whl$")


class BuildError(Exception):
    pass


def release_version():
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BuildError(f"cannot read release manifest: {exc}") from exc
    value = str(manifest.get("version") or "")
    if not re.match(r"^\d+\.\d+\.\d+$", value):
        raise BuildError(f"release manifest version is not X.Y.Z: {value!r}")
    return value


def build_wheel(out_dir, version=None):
    version = version or release_version()
    current = release_version()
    if version != current:
        raise BuildError(f"requested {version}, release manifest is {current}")
    uv = shutil.which("uv")
    if not uv:
        raise BuildError("uv is required to build the wf-cli wheel")
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [uv, "build", "--project", str(CLI_ROOT), "--out-dir", str(out_dir)],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise BuildError("uv build failed: " + (result.stderr or result.stdout).strip()[-800:])
    wheels = sorted(out_dir.glob("wf_cli-*.whl"))
    matches = [path for path in wheels if WHEEL_RE.match(path.name) and WHEEL_RE.match(path.name).group(1) == version]
    if len(matches) != 1:
        raise BuildError(f"expected one wf_cli-{version} wheel, found {[path.name for path in wheels]}")
    bootstrap = CLI_ROOT / "install.py"
    if not bootstrap.is_file():
        raise BuildError("missing docs/workflows/wf-cli/install.py")
    shutil.copyfile(bootstrap, out_dir / "install.py")
    os.chmod(out_dir / "install.py", 0o755)
    return matches[0]


def main(argv=None):
    parser = argparse.ArgumentParser(description="构建系统级 wf 命令 wheel（发行附件）")
    parser.add_argument("--version", default=None, help="0.x.y；缺省读发行清单；用于防止构建错版")
    parser.add_argument("--out", default=str(REPO_ROOT / "tmp" / "wf-cli-dist"),
                        help="输出目录；缺省 tmp/wf-cli-dist（已被 .gitignore 忽略）")
    args = parser.parse_args(argv)
    try:
        wheel = build_wheel(args.out, args.version)
    except BuildError as exc:
        sys.stdout.write(f"BLOCKED  WF_CAPABILITY_UNAVAILABLE\n事实: {exc}\n")
        return 1
    sys.stdout.write(f"OK  {wheel}\n")
    sys.stdout.write(f"OK  {Path(args.out).resolve() / 'install.py'}\n")
    sys.stdout.write("下一步：把 wheel 与 install.py 都作为 Forgejo release 附件；release 名称/附件版本必须与 tag 一致。\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())