"""repro 公开 CLI（`full/repro/cli.py` + `run.sh` 消费）：终止性、兼容保真与零副作用。

父任务 R4 / AC11–AC12 的公开解析部分：
- 每个有值选项缺值、空值、后继选项冒充取值都确定非零，且不留下 scope/结果/缓存/state；
- 合法重复 `--group` 保留全部取值，标量选项沿用最后一次，含空格/引号的路径原样保真；
- `--list`/`--help` 仍是纯选择面，非法组合在取锁/布局前拒绝；
- 内部 frame 仍由 runner_protocol 先剥离，公开 parser 看不到保留选项。
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
REPRO = REPO / "scripts" / "tests" / "wf_runtime" / "full" / "repro"
RUN = REPRO / "run.sh"
CLI = REPRO / "cli.py"
PY = sys.executable

VALUED_OPTIONS = ("--mode", "--group", "--only", "--jobs", "--fixture-deploy",
                  "--release-root", "--release-ref", "--release-version",
                  "--release-meta", "--results-dir")
SCALARS = ("MODE", "ONLY", "JOBS", "BUILD", "DEPLOY", "RELEASE_ROOT", "RELEASE_REF",
           "RELEASE_VERSION", "RELEASE_META", "RESULTS", "LIST", "HELP")


def clean_env(root):
    """剥掉宿主 runner 定位与故障变量，只留本用例自己的隔离根。"""
    env = {key: value for key, value in os.environ.items() if not key.startswith("WF_")}
    env["TMPDIR"] = root
    env["HOME"] = root
    return env


def parse_direct(args, env=None):
    """直接调用唯一 parser，返回 (rc, stdout, stderr)。"""
    merged = {key: value for key, value in os.environ.items() if not key.startswith("WF_")}
    merged.update(env or {})
    return subprocess.run([PY, str(CLI), *args], cwd=str(REPO), env=merged,
                          capture_output=True, text=True, timeout=60)


def eval_assignments(text):
    """在干净 bash 里 eval parser 输出，返回标量字典与 GROUP_NAMES 数组。"""
    script = text + "\n"
    for name in SCALARS:
        script += 'printf "%s\\n" "${' + name + '}"\n'
    script += 'for item in "${GROUP_NAMES[@]}"; do printf "GROUP:%s\\n" "$item"; done\n'
    result = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    lines = result.stdout.splitlines()
    values = dict(zip(SCALARS, lines[:len(SCALARS)]))
    values["GROUP_NAMES"] = [line[len("GROUP:"):] for line in lines[len(SCALARS):]
                             if line.startswith("GROUP:")]
    return values


class RejectionTest(unittest.TestCase):
    """非法公开参数：rc=2，且在租约/layout/scope/cache/build 之前退出（零写入）。"""

    def assert_rejected(self, args):
        with tempfile.TemporaryDirectory(prefix="wf-repro-cli-reject-") as root:
            result = subprocess.run(["bash", str(RUN), *args], cwd=str(REPO),
                                    env=clean_env(root), capture_output=True, text=True,
                                    timeout=120)
            self.assertEqual(result.returncode, 2,
                             f"{args} 必须非零；stdout={result.stdout} stderr={result.stderr}")
            self.assertEqual(sorted(os.listdir(root)), [],
                             f"{args} 不得在解析阶段留下任何文件（scope/结果/缓存/state）")

    def test_every_valued_option_requires_a_value(self):
        for option in VALUED_OPTIONS:
            with self.subTest(option=option, case="missing"):
                self.assert_rejected([option])

    def test_every_valued_option_rejects_empty_value(self):
        for option in VALUED_OPTIONS:
            with self.subTest(option=option, case="empty"):
                self.assert_rejected([option, ""])

    def test_every_valued_option_rejects_next_option_as_value(self):
        for option in VALUED_OPTIONS:
            with self.subTest(option=option, case="next-option"):
                self.assert_rejected([option, "--mode", "green"])

    def test_explicit_equals_form_rejects_empty_or_dash_value(self):
        self.assert_rejected(["--mode="])
        self.assert_rejected(["--only=-x"])
        self.assert_rejected(["--results-dir=-"])

    def test_unknown_and_invalid_values_are_rejected(self):
        self.assert_rejected(["--bogus"])
        self.assert_rejected(["--mode", "slow"])
        self.assert_rejected(["--jobs", "0"])
        self.assert_rejected(["--jobs", "many"])
        self.assert_rejected(["--fixture-deploy", "zip"])
        self.assert_rejected(["--group", "review", "--bogus"])

    def test_list_cannot_be_combined_with_mode(self):
        # --list 曾是“最后出现的 --mode 覆盖它”的顺序敏感写法；现按纯选择面拒绝。
        self.assert_rejected(["--list", "--mode", "green"])
        self.assert_rejected(["--mode", "green", "--list"])

    def test_candidate_preconditions_fail_before_any_write(self):
        self.assert_rejected(["--fixture-deploy", "candidate"])
        self.assert_rejected(["--fixture-deploy", "candidate", "--release-root", "/tmp/x",
                              "--release-ref", "refs/tags/wf-v0.1.0",
                              "--release-version", "0.1.0", "--mode", "red"])

    def test_internal_frame_options_never_reach_the_public_parser(self):
        self.assert_rejected(["--_wf-internal", "lease"])
        self.assert_rejected(["--mode", "green", "--_wf-inherited-release"])


class CompatibilityTest(unittest.TestCase):
    """合法公开参数的保真：默认值、重复项、最后值、含空格/引号路径、help/list 置位。"""

    def test_defaults_match_the_shell_contract(self):
        result = parse_direct([])
        self.assertEqual(result.returncode, 0, result.stderr)
        values = eval_assignments(result.stdout)
        self.assertEqual(values["MODE"], "both")
        self.assertEqual(values["DEPLOY"], "dev")
        self.assertEqual(values["JOBS"], "1")
        self.assertEqual(values["BUILD"], "1")
        self.assertEqual(values["LIST"], "0")
        self.assertEqual(values["HELP"], "0")
        self.assertEqual(values["ONLY"], "")
        self.assertEqual(values["GROUP_NAMES"], [])

    def test_environment_defaults_are_preserved_and_explicit_wins(self):
        env = {"WF_REPRO_JOBS": "3", "WF_FIXTURE_DEPLOY": "candidate",
               "WF_RELEASE_ROOT": "/tmp/root", "WF_RELEASE_REF": "refs/tags/wf-v0.1.0",
               "WF_RELEASE_VERSION": "0.1.0", "WF_REPRO_RESULTS": "/tmp/results"}
        values = eval_assignments(parse_direct([], env=env).stdout)
        self.assertEqual((values["JOBS"], values["DEPLOY"]), ("3", "candidate"))
        self.assertEqual((values["RELEASE_ROOT"], values["RELEASE_REF"],
                          values["RELEASE_VERSION"], values["RESULTS"]),
                         ("/tmp/root", "refs/tags/wf-v0.1.0", "0.1.0", "/tmp/results"))
        values = eval_assignments(parse_direct(["--jobs", "5", "--release-root", "/tmp/explicit"],
                                               env=env).stdout)
        self.assertEqual((values["JOBS"], values["RELEASE_ROOT"]), ("5", "/tmp/explicit"))

    def test_empty_environment_values_fall_back(self):
        values = eval_assignments(parse_direct([], env={"WF_REPRO_JOBS": "",
                                                        "WF_FIXTURE_DEPLOY": "",
                                                        "WF_REPRO_RESULTS": ""}).stdout)
        self.assertEqual((values["JOBS"], values["DEPLOY"], values["RESULTS"]), ("1", "dev", ""))

    def test_repeated_group_preserves_order_and_scalars_take_the_last_value(self):
        values = eval_assignments(parse_direct(
            ["--group", "review", "--group", "executor", "--mode", "green",
             "--mode", "red", "--only", "r1", "--only", "r2"]).stdout)
        self.assertEqual(values["GROUP_NAMES"], ["review", "executor"])
        self.assertEqual((values["MODE"], values["ONLY"]), ("red", "r2"))

    def test_paths_with_spaces_and_quotes_round_trip(self):
        odd = "/tmp/a b/it's-here"
        values = eval_assignments(parse_direct(["--results-dir", odd, "--group", odd]).stdout)
        self.assertEqual(values["RESULTS"], odd)
        self.assertEqual(values["GROUP_NAMES"], [odd])

    def test_help_and_list_are_flags_not_modes(self):
        help_values = eval_assignments(parse_direct(["--help"]).stdout)
        self.assertEqual(help_values["HELP"], "1")
        self.assertEqual(help_values["LIST"], "0")
        list_values = eval_assignments(parse_direct(["--list"]).stdout)
        self.assertEqual(list_values["LIST"], "1")
        self.assertEqual(list_values["MODE"], "both")

    def test_help_short_form_is_accepted(self):
        self.assertEqual(parse_direct(["-h"]).returncode, 0)
        result = subprocess.run(["bash", str(RUN), "--help"], cwd=str(REPO),
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0)
        self.assertIn("--list", result.stdout)
        self.assertIn("--fixture-deploy", result.stdout)


class HelperRegistrationTest(unittest.TestCase):
    """新公共 helper 必须进入证明身份与假树清单（否则旧证明会冒充新行为）。"""

    def test_cli_parser_is_a_proof_input_and_fake_tree_member(self):
        import importlib.util

        def load(name, path):
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module

        repro_select = load("wf_repro_select_cli", REPRO / "repro_select.py")
        plan = load("wf_plan_cli", REPRO.parent / "plan.py")
        self.assertIn("cli.py", repro_select.HELPERS)
        self.assertIn("cli.py", repro_select.RUNNER_FILES)
        self.assertIn("repro/cli.py", plan.FAKE_TREE_COPY)
        self.assertTrue(CLI.is_file())


if __name__ == "__main__":
    unittest.main()
