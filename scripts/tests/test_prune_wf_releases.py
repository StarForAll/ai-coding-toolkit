"""Forgejo historical-release pruning tests (no network).

Why this exists: a Forgejo tag and its release are two separate objects. Tag retention already
deleted old `wf-v*` tags, yet `…/releases` kept every historical release page (and its wheel /
install.py assets). These tests lock the retention basis (release creation time, newest first),
the protection of the release being published, pagination, and the refusal to delete without a
token.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "prune-wf-releases.py"


def _module():
    spec = importlib.util.spec_from_file_location("wf_prune_releases", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _release(tag, created, release_id):
    return {"id": release_id, "tag_name": tag, "created_at": created,
            "assets": [{"name": f"wf_cli-{tag[4:]}-py3-none-any.whl"}]}


class PruneTestBase(unittest.TestCase):
    def setUp(self):
        self.module = _module()
        self.api = self.module.forgejo_api
        self.calls = []

    def _patch(self, name, value):
        old = getattr(self.api, name)
        setattr(self.api, name, value)
        self.addCleanup(lambda: setattr(self.api, name, old))

    def _fixture(self, releases):
        self._patch("list_releases", lambda base, repo, token, **kw: releases)

        def delete(base, repo, token, release_id):
            self.calls.append(("delete", release_id))

        self._patch("delete_release", delete)

    def test_keeps_newest_three_by_creation_time(self):
        self._fixture([
            _release("wf-v0.0.10", "2026-11-24T10:00:00Z", 10),
            _release("wf-v0.0.12", "2026-11-25T12:00:00Z", 12),
            _release("wf-v0.0.14", "2026-11-26T09:00:00Z", 14),
            _release("wf-v0.0.9", "2026-11-20T10:00:00Z", 9),
            _release("wf-v0.0.13", "2026-11-25T20:00:00Z", 13),
        ])
        result = self.module.prune("https://forgejo.example", "xzc/repo", "token")
        # 最近删除优先：候选取「保留 3 个之后」的其余项，按创建时间从新到旧
        self.assertEqual(result["deleted"], ["wf-v0.0.10", "wf-v0.0.9"])
        self.assertEqual(sorted(result["kept"]),
                         ["wf-v0.0.12", "wf-v0.0.13", "wf-v0.0.14"])
        self.assertEqual(self.calls, [("delete", 10), ("delete", 9)])

    def test_current_release_is_never_deleted(self):
        self._fixture([
            _release("wf-v0.0.9", "2026-11-20T10:00:00Z", 9),
            _release("wf-v0.0.10", "2026-11-24T10:00:00Z", 10),
            _release("wf-v0.0.12", "2026-11-25T12:00:00Z", 12),
            _release("wf-v0.0.14", "2026-11-26T09:00:00Z", 14),
        ])
        result = self.module.prune("https://forgejo.example", "xzc/repo", "token",
                                   protect="wf-v0.0.9")
        self.assertNotIn("wf-v0.0.9", result["deleted"])
        self.assertIn("wf-v0.0.9", result["kept"])

    def test_non_wf_releases_are_left_alone(self):
        self._fixture([
            _release("wf-v0.0.12", "2026-11-25T12:00:00Z", 12),
            _release("wf-v0.0.13", "2026-11-25T20:00:00Z", 13),
            _release("wf-v0.0.14", "2026-11-26T09:00:00Z", 14),
            {"id": 99, "tag_name": "v1.0.0", "created_at": "2026-01-01T00:00:00Z"},
        ])
        result = self.module.prune("https://forgejo.example", "xzc/repo", "token")
        self.assertEqual(result["deleted"], [])
        self.assertEqual(self.calls, [])

    def test_dry_run_deletes_nothing(self):
        self._fixture([
            _release("wf-v0.0.9", "2026-11-20T10:00:00Z", 9),
            _release("wf-v0.0.12", "2026-11-25T12:00:00Z", 12),
            _release("wf-v0.0.13", "2026-11-25T20:00:00Z", 13),
            _release("wf-v0.0.14", "2026-11-26T09:00:00Z", 14),
        ])
        result = self.module.prune("https://forgejo.example", "xzc/repo", "token", dry_run=True)
        self.assertEqual(result["deleted"], ["wf-v0.0.9"])
        self.assertTrue(result["dry_run"])
        self.assertEqual(self.calls, [])

    def test_release_without_id_is_a_hard_error(self):
        self._fixture([{"tag_name": "wf-v0.0.9", "created_at": "2026-11-20T10:00:00Z"},
                       _release("wf-v0.0.12", "2026-11-25T12:00:00Z", 12),
                       _release("wf-v0.0.13", "2026-11-25T20:00:00Z", 13),
                       _release("wf-v0.0.14", "2026-11-26T09:00:00Z", 14)])
        with self.assertRaises(self.module.PruneError):
            self.module.prune("https://forgejo.example", "xzc/repo", "token")

    def test_list_releases_paginates_until_a_short_page(self):
        pages = {
            1: [_release(f"wf-v0.0.{index}", "2026-11-20T10:00:00Z", index) for index in range(3)],
            2: [_release("wf-v0.0.9", "2026-11-21T10:00:00Z", 9)],
        }
        seen = []

        def api(base, repo, path, token, **kwargs):
            seen.append(path)
            page = int(path.split("page=")[1])
            return pages[page]

        old = self.api.api
        self.api.api = api
        self.addCleanup(lambda: setattr(self.api, "api", old))
        collected = self.api.list_releases("https://forgejo.example", "xzc/repo", "token",
                                           page_size=3)
        self.assertEqual(len(collected), 4)
        self.assertEqual(len(seen), 2)

    def test_cli_refuses_without_token(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = self.module.main(["--json", "--token-env", "WF_TEST_PRUNE_TOKEN"])
        self.assertEqual(code, 1)
        self.assertIn("WF_CAPABILITY_UNAVAILABLE", buffer.getvalue())
        self.assertEqual(self.calls, [])

    def test_cli_emits_one_json_line(self):
        self._fixture([
            _release("wf-v0.0.9", "2026-11-20T10:00:00Z", 9),
            _release("wf-v0.0.12", "2026-11-25T12:00:00Z", 12),
            _release("wf-v0.0.13", "2026-11-25T20:00:00Z", 13),
            _release("wf-v0.0.14", "2026-11-26T09:00:00Z", 14),
        ])
        os.environ["WF_TEST_PRUNE_TOKEN"] = "token"
        self.addCleanup(os.environ.pop, "WF_TEST_PRUNE_TOKEN", None)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = self.module.main(["--json", "--token-env", "WF_TEST_PRUNE_TOKEN",
                                     "--protect", "wf-v0.0.14"])
        self.assertEqual(code, 0)
        lines = [line for line in buffer.getvalue().splitlines() if line.strip()]
        self.assertEqual(len(lines), 1)
        payload = json.loads(lines[0])
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["deleted"], ["wf-v0.0.9"])

    def test_cli_reports_api_failure(self):
        def boom(base, repo, token, **kwargs):
            raise self.api.ForgejoApiError("forgejo api failed: status=500")

        self._patch("list_releases", boom)
        os.environ["WF_TEST_PRUNE_TOKEN"] = "token"
        self.addCleanup(os.environ.pop, "WF_TEST_PRUNE_TOKEN", None)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = self.module.main(["--token-env", "WF_TEST_PRUNE_TOKEN"])
        self.assertEqual(code, 1)
        self.assertIn("BLOCKED", buffer.getvalue())
        self.assertIn("status=500", buffer.getvalue())

if __name__ == "__main__":
    unittest.main()