#!/usr/bin/env python3
"""Delete historical Forgejo wf releases so only the newest N remain.

A Forgejo tag and its release are two separate objects: pruning tags alone leaves the release page
and its attached assets (`wf_cli-<version>-py3-none-any.whl`, `install.py`) behind, so "only the
newest three" would hold for tags but not for the release list. This script lists the repository
releases through the API, orders the `wf-vX.Y.Z` releases by creation time (newest first, the same
basis the tag retention uses), and deletes every release after the newest `--keep` ones. The release
being published is always protected through `--protect`.

Deleting a release removes its attached assets; the tag itself is not touched (that is the release
flow's own tag pruning). Run it standalone after a failed prune; the release flow calls it before
pruning tags so a failure never leaves an orphan release behind.

The token is read from an environment variable and sent only in the Authorization header; it is
never printed or passed as a command-line argument.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import forgejo_api  # noqa: E402

KEEP = 3


class PruneError(Exception):
    pass


def prune(base, repo, token, *, keep=KEEP, protect=None, dry_run=False):
    """Delete `wf-vX.Y.Z` releases beyond the newest `keep`; returns kept/deleted tag names."""
    ordered = forgejo_api.wf_releases(forgejo_api.list_releases(base, repo, token))
    candidates = forgejo_api.prune_candidates(ordered, keep=keep, protect=(protect or (),))
    deleted = []
    for entry in candidates:
        tag = str(entry.get("tag_name"))
        release_id = entry.get("id")
        if not release_id:
            raise PruneError(f"release {tag} has no id; 无法定位要删除的对象")
        if not dry_run:
            forgejo_api.delete_release(base, repo, token, release_id)
        deleted.append(tag)
    kept = [str(entry.get("tag_name")) for entry in ordered
            if str(entry.get("tag_name")) not in set(deleted)]
    return {"kept": kept, "deleted": deleted, "dry_run": bool(dry_run)}


def main(argv=None):
    parser = argparse.ArgumentParser(description="清理 Forgejo 历史 wf release（只保留最新若干个）")
    parser.add_argument("--keep", type=int, default=KEEP, help=f"保留最新几个 release（默认 {KEEP}）")
    parser.add_argument("--protect", default=None,
                        help="永不删除的 tag（发布中的版本）；缺省无保护项")
    parser.add_argument("--base", default=forgejo_api.DEFAULT_BASE,
                        help="Forgejo Web/API 基址；缺省读 WF_FORGEJO_BASE")
    parser.add_argument("--repo", default=forgejo_api.DEFAULT_REPO)
    parser.add_argument("--token-env", default=forgejo_api.DEFAULT_TOKEN_ENV,
                        help="保存 token 的环境变量名（默认 FORGEJO_TOKEN）；token 不作为参数")
    parser.add_argument("--dry-run", action="store_true", help="只列出将被删除的 release，不调用删除")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    token = forgejo_api.token_from_env(args.token_env)
    if not token:
        payload = {"ok": False, "code": "WF_CAPABILITY_UNAVAILABLE",
                   "facts": {"token_env": args.token_env}}
        if args.json:
            sys.stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        else:
            sys.stdout.write("BLOCKED  WF_CAPABILITY_UNAVAILABLE\n")
            sys.stdout.write(f"事实: 环境变量 {args.token_env} 为空\n")
        sys.stdout.write("出口: 在环境中提供 Forgejo token 后重跑；不把 token 写进命令\n")
        return 1
    if args.keep < 1:
        sys.stdout.write("BLOCKED  WF_USAGE_INVALID\n事实: --keep 必须是正整数\n")
        return 1

    try:
        result = prune(args.base, args.repo, token, keep=args.keep,
                       protect=args.protect, dry_run=args.dry_run)
    except (PruneError, forgejo_api.ForgejoApiError) as exc:
        payload = {"ok": False, "code": "WF_CAPABILITY_UNAVAILABLE",
                   "facts": {"detail": str(exc), "base": args.base, "repo": args.repo}}
        if args.json:
            sys.stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        else:
            sys.stdout.write("BLOCKED  WF_CAPABILITY_UNAVAILABLE\n")
            sys.stdout.write(f"事实: {exc}\n")
        sys.stdout.write("出口: 核对 Forgejo HTTP/API 与 token 后重跑；已删除的 release 不会回滚\n")
        return 1

    if args.json:
        sys.stdout.write(json.dumps(dict(result, ok=True), ensure_ascii=False,
                                    sort_keys=True) + "\n")
        return 0
    verb = "将删除" if result["dry_run"] else "已删除"
    sys.stdout.write(f"保留最新 {args.keep} 个 release：{', '.join(result['kept']) or '（无）'}\n")
    if result["deleted"]:
        for tag in result["deleted"]:
            sys.stdout.write(f"{verb} Forgejo release {tag}\n")
    else:
        sys.stdout.write("没有超出保留数的历史 release\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())