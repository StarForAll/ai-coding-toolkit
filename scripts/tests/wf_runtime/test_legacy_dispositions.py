"""F2：历史 dispositions 的形状（无 `finding_id`、无 `decision`）必须能被读取端容忍。

历史归档证据里 35 条处置是另一套形状：`{"decision_ref": …, "finding": "dsh:f1", "reason": …}`。
它们**不是**本机制的关闭记录（没有 `finding_id`、没有 `decision`），所以：
- 读取端不得崩、不得把它们当成关闭（裁定：歧义/不可归属的条目不自动关闭）；
- 也不得进"待裁"歧义列表——它们连身份字段都没有，不是"同名歧义"；
- 读取是纯派生：不写回、不迁移。

用例同时覆盖真实证据（`analysis/evidence/archived-task.tar.gz`，缺失时跳过）。
"""

import copy
import json
import shutil
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import records, review  # noqa: E402

ARCHIVE = REPO / "docs" / "workflows" / "wf" / "analysis" / "evidence" / "archived-task.tar.gz"
ANCHOR = "sha256:" + "a" * 64


class FakeCtx:
    def __init__(self, root):
        self.root = str(root)


def write_report(root, relative, findings):
    path = Path(root) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {"protocol": "wf-review-v1", "task-id": "t1", "round": 1,
            "review-time": "2026-11-11T00:00:00.000000Z", "review-focus": "x",
            "check-anchor": {"check_id": "c1", "check_anchor": ANCHOR},
            "read-scope": ["pkg/**"],
            "excluded-scope": ["node_modules/**", ".env", "*.pem", ".codex/**", "../**"],
            "scope-exceptions": [], "axes": {name: "pass" for name in review.REVIEW_AXES},
            "findings": findings, "verdict": "pass"}
    path.write_text(review.REPORT_MARKER + "\n\n```json\n"
                    + json.dumps(body, ensure_ascii=False) + "\n```\n", encoding="utf-8")
    return relative, records.file_digest(path)


def legacy_dispositions(count=35):
    """与归档证据同形：只有 decision_ref / finding / reason，没有任何身份字段。"""
    return [{"decision_ref": f"proposal:agent:review-action:p{index}",
             "finding": f"dsh:f{index}",
             "reason": "历史处置，登记的是工作流材料改进建议"}
            for index in range(1, count + 1)]


class LegacyDispositionsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self.ctx = FakeCtx(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def task(self):
        relative, digest = write_report(self.root, "review/round-1/review-dsh.md",
                                        [{"id": "f1", "severity": "blocking"}])
        return {"id": "t1", "reviews": {
            "launches": [{"round": 1, "slots": [{"slot": "s1"}]}],
            "imported": [{"round": 1, "slot": "s1", "agent": "dsh", "report_path": relative,
                          "report_digest": digest, "anchor": {"check_anchor": ANCHOR}}],
            "dispositions": legacy_dispositions()}}

    def test_legacy_entries_are_tolerated_and_close_nothing(self):
        task = self.task()
        before = copy.deepcopy(task)
        facts = review.open_findings(self.ctx, task)
        full = review.all_findings(self.ctx, task)
        self.assertEqual(facts["closed"], [])
        self.assertEqual(facts["ambiguous"], [])           # 不是"同名歧义"，是"没有身份"
        self.assertEqual([item["finding_id"] for item in facts["blocking"]], ["f1"])
        self.assertEqual([item["closed"] for item in full], [False])
        self.assertEqual(task, before)                     # 读取是纯派生，不写回

    def test_legacy_entries_do_not_participate_in_closing_decisions(self):
        task = self.task()
        task["reviews"]["dispositions"] = [{"finding_id": "f1", "decision": "accepted",
                                            "reason": "已修", "recheck_by": "human:xzc"}]
        task["reviews"]["dispositions"] += legacy_dispositions(3)
        facts = review.open_findings(self.ctx, task)
        self.assertEqual([item["finding_id"] for item in facts["closed"]], ["f1"])
        self.assertEqual(facts["blocking"], [])


@unittest.skipUnless(ARCHIVE.is_file(), "归档证据不在仓库里")
class ArchivedEvidenceTest(unittest.TestCase):
    """用真实的 35 条历史处置跑一遍读取端。"""

    def test_real_archive_is_readable_and_closes_nothing(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            flat = tmp / "flat"
            flat.mkdir()
            with tarfile.open(ARCHIVE) as tar:
                try:
                    tar.extractall(flat, filter="data")
                except TypeError:            # Python < 3.12
                    tar.extractall(flat)
            task = json.loads((flat / "task.json").read_text(encoding="utf-8"))
            self.assertEqual(sum(1 for item in task["reviews"]["dispositions"]
                                 if item.get("finding_id") is None), 35)
            name = task["reviews"]["imported"][0]["report_path"].split("/")[2]
            root = tmp / "root"
            shutil.copytree(flat, root / ".wf" / "tasks" / name)
            facts = review.open_findings(FakeCtx(root), task)
            full = review.all_findings(FakeCtx(root), task)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(facts["unavailable"], [])
        self.assertTrue(full)                       # 报告能解析出 findings
        self.assertEqual(facts["closed"], [])       # 35 条历史处置不自动关闭任何一条
        self.assertEqual(facts["ambiguous"], [])
        self.assertFalse(any(item["closed"] for item in full))


if __name__ == "__main__":
    unittest.main()
