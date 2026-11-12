"""P2-8：执行器项目键的批准证据要按**键值成对**核对（机制稿 §3.4 末段）。

历史状态：`bin/wf.py::project_key_approved` 用 `"python_executable" in text and value in text`——
键名与取值各出现在文件任意位置就成立（键名在说明句、取值在另一处举例也能过）。
机制稿要求「逐项列键和值」，因此改成逐行解析键值对（`key = v` / `key: v` / `"key": "v"`）。

注入形态：把判据退回文本包含 → 「键值分处两行」的 PRD 会被误判为已批准。
"""

import importlib.util
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
BIN = REPO / "docs" / "workflows" / "wf" / "payload" / "bin" / "wf.py"

spec = importlib.util.spec_from_file_location("wf_bin_under_test", BIN)
wf_bin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wf_bin)

VALUE = ".venv/bin/python"


def _approved(text):
    return VALUE in wf_bin.declared_values(text, "python_executable")


class ProjectKeySemanticTest(unittest.TestCase):
    def test_plain_assignation_pairs(self):
        self.assertTrue(_approved(f"python_executable = {VALUE}"))

    def test_yaml_style_and_json_style_pair(self):
        self.assertTrue(_approved(f'python_executable: "{VALUE}"'))
        self.assertTrue(_approved(f'"python_executable": "{VALUE}",'))

    def test_key_and_value_in_different_lines_do_not_count(self):
        """旧实现的缺陷形态：键名与取值各在一处，仍然过。"""
        text = f"说明：不要把 {VALUE} 写死。\n\npython_executable 见配置文件。\n"
        self.assertFalse(_approved(text))

    def test_lookalike_key_is_not_the_same_key(self):
        self.assertFalse(_approved(f"my_python_executable = {VALUE}"))

    def test_other_value_under_the_same_key_does_not_count(self):
        self.assertFalse(_approved("python_executable = /usr/bin/python3"))


if __name__ == "__main__":
    unittest.main()
