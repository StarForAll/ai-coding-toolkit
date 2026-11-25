"""指引契约的可核对面（2026-11-23 五轮，三轮审查后的收口）。

本文件只锁两件事——它们都是"指引/契约"而非新机制：

1. **报告状态行的位置约定必须与判定窗口同源**。判定只读报告开头 `STATUS_HEAD_CHARS`
   字符（自动发现与 lint 共用同一实现），而错误出口曾统一说"放在报告第一行"：两句话
   不是同一个契约，reviewer 照出口做会被另一个窗口放过/拒绝，来回一次就是整轮成本。
   这里断言窗口边界行为 + 出口文案里出现同一个数字，任何一边改动都会变红。
2. **"作决定"与"转录"是两件事**（设计稿 §1.2）。决定内容必须由人明确给出，模型可按
   该选择填写决定文件，但不得推测/补造/替人选择；`--draft` 骨架只是省掉猜字段。
   这里断言这条口径在判据位（设计稿）与 skill/草稿出口上都在，防止只改一处又漂回去。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PAYLOAD = REPO / "docs" / "workflows" / "wf" / "payload"
sys.path.insert(0, str(PAYLOAD / "lib"))

from wflib import cli, review, tasks  # noqa: E402

DESIGN = (REPO / "docs" / "workflows" / "wf-framework-design.md").read_text(encoding="utf-8")
SKILL_REVIEW = (REPO / "docs" / "workflows" / "wf" / "skills" / "wf-review" / "SKILL.md").read_text(
    encoding="utf-8")
SKILL_CONTINUE = (REPO / "docs" / "workflows" / "wf" / "skills" / "wf-continue" / "SKILL.md").read_text(
    encoding="utf-8")
SKILL_FINISH = (REPO / "docs" / "workflows" / "wf" / "skills" / "wf-finish" / "SKILL.md").read_text(
    encoding="utf-8")


class StatusWindowTest(unittest.TestCase):
    def _report(self, prefix):
        return f"{prefix}<!-- wf-review-agent:v1 status=done -->\n正文\n"

    def test_marker_inside_window_is_read(self):
        prefix = "x" * (review.STATUS_HEAD_CHARS - len("<!-- wf-review-agent:v1 status=done -->"))
        self.assertEqual(review.report_status(self._report(prefix)), "done")

    def test_marker_past_window_is_not_read(self):
        prefix = "x" * (review.STATUS_HEAD_CHARS + 1)
        self.assertIsNone(review.report_status(self._report(prefix)))

    def test_exit_texts_quote_the_same_window(self):
        """出口文案必须说"开头前 N 字符"，不能再说"第一行"——否则契约有两份。

        断言落在**渲染后的出口字符串**上（源码里是 `{STATUS_HEAD_CHARS}` 占位，
        拿源码文本比数字会得到假绿/假红）。
        """
        window = str(review.STATUS_HEAD_CHARS)
        report = review.report_input_problems({"protocol": review.PROTOCOL},
                                              task={"id": "t1"},
                                              text="no status marker here",
                                              require_done=True)
        exits = [exit_ for entry in report["checks"].get("status-head") or []
                 for exit_ in entry.get("exits") or []]
        self.assertTrue(exits, "缺少状态行的报告必须给出出口")
        self.assertTrue(any(f"前 {window} 字符" in exit_ for exit_ in exits), exits)
        self.assertFalse(any("报告第一行" in exit_ for exit_ in exits), exits)
        self.assertIn(window, SKILL_REVIEW)


class DecisionTranscriptionTest(unittest.TestCase):
    def test_design_states_decision_vs_transcription(self):
        self.assertIn("作决定与转录是两个动作", DESIGN)
        self.assertIn("不得推测、补全或替人选择", DESIGN)

    def test_skill_keeps_the_boundary_at_the_writing_rule(self):
        self.assertIn("决定内容必须是人已明确给出的选择", SKILL_CONTINUE)
        self.assertIn("作决定与转录是两件事", SKILL_CONTINUE)

    def test_draft_exit_tells_the_model_not_to_guess(self):
        """草稿出口的实际文案（用户/模型看到的那一句）必须写明"按人的明确答复填写"。"""
        payload = tasks._decision_draft_result(
            None, "t-1", [{"choice": "TODO（批准|机械修订）"}], command="task-approve")
        next_text = str(payload.get("next") or "")
        self.assertIn("按人的明确答复填写", next_text)
        self.assertIn("不得推测或替人选择", next_text)


class GuidanceLandingTest(unittest.TestCase):
    """人签清单里的 manual 项、收工规模确认、审查链轮次都要有**落点**。

    这不是措辞偏好：每条都有行为对应物（manual 决定必须带 `content_digest`、
    `sampling confirm` 是规模确认的唯一写入路径、`review-import/decide --round`
    决定读哪一轮）。缺落点时 AI 只能在失败后读源码猜。
    """

    def test_manual_verification_has_a_field_and_a_source(self):
        self.assertIn("kind=manual", SKILL_CONTINUE)
        self.assertIn("content_digest", SKILL_CONTINUE)
        self.assertIn("delivery.content_digest", SKILL_CONTINUE)
        help_text = str(cli.COMMAND_HELP["task-check"]["args"]["--decision"])
        self.assertIn("content_digest", help_text)
        self.assertIn("manual", help_text)
        self.assertIn("kind=manual", SKILL_FINISH)

    def test_scale_confirmation_names_the_write_command(self):
        self.assertIn("wf sampling confirm --task <id>", SKILL_FINISH)

    def test_review_chain_names_the_round_explicitly(self):
        self.assertIn("review-import --round <n>", SKILL_CONTINUE)
        self.assertIn("review-decide --round <n>", SKILL_CONTINUE)

    def test_task_abandon_disposition_is_conditionally_required(self):
        text = str(cli.COMMAND_HELP["task-abandon"]["args"]["--disposition"])
        self.assertIn("必填", text)
        self.assertIn("changes", cli.COMMAND_HELP["task-abandon"]["inputs"]["--disposition"])

    def test_sampling_help_separates_attestation_and_quote(self):
        args = cli.COMMAND_HELP["sampling"]["args"]
        self.assertIn("必填", args["--attestation"])
        self.assertIn("evaluate/reviewed", args["--attestation"])
        self.assertIn("confirm", args["--quote"])
        self.assertNotIn("reviewed/confirm", args["--quote"])

    def test_manual_plan_version_names_its_source(self):
        self.assertIn("facts.task.plan_version", str(cli.COMMAND_HELP["task-check"]))

    def test_direct_acceptance_has_a_shape_and_landing(self):
        self.assertIn("空 `verification_ids`", SKILL_CONTINUE)
        self.assertIn("空 `verification_ids`", SKILL_FINISH)
        inputs = str(cli.COMMAND_HELP["task-check"]["inputs"])
        self.assertIn("acceptance-direct", inputs)
        self.assertIn("content_digest", inputs)


if __name__ == "__main__":
    unittest.main()