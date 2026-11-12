"""P1-2（上半）：`run create` 的输入校验与准备范围重核（机制稿 §7.2）。

`run create` 只取得「规划权限」：不代批准业务、不建任务、不推进 cursor。它必须先证明三件事——
① 创建输入结构成立（缺字段/未知 step/取值域）；
② 与实际输入（`inputs`）按定义声明逐条对得上（必填缺失、类型不符、`secret_ref` 只接受引用）；
③ **本会话确有该定义的有效准备记录**（机制稿 §1.4 的「已授权准备范围」，
也是实现稿 §2.3.11 登记的第 ② 项）。

这里核 ① ② 的纯判定；③ 与端到端（快照/记录/绑定/幂等重入）走 `repro/run-create-once.py`。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import runs  # noqa: E402

DOC = {
    "inputs": {
        "request": {"type": "text", "required": True, "description": "变更要求"},
        "target": {"type": "path", "required": False, "description": "目标文件"},
        "token": {"type": "secret_ref", "required": False, "description": "凭据引用"},
        "artifact": {"type": "artifact_ref", "required": False, "description": "前序产物"},
    },
    "steps": [{"id": "change"}, {"id": "review"}],
}

CREATION = {"definition_id": "bounded-change", "definition_digest": "sha256:" + "a" * 64,
            "inputs": {"request": "把 X 改掉"}, "steps": {"change": "applicable",
                                                          "review": "skipped"}}


class CreationStructureTest(unittest.TestCase):
    def test_minimal_creation_is_clean(self):
        self.assertEqual(runs.creation_problems(CREATION, DOC), [])

    def test_each_required_field_is_reported(self):
        for field in runs.CREATION_FIELDS:
            broken = {key: value for key, value in CREATION.items() if key != field}
            with self.subTest(field=field):
                problems = runs.creation_problems(broken, DOC)
                self.assertTrue(any(field in str(item.get("field")) for item in problems))

    def test_unknown_step_is_rejected(self):
        broken = dict(CREATION, steps={"nope": "applicable"})
        problems = runs.creation_problems(broken, DOC)
        self.assertTrue(any(item.get("step") == "nope" for item in problems))

    def test_applicability_domain(self):
        broken = dict(CREATION, steps={"change": "maybe"})
        problems = runs.creation_problems(broken, DOC)
        self.assertTrue(any("applicable" in item["reason"] for item in problems))


class InputValueTest(unittest.TestCase):
    def test_required_input_missing(self):
        problems = runs.input_value_problems(DOC, {})
        self.assertEqual(problems, [{"reason": "required input missing", "input": "request"}],
                         problems)

    def test_text_must_be_string(self):
        problems = runs.input_value_problems(DOC, {"request": 3})
        self.assertTrue(any(item["input"] == "request" for item in problems))

    def test_path_must_be_safe(self):
        problems = runs.input_value_problems(DOC, {"request": "x", "target": "../outside"})
        self.assertTrue(any(item["input"] == "target" for item in problems))

    def test_secret_ref_never_accepts_plaintext(self):
        problems = runs.input_value_problems(DOC, {"request": "x", "token": "sk-live-plaintext"})
        self.assertTrue(any("never a plaintext value" in item["reason"] for item in problems))
        ok = runs.input_value_problems(DOC, {"request": "x",
                                             "token": {"from": "secret_ref", "provider": "env",
                                                       "name": "WF_TOKEN"}})
        self.assertEqual(ok, [])

    def test_artifact_ref_must_be_a_reference(self):
        problems = runs.input_value_problems(DOC, {"request": "x",
                                                   "artifact": {"from": "input", "name": "request"}})
        self.assertTrue(any(item["input"] == "artifact" for item in problems))

    def test_undeclared_input_is_rejected(self):
        problems = runs.input_value_problems(DOC, {"request": "x", "extra": 1})
        self.assertTrue(any("not declared" in item["reason"] for item in problems))


if __name__ == "__main__":
    unittest.main()
