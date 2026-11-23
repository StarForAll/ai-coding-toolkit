"""Asset boundaries (AC19/AC20): project → base → asset containment for the three entry points.

install.py and bin/uninstall.py are self-contained product scripts; scripts/wf-dev-deploy.py
is the author-side deployment plan.  All three are exercised with the same parameterized
input matrix: project-internal roots pass, while skill roots / ancestors / asset targets
that resolve outside the project are refused wholesale before any write or delete.
"""

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PAYLOAD = REPO / "docs" / "workflows" / "wf" / "payload"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


install = _load("wf_asset_install", PAYLOAD / "install.py")
uninstall = _load("wf_asset_uninstall", PAYLOAD / "bin" / "uninstall.py")
sys.path.insert(0, str(REPO / "scripts"))
dev_deploy = _load("wf_asset_dev_deploy", REPO / "scripts" / "wf-dev-deploy.py")


def manifest(root_ref="skill_root", target="wf-start/SKILL.md"):
    return {"assets": [{"target_class": root_ref, "target_relative": target,
                        "source_path": "skills/wf-start/SKILL.md", "digest": "sha256:x"}]}


class InstallBoundaryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-asset-install-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = self.root / "proj"
        self.project.mkdir()
        self.outside = self.root / "outside"
        self.outside.mkdir()
        self.skill_root = self.project / ".agents" / "skills"

    def test_project_internal_skill_root_is_accepted(self):
        writes, problems = install.plan_writes(str(self.project), [str(self.skill_root)],
                                               manifest())
        self.assertEqual(problems, [])
        self.assertEqual(len(writes), 1)

    def test_symlinked_skill_root_is_rejected_wholesale(self):
        self.skill_root.parent.mkdir()
        self.skill_root.symlink_to(self.outside, target_is_directory=True)
        writes, problems = install.plan_writes(str(self.project), [str(self.skill_root)],
                                               manifest())
        self.assertEqual(writes, [])
        self.assertTrue(problems)
        self.assertIn("outside", json.dumps(problems))
        self.assertEqual(os.listdir(self.outside), [], "拒绝路径不得写穿到项目外")

    def test_symlinked_ancestor_and_broken_link_are_rejected(self):
        self.project.joinpath(".agents").symlink_to(self.outside, target_is_directory=True)
        writes, problems = install.plan_writes(str(self.project), [str(self.skill_root)],
                                               manifest())
        self.assertEqual(writes, [])
        self.assertTrue(problems)
        broken = self.project / ".cursor"
        broken.symlink_to(self.root / "missing")
        writes, problems = install.plan_writes(str(self.project), [str(broken / "skills")],
                                               manifest())
        self.assertEqual(writes, [])
        self.assertIn("broken symlink", json.dumps(problems))

    def test_project_asset_symlink_escape_is_rejected(self):
        destination = self.project / ".wf" / "bin" / "wf.py"
        destination.parent.mkdir(parents=True)
        (self.outside / "evil.py").write_text("sentinel\n")
        destination.symlink_to(self.outside / "evil.py")
        writes, problems = install.plan_writes(
            str(self.project), [str(self.skill_root)],
            manifest("project_wf", ".wf/bin/wf.py"))
        self.assertEqual(writes, [])
        self.assertIn("outside", json.dumps(problems))

    def test_registered_roots_keep_in_project_history_and_reject_outside(self):
        inside_abs = str(self.project / "other-skills")
        installation = {"roots": [".agents/skills", inside_abs]}
        self.assertEqual(install.registered_root_problems(str(self.project), installation), [])
        external = {"roots": [str(self.outside)]}
        problems = install.registered_root_problems(str(self.project), external)
        self.assertTrue(problems)
        self.assertIn("outside", json.dumps(problems))


class UninstallBoundaryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-asset-uninstall-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = self.root / "proj"
        self.project.mkdir()
        self.outside = self.root / "outside"
        self.outside.mkdir()
        (self.project / ".agents" / "skills").mkdir(parents=True)
        (self.project / ".wf" / "bin").mkdir(parents=True)
        for path in (self.project / ".agents" / "skills" / "wf-start",
                     self.project / ".wf" / "bin"):
            path.mkdir(exist_ok=True)
        (self.project / ".agents" / "skills" / "wf-start" / "SKILL.md").write_text("x")
        (self.project / ".wf" / "bin" / "wf.py").write_text("x")
        self.installation = {"roots": [".agents/skills"]}

    def collect(self, installation=None):
        return uninstall.collect_targets(str(self.project), installation or self.installation,
                                         manifest())

    def test_normal_targets_are_collected(self):
        project, skills = self.collect()
        self.assertEqual(project, [])
        self.assertEqual(len(skills), 1)
        self.assertTrue(skills[0].startswith(str(self.project)))

    def test_symlinked_skill_root_is_rejected(self):
        shutil.rmtree(self.project / ".agents" / "skills")
        (self.project / ".agents" / "skills").symlink_to(self.outside, target_is_directory=True)
        with self.assertRaises(uninstall.AssetBoundary) as caught:
            self.collect()
        self.assertIn("outside", json.dumps(caught.exception.problems))
        self.assertEqual(os.listdir(self.outside), [])

    def test_historical_external_root_ref_is_rejected_without_touching_outside(self):
        (self.outside / "wf-start").mkdir()
        (self.outside / "wf-start" / "SKILL.md").write_text("external")
        with self.assertRaises(uninstall.AssetBoundary) as caught:
            self.collect({"roots": [str(self.outside)]})
        self.assertIn("outside", json.dumps(caught.exception.problems))
        self.assertEqual((self.outside / "wf-start" / "SKILL.md").read_text(), "external")

    def test_root_drift_between_preview_and_apply_is_recomputed(self):
        preview = self.collect()
        shutil.rmtree(self.project / ".agents" / "skills")
        (self.project / ".agents" / "skills").symlink_to(self.outside, target_is_directory=True)
        with self.assertRaises(uninstall.AssetBoundary):
            self.collect()
        self.assertEqual(preview, ([], [str(self.project / ".agents" / "skills" / "wf-start" / "SKILL.md")]))

    def test_project_asset_symlink_escape_is_rejected(self):
        (self.project / ".wf" / "bin" / "wf.py").unlink()
        (self.outside / "evil.py").write_text("sentinel\n")
        (self.project / ".wf" / "bin" / "wf.py").symlink_to(self.outside / "evil.py")
        writes = manifest("project_wf", ".wf/bin/wf.py")
        with self.assertRaises(uninstall.AssetBoundary):
            uninstall.collect_targets(str(self.project), self.installation, writes)


class DevDeployBoundaryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-asset-devdeploy-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = self.root / "proj"
        self.project.mkdir()
        self.outside = self.root / "outside"
        self.outside.mkdir()
        self.dev_manifest = dev_deploy.common.load_dev_manifest()
        self.manifest = dev_deploy.common.build_manifest(dev_deploy.DEV_VERSION,
                                                         self.dev_manifest)
        self.skill_root = self.project / ".agents" / "skills"

    def args(self, **overrides):
        import argparse
        base = dict(target=str(self.project), confirm=True, json=True)
        base.update(overrides)
        return argparse.Namespace(**base)

    def run_deploy(self, **overrides):
        import contextlib
        import io
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            rc = dev_deploy.deploy(self.args(**overrides))
        return rc, buffer.getvalue()

    def test_plan_rejects_symlinked_skill_root(self):
        self.skill_root.parent.mkdir()
        self.skill_root.symlink_to(self.outside, target_is_directory=True)
        writes, problems = dev_deploy.plan_deployment(str(self.project), [str(self.skill_root)],
                                                      self.manifest)
        self.assertEqual(writes, [])
        self.assertTrue(problems)
        self.assertIn("outside", json.dumps(problems))

    def test_root_record_refuses_outside_roots(self):
        with self.assertRaises(ValueError):
            dev_deploy.root_record(str(self.project), str(self.outside))

    def test_preview_does_not_write_and_shows_the_plan(self):
        rc, output = self.run_deploy(confirm=False)
        self.assertEqual(rc, 0, output)
        self.assertIn("预览", output)
        self.assertEqual(sorted(os.listdir(self.project)), [])

    def test_first_confirm_and_noop(self):
        """一次装齐全部平台；重跑同一条命令只读核对（幂等、不取写权）。"""
        rc, output = self.run_deploy()
        self.assertEqual(rc, 0, output)
        self.assertIn("WF_OK", output)
        self.assertTrue((self.project / ".wf" / "writer.json").is_file())
        installation = json.loads((self.project / ".wf" / "install" / "installation.json").read_text())
        self.assertEqual(sorted(installation["roots"]), [".agents/skills", ".claude/skills"])
        self.assertTrue(all(not os.path.isabs(root) for root in installation["roots"]))
        self.assertEqual(len(installation["platforms"]), 8)
        writer_before = (self.project / ".wf" / "writer.json").read_text()
        rc, output = self.run_deploy()
        self.assertEqual(rc, 0, output)
        self.assertIn("无任何变化", output)
        self.assertEqual((self.project / ".wf" / "writer.json").read_text(), writer_before)

    def test_redeploy_rejects_symlinked_root_instead_of_writing_through(self):
        """自有根被换成指向项目外的符号链接时，重部署必须整批拒绝、不写穿。"""
        rc, output = self.run_deploy()
        self.assertEqual(rc, 0, output)
        import shutil as _shutil
        _shutil.rmtree(self.project / ".claude")
        (self.project / ".claude").mkdir()
        (self.project / ".claude" / "skills").symlink_to(self.outside, target_is_directory=True)
        rc, output = self.run_deploy()
        self.assertNotEqual(rc, 0, output)
        self.assertIn("WF_ASSET_DECISION", output)
        self.assertEqual(os.listdir(self.outside), [], "重部署不得写穿到项目外")

    def test_apply_rejects_root_drift_between_preview_and_confirm(self):
        rc, output = self.run_deploy(confirm=False)
        self.assertEqual(rc, 0, output)
        self.skill_root.parent.mkdir()
        self.skill_root.symlink_to(self.outside, target_is_directory=True)
        rc, output = self.run_deploy()
        self.assertNotEqual(rc, 0, output)
        self.assertIn("WF_ASSET_DECISION", output)
        self.assertEqual(os.listdir(self.outside), [], "域外目标不得被写入")
        self.assertFalse((self.project / ".wf" / "installation.json").exists()
                         or (self.project / ".wf" / "writer.json").exists())


if __name__ == "__main__":
    unittest.main()
