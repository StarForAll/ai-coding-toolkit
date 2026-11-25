"""Command construction and process hand-off.

The system command never implements install/upgrade/uninstall/repair semantics itself. It builds
the exact command for the release installer or the installed independent entry and replaces the
current process, preserving the caller's terminal for preview/token confirmation.
"""

from __future__ import annotations

import os
import sys


def _python():
    return sys.executable or "python3"


def installer_command(release_root, target, *, upgrade=False, confirm=False, python=None,
                      apply=False, export_deviations=False, out=None, keep=(), restore=(),
                      json_mode=False):
    installer = os.path.join(release_root, "install.py")
    command = [_python(), installer, "--target", target, "--strict-source"]
    if upgrade:
        command.append("--upgrade")
    if confirm:
        command.append("--confirm")
    if python:
        command.extend(["--python", python])
    if apply:
        command.append("--apply")
    if export_deviations:
        command.append("--export-deviations")
    if out:
        command.extend(["--out", out])
    for value in keep:
        command.extend(["--keep", value])
    for value in restore:
        command.extend(["--restore", value])
    if json_mode:
        command.append("--json")
    return command


def independent_command(project, kind, *, local_script=None, release_root=None, purge=False,
                        apply=False, dispose=None, json_mode=False):
    if kind not in ("uninstall", "repair"):
        raise ValueError(kind)
    if local_script and os.path.isfile(local_script):
        script = local_script
    elif release_root:
        script = os.path.join(release_root, "wf-release", "bin", f"{kind}.py")
    else:
        script = None
    if not script or not os.path.isfile(script):
        raise FileNotFoundError(kind)
    command = [_python(), script, "--project", project]
    if purge:
        command.append("--purge")
    if apply:
        command.append("--apply")
    if dispose:
        command.extend(["--dispose", dispose])
    if json_mode:
        command.append("--json")
    return command


def bootstrap_command(project, argv):
    script = os.path.join(project, ".wf", "bin", "wf.py")
    if not os.path.isfile(script):
        raise FileNotFoundError(script)
    return [_python(), script, *argv]


def exec_replace(command, exec_fn=None):
    env = os.environ.copy()
    if exec_fn is None:
        os.execve(command[0], command, env)
        return 0  # unreachable on POSIX
    return exec_fn(command[0], command, env)