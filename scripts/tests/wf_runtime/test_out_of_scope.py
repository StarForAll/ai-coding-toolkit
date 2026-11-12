"""P1-8：`.wf/out-of-scope/` 知识拒绝项（机制稿 §8.4；设计稿 §6.3 的四项启用前置）。

四项前置必须同时在位，缺一不得只留目录：

1. 写入者：`spec-update` 能按 schema 建 `<concept>.md`；
2. 重提追加：同 concept 只追加 `## 既往请求` 一行，不新建文件、不改写既往内容；
3. 路径放行：`.wf/out-of-scope/**` 进 `paths.WRITE_TARGET_PREFIXES` 与 `protocol.project_data()`；
4. 消费者：`inspect` 的治理面报「重复登记」，并且 `governance_omitted` 不再拿它当未交付类别。

正反用例逐条对应 PRD 的验收：建文件 / 重提追加 / 空 reason 拒 / concept 与文件名不符拒 / 多文件被巡检报重复。
机制只核这些可机械判定的部分；「什么算已拒绝、何时可重议」是人写的正文，不在这层。
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

from wflib import paths as paths_mod  # noqa: E402
from wflib import protocol, spec as spec_mod, tasks as tasks_mod  # noqa: E402


def _item(concept, reason='"理由：不属本框架目标"', reconsider='"条件：出现真实缺口时重议"', history=None):
    lines = [
        "---",
        f'concept: "{concept}"',
        f"reason: {reason}",
        f"reconsider_when: {reconsider}",
        'status: "active"',
        "---",
        "",
        f"# {concept}",
        "",
        "## 既往请求",
    ]
    lines.extend(history or ["- 2026-11-12 ｜ 首次请求 ｜ 人裁：不做"])
    return "\n".join(lines) + "\n"


def _root():
    root = tempfile.mkdtemp(prefix="wf-oos-")
    os.makedirs(os.path.join(root, ".wf", "out-of-scope"), exist_ok=True)
    return root


def _add(relative, concept, **kwargs):
    return {"operation": "add", "new_paths": [relative], "content": _item(concept, **kwargs)}


class OutOfScopeTest(unittest.TestCase):
    def test_path_and_project_data_allow_the_directory(self):
        self.assertTrue(paths_mod.write_target_allowed(".wf/out-of-scope/thing.md"))
        self.assertIn(".wf/out-of-scope/", protocol.project_data()["prefixes"])
        self.assertIn(".wf/out-of-scope/**", paths_mod.write_target_allowed_list())

    def test_add_creates_a_valid_item(self):
        root = _root()
        change = _add(".wf/out-of-scope/scheduler.md", "scheduler")
        self.assertTrue(spec_mod.validate_changes(root, [change]))
        spec_mod.apply_changes(root, [change], {"id": "t1"})
        written = os.path.join(root, ".wf/out-of-scope/scheduler.md")
        metadata, problems = spec_mod.parse_frontmatter(written)
        self.assertEqual(problems, [])
        self.assertEqual(metadata["concept"], "scheduler")

    def test_empty_reason_is_rejected(self):
        root = _root()
        change = _add(".wf/out-of-scope/x.md", "x", reason='""')
        with self.assertRaises(spec_mod.SpecError) as caught:
            spec_mod.validate_changes(root, [change])
        self.assertEqual(caught.exception.code, "WF_SEMANTIC_DECISION")
        self.assertIn("reason", json.dumps(caught.exception.facts, ensure_ascii=False))

    def test_concept_must_match_filename(self):
        root = _root()
        change = _add(".wf/out-of-scope/a.md", "b")
        with self.assertRaises(spec_mod.SpecError) as caught:
            spec_mod.validate_changes(root, [change])
        self.assertEqual(caught.exception.code, "WF_SEMANTIC_DECISION")
        self.assertIn("文件名必须与 concept 一致",
                      json.dumps(caught.exception.facts, ensure_ascii=False))

    def test_resubmission_appends_one_line_and_keeps_history(self):
        root = _root()
        spec_mod.apply_changes(root, [_add(".wf/out-of-scope/scheduler.md", "scheduler")], {"id": "t1"})
        path = os.path.join(root, ".wf/out-of-scope/scheduler.md")
        with open(path, encoding="utf-8") as handle:
            previous = handle.read()
        appended = previous + "- 2026-12-01 ｜ 重提：要并行调度 ｜ 人裁：仍不做\n"
        spec_mod.validate_changes(root, [{"operation": "update",
                                          "new_paths": [".wf/out-of-scope/scheduler.md"],
                                          "content": appended}])
        spec_mod.apply_changes(root, [{"operation": "update",
                                       "new_paths": [".wf/out-of-scope/scheduler.md"],
                                       "content": appended}], {"id": "t2"})
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        self.assertEqual(text.count("## 既往请求"), 1)
        self.assertIn("重提：要并行调度", text)

    def test_resubmission_cannot_rewrite_previous_lines(self):
        root = _root()
        spec_mod.apply_changes(root, [_add(".wf/out-of-scope/scheduler.md", "scheduler")], {"id": "t1"})
        rewritten = _item("scheduler", reason='"理由：改口了"') + "- 2026-12-01 ｜ x ｜ y\n"
        with self.assertRaises(spec_mod.SpecError) as caught:
            spec_mod.validate_changes(root, [{"operation": "update",
                                              "new_paths": [".wf/out-of-scope/scheduler.md"],
                                              "content": rewritten}])
        self.assertIn("只增不改", json.dumps(caught.exception.facts, ensure_ascii=False))

    def test_second_file_for_same_concept_is_rejected_on_add(self):
        root = _root()
        spec_mod.apply_changes(root, [_add(".wf/out-of-scope/scheduler.md", "scheduler")], {"id": "t1"})
        with self.assertRaises(spec_mod.SpecError):
            spec_mod.validate_changes(root, [_add(".wf/out-of-scope/scheduler2.md", "scheduler")])

    def test_inspect_reports_duplicate_registration(self):
        """巡检侧：同 concept 多文件（含手工复制出来的）必须被报出来。"""
        root = _root()
        spec_mod.apply_changes(root, [_add(".wf/out-of-scope/scheduler.md", "scheduler")], {"id": "t1"})
        with open(os.path.join(root, ".wf/out-of-scope/scheduler-copy.md"), "w", encoding="utf-8") as handle:
            handle.write(_item("scheduler"))
        facts = tasks_mod._out_of_scope_duplicates(root)
        self.assertEqual(len(facts["duplicates"]), 1)
        self.assertEqual(facts["duplicates"][0]["concept"], "scheduler")
        self.assertEqual(len(facts["duplicates"][0]["files"]), 2)
        self.assertEqual(facts["unverified"], [])

    def test_unparsable_item_is_unknown_not_absent(self):
        root = _root()
        with open(os.path.join(root, ".wf/out-of-scope/broken.md"), "w", encoding="utf-8") as handle:
            handle.write("# 没有 frontmatter\n")
        facts = tasks_mod._out_of_scope_duplicates(root)
        self.assertEqual(facts["duplicates"], [])
        self.assertEqual(len(facts["unverified"]), 1)

    def test_governance_omitted_is_empty_after_delivery(self):
        root = _root()
        for sub in (".wf/tasks", ".wf/spec", ".wf/session-bindings"):
            os.makedirs(os.path.join(root, sub), exist_ok=True)
        payload = tasks_mod.inspect(SimpleNamespace(root=root))
        self.assertEqual(payload["facts"]["governance_omitted"], [])
        self.assertIn("out_of_scope_duplicates", payload["facts"]["governance"])


if __name__ == "__main__":
    unittest.main()
