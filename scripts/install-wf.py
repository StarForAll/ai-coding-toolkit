#!/usr/bin/env python3
"""Install the system-level wf command from the latest Forgejo release.

This is the local, cross-platform alternative to the curl bootstrap. It resolves
WF_FORGEJO_BASE / FORGEJO_TOKEN from the environment, prompts for missing values on a TTY, and
runs the local docs/workflows/wf-cli/install.py bootstrap so the latest release is selected.

Public repository: FORGEJO_TOKEN may be empty.
Private repository: FORGEJO_TOKEN is required; the bootstrap fetches the release wheel with it.

The token is never accepted as a command-line argument, printed, or written to disk.
"""

from __future__ import annotations

import argparse
import getpass
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BOOTSTRAP = REPO_ROOT / "docs" / "workflows" / "wf-cli" / "install.py"
DEFAULT_BASE = "https://forgejo.xzc.com:13785"
TOKEN_ENV = "FORGEJO_TOKEN"


class InstallError(Exception):
    pass


def resolve_base(value=None):
    base = (value or os.environ.get("WF_FORGEJO_BASE") or "").strip()
    if not base:
        if not sys.stdin.isatty():
            raise InstallError("缺少 WF_FORGEJO_BASE；请在环境中设置或用 --base 指定")
        entered = input(f"WF_FORGEJO_BASE [{DEFAULT_BASE}]: ").strip()
        base = entered or DEFAULT_BASE
    if not base.startswith(("http://", "https://")):
        raise InstallError("WF_FORGEJO_BASE 必须是 http(s) URL")
    return base.rstrip("/")


def resolve_token(env_name=TOKEN_ENV):
    token = (os.environ.get(env_name) or "").strip()
    if token:
        return token
    if sys.stdin.isatty():
        return getpass.getpass(f"{env_name}（公开仓库可留空）: ").strip()
    return ""


def main(argv=None):
    parser = argparse.ArgumentParser(description="从最新 Forgejo 发行安装系统 wf 命令")
    parser.add_argument("--base", help="Forgejo Web/API 基址；缺省读 WF_FORGEJO_BASE 或交互输入")
    parser.add_argument("--token-env", default=TOKEN_ENV,
                        help="保存 token 的环境变量名（默认 FORGEJO_TOKEN）；token 不作为参数")
    args = parser.parse_args(argv)

    try:
        if not BOOTSTRAP.is_file():
            raise InstallError(f"找不到本地安装器：{BOOTSTRAP}")
        base = resolve_base(args.base)
        token = resolve_token(args.token_env)
        env = dict(os.environ)
        env["WF_FORGEJO_BASE"] = base
        if token:
            env["FORGEJO_TOKEN"] = token
        else:
            env.pop("FORGEJO_TOKEN", None)
            sys.stderr.write("install-wf: 未提供 token；公开仓库可继续，私有仓库会失败\n")
        sys.stderr.write(f"install-wf: Forgejo {base}\n")
        result = subprocess.run([sys.executable, str(BOOTSTRAP)], env=env, check=False)
        return result.returncode
    except InstallError as exc:
        sys.stderr.write(f"BLOCKED  {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
