#!/usr/bin/env python3
"""Minimal Forgejo release-API client shared by the wf release tooling.

Only the endpoints the release flow needs: read the repository release list (paginated) and delete
a release (its attached assets go with it). Callers read the token from an environment variable and
hand it to these functions; it is sent only in the Authorization header and is never printed,
logged, or passed as a command-line argument.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

DEFAULT_BASE = os.environ.get("WF_FORGEJO_BASE") or "https://forgejo.xzc.com"
DEFAULT_REPO = "xzc/ai-coding-toolkit"
DEFAULT_TOKEN_ENV = "FORGEJO_TOKEN"
TAG_RE = re.compile(r"^wf-v(\d+\.\d+\.\d+)$")
PAGE_SIZE = 50
MAX_PAGES = 100


class ForgejoApiError(Exception):
    """An API response that cannot be used as release identity."""

    def __init__(self, message, *, status=None, missing=False):
        super().__init__(message)
        self.status = status
        self.missing = missing


def token_from_env(name=DEFAULT_TOKEN_ENV):
    return (os.environ.get(name) or "").strip() or None


def api(base, repo, path, token, *, data=None, content_type=None, method=None, timeout=120):
    """Call `/api/v1/repos/<repo>/<path>` and return the decoded JSON body (None when empty)."""
    url = f"{base.rstrip('/')}/api/v1/repos/{repo}/{path.lstrip('/')}"
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = "token " + token
    if content_type:
        headers["Content-Type"] = content_type
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise ForgejoApiError(f"release/tag not found: {url}", status=404,
                                  missing=True) from exc
        raise ForgejoApiError(f"forgejo api failed: status={exc.code} url={url}",
                              status=exc.code) from exc
    except OSError as exc:
        raise ForgejoApiError(
            f"forgejo api unavailable: {url}: {exc}；"
            "核对 WF_FORGEJO_BASE/VPN；若只有 SSH 可用，改用 scripts/install-wf-ssh.sh"
        ) from exc
    if not body:
        return None
    try:
        return json.loads(body.decode("utf-8"))
    except ValueError as exc:
        raise ForgejoApiError(f"forgejo api returned non-JSON: {url}") from exc


def list_releases(base, repo, token, *, page_size=PAGE_SIZE):
    """Every repository release, page by page; pagination stops at a short page."""
    collected = []
    page = 1
    while page <= MAX_PAGES:
        payload = api(base, repo, f"releases?limit={page_size}&page={page}", token)
        if not isinstance(payload, list):
            raise ForgejoApiError(f"release list is not an array (page {page})")
        collected.extend(entry for entry in payload if isinstance(entry, dict))
        if len(payload) < page_size:
            break
        page += 1
    return collected


def wf_releases(releases):
    """`wf-vX.Y.Z` releases ordered newest-first by creation time (release selection identity)."""
    ordered = [entry for entry in releases if TAG_RE.match(str(entry.get("tag_name") or ""))]
    ordered.sort(key=lambda entry: (str(entry.get("created_at") or entry.get("published_at") or ""),
                                    str(entry.get("tag_name") or "")),
                 reverse=True)
    return ordered


def prune_candidates(ordered, *, keep, protect=()):
    """Entries after the newest `keep`; `ordered` must be newest-first."""
    protected = set(protect)
    return [entry for entry in ordered[keep:] if entry.get("tag_name") not in protected]


def delete_release(base, repo, token, release_id):
    return api(base, repo, f"releases/{release_id}", token, method="DELETE")