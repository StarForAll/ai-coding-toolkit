#!/usr/bin/env python3
"""Bootstrap the system-level wf command from the newest Forgejo release.

No version is accepted: the script asks the repository release API for the newest published
release, requires that release to carry the `wf_cli-<version>-py3-none-any.whl` system-install
asset, downloads it, and installs it through uv or pipx. Use it as:

    curl -fsSL "https://forgejo.xzc.com:13785/xzc/ai-coding-toolkit/raw/branch/main/docs/workflows/wf-cli/install.py" | python3 -

For a private repository set FORGEJO_TOKEN in the environment (never pass it as an argument).

On success the base that actually served the asset is written to the machine install record
(`~/.wf/system-command.json`). `wf self-upgrade` reads the same record, so the upgrade uses the
same asset URL source as this install instead of guessing one from the git source URL. The record
path and schema are duplicated here on purpose: this file must stay runnable standalone before the
package exists (parity is pinned by `scripts/tests/test_wf_cli.py`).

The registered instance serves the Web/API endpoint on port 13785 (git runs on another port), so
the base default carries that port; never derive an HTTP base from the git source URL.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE = os.environ.get("WF_FORGEJO_BASE") or "https://forgejo.xzc.com:13785"
DEFAULT_REPO = "xzc/ai-coding-toolkit"
# 与 `wf_cli.release` 的同名常量逐字一致（写/读两端同一事实，由 parity 用例锁住）
INSTALL_RECORD_REL = (".wf", "system-command.json")
INSTALL_RECORD_SCHEMA = 1
TAG_RE = re.compile(r"^wf-v(\d+)\.(\d+)\.(\d+)$")
WHEEL_RE = re.compile(r"^wf[_-]cli-(\d+\.\d+\.\d+)-py3-none-any\.whl$")


class BootstrapError(Exception):
    def __init__(self, code, message, facts=None, exit_hint=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.facts = facts or {}
        self.exit_hint = exit_hint


def _request(url, token=None, timeout=120):
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = "token " + token
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout)


def _json(url, token=None):
    try:
        with _request(url, token) as response:
            payload = response.read()
    except urllib.error.HTTPError as exc:
        hint = ("私有仓库请在环境中设置 FORGEJO_TOKEN" if exc.code in (401, 403)
                else "核对 Forgejo HTTP/API（可用 WF_FORGEJO_BASE 指定）；若只有 SSH 可用，用 scripts/install-wf-ssh.sh")
        raise BootstrapError("WF_CAPABILITY_UNAVAILABLE", "无法读取 Forgejo 发行列表",
                             {"url": url, "status": exc.code}, hint) from exc
    except OSError as exc:
        raise BootstrapError("WF_CAPABILITY_UNAVAILABLE", "无法连接 Forgejo 发行列表",
                             {"url": url, "detail": str(exc)},
                             "核对 Forgejo HTTP/API 与 WF_FORGEJO_BASE；若只有 SSH 可用，用 scripts/install-wf-ssh.sh") from exc
    try:
        return json.loads(payload.decode("utf-8"))
    except ValueError as exc:
        raise BootstrapError("WF_CAPABILITY_UNAVAILABLE", "Forgejo 发行列表不是 JSON",
                             {"url": url, "detail": str(exc)}, "核对 API 地址") from exc


def _version_from_tag(tag):
    match = TAG_RE.match(tag or "")
    return ".".join(match.groups()) if match else None


def latest_release(base, repo, token=None):
    url = f"{base.rstrip('/')}/api/v1/repos/{repo}/releases?limit=20"
    payload = _json(url, token)
    if not isinstance(payload, list):
        raise BootstrapError("WF_CAPABILITY_UNAVAILABLE", "Forgejo 发行列表不是数组",
                             {"url": url}, "核对 Forgejo API 版本")
    releases = []
    for entry in payload:
        if not isinstance(entry, dict) or entry.get("draft") or entry.get("prerelease"):
            continue
        tag = str(entry.get("tag_name") or "")
        version = _version_from_tag(tag)
        if not version:
            continue
        releases.append((str(entry.get("published_at") or entry.get("created_at") or ""),
                         tag, version, entry))
    if not releases:
        raise BootstrapError("WF_CAPABILITY_UNAVAILABLE", "Forgejo 没有可用的 wf-vX.Y.Z 正式发行",
                             {"base": base, "repo": repo},
                             "先创建正式 release，不标 draft/prerelease")
    releases.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return releases[0]


def wheel_asset(release, base, repo):
    tag, version, entry = release[1], release[2], release[3]
    assets = entry.get("assets") or []
    expected = f"wf_cli-{version}-py3-none-any.whl"
    candidates = []
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name") or "")
        match = WHEEL_RE.match(name)
        if match and match.group(1) == version:
            candidates.append(asset)
    chosen = next((item for item in candidates if item.get("name") == expected), None)
    if chosen is None and candidates:
        chosen = candidates[0]
    if chosen is None:
        names = sorted(str(item.get("name")) for item in assets if isinstance(item, dict))
        raise BootstrapError(
            "WF_CAPABILITY_UNAVAILABLE", "最新发行缺少系统 wf 安装 wheel",
            {"tag": tag, "version": version, "assets": names,
             "expected": expected},
            "把 scripts/build-wf-cli-wheel.py 生成的 wheel 作为该 release 附件后重试",
        )
    url = chosen.get("browser_download_url")
    if not url:
        url = f"{base.rstrip('/')}/{repo}/releases/download/{tag}/{chosen['name']}"
    parsed = urllib.parse.urlparse(str(url))
    if not parsed.scheme:
        url = base.rstrip("/") + "/" + str(url).lstrip("/")
    return str(url), tag, version, chosen["name"]


def download(url, destination, token=None):
    try:
        with _request_bytes(url, token) as response:
            with open(destination, "wb") as handle:
                while True:
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    handle.write(chunk)
    except urllib.error.HTTPError as exc:
        raise BootstrapError("WF_CAPABILITY_UNAVAILABLE", "无法下载系统 wf wheel",
                             {"url": url, "status": exc.code},
                             "私有仓库请在环境中设置 FORGEJO_TOKEN") from exc
    except OSError as exc:
        raise BootstrapError("WF_CAPABILITY_UNAVAILABLE", "无法下载系统 wf wheel",
                             {"url": url, "detail": str(exc)}, "核对网络后重试") from exc
    if not os.path.isfile(destination) or os.path.getsize(destination) == 0:
        raise BootstrapError("WF_CAPABILITY_UNAVAILABLE", "系统 wf wheel 下载为空",
                             {"url": url}, "核对 release 附件后重试")


def _request_bytes(url, token=None):
    headers = {"Accept": "application/octet-stream"}
    if token:
        headers["Authorization"] = "token " + token
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=120)


def manager_for(requested=None, which=shutil.which):
    if requested:
        return requested
    if which("uv"):
        return "uv"
    if which("pipx"):
        return "pipx"
    return None


def install(manager, wheel):
    if manager == "uv":
        located = shutil.which("uv")
        if not located:
            raise BootstrapError("WF_CAPABILITY_UNAVAILABLE", "找不到 uv", {}, "安装 uv 后重试")
        command = [located, "tool", "install", "--force", wheel]
    elif manager == "pipx":
        located = shutil.which("pipx")
        if not located:
            raise BootstrapError("WF_CAPABILITY_UNAVAILABLE", "找不到 pipx", {}, "安装 pipx 后重试")
        command = [located, "install", "--force", wheel]
    else:
        raise BootstrapError("WF_CAPABILITY_UNAVAILABLE", "没有 uv 或 pipx，无法安装系统 wf",
                             {}, "先安装 uv 或 pipx 后重试")
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise BootstrapError("WF_CAPABILITY_UNAVAILABLE", "系统 wf 安装失败",
                             {"command": command, "exit": result.returncode,
                              "stderr": (result.stderr or "").strip()[-800:]},
                             "核对 wheel 与 uv/pipx 后重试")
    return (result.stdout or "").strip()


def write_install_record(base, repo, now=None):
    """写下"这个基址确实取到了发行资产"这一本机事实（原子写、0600）。

    记录只承载资产基址，不存版本/tag（它们随升级变化，记下来必然过期）。
    """
    import datetime

    target = os.path.join(os.path.expanduser("~"), *INSTALL_RECORD_REL)
    payload = {
        "schema_version": INSTALL_RECORD_SCHEMA,
        "http_base": str(base).rstrip("/"),
        "repo": repo,
        "written_at": (now or datetime.datetime.now(datetime.timezone.utc)
                       ).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
    }
    directory = os.path.dirname(target) or "."
    os.makedirs(directory, mode=0o700, exist_ok=True)
    temporary = target + ".tmp"
    with open(temporary, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(temporary, 0o600)
    os.replace(temporary, target)
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description="从最新 Forgejo 发行安装系统 wf 命令（无版本参数）")
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--token-env", default="FORGEJO_TOKEN",
                        help="保存 token 的环境变量名；token 不作为参数传入")
    parser.add_argument("--manager", choices=("uv", "pipx"), default=None)
    args = parser.parse_args(argv)
    token = os.environ.get(args.token_env) or None
    try:
        release = latest_release(args.base, args.repo, token)
        url, tag, version, _name = wheel_asset(release, args.base, args.repo)
        manager = manager_for(args.manager)
        if manager is None:
            raise BootstrapError("WF_CAPABILITY_UNAVAILABLE", "没有 uv 或 pipx，无法安装系统 wf",
                                 {}, "先安装 uv 或 pipx 后重试")
        with tempfile.TemporaryDirectory(prefix="wf-bootstrap-") as temporary:
            wheel = os.path.join(temporary, f"wf_cli-{version}-py3-none-any.whl")
            download(url, wheel, token)
            output = install(manager, wheel)
        sys.stdout.write(f"OK  wf {version}（{tag}）→ {manager}\n")
        if output:
            sys.stdout.write(output[-800:] + "\n")
        try:
            record = write_install_record(args.base, args.repo)
        except OSError as exc:
            sys.stdout.write(f"WARN  安装记录写入失败（不影响已完成的安装）：{exc}\n")
        else:
            sys.stdout.write(f"资产基址已记录：{record}\n")
        sys.stdout.write("下一步：运行 `wf version` 核对系统命令。\n")
        return 0
    except BootstrapError as exc:
        sys.stdout.write(f"BLOCKED  {exc.code}\n")
        sys.stdout.write(f"事实: {json.dumps(exc.facts, ensure_ascii=False, sort_keys=True)}\n")
        if exc.exit_hint:
            sys.stdout.write(f"出口: {exc.exit_hint}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())