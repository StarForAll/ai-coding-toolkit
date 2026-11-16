"""Repro case helpers that must not depend on filesystem readdir order."""

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

REPRO = Path(__file__).resolve().parent / "full" / "repro"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BindRunRuntimeLookupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-bindrun-helper-")
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        (self.project / ".wf/.runtime/sessions").mkdir(parents=True)
        self.module = _load("wf_bind_run_helper", REPRO / "bind-run.py")

    def test_exact_session_key_is_used_even_when_an_old_file_sorts_first(self):
        target = "sess-BR2"
        key = self.module.session_key(target)
        # 一个字典序更小、对象相同的旧会话文件：旧实现会先读到它并误判通过。
        (self.project / ".wf/.runtime/sessions/0000-old.json").write_text(
            json.dumps({"object": {"id": "run-1"}, "current_task": "old-task"}))
        (self.project / ".wf/.runtime/sessions" / f"{key}.json").write_text(
            json.dumps({"object": {"id": "run-1"}, "current_task": "new-task"}))
        record = self.module.runtime_record(str(self.project), target)
        self.assertEqual(record["current_task"], "new-task")
        self.assertNotEqual(self.module.runtime_record(str(self.project), "sess-other"), record)


if __name__ == "__main__":
    unittest.main()
