"""P1-3（2026-11-24）：PRD 摘要口径唯一——草稿预填、正式批准、机械修订、replan 同一读数。

防的失败：`task-approve --draft` 按原始字节哈希，正式批准按文本模式读回再重编码；CRLF 的
PRD 上两者得到不同摘要，人照着草稿批准完才在正式入口撞 `WF_APPROVAL_MISSING`——首轮 dogfood
"人已批准才发现绑定失败"的直接复发路径。修法不是补一次转换，而是把"读 + 摘要"收成一个
读数：解析与摘要出自同一次读，所有入口取同一个值。
"""

import os
import re
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import records, review, tasks  # noqa: E402

PRD_BODY = """# 标题

## 目标

g

## 范围与触碰面

s

## 方案说明

a

## 不做项

n

## 机读块

<!-- wf-plan:v1 -->
```json
{
  "schema_version": 1,
  "complexity": "light",
  "tdd": false,
  "touch_paths": ["pkg/a.py"],
  "acceptance": [{"id": "a1", "statement": "s", "verification_ids": ["v1"]}],
  "verifications": [{"id": "v1", "invocation": {"kind": "argv", "argv": ["true"]},
                     "cwd": ".", "input_refs": [], "required": true, "consume_at": "check"}]
}
```
"""


class PrdDigestSingleSourceTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.task_id = "t1-" + uuid.uuid4().hex[:8]
        self.task_dir = self.root / ".wf" / "tasks" / self.task_id
        self.task_dir.mkdir(parents=True)
        self.task = {"id": self.task_id, "title": "t", "status": "not_started", "phase": "plan",
                     "revision": 1, "plan": {"complexity": "light"}}
        records.write_json(self.task_dir / "task.json", self.task)
        # 复杂任务还要求 design/implement 完整：按模板填空，别让夹具因旁支产物失配
        for name in ("design.md", "implement.md"):
            tpl = (REPO / "docs" / "workflows" / "wf" / "payload" / "templates"
                   / "task" / name)
            text = re.sub(r"\{\{WF_REQUIRED:[^}]+\}\}", "x", tpl.read_text(encoding="utf-8"))
            (self.task_dir / name).write_text(text.replace("__WF_REQUIRED__", "x"),
                                              encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def _write_prd(self, body: str, *, crlf: bool):
        text = body.replace("\n", "\r\n") if crlf else body
        (self.task_dir / "prd.md").write_bytes(text.encode("utf-8"))

    def test_crlf_prd_digest_equals_raw_bytes_digest(self):
        self._write_prd("# PRD\n\n正文\n", crlf=True)
        text, digest = tasks.read_prd_bytes(self.root, self.task)
        self.assertEqual(text, "# PRD\n\n正文\n")          # 解析侧仍是归一后的文本
        raw = (self.task_dir / "prd.md").read_bytes()
        self.assertEqual(digest, "sha256:" + records.sha256_hex(raw))

    def test_prefill_digest_accepted_by_formal_approval(self):
        """草稿预填值必须能被正式批准接受（CRLF PRD 是失败发生的确切输入）。"""
        body = PRD_BODY
        self._write_prd(body, crlf=True)
        draft = tasks.cmd_task_approve(_ctx(self.root), _Args(["--task", self.task_id, "--draft"]))
        digest = draft["facts"]["draft"][0]["object_digest"]
        self.assertTrue(digest.startswith("sha256:"))
        # 正式批准：同一摘要必须核过（只留 subject 绑定，去掉 object_digest 的兜底）
        decision = Path(self.root) / "decision.json"
        entry = dict(draft["facts"]["draft"][0])
        entry.update({"source": "human:test", "at": records.now_str(), "reason": "人确认"})
        records.write_json(decision, [entry])
        ctx = _ctx(self.root)
        records.write_json(Path(self.root) / ".wf" / "session-bindings" / f"{ctx.key()}.json",
                           {"session_key": ctx.key(), "object": {"kind": "task",
                                                                "id": self.task_id}})
        with mock.patch.object(tasks, "_require_instance_match", return_value=None):
            result = tasks.cmd_task_approve(ctx, _Args(
                ["--task", self.task_id, "--decision", str(decision)]))
        self.assertEqual(result["code"] if isinstance(result, dict) else result,
                         "WF_OK")
        stored = records.load_json(self.task_dir / "task.json")
        self.assertEqual((stored.get("plan") or {})["approval"]["object_digest"], digest)


class _Args:
    def __init__(self, argv):
        self._argv = list(argv)

    def value(self, flag, default=None):
        if flag in self._argv:
            return self._argv[self._argv.index(flag) + 1]
        return default

    def flag(self, name):
        return name in self._argv


def _ctx(root):
    from types import SimpleNamespace

    holder = {"session": "s", "generation": 1}
    key = "k" * 16

    def require_held(task=None, strict=True):
        return None, holder

    session_dir = Path(root) / ".wf" / "session-bindings"
    session_dir.mkdir(parents=True, exist_ok=True)
    records.write_json(session_dir / f"{key}.json", {"session_key": key, "object": {}})
    ctx = SimpleNamespace(root=str(root), require_held=require_held, debug_threshold=lambda: 3,
                          platforms=lambda: [], key=lambda: key, activation=lambda: None,
                          inputs=lambda: {}, rule_version=lambda: "r1")
    return ctx


if __name__ == "__main__":
    unittest.main()
