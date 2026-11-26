#!/usr/bin/env python3
"""Attach the system wf command wheel to a Forgejo release.

The release must already exist for the tag (a tag alone is not a Forgejo release). The token is
read from an environment variable and sent only in the Authorization header; it is never printed
or passed as a command-line argument. An existing same-size asset is treated as already attached;
a same-name asset with a different size is refused instead of silently replacing release content.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import forgejo_api  # noqa: E402

DEFAULT_BASE = forgejo_api.DEFAULT_BASE
DEFAULT_REPO = forgejo_api.DEFAULT_REPO


class AttachError(Exception):
    def __init__(self, message, *, missing=False):
        super().__init__(message)
        self.missing = missing


def _api(base, repo, path, token, *, data=None, content_type=None, method=None):
    """共享客户端只有一种错误类型；这里转换成本脚本的 `AttachError`（保留 `missing` 语义）。"""
    try:
        return forgejo_api.api(base, repo, path, token, data=data,
                               content_type=content_type, method=method)
    except forgejo_api.ForgejoApiError as exc:
        raise AttachError(str(exc), missing=exc.missing) from exc


def multipart(name, filename, payload):
    boundary = "----wf-release-asset-" + os.urandom(8).hex()
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode("utf-8")
    tail = f"\r\n--{boundary}--\r\n".encode("utf-8")
    return boundary, head + payload + tail


TAG_RE = re.compile(r"^wf-v(\d+\.\d+\.\d+)$")
WHEEL_RE = re.compile(r"^wf[_-]cli-(\d+\.\d+\.\d+)-py3-none-any\.whl$")


def _attach_one(base, repo, release_id, path, token):
    path = Path(path)
    if not path.is_file() or path.stat().st_size == 0:
        raise AttachError(f"asset is missing or empty: {path}")
    size = path.stat().st_size
    existing = next(
        (item for item in release_id.get("assets") or []
         if isinstance(item, dict) and item.get("name") == path.name),
        None,
    )
    if existing is not None:
        if int(existing.get("size") or -1) == size:
            return f"already attached: {existing.get('browser_download_url') or path.name}"
        raise AttachError("release already has a different asset with the same name; "
                          "do not replace release content silently")
    boundary, body = multipart("attachment", path.name, path.read_bytes())
    result = _api(
        base, repo,
        f"releases/{release_id['id']}/assets?name={urllib.parse.quote(path.name, safe='')}",
        token, data=body, content_type=f"multipart/form-data; boundary={boundary}",
        method="POST",
    )
    release_id.setdefault("assets", []).append(
        {"name": path.name, "size": size,
         "browser_download_url": result.get("browser_download_url")})
    return str(result.get("browser_download_url") or result.get("name") or path.name)


def create_release(base, repo, tag, token):
    """Create a Forgejo release for an existing tag; never creates the tag itself."""
    try:
        ref = _api(base, repo, f"git/refs/tags/{urllib.parse.quote(tag, safe='')}", token)
    except AttachError as exc:
        raise AttachError(f"tag {tag} is not on Forgejo; 先创建/推送 tag 后重试") from exc
    if isinstance(ref, list):
        ref = ref[0] if ref else None
    if not isinstance(ref, dict):
        raise AttachError(f"tag {tag} has no resolvable commit")
    sha = (ref.get("object") or {}).get("sha") or ref.get("sha")
    if not sha:
        raise AttachError(f"tag {tag} has no resolvable commit")
    payload = json.dumps({"tag_name": tag, "target_commitish": sha, "name": tag,
                          "draft": False, "prerelease": False}).encode("utf-8")
    return _api(base, repo, "releases", token, data=payload,
                content_type="application/json", method="POST")


def attach(base, repo, tag, wheel, token, bootstrap=None, create_missing=False):
    tag_match = TAG_RE.match(tag or "")
    wheel_match = WHEEL_RE.match(Path(wheel).name)
    if not tag_match or not wheel_match or tag_match.group(1) != wheel_match.group(1):
        raise AttachError("tag 与 wheel 版本不一致")
    try:
        release = _api(base, repo, f"releases/tags/{urllib.parse.quote(tag, safe='')}", token)
    except AttachError as exc:
        if exc.missing and create_missing:
            release = create_release(base, repo, tag, token)
        elif exc.missing:
            raise AttachError(f"{exc}；先在 Forgejo 创建 release {tag} 后重试，"
                              "或加 --create-release（tag 必须已存在）",
                              missing=True) from exc
        else:
            raise
    if not release.get("id"):
        raise AttachError("release JSON has no id")
    outputs = [_attach_one(base, repo, release, wheel, token)]
    if bootstrap:
        outputs.append(_attach_one(base, repo, release, bootstrap, token))
    return "\n".join(outputs)

def main(argv=None):
    parser = argparse.ArgumentParser(description="把系统 wf wheel 附加到 Forgejo release")
    parser.add_argument("--tag", required=True, help="wf-vX.Y.Z（tag 必须已存在；release 可加 --create-release）")
    parser.add_argument("--wheel", required=True)
    parser.add_argument("--bootstrap", default=str(Path(__file__).resolve().parent.parent / "docs" / "workflows" / "wf-cli" / "install.py"),
                        help="无版本安装脚本；默认 docs/workflows/wf-cli/install.py")
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--token-env", default="FORGEJO_TOKEN",
                        help="保存 token 的环境变量名；token 不作为参数传入")
    parser.add_argument("--create-release", action="store_true",
                        help="release 不存在时用 API 创建（tag 必须已存在）")
    args = parser.parse_args(argv)
    token = os.environ.get(args.token_env) or None
    if not token:
        sys.stdout.write(f"BLOCKED  WF_CAPABILITY_UNAVAILABLE\n事实: 环境变量 {args.token_env} 为空\n")
        sys.stdout.write("出口: 在环境中提供 Forgejo token 后重跑；不把 token 写进命令\n")
        return 1
    try:
        location = attach(args.base, args.repo, args.tag, args.wheel, token, args.bootstrap,
                      args.create_release)
    except AttachError as exc:
        sys.stdout.write(f"BLOCKED  WF_CAPABILITY_UNAVAILABLE\n事实: {exc}\n")
        return 1
    sys.stdout.write(f"OK  {location}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())