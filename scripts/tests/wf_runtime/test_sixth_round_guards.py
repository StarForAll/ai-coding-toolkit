"""六轮复核回归（2026-11-26 第二轮审查）：

1. **草稿旗标与真实输入互斥**（B3）：`--draft`/`--*-draft` 与它对应的值旗标同给时必须拒，
   不能静默胜出（此前只有 archive 拒绝）。
2. **TDD 红绿必须同验证定义**（外部报告 b-P1）：同 `verification_id` 但 argv/cwd/required
   改过的历史失败运行不能与新的通过运行配对。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import check as check_mod  # noqa: E402
from wflib import cli, fingerprint  # noqa: E402


class _Args:
    """最小 Args 替身：只回答 flag/value（与 cli.Args 的消费面一致）。"""

    def __init__(self, flags=(), values=None):
        self._flags = set(flags)
        self._values = dict(values or {})

    def flag(self, name):
        return name in self._flags

    def value(self, name):
        return self._values.get(name)


class DraftConflictTest(unittest.TestCase):
    def test_draft_with_decision_is_refused(self):
        for command in ("task-approve", "task-replan", "task-rework", "stop"):
            with self.assertRaises(cli.CliError) as caught:
                cli.reject_draft_conflicts(command, _Args(["--draft"], {"--decision": "d.json"}))
            self.assertEqual(caught.exception.code, "WF_USAGE_INVALID", command)

    def test_knowledge_draft_conflicts_with_its_real_pair(self):
        """`--changes-draft` 的骨架对象是 `--changes`；`--decision` 只是同给的取值输入。"""
        for value in ("--changes", "--decision", "--no-update"):
            args = _Args(["--changes-draft", "--no-update"], {value: "x.json"}) if value != "--no-update" \
                else _Args(["--changes-draft", "--no-update"])
            with self.assertRaises(cli.CliError, msg=value):
                cli.reject_draft_conflicts("task-knowledge", args)

    def test_legacy_red_without_verification_digest_is_refused(self):
        """升级前的历史红运行没有验证定义摘要 ⇒ 不能给当前定义的绿运行背书（fail-closed）。"""
        verification = _verification()
        legacy = {"verification_id": "v1", "status": "failed", "evidence_ref": "run-0"}
        evidence = {"assertion": "a", "red_reason": "r", "red_command_ref": "v1",
                    "green_command_ref": "v1", "properties": "p"}
        problem = check_mod.tdd_evidence_problem(evidence, [_command(verification)], [legacy])
        self.assertIsNotNone(problem)
        self.assertIn("predates verification identity", problem.get("reason", ""))

    def test_draft_alone_is_accepted(self):
        for command in ("task-approve", "task-replan", "task-rework", "stop"):
            cli.reject_draft_conflicts(command, _Args(["--draft"]))

    def test_decision_alone_is_accepted(self):
        cli.reject_draft_conflicts("task-approve", _Args([], {"--decision": "d.json"}))

    def test_specific_draft_flags_are_covered(self):
        cases = [
            ("task-check", "--review-notes-draft", "--review-notes"),
            ("spec-update", "--changes-draft", "--changes"),
            ("authorize", "--draft", "--file"),
            ("task-knowledge", "--changes-draft", "--changes"),
            ("judgments", "--draft", "--file"),
            ("definition", "--authorization-draft", "--authorization"),
            ("run", "--authorization-draft", "--authorization"),
            ("run", "--creation-draft", "--creation"),
        ]
        for command, draft, value in cases:
            with self.assertRaises(cli.CliError, msg=f"{command} {draft}+{value}"):
                cli.reject_draft_conflicts(command, _Args([draft], {value: "x.json"}))

    def test_every_registered_conflict_flag_is_a_real_flag(self):
        """登记表不得凭空写旗标：草稿旗标与冲突旗标都要在该命令的用法面里出现。"""
        problems = []
        for command, table in sorted(cli.DRAFT_CONFLICTS.items()):
            documented = set()
            entry = cli.COMMAND_HELP.get(command) or {}
            documented |= {key for key in (entry.get("args") or {}) if key.startswith("--")}
            documented |= {key for key in (entry.get("inputs") or {}) if key.startswith("--")}
            for draft_flag, conflicts in table.items():
                for flag in (draft_flag, *conflicts):
                    if flag not in documented:
                        problems.append(f"{command}: {flag}")
        self.assertEqual(problems, [], "草稿冲突登记了帮助里没有的旗标: " + "; ".join(problems))


def _verification(argv=("/usr/bin/python3", "-c", "print(1)")):
    return {"id": "v1", "invocation": {"kind": "argv", "argv": list(argv)},
            "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}


def _command(verification, status="passed", ref="run-1"):
    return {"verification_id": verification.get("id"),
            "verification_digest": fingerprint.verification_digest(verification),
            "status": status, "evidence_ref": ref}


class TddVerificationDefinitionTest(unittest.TestCase):
    def test_same_definition_red_then_green_is_accepted(self):
        verification = _verification()
        evidence = {"assertion": "a", "red_reason": "r", "red_command_ref": "v1",
                    "green_command_ref": "v1", "properties": "p"}
        problem = check_mod.tdd_evidence_problem(
            evidence, [_command(verification)], [_command(verification, "failed", "run-0")])
        self.assertIsNone(problem)

    def test_red_run_under_old_command_definition_is_refused(self):
        """重规划保留 id 换命令：旧失败运行不能再证明新命令的行为。"""
        old = _verification(("/usr/bin/python3", "-c", "print(0)"))
        new = _verification()
        evidence = {"assertion": "a", "red_reason": "r", "red_command_ref": "v1",
                    "green_command_ref": "v1", "properties": "p"}
        problem = check_mod.tdd_evidence_problem(
            evidence, [_command(new)], [_command(old, "failed", "run-0")])
        self.assertIsNotNone(problem, "不同验证定义的红绿被放行")
        self.assertIn("different verification definitions", problem.get("reason", ""))

    def test_same_id_but_different_verification_is_still_refused(self):
        v1 = _verification()
        v2 = dict(_verification(), id="v2")
        evidence = {"assertion": "a", "red_reason": "r", "red_command_ref": "v1",
                    "green_command_ref": "v2", "properties": "p"}
        problem = check_mod.tdd_evidence_problem(
            evidence, [_command(v2)], [_command(v1, "failed", "run-0")])
        self.assertIsNotNone(problem)
        self.assertIn("same verification", problem.get("reason", ""))


if __name__ == "__main__":
    unittest.main()