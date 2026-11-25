"""Forgejo release asset attachment helper tests (no network)."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "attach-wf-cli-asset.py"


def _module():
    spec = importlib.util.spec_from_file_location("wf_attach_asset", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AttachAssetTest(unittest.TestCase):
    def setUp(self):
        self.module = _module()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.wheel = Path(self._tmp.name) / "wf_cli-0.0.8-py3-none-any.whl"
        self.wheel.write_bytes(b"wheel")

    def test_existing_same_size_is_not_reuploaded(self):
        calls = []

        def api(base, repo, path, token, **kwargs):
            calls.append((path, kwargs))
            return {"id": 1, "assets": [{"name": self.wheel.name, "size": 5,
                                         "browser_download_url": "https://x/asset"}]}

        old = self.module._api
        self.module._api = api
        self.addCleanup(lambda: setattr(self.module, "_api", old))
        result = self.module.attach("https://forgejo.example", "xzc/repo", "wf-v0.0.8",
                                    str(self.wheel), "token")
        self.assertIn("already attached", result)
        self.assertEqual(len(calls), 1)

    def test_missing_asset_is_uploaded_as_multipart(self):
        calls = []

        def api(base, repo, path, token, **kwargs):
            calls.append((path, kwargs))
            if len(calls) == 1:
                return {"id": 7, "assets": []}
            return {"browser_download_url": "https://x/uploaded"}

        old = self.module._api
        self.module._api = api
        self.addCleanup(lambda: setattr(self.module, "_api", old))
        result = self.module.attach("https://forgejo.example", "xzc/repo", "wf-v0.0.8",
                                    str(self.wheel), "token")
        self.assertEqual(result, "https://x/uploaded")
        self.assertEqual(len(calls), 2)
        path, kwargs = calls[1]
        self.assertIn("/assets?name=", path)
        self.assertIn(b"Content-Disposition", kwargs["data"])
        self.assertIn(b"wf_cli-0.0.8-py3-none-any.whl", kwargs["data"])

    def test_bootstrap_is_uploaded_with_wheel(self):
        calls = []
        bootstrap = Path(self._tmp.name) / "install.py"
        bootstrap.write_bytes(b"bootstrap")

        def api(base, repo, path, token, **kwargs):
            calls.append((path, kwargs))
            if len(calls) == 1:
                return {"id": 7, "assets": []}
            return {"browser_download_url": "https://x/uploaded-" + str(len(calls))}

        old = self.module._api
        self.module._api = api
        self.addCleanup(lambda: setattr(self.module, "_api", old))
        result = self.module.attach("https://forgejo.example", "xzc/repo", "wf-v0.0.8",
                                    str(self.wheel), "token", str(bootstrap))
        self.assertIn("uploaded-2", result)
        self.assertIn("uploaded-3", result)
        self.assertEqual(len(calls), 3)
        self.assertIn(b"install.py", calls[2][1]["data"])

    def test_different_existing_asset_is_refused(self):
        def api(base, repo, path, token, **kwargs):
            return {"id": 1, "assets": [{"name": self.wheel.name, "size": 99}]}

        old = self.module._api
        self.module._api = api
        self.addCleanup(lambda: setattr(self.module, "_api", old))
        with self.assertRaises(self.module.AttachError):
            self.module.attach("https://forgejo.example", "xzc/repo", "wf-v0.0.8",
                               str(self.wheel), "token")


if __name__ == "__main__":
    unittest.main()