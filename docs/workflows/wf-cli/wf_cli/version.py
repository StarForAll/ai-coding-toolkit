"""Version resolution for the system-level wf command.

The single version source is the release manifest (`docs/workflows/wf-release/wf-release.json`).
A wheel built from git embeds that version in its metadata, so the installed command and the
release it installs cannot drift. The source-tree fallback keeps ``python -m wf_cli`` usable
without installing the package.
"""

from __future__ import annotations

import json
import os
import re
from importlib.metadata import PackageNotFoundError, version as distribution_version

DIST_NAME = "wf-cli"
VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


class VersionError(Exception):
    """The CLI version cannot be used as a release identity."""


def manifest_path():
    here = os.path.realpath(__file__)
    workflows = os.path.dirname(os.path.dirname(os.path.dirname(here)))
    return os.path.join(workflows, "wf-release", "wf-release.json")


def source_version():
    path = manifest_path()
    try:
        with open(path, "r", encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (OSError, ValueError) as exc:
        raise VersionError(f"cannot read release manifest {path}: {exc}") from exc
    value = str((manifest or {}).get("version") or "")
    if not VERSION_RE.match(value):
        raise VersionError(f"release manifest has an invalid version: {value!r}")
    return value


def cli_version():
    """Return the installed CLI version, falling back to the checked-out release manifest."""
    try:
        value = distribution_version(DIST_NAME)
        if VERSION_RE.match(value or ""):
            return value
    except PackageNotFoundError:
        pass
    except Exception:
        pass
    try:
        return source_version()
    except VersionError:
        return "0.0.0+unknown"


def require_release_version(value):
    if not VERSION_RE.match(value or ""):
        raise VersionError(f"wf 版本不可用于发行解析：{value!r}（只接受 X.Y.Z）")
    return value


def tag_name(value):
    return "wf-v" + require_release_version(value)


def tag_ref(value):
    return "refs/tags/" + tag_name(value)