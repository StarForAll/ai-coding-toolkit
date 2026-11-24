"""R5：`task-approve` 帮助里的取值域由 `decisions.DOMAINS` 生成。

dogfood 的病灶是帮助与登记域各写一份（帮助写 `approve-light|approve-complex|mechanical`，
登记域只接受 `approve/批准` 与 `机械修订`）。本用例要求帮助文本里出现的每个取值都能被
对应域接受，且旧写法不再出现。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from wflib import cli, decisions  # noqa: E402


def _choice_help():
    inputs = cli.COMMAND_HELP["task-approve"]["inputs"]
    entry = inputs.get("decision[]") or {}
    return str(entry.get("choice") or "")


class HelpDomainTest(unittest.TestCase):
    def test_every_listed_choice_is_registered(self):
        text = _choice_help()
        self.assertIn("批准：", text)
        self.assertIn("机械修订：", text)
        approval, _, rest = text.partition("；")
        mechanical = rest.split("（", 1)[0]
        for token in approval.split("：", 1)[1].split("|"):
            self.assertTrue(decisions.accepts("plan_approval", token.strip()), token)
        for token in mechanical.split("：", 1)[1].split("|"):
            self.assertTrue(decisions.accepts("mechanical_revision", token.strip()), token)

    def test_stale_choices_are_gone(self):
        text = _choice_help()
        for stale in ("approve-light", "approve-complex", "mechanical"):
            self.assertNotIn(stale, text)


if __name__ == "__main__":
    unittest.main()


class ExampleFileTest(unittest.TestCase):
    """2026-11-21（dogfood 二轮 AC2）：archive/stop 的 example_file 断言。

    - example_file 存在且每条字段 ⊆ DECISION_FIELDS（模块常量，六键唯一事实源）；
    - archive 的 example_file 同时含 finish 与 commit 两类 choice（决定域形状）；
    - stop 的 example_file 只需合法决定（choice ∈ stop_choice）。
    """

    def test_archive_and_stop_have_example_file(self):
        for name in ("archive", "stop"):
            entry = cli.COMMAND_HELP[name]
            self.assertIn("example_file", entry, f"{name} 缺 example_file")
            for item in entry["example_file"]:
                self.assertTrue(isinstance(item, dict), item)
                for field in cli.DECISION_FIELDS:
                    self.assertIn(field, item, f"{name} example 缺 {field}")

    def test_archive_example_covers_both_choices(self):
        choices = {item["choice"] for item in cli.COMMAND_HELP["archive"]["example_file"]}
        self.assertIn("finish", choices)
        self.assertIn("commit", choices)

    def test_stop_example_choice_is_valid(self):
        for item in cli.COMMAND_HELP["stop"]["example_file"]:
            self.assertTrue(decisions.accepts("stop_choice", item["choice"]), item["choice"])


class ReleaseRefExampleTest(unittest.TestCase):
    """十四轮 b-4：升级示例引用的发行 tag 必须真实存在。

    病灶：示例写着 `refs/tags/wf-v0.1.6`，而 0.1.1–0.1.6 从未打 tag——照抄示例的
    操作者在 `rev-parse` 层面直接失败。判据不是"等于当前 manifest 版本"（开发中的
    版本还没有 tag），而是"示例引用的版本已在本地 tag 列表里"。
    """

    def test_upgrade_example_refs_an_existing_tag(self):
        import re
        import subprocess

        repo = str(Path(__file__).resolve().parents[3])
        # 无 tag 的 clone（shallow/新 clone）无法核验存在性：跳过而不是误报
        any_tag = subprocess.run(["git", "tag", "--list", "wf-v*"], cwd=repo,
                                 capture_output=True, text=True, check=True).stdout.strip()
        if not any_tag:
            self.skipTest("本地 clone 无 wf-v* tag，存在性判据不可用")
        entry = cli.COMMAND_HELP["upgrade"]
        for field in ("example", "example_export"):
            example = str(entry.get(field) or "")
            match = re.search(r"refs/tags/(wf-v\d+\.\d+\.\d+)", example)
            self.assertIsNotNone(match, f"升级示例 {field} 缺 refs/tags/wf-vX.Y.Z 形态：{example}")
            tag = match.group(1)
            existing = subprocess.run(
                ["git", "tag", "--list", tag],
                cwd=repo,
                capture_output=True, text=True, check=True).stdout.strip()
            self.assertEqual(existing, tag,
                             f"升级示例 {field} 引用了不存在的 tag：{tag}（只引用已打 tag 的发行版本）")


class UsageRegistryTest(unittest.TestCase):
    """2026-11-21（五轮审查 P0-1/P0-2）：help 全覆盖 + 用法校验注册表一致性。"""

    def test_help_covers_every_command(self):
        self.assertEqual(set(cli.COMMAND_HELP), set(cli.COMMANDS),
                         f"help 缺: {sorted(set(cli.COMMANDS) - set(cli.COMMAND_HELP))}")

    def test_usage_registry_covers_every_command(self):
        self.assertEqual(set(cli.COMMAND_FLAGS), set(cli.COMMANDS),
                         f"flag 注册表缺: {sorted(set(cli.COMMANDS) - set(cli.COMMAND_FLAGS))}")

    def test_every_documented_flag_is_in_registry(self):
        """帮助里写的每个 flag 都必须在注册表里（否则合法调用会被用法校验拒绝）。"""
        import json as _json

        for name, entry in cli.COMMAND_HELP.items():
            documented = set()
            for key in (entry.get("args") or {}):
                if key.startswith("--"):
                    documented.add(key)
            registry = cli.GLOBAL_FLAGS + tuple(cli.COMMAND_FLAGS.get(name, ()))
            missing = sorted(documented - set(registry))
            self.assertFalse(missing, f"{name} 帮助声明但注册表缺: {missing}")


    def test_every_registered_flag_is_documented(self):
        """反向：注册表里的每个 flag 都必须写进 help——help 是唯一发现通道，漏写等于不可发现。"""
        problems = []
        for name, flags in cli.COMMAND_FLAGS.items():
            entry = cli.COMMAND_HELP.get(name) or {}
            documented = set()
            for key in (entry.get("args") or {}):
                if key.startswith("--"):
                    documented.add(key)
            missing = sorted(flags - documented)
            if missing:
                problems.append(f"{name}: {missing}")
        self.assertFalse(problems, f"注册表有但 help 未写: {problems}")


class UsageValidationTest(unittest.TestCase):
    """dispatch 前的用法校验：未知 flag/未知子命令不再静默。"""

    def _dispatch(self, argv):
        from wflib import cli as cli_mod

        try:
            cli_mod.dispatch(type("C", (), {"root": "/tmp", "command": None})(), list(argv))
        except cli_mod.CliError as exc:
            return exc.code
        return "WF_OK"

    def test_unknown_flag_is_rejected(self):
        self.assertEqual(self._dispatch(["stop", "--prevew"]), "WF_USAGE_INVALID")

    def test_unknown_subcommand_is_rejected(self):
        self.assertEqual(self._dispatch(["writter", "acquire"]), "WF_USAGE_INVALID")

    def test_unknown_sampling_sub_is_rejected(self):
        self.assertEqual(self._dispatch(["sampling", "pik"]), "WF_USAGE_INVALID")

    def test_missing_required_arg_is_usage_code(self):
        self.assertEqual(self._dispatch(["writer"]), "WF_USAGE_INVALID")
        self.assertEqual(self._dispatch(["help", "no-such-cmd"]), "WF_USAGE_INVALID")


class RegistryCompletenessTest(unittest.TestCase):
    """注册表完备性：每个 handler 实际消费的 flag 必须在注册表（防静默拒绝合法调用）。

    2026-11-23（dogfood 五轮）：原实现用闭包 `cell_contents` 取源码，而 `_task_command`
    的闭包只含字符串名 → 20 余个委托型命令的 `flags` 为空并被 `if not flags: continue`
    跳过，断言对它们**空跑**。现在改用 `command_introspection`（与 `test_help_contract`
    共用同一实现），委托型命令解到真实模块函数 + 一层同模块助手。
    """

    def test_registry_covers_all_consumed_flags(self):
        import command_introspection as ci
        from wflib import cli

        # 共享分派器（`_review_command(kind)` 生成的四个 review-* 用同一闭包）无法按命令
        # 静态分离旗标：按 handler 对象分组，组内比并集，组外逐命令比。
        groups = {}
        for name in sorted(cli.COMMANDS):
            sources = ci.handler_sources(cli, name, ci.example_argv(cli, name))
            key = sources[0] if sources else f"none:{name}"
            groups.setdefault(key, []).append(name)
        problems = []
        covered = 0
        for members in groups.values():
            flags = set()
            for name in members:
                consumed, _dynamic = ci.consumed_flags(cli, name, ci.example_argv(cli, name))
                flags |= consumed
            if not flags:
                continue
            covered += 1
            registered = set(cli.GLOBAL_FLAGS)
            for name in members:
                registered |= set(cli.COMMAND_FLAGS.get(name, ()))
            missing = flags - registered
            if missing:
                problems.append(f"{'/'.join(members)}: {sorted(missing)}")
        self.assertFalse(problems, f"handler 消费但注册表缺: {problems}")
        # 覆盖下限：委托型命令解不开时这条断言会掉到个位数，静默盲区不能靠"总绿"掩盖
        self.assertGreater(covered, 20, f"只有 {covered} 个命令的消费集合被静态核到")


class SubcommandFlagNarrowingTest(unittest.TestCase):
    """九轮审查 b-2：run 子命令参数收窄——对当前子命令无效的参数在用法层拒绝。"""

    def _usage(self, argv):
        from wflib import cli as cli_mod

        try:
            cli_mod.dispatch(type("C", (), {"root": "/tmp", "command": None})(), list(argv))
        except cli_mod.CliError as exc:
            return exc.code
        except Exception:
            return "PASS"      # 用法层放行、进入 handler 后因缺项目布局失败——即所需证明
        return "PASS"

    def test_finish_rejects_preview_flag(self):
        # finish 不收 --preview：按并集放行会静默执行真实收尾
        self.assertEqual(self._usage(["run", "finish", "--run", "R", "--decision", "D", "--preview"]),
                         "WF_USAGE_INVALID")

    def test_terminate_accepts_preview_flag(self):
        code = self._usage(["run", "terminate", "--run", "R", "--preview"])
        self.assertNotEqual(code, "WF_USAGE_INVALID")

    def test_inline_value_form_is_accepted(self):
        """Args.value 支持 --flag=value：用法校验不再拒绝该形态。"""
        code = self._usage(["task-new", "--title=x", "--json"])
        self.assertNotEqual(code, "WF_USAGE_INVALID")


class HelpExampleUsableTest(unittest.TestCase):
    """十一轮审查 P1-1：帮助是唯一发现通道——每条 example 必须能过用法校验。"""

    def test_every_example_passes_validate_usage(self):
        problems = []
        for name, entry in cli.COMMAND_HELP.items():
            for key, example in entry.items():
                if not key.startswith("example") or key == "example_file":
                    continue
                if not isinstance(example, str) or not example.strip():
                    continue
                parts = example.split()
                if parts and parts[0] == "wf.py":
                    parts = parts[2:]      # 跳过 wf.py 与命令名：validate_usage 收 argv[1:]
                try:
                    cli.validate_usage(name, parts)
                except cli.CliError as exc:
                    problems.append(f"{name}.{key}: {exc.facts.get('reason')}")
        self.assertFalse(problems, f"help 示例被用法校验拒绝: {problems}")
