"""Upgrade the system-level wf command itself.

This is deliberately separate from the project command ``wf upgrade``: that one upgrades the wf
assets inside a project to the newest project release; this one replaces the installed CLI. It
never accepts a version, tag or local checkout. The newest release is resolved from the registered
source, downloaded from the Forgejo release asset when available, and installed through the same
manager that owns the current command (uv/pipx, or pip on explicit request).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

from .release import SOURCE_URL, http_base, release_asset_url, validate_cli_tag
from .version import VERSION_RE, require_release_version, tag_name


class SelfUpgradeError(Exception):
    def __init__(self, code, message, facts=None, exit_hint=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.facts = facts or {}
        self.exit_hint = exit_hint


def manager_for(executable=None, requested=None, which=shutil.which):
    allowed = ("uv", "pipx", "pip")
    if requested:
        if requested not in allowed:
            raise SelfUpgradeError("WF_USAGE_INVALID", "未知的安装管理器",
                                   {"manager": requested, "known": list(allowed)},
                                   "用 --manager uv|pipx|pip 指定，或省略让命令自动识别")
        return requested
    path = os.path.realpath(executable or sys.executable)
    if "/uv/tools/" in path or "/.local/share/uv/" in path:
        return "uv"
    if "/pipx/venvs/" in path or "/.local/pipx/" in path:
        return "pipx"
    if which("uv"):
        return "uv"
    if which("pipx"):
        return "pipx"
    return None


def install_command(manager, target, executable=None, which=shutil.which):
    if manager == "uv":
        located = which("uv")
        if not located:
            raise SelfUpgradeError("WF_CAPABILITY_UNAVAILABLE", "找不到 uv，无法升级系统 wf",
                                   {"manager": "uv"},
                                   "安装 uv 后重试；或用 --manager pipx")
        return [located, "tool", "install", "--force", target]
    if manager == "pipx":
        located = which("pipx")
        if not located:
            raise SelfUpgradeError("WF_CAPABILITY_UNAVAILABLE", "找不到 pipx，无法升级系统 wf",
                                   {"manager": "pipx"},
                                   "安装 pipx 后重试；或用 --manager uv")
        return [located, "install", "--force", target]
    if manager == "pip":
        return [executable or sys.executable, "-m", "pip", "install",
                "--upgrade", "--force-reinstall", target]
    raise SelfUpgradeError("WF_USAGE_INVALID", "未知的安装管理器",
                           {"manager": manager, "known": ["uv", "pipx", "pip"]},
                           "用 --manager uv|pipx|pip 指定")


def git_spec(version, source_url=SOURCE_URL):
    require_release_version(version)
    if source_url.startswith("ssh://"):
        url = "git+ssh://" + source_url[len("ssh://"):]
    elif source_url.startswith("git+ssh://"):
        url = source_url
    else:
        raise SelfUpgradeError("WF_CAPABILITY_UNAVAILABLE", "登记发行源不是可安装的 git 地址",
                               {"source": source_url},
                               "核对登记源；不把本机路径当作系统安装源")
    return f"{url}@{tag_name(version)}#subdirectory=docs/workflows/wf-cli"


def _token():
    return os.environ.get("FORGEJO_TOKEN") or None


def download_asset(url, destination, token=None, opener=urllib.request.urlopen, timeout=120):
    headers = {"Accept": "application/octet-stream"}
    if token:
        headers["Authorization"] = "token " + token
    request = urllib.request.Request(url, headers=headers)
    try:
        response = opener(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise SelfUpgradeError(
            "WF_CAPABILITY_UNAVAILABLE", "无法下载系统 wf 发行资产",
            {"url": url, "status": exc.code},
            "私有仓库请在环境中提供 FORGEJO_TOKEN，或从 tag 用 git 安装；不把 token 写进命令/日志",
        ) from exc
    except OSError as exc:
        raise SelfUpgradeError("WF_CAPABILITY_UNAVAILABLE", "无法连接系统 wf 发行资产",
                               {"url": url, "detail": str(exc)},
                               "核对 forgejo 可达性与网络后重试") from exc
    try:
        with open(destination, "wb") as handle:
            while True:
                chunk = response.read(65536)
                if not chunk:
                    break
                handle.write(chunk)
    finally:
        close = getattr(response, "close", None)
        if close:
            close()
    if not os.path.isfile(destination) or os.path.getsize(destination) == 0:
        return None
    return destination


def run_install(manager, target, runner=subprocess.run, executable=None, which=shutil.which):
    command = install_command(manager, target, executable=executable, which=which)
    result = runner(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise SelfUpgradeError(
            "WF_CAPABILITY_UNAVAILABLE", "系统 wf 安装失败",
            {"manager": manager, "target": target, "exit": result.returncode,
             "stderr": (result.stderr or "").strip()[-800:]},
            "核对 uv/pipx 与 wheel 完整性后重试；不从失败结果声称已升级",
        )
    return (result.stdout or "").strip()


def perform(version, latest, *, manager=None, token=None, base=None, source_url=SOURCE_URL,
            download=download_asset, runner=subprocess.run, executable=None, which=shutil.which):
    """Install the CLI from the latest release, with a git-tag fallback for a missing asset."""
    require_release_version(version)
    require_release_version(latest.version)
    validate_cli_tag(latest.repo, latest.tag, latest.version)
    manager = manager_for(executable=executable, requested=manager, which=which)
    if manager is None:
        raise SelfUpgradeError("WF_CAPABILITY_UNAVAILABLE", "无法识别系统 wf 的安装管理器",
                               {"executable": executable or sys.executable},
                               "用 --manager uv|pipx|pip 指定；先 bootstrap 安装系统 wf")
    base = base if base is not None else http_base(source_url)
    token = token if token is not None else _token()
    asset_error = None
    target_kind = "git"
    target = git_spec(latest.version, source_url)
    if base:
        with tempfile.TemporaryDirectory(prefix="wf-self-upgrade-") as temporary:
            wheel = os.path.join(temporary, f"wf_cli-{latest.version}-py3-none-any.whl")
            try:
                downloaded = download(release_asset_url(latest.version, base), wheel, token)
            except SelfUpgradeError as exc:
                downloaded = None
                asset_error = {"code": exc.code, "message": exc.message, "facts": exc.facts}
            if downloaded:
                target = downloaded
                target_kind = "wheel"
            install_output = run_install(manager, target, runner=runner, executable=executable,
                                         which=which)
    else:
        install_output = run_install(manager, target, runner=runner, executable=executable,
                                     which=which)
    facts = {
        "from": version,
        "to": latest.version,
        "tag": latest.tag,
        "manager": manager,
        "target_kind": target_kind,
    }
    if asset_error:
        facts["asset_error"] = asset_error
    if install_output:
        facts["install_output"] = install_output[-800:]
    return facts


def latest_asset_name(version):
    require_release_version(version)
    return f"wf_cli-{version}-py3-none-any.whl"


def valid_version(value):
    return bool(VERSION_RE.match(value or ""))