"""P1-7：`inspect` 的两项治理输出（机制稿 §8.5；实现稿 §2.3.11「巡检治理两类」）。

历史状态：`inspect` 只出归档终态、归档引用、spec 复用与周期触发四类，
「需人工比对」清单与 `author` 复核顺序**没有输出**，只在 `governance_omitted` 里声明延后。
现在两类都交付，且 `governance_omitted` 只保留尚未交付的类别——不允许「未声明且未输出」。

口径（机制稿 §8.5）：分类只取 `witnessed`/`potential`，**不判语义矛盾**；
无合法 paths、规格不可解析、扫描不可用一律进 `unverified`（未知不当零）；
`author` 顺序只给顺序与依据，不判该不该复核。
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import tasks as tasks_mod  # noqa: E402

SPEC = """---
schema_version: 1
status: "active"
author: "{author}"
verified_at: "{verified}"
counterexample: "x"
paths: {paths}
---

# 规则

正文。
"""


def _git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def _project(specs, files):
    root = tempfile.mkdtemp(prefix="wf-gov-")
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    os.makedirs(os.path.join(root, ".wf", "spec"), exist_ok=True)
    for name, (author, verified, paths) in specs.items():
        with open(os.path.join(root, ".wf", "spec", name), "w", encoding="utf-8") as handle:
            handle.write(SPEC.format(author=author, verified=verified, paths=json.dumps(paths)))
    for relative in files:
        absolute = os.path.join(root, relative)
        os.makedirs(os.path.dirname(absolute) or root, exist_ok=True)
        with open(absolute, "w", encoding="utf-8") as handle:
            handle.write("x\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "base")
    return root


class InspectGovernanceTest(unittest.TestCase):
    def test_witnessed_pair_with_a_real_shared_path(self):
        root = _project({"a.md": ("human", "2026-11-01", ["src/**"]),
                         "b.md": ("ai", "2026-11-01", ["src/api/**"])},
                        ["src/api/x.py"])
        compare = tasks_mod._manual_compare(root)
        self.assertEqual(compare["counts"]["witnessed"], 1)
        item = compare["witnessed"][0]
        self.assertEqual(item["pair"], [".wf/spec/a.md", ".wf/spec/b.md"])
        self.assertEqual(item["witnesses"], ["src/api/x.py"])
        self.assertEqual(item["class"], "witnessed")
        self.assertEqual(compare["potential"], [])

    def test_potential_when_prefix_cannot_prove_disjoint(self):
        root = _project({"a.md": ("human", "2026-11-01", ["src/**"]),
                         "c.md": ("human", "2026-11-01", ["**/*.md"])},
                        ["docs/readme.md"])
        compare = tasks_mod._manual_compare(root)
        self.assertEqual(compare["counts"]["potential"], 1)
        self.assertEqual(compare["potential"][0]["unexcluded"], [["src/**", "**/*.md"]])
        self.assertIn("无当前路径见证", compare["potential"][0]["basis"])

    def test_provably_disjoint_pairs_are_excluded(self):
        root = _project({"a.md": ("human", "2026-11-01", ["src/**"]),
                         "d.md": ("human", "2026-11-01", ["tests/**"])},
                        ["src/a.py", "tests/b.py"])
        compare = tasks_mod._manual_compare(root)
        self.assertEqual(compare["counts"]["candidates"], 0)

    def test_active_spec_without_paths_is_unverified_not_dropped(self):
        root = _project({"e.md": ("human", "2026-11-01", []), "a.md": ("human", "2026-11-01", ["src/**"])},
                        ["src/a.py"])
        compare = tasks_mod._manual_compare(root)
        self.assertEqual([item["path"] for item in compare["unverified"]], [".wf/spec/e.md"])
        self.assertIn("no legal paths", compare["unverified"][0]["reason"])

    def test_author_order_puts_extracted_first_then_ai(self):
        root = _project({"human-dated.md": ("human", "2026-11-01", ["a/**"]),
                         "ai-dated.md": ("ai", "2026-11-01", ["b/**"]),
                         "human-extracted.md": ("human", "extracted", ["c/**"]),
                         "ai-extracted.md": ("ai", "extracted", ["d/**"])},
                        ["a/x", "b/x"])
        order = [item["path"] for item in tasks_mod._author_order(root)]
        self.assertEqual(order, [".wf/spec/ai-extracted.md", ".wf/spec/human-extracted.md",
                                 ".wf/spec/ai-dated.md", ".wf/spec/human-dated.md"])

    def test_archive_dir_name_mismatch_carries_typed_kind(self):
        """目录名与记录 id 不符要能按类消费，不只靠一句自由文本（F10 的小欠账）。"""
        root = _project({"a.md": ("human", "2026-11-01", ["src/**"])}, ["src/a.py"])
        bad = os.path.join(root, ".wf/tasks/archive/2026-11", "2026-wrong-x")
        os.makedirs(bad, exist_ok=True)
        with open(os.path.join(bad, "task.json"), "w", encoding="utf-8") as handle:
            json.dump({"schema_version": 1, "id": "2026-abc", "status": "archived",
                       "terminal": "normal", "archived_at": "2026-11-01T00:00:00.000000Z",
                       "curation": []}, handle, ensure_ascii=False)
        problems = tasks_mod._archive_terminal_problems(
            root, list(tasks_mod.iter_tasks(root)))
        mismatch = [item for item in problems if item.get("kind") == "dir-name-mismatch"]
        self.assertEqual(len(mismatch), 1)
        self.assertEqual(mismatch[0]["record_id"], "2026-abc")
        self.assertEqual(mismatch[0]["dir_name"], "2026-wrong-x")

    def test_governance_omitted_no_longer_hides_delivered_classes(self):
        root = _project({"a.md": ("human", "2026-11-01", ["src/**"])}, ["src/a.py"])
        from types import SimpleNamespace

        payload = tasks_mod.inspect(SimpleNamespace(root=root))
        categories = {item["category"] for item in payload["facts"]["governance_omitted"]}
        self.assertNotIn("manual_compare", categories)
        self.assertNotIn("author_order", categories)
        governance = payload["facts"]["governance"]
        self.assertIn("manual_compare", governance)
        self.assertIn("author_order", governance)


if __name__ == "__main__":
    unittest.main()
