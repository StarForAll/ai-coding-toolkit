"""R3：写权代次由会话运行态携带（不再要求模型手填）。

机制：`writer.save()`（所有写权持久化的唯一出口）把 holder 代次记进该会话侧车；
`cli.resolve_generation()` 只做来源解析（显式请求 → 侧车 → 缺失）。断言：

1. 持权后侧车带上代次，且与游标等既有字段**合并**写入，不互相覆盖；
2. 自动模式（无显式 inputs）能从侧车取到代次；
3. 显式值优先；
4. 两边都没有时返回缺失（由 `require_held` 转成 `WF_GENERATION_STALE` 并给出口）。
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import cli, session, writer  # noqa: E402


def _root():
    root = tempfile.mkdtemp(prefix="wf-generation-")
    os.makedirs(os.path.join(root, ".wf"), exist_ok=True)
    return root


def _held_record(generation=3, session_key="session-key"):
    record = writer.initial_record()
    record.update(state="held", generation=generation,
                  holder={"kind": "session", "id": session_key, "scope": None,
                          "generation": generation})
    return record


def _ctx(root, inputs=None):
    return SimpleNamespace(root=root, inputs=lambda: dict(inputs or {}))


class GenerationCarryTest(unittest.TestCase):
    def test_writer_save_records_generation_in_session_runtime(self):
        root = _root()
        session.update_runtime(root, "session-key", run_cursor={"step": 2})
        writer.save(root, _held_record(3))
        runtime = session.load_runtime(root, "session-key") or {}
        self.assertEqual(runtime.get("writer_generation"), 3)
        self.assertEqual(runtime.get("run_cursor"), {"step": 2})

    def test_auto_mode_carries_generation_without_explicit_inputs(self):
        root = _root()
        writer.save(root, _held_record(4))
        generation, source = cli.resolve_generation(_ctx(root), "session-key")
        self.assertEqual(generation, 4)
        self.assertEqual(source, "session-runtime")

    def test_explicit_generation_wins(self):
        root = _root()
        writer.save(root, _held_record(4))
        generation, source = cli.resolve_generation(_ctx(root, {"generation": 2}), "session-key")
        self.assertEqual(generation, 2)
        self.assertEqual(source, "request")

    def test_missing_both_sources_is_reported(self):
        root = _root()
        generation, source = cli.resolve_generation(_ctx(root), "session-key")
        self.assertIsNone(generation)
        self.assertEqual(source, "session-runtime")

    def test_maintenance_holder_does_not_create_session_runtime(self):
        root = _root()
        record = writer.initial_record()
        record.update(state="held", generation=1,
                      holder={"kind": "maintenance", "id": "op-1", "scope": None, "generation": 1})
        writer.save(root, record)
        self.assertFalse(os.path.exists(os.path.join(root, ".wf", ".runtime", "sessions")))


if __name__ == "__main__":
    unittest.main()
