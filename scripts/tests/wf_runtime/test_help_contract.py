"""帮助声明 ↔ 真实实现的机械对照（2026-11-23，dogfood 五轮）。

dogfood 的两类真实失败被三个 agent 各自点名、但机制上从未被拦住：
1. `task-retrospect` 帮助把 `--evidence` 标成"可选"、`--decision` 标成"必填"，
   而 handler 恰好反过来；AI 按帮助调用先吃一次无效失败（a-2）。
2. `task-retrospect --commit`、`task-knowledge --evidence`、`task-curate --kind/--reason/
   --compensation/--evidence/--check` 是**幽灵旗标**：帮助登了、用法校验放行、
   handler 从不读取——写进去的参数被静默丢弃（比报错更贵）。
同时，"帮助 ↔ 注册表 ↔ handler 消费"的既有断言对 `_task_command` 委托型命令**空跑**
（闭包里只有字符串名），所以这些漂移逃过了全绿。

本用例只做两件可稳定计算的事：
- `ConsumptionTest`：帮助登记的每个旗标必须被该命令的真实实现读取（含一层同模块助手
  与登记过的引导层来源；动态读取形态显式登记理由）。
- `ClaimTest`：以帮助 `example` 为基线逐条删旗标——
  ① 文本以"可选"开头 ⇒ 不得出现"点名该旗标的 `WF_USAGE_INVALID`"；
  ② 文本以"必填"开头 ⇒ 不得 `WF_OK`。
条件式必填（"record 必填"、"pause：…"等）不在自动声明集内，由各命令的目标断言覆盖。
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from wflib import cli  # noqa: E402
import command_introspection as ci  # noqa: E402


def documented_flags(entry):
    flags = {key for key in (entry.get("args") or {}) if key.startswith("--")}
    flags |= {key for key in (entry.get("inputs") or {})
              if key.startswith("--") and not key.endswith("[]")}
    return flags


class RegistryHygieneTest(unittest.TestCase):
    """登记表本身的自检（六轮复核 A3 的回归来源）：

    ① 同名键在同一字典字面量里重复时，Python 静默取最后一条——`COMMAND_BOOL_FLAGS` 曾因此丢掉
       `--creation-draft`/`--authorization-draft`，表现为"帮助里登记了、调用却报未知旗标"；
    ② 帮助登记的每个旗标，至少要能在该命令的某个子命令集合或并集里被用法校验放行，
       否则帮助说得出、入口走不通。
    """

    def test_no_duplicate_keys_in_cli_registries(self):
        import ast
        import inspect
        import tempfile
        from pathlib import Path

        source = inspect.getsource(cli)
        tree = ast.parse(source)
        problems = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            seen = {}
            for key in node.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    seen[key.value] = seen.get(key.value, 0) + 1
            problems.extend(f"L{node.lineno}: duplicate key {key}" for key, count in seen.items()
                            if count > 1)
        # 逐字面量重复键在 AST 上可见；这里同时给出文件行号上下文便于定位
        self.assertEqual(problems, [], "登记表出现重复键（被静默覆盖）：" + "; ".join(problems))

    def test_documented_flags_are_accepted_by_usage_validation(self):
        problems = []
        for command, entry in sorted(cli.COMMAND_HELP.items()):
            documented = documented_flags(entry)
            union = set(cli.GLOBAL_FLAGS) | set(cli.COMMAND_FLAGS.get(command, ()))
            sub_sets = cli.COMMAND_SUB_FLAGS.get(command) or {}
            reachable = set(union)
            for flags in sub_sets.values():
                reachable |= set(cli.GLOBAL_FLAGS) | set(flags)
            missing = sorted(documented - reachable)
            if missing:
                problems.append(f"{command}: {missing}")
        self.assertEqual(problems, [], "帮助登记但用法校验会拒的旗标: " + "; ".join(problems))


class ConsumptionTest(unittest.TestCase):
    """帮助登记的旗标必须被真实实现读取（幽灵旗标 = 静默丢弃输入）。"""

    def test_every_documented_flag_is_consumed(self):
        problems = []
        for command, entry in sorted(cli.COMMAND_HELP.items()):
            documented = documented_flags(entry)
            flags, dynamic = ci.consumed_flags(cli, command, ci.example_argv(cli, command))
            consumed = flags | set(cli.GLOBAL_FLAGS)
            if command in ci.NON_STANDARD_READERS:
                continue          # 见下方理由断言；这里不假装核过
            missing = sorted(documented - consumed)
            if missing:
                problems.append(f"{command}: {missing}")
            if dynamic:
                problems.append(f"{command}: 含无法静态提取的动态旗标读取，必须显式登记理由")
        self.assertFalse(problems, "帮助登记但真实实现不读取（幽灵旗标）: " + "; ".join(problems))

    def test_non_standard_readers_are_registered_with_reason(self):
        """allowlist 不许悄悄吞命令：键必须是真命令，值必须写清为什么提取不到。"""
        for command, reason in ci.NON_STANDARD_READERS.items():
            self.assertIn(command, cli.COMMANDS, command)
            self.assertGreater(len(reason), 20, f"{command} 的 allowlist 理由太短，等于没写")

    def test_task_retrospect_help_matches_handler(self):
        """a-2 回归：帮助的必填/可选必须与 handler 的实际要求一致。

        五轮复审 a-1 后 `--decision` 已删（它曾被读入即丢弃）：复盘只收 `--evidence`，
        结论取自 `evidence.conclusion`。
        """
        args = cli.COMMAND_HELP["task-retrospect"]["args"]
        self.assertTrue(args["--evidence"].startswith("必填"), args["--evidence"])
        for gone in ("--decision", "--commit"):
            self.assertNotIn(gone, args)
            self.assertNotIn(gone, cli.COMMAND_FLAGS["task-retrospect"])

    def test_phantom_flags_are_gone(self):
        """幽灵旗标回归：删掉之后不得再从帮助或注册表复活。"""
        for command, flags in (("task-knowledge", ["--evidence"]),
                               ("task-curate", ["--kind", "--reason", "--compensation",
                                                "--evidence", "--check"])):
            documented = documented_flags(cli.COMMAND_HELP[command])
            registered = set(cli.COMMAND_FLAGS.get(command, ()))
            for flag in flags:
                self.assertNotIn(flag, documented, f"{command} 帮助仍有幽灵旗标 {flag}")
                self.assertNotIn(flag, registered, f"{command} 注册表仍有幽灵旗标 {flag}")


class ClaimTest(unittest.TestCase):
    """帮助的"必填/可选"声明必须与真实行为一致。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="wf-help-claim-")
        self.addCleanup(self._tmp.cleanup)
        self.root = self._tmp.name

    def _bool_flags(self, command):
        return set(cli.GLOBAL_BOOL_FLAGS) | set(cli.COMMAND_BOOL_FLAGS.get(command, ()))

    def _strip(self, argv, command, flag):
        out, index = [], 1
        while index < len(argv):
            token = argv[index]
            if token == flag:
                index += 1
                if flag not in self._bool_flags(command) and index < len(argv):
                    index += 1
                continue
            if token.startswith(flag + "="):
                index += 1
                continue
            out.append(token)
            index += 1
        return [argv[0]] + out

    def _run(self, command, argv):
        """直接调用 handler：绕开 activation/写权前置，让"缺参"这一层的判定可达。

        与 `dispatch` 的差别只在跳过 `_needs_activation` 与信封缓存；用法校验、Args
        解析、handler 本体与错误码全部走同一实现，所以断言的仍是真实行为。
        """
        ctx = cli.Context(self.root, list(argv))
        ctx.command = command
        cli.validate_usage(command, list(argv[1:]))
        ctx.args = cli.Args(list(argv[1:]))
        try:
            payload = cli.COMMANDS[command](ctx, ctx.args)
        except cli.CliError as exc:
            return exc.code, json.dumps(exc.facts, ensure_ascii=False)
        except Exception as exc:                       # 领域错误按各自码归类
            return (getattr(exc, "code", None) or type(exc).__name__,
                    json.dumps(getattr(exc, "facts", {}) or {}, ensure_ascii=False))
        return (payload or {}).get("code", "WF_OK"), ""

    def _example(self, command):
        argv = ci.example_argv(cli, command)
        # 例子里的项目外路径换成临时目录：断言不依赖也不写入真实 /tmp
        return [token.replace("/tmp/wf-deviations", os.path.join(self.root, "deviations"))
                     .replace("/path/to/wf-checkout", os.path.join(self.root, "checkout"))
                for token in argv]

    def test_optional_flags_are_really_optional(self):
        problems = []
        for command, entry in sorted(cli.COMMAND_HELP.items()):
            argv = self._example(command)
            for flag, text in (entry.get("args") or {}).items():
                if not flag.startswith("--") or flag in cli.GLOBAL_FLAGS:
                    continue
                if not str(text).startswith("可选"):
                    continue
                code, facts = self._run(command, self._strip(argv, command, flag))
                if code == "WF_USAGE_INVALID" and flag in facts:
                    problems.append(f"{command} {flag}: 标为可选却被强制要求")
        self.assertFalse(problems, "; ".join(problems))

    def test_required_flags_cannot_be_dropped(self):
        problems = []
        for command, entry in sorted(cli.COMMAND_HELP.items()):
            argv = self._example(command)
            for flag, text in (entry.get("args") or {}).items():
                if not flag.startswith("--") or flag in cli.GLOBAL_FLAGS:
                    continue
                if flag not in argv:
                    continue
                if not str(text).startswith("必填"):
                    continue
                code, _facts = self._run(command, self._strip(argv, command, flag))
                if code == "WF_OK":
                    problems.append(f"{command} {flag}: 标为必填却可省略")
        self.assertFalse(problems, "; ".join(problems))

    def test_injection_is_exercised(self):
        """回归注入：把 `--evidence` 又标回可选，必须让断言变红（证明用例不空跑）。"""
        original = cli.COMMAND_HELP["task-retrospect"]["args"]["--evidence"]
        cli.COMMAND_HELP["task-retrospect"]["args"]["--evidence"] = "可选：复盘证据"
        try:
            argv = self._example("task-retrospect")
            self.assertIn("--evidence", argv)
            code, facts = self._run("task-retrospect", self._strip(argv, "task-retrospect", "--evidence"))
            self.assertEqual(code, "WF_USAGE_INVALID")
            self.assertIn("--evidence", facts)
        finally:
            cli.COMMAND_HELP["task-retrospect"]["args"]["--evidence"] = original


