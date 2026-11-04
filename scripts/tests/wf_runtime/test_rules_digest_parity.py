"""rules_digest 的多份实现必须一致（P3）：运行时、install.py、开发态部署共用同一算法。

`assets.py` 是唯一的算法源；`install.py` 自含一份以便独立运行；`wf_release_common.py`
只是转发 `assets`。这里直接比对独立实现与运行时实现，防止分叉。
"""

import importlib.util
import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PAYLOAD = os.path.join(ROOT, "docs", "workflows", "新项目开发工作流", "payload")
MANIFEST = os.path.join(ROOT, "docs", "workflows", "新项目开发工作流", "dev-manifest.json")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RulesDigestParityTest(unittest.TestCase):
    def setUp(self):
        import sys

        sys.path.insert(0, os.path.join(PAYLOAD, "lib"))
        self.addCleanup(lambda: sys.path.remove(os.path.join(PAYLOAD, "lib")))

    def test_install_matches_runtime(self):
        from wflib import assets as wf_assets

        manifest = json.load(open(MANIFEST, encoding="utf-8"))
        installed = _load("wf_install_rules", os.path.join(PAYLOAD, "install.py"))
        self.assertEqual(installed.compute_rules_digest(manifest), wf_assets.compute_rules_digest(manifest))

    def test_digest_is_domain_separated(self):
        from wflib import assets as wf_assets

        manifest = json.load(open(MANIFEST, encoding="utf-8"))
        digest = wf_assets.compute_rules_digest(manifest)
        self.assertTrue(digest.startswith("sha256:"))


if __name__ == "__main__":
    unittest.main()
