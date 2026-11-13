"""R-侧车：会话运行态只有合并写一种入口（D1）。

失败模式（dogfood 实录）：侧车同时承载"对象定位/游标"与"本次取得写权时的代次"，五个调用点
用整份替换写，后写者抹掉先写者的字段——`run advance` 之后代次消失，下一步写操作要求人工补协议。

断言：
1. 先写代次、后写游标，代次仍在；反向顺序同样；
2. 写权入口写入的代次，经"绑定/游标"更新后仍可被 `cli.resolve_generation` 取到；
3. 停止请求这类侧车事实也走合并写，不清空别的字段；
4. 结构守卫：`wflib/` 里除 `session.py` 外没有模块调用整份写，且 `session.py` 不再暴露
   `write_runtime` 这个公开名字（避免"再引入一个整份写调用点"）。
"""

import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import cli, session, writer  # noqa: E402

WFLIB = REPO / "docs" / "workflows" / "wf" / "payload" / "lib" / "wflib"


def _root():
    root = tempfile.mkdtemp(prefix="wf-runtime-merge-")
    os.makedirs(os.path.join(root, ".wf"), exist_ok=True)
    return root


def _held_record(generation=3, session_key="session-key"):
    record = writer.initial_record()
    record.update(state="held", generation=generation,
                  holder={"kind": "session", "id": session_key, "scope": None,
                          "generation": generation})
    return record


class RuntimeMergeTest(unittest.TestCase):
    def test_generation_survives_cursor_update(self):
        root = _root()
        session.update_runtime(root, "session-key", writer_generation=5)
        session.update_runtime(root, "session-key", cursor={"step_id": "s1", "task_id": "t1"},
                               current_task="t1")
        runtime = session.load_runtime(root, "session-key") or {}
        self.assertEqual(runtime.get("writer_generation"), 5)
        self.assertEqual(runtime.get("cursor"), {"step_id": "s1", "task_id": "t1"})
        self.assertEqual(runtime.get("current_task"), "t1")

    def test_generation_written_after_cursor_is_kept(self):
        root = _root()
        session.update_runtime(root, "session-key", cursor={"step_id": "s1"})
        session.update_runtime(root, "session-key", writer_generation=7)
        session.update_runtime(root, "session-key", cursor={"step_id": "s2"})
        runtime = session.load_runtime(root, "session-key") or {}
        self.assertEqual(runtime.get("writer_generation"), 7)
        self.assertEqual(runtime.get("cursor"), {"step_id": "s2"})

    def test_generation_reachable_after_binding_style_update(self):
        root = _root()
        writer.save(root, _held_record(generation=11))
        # 模拟 run advance / bind：只提交定位字段
        session.update_runtime(root, "session-key",
                               binding_digest="sha256:00", instance_id="i1",
                               object={"kind": "run", "id": "r1"},
                               current_task="t1", cursor={"step_id": "s1", "task_id": "t1"})
        generation, source = cli.resolve_generation(SimpleNamespace(root=root, inputs=lambda: {}),
                                                    "session-key")
        self.assertEqual((generation, source), (11, "session-runtime"))
        runtime = session.load_runtime(root, "session-key") or {}
        self.assertEqual(runtime.get("object"), {"kind": "run", "id": "r1"})
        self.assertEqual(runtime.get("instance_id"), "i1")

    def test_stop_request_does_not_clear_other_fields(self):
        root = _root()
        session.update_runtime(root, "session-key", writer_generation=2, cursor={"step_id": "s9"})
        session.update_runtime(root, "session-key", stop_request={"run": "r1"})
        runtime = session.load_runtime(root, "session-key") or {}
        self.assertEqual(runtime.get("writer_generation"), 2)
        self.assertEqual(runtime.get("cursor"), {"step_id": "s9"})
        self.assertEqual(runtime.get("stop_request"), {"run": "r1"})


class SingleWriterSurfaceTest(unittest.TestCase):
    def test_no_module_outside_session_calls_whole_record_write(self):
        offenders = []
        for path in sorted(WFLIB.glob("*.py")):
            if path.name == "session.py":
                continue
            text = path.read_text(encoding="utf-8")
            if re.search(r"\bwrite_runtime\s*\(", text) or re.search(r"\b_replace_runtime\s*\(", text):
                offenders.append(path.name)
        self.assertEqual(offenders, [],
                         "侧车整份写只允许在 session.update_runtime 内部；新调用点会再次抹掉代次")

    def test_public_whole_record_write_name_is_gone(self):
        text = (WFLIB / "session.py").read_text(encoding="utf-8")
        self.assertNotIn("def write_runtime(", text)
        self.assertIn("def _replace_runtime(", text)
        self.assertIn("def update_runtime(", text)


if __name__ == "__main__":
    unittest.main()