if __name__ == "__main__":
    unittest.main()


class DeadValueTest(unittest.TestCase):
    """"读入 ≠ 消费"的定向断言（2026-11-23 五轮复审 a-1 的盲区）。

    `ConsumptionTest` 只要求帮助登记的旗标被 handler **读取**（`args.value("--x")`）。
    但"读进来赋给一个变量、之后再也不看"同样会静默丢输入——`task-retrospect --decision`
    就是这样复发的（`decision = cli._load_decision(...)` 之后从未使用，帮助却承诺"并入记录"）。
    这里对**每个命令的真实实现**做一次赋值-未使用扫描：不求全库无死代码，只保证
    "命令实现里没有把值算出来就丢掉"的局部变量。
    """

    def test_no_dead_local_in_command_handlers(self):
        import ast
        import command_introspection as ci
        from wflib import cli

        problems = []
        for command in sorted(cli.COMMANDS):
            sources = ci.handler_sources(cli, command, ci.example_argv(cli, command))
            for text in sources:
                try:
                    tree = ast.parse(textwrap_dedent(text))
                except (SyntaxError, ValueError):
                    continue
                for node in ast.walk(tree):
                    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue
                    loads = {name.id for name in ast.walk(node)
                             if isinstance(name, ast.Name) and isinstance(name.ctx, ast.Load)}
                    for stmt in ast.walk(node):
                        if not isinstance(stmt, ast.Assign):
                            continue
                        for target in stmt.targets:
                            if (isinstance(target, ast.Name) and not target.id.startswith("_")
                                    and target.id not in loads):
                                problems.append(f"{command}:{node.name} 局部值 {target.id} "
                                                f"(line {stmt.lineno}) 赋值后从未使用")
        self.assertFalse(problems, "; ".join(sorted(set(problems))))


class HelpAliasTest(unittest.TestCase):
    """`--help`/`-h` 是首次接触入口的通用写法：不得落进 `unknown subcommand`。

    dogfood 会话 4 实录：AI 第一条命令就是 `wf.py --help`，得到用法错误后才改用
    `wf.py help`——多一次失败试错，且错误出口把 `--help` 写成"未知子命令"。
    """

    def test_help_flags_alias_the_help_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = cli.Context(tmp, [])
            for flag in ("--help", "-h"):
                with self.subTest(flag=flag):
                    payload = cli.dispatch(ctx, [flag])
                    self.assertEqual(payload["code"], "WF_OK")
                    self.assertIn("status", payload["facts"]["commands"])
            payload = cli.dispatch(ctx, ["--help", "task-check"])
            self.assertEqual(payload["facts"]["command"], "task-check")


def textwrap_dedent(text):
    import textwrap

    return textwrap.dedent(text)

