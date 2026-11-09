"""S12 部署表：平台 → 技能根 + 会话标识来源，只有一份、且未核实的宿主不猜。

防的失败：dogfood 的 I1/I3——平台知识散落在核心代码里（`cli.py` 的宿主配置表），
新增宿主时又被"按框架约定猜目录/猜标识来源"填平。这张表把"来源"变成显式字段：
`official-docs` / `user-declared` / `unknown`，未核实的宿主只能标 unknown 并走人裁决。
"""

import importlib.util
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PAYLOAD = REPO / "docs" / "workflows" / "新项目开发工作流" / "payload"
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(PAYLOAD / "lib"))
sys.path.insert(0, str(SCRIPTS))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestDeploymentTable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.install = _load("wf_install_table", PAYLOAD / "install.py")
        cls.dev = _load("wf_dev_deploy_table", SCRIPTS / "wf-dev-deploy.py")

    def test_every_platform_declares_session_identity_source(self):
        for name, entry in self.install.PLATFORMS.items():
            identity = entry.get("session_identity")
            self.assertIsInstance(identity, dict, f"{name} 缺 session_identity 声明")
            self.assertIn(identity.get("source"), ("official-docs", "user-declared", "unknown"),
                          f"{name} 的 session_identity.source 非法：{identity.get('source')}")
            if identity["source"] == "unknown":
                self.assertIsNone(identity.get("value"),
                                  f"{name} 未核实却声明了标识来源（不许猜）：{identity.get('value')}")
            else:
                self.assertTrue(identity.get("value"),
                                f"{name} 声明了来源却没写标识入口")
            self.assertIn(identity.get("clear_resets"), (True, False, None),
                          f"{name} 的 clear_resets 只接受 true/false/null")

    def test_dev_deploy_uses_the_single_table(self):
        """开发态与发行态不得各写一份部署表（纪律 #4）。"""
        self.assertEqual(self.dev.PLATFORMS, self.install.PLATFORMS)
        source = (SCRIPTS / "wf-dev-deploy.py").read_text(encoding="utf-8")
        self.assertNotIn("PLATFORMS = {", source,
                         "开发态部署脚本又把部署表抄了一份：表只允许在 install.py 一处定义")

    def test_identity_semantics_stay_platform_free(self):
        """S12 ②：身份语义层不得出现宿主分支（平台知识只在部署表与适配层）。"""
        for module in ("session.py", "identity_store.py", "protocol.py"):
            source = (PAYLOAD / "lib" / "wflib" / module).read_text(encoding="utf-8")
            for host in ("dsh", "codex", "claudecode", "geminicli"):
                self.assertNotIn(f'"{host}"', source, f"{module} 出现宿主名 {host}")


if __name__ == "__main__":
    unittest.main()
