"""v42 P0 的 6 条常驻不变量（v42 §6「不变量检查」）。

每条测试都回答「它防的失败实际发生过、或可具体推演吗」——元规则见 v42 §6。
6 条全绿表示：状态可达、出口完备、next 单一来源、投影等值、文档与 protocol 不分叉、
脱敏只增不减。它们**不**判断业务正确性。
"""

from __future__ import annotations

import glob
import importlib.util
import inspect
import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SOURCE_ROOT = os.path.join(ROOT, "docs", "workflows", "wf")
PAYLOAD = os.path.join(SOURCE_ROOT, "payload")
LIB = os.path.join(PAYLOAD, "lib")
PROTOCOL_DIR = os.path.join(PAYLOAD, "protocol")

# 非原因码的 `WF_*` 字面量：环境变量与模板占位标记（机制稿 §2.3 的 `{{WF_REQUIRED:<field>}}`）。
NON_CODE_TOKENS = frozenset({"WF_DEBUG", "WF_PROJECT_ROOT", "WF_REQUIRED", "WF_REQUIRED__"})


def _load_script(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "scripts", filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProtocolInvariantTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import sys

        if LIB not in sys.path:
            sys.path.insert(0, LIB)
        from wflib import cli, codes, config, protocol

        cls.cli = cli
        cls.codes = codes
        cls.config = config
        cls.protocol = protocol
        cls.states = protocol.states()

    # -- ① 可达性 ---------------------------------------------------------
    def test_every_reachable_position_has_a_path_to_terminal(self):
        """死路检测（G3）：dogfood 里「两轮用尽」就是没有终态路径的状态。

        没有这条，任何新增转移都可能造出一个只能靠现场发明命令（review-restart 之类）
        才能离开的位置。
        """
        terminal_status = self.states.terminal["status"]
        legal = self.states.legal_positions

        def nodes_of(position):
            status = position.get("status")
            if "phase" in position:
                return [(status, position["phase"])]
            phases = legal.get(status) or []
            return [(status, phase) for phase in phases] or [(status, None)]

        edges = {}
        terminals = set()
        initial = (self.states.status_initial, self.states.phase_initial)
        for entry in self.states.transitions:
            sources = [node for position in entry.get("from") or [] for node in nodes_of(position)]
            targets = [node for position in entry.get("to") or [] for node in nodes_of(position)]
            for position in entry.get("to") or []:
                if position.get("status") == terminal_status and "phase" not in position:
                    terminals.add((terminal_status, None))
            if not entry.get("to"):
                targets = sources  # keeps_position：位置不变
            for source in sources:
                edges.setdefault(source, set()).update(targets)

        reachable = {initial}
        frontier = [initial]
        while frontier:
            current = frontier.pop()
            for target in edges.get(current, ()):
                if target not in reachable:
                    reachable.add(target)
                    frontier.append(target)

        self.assertTrue(terminals, "protocol/states.json 没有可达的终态位置")

        def can_reach_terminal(start):
            seen = {start}
            stack = [start]
            while stack:
                current = stack.pop()
                if current in terminals:
                    return True
                for target in edges.get(current, ()):
                    if target not in seen:
                        seen.add(target)
                        stack.append(target)
            return False

        stuck = sorted(node for node in reachable if not can_reach_terminal(node))
        self.assertEqual(stuck, [], f"这些位置没有通往终态的路径：{stuck}")

    # -- ② 出口完备 -------------------------------------------------------
    def test_every_gate_error_has_an_executable_exit(self):
        """出口完备（B5「缺报告报错含糊」）：每个阻断都必须给下一步，且码值不得口头新增。

        没有这条，代码里可以随手写一个未登记的 `WF_*`，输出与码表不一致按机制稿
        §1.5 只能判阻断，而人拿不到出口。
        """
        for name, (tier, exit_text, prohibited) in self.codes.CODES.items():
            self.assertTrue(exit_text.strip(), f"{name} 缺 exit")
            if tier != "pass":
                self.assertTrue((prohibited or "").strip(), f"{name} 缺 prohibited_repairs")
        unknown = []
        for path in sorted(glob.glob(os.path.join(LIB, "wflib", "*.py"))):
            with open(path, "r", encoding="utf-8") as handle:
                body = handle.read()
            for token in set(re.findall(r"WF_[A-Z_]+", body)):
                if token in NON_CODE_TOKENS or token in self.codes.CODES:
                    continue
                unknown.append(f"{os.path.basename(path)}:{token}")
        self.assertEqual(unknown, [], f"出现未登记的原因码：{sorted(unknown)}")

    # -- ③ status.next 与真实错误码一致 -----------------------------------
    def test_status_next_comes_from_protocol_and_names_real_commands(self):
        """`next` 单一来源（B7「协议四处漂移」+ D3「人当传声筒」）。

        dogfood 里同一句「下一步」在 help/SKILL/实现里各写一份并互相矛盾；
        这里锁两件事：表里的每个 next 都指向真实命令，且 `cmd_status` 不再自带字面量。
        """
        table = dict(self.states.next_by_position)
        table.update(self.states.next_by_mark)
        for key, text in table.items():
            named = re.findall(r"wf ([a-z][a-z0-9-]*)", text)
            self.assertTrue(named, f"{key} 的 next 没有点名任何 wf 命令：{text}")
            for command in named:
                self.assertIn(command, self.cli.COMMANDS, f"{key} 的 next 指向不存在的命令：{command}")

        for status in self.states.status_enum:
            for phase in self.states.phase_enum:
                expected = self.states.next_by_position.get(f"{status}/{phase}")
                actual = self.states.next_for(status, phase)
                if expected is not None:
                    self.assertEqual(actual, expected, f"next_for({status},{phase}) 未按表取值")
                else:
                    self.assertTrue(actual)

        source = inspect.getsource(self.cli.cmd_status)
        self.assertIsNone(
            re.search(r"next_=\s*[\"']", source),
            "cmd_status 里仍有手写的 next 字面量：next 必须来自 protocol.states().next_for()",
        )

    # -- ④ 投影/骨架重建等值 ----------------------------------------------
    def test_protocol_projections_are_equal(self):
        """投影等值（F3「同一事实两处存」）：码表与阈值只能有一份，Python 侧是纯投影。

        P0 覆盖 `codes`/`thresholds` 两组投影；`open-items`/`attribution`/判断骨架的
        等值断言要等 P5 的投影落地（此处不编造夹具）。
        """
        from wflib import protocol as protocol_mod

        self.assertEqual(self.codes.CODES, protocol_mod.codes())

        expected_defaults = protocol_mod.threshold_defaults()
        expected_defaults.pop("schema_version", None)
        self.assertEqual(self.config.DEFAULTS, expected_defaults)
        self.assertEqual(self.config.KNOWN_KEYS, set(protocol_mod.thresholds()))

        for filename, keys in (("codes.py", None), ("config.py", tuple(protocol_mod.thresholds()))):
            with open(os.path.join(LIB, "wflib", filename), "r", encoding="utf-8") as handle:
                body = handle.read()
            if keys is None:
                self.assertEqual(re.findall(r"WF_[A-Z_]+", body), [], f"{filename} 仍手写原因码")
                continue
            for key in keys:
                self.assertIsNone(
                    re.search(rf'"{key}"\s*:\s*[0-9]', body),
                    f"{filename} 仍手写阈值缺省数值：{key}",
                )
                self.assertIsNone(
                    re.search(rf'"{key}"\s*:\s*(true|false)\b', body),
                    f"{filename} 仍手写阈值缺省布尔值：{key}",
                )

    def test_deleted_caps_do_not_come_back(self):
        """v42 §7.1「删了不漏」：轮次额度与三类 cap 阈值已删除，不得以配置键形式回流。

        dogfood 的死路正是这些 cap 造成的（两轮上限、扩面上限）；它们回流会让
        「判断归 AI」重新变成许可制，而 §7.1 已认定覆盖者是收敛谓词与判断清单。
        """
        from wflib import protocol as protocol_mod

        with open(os.path.join(PROTOCOL_DIR, "thresholds.json"), encoding="utf-8") as stream:
            payload = json.load(stream)
        forbidden = set((payload.get("not_thresholds") or {}).get("forbidden_cap_names") or ())
        self.assertTrue(forbidden, "thresholds.json 必须登记禁止回流的 cap 名")
        self.assertEqual(forbidden & set(protocol_mod.thresholds()), set(), "禁止的 cap 名出现在阈值键里")
        with open(os.path.join(LIB, "wflib", "config.py"), encoding="utf-8") as stream:
            body = stream.read()
        for name in forbidden:
            self.assertNotIn(name, body, f"config.py 仍出现已删除的 cap：{name}")

    # -- ⑤ 文档机器事实与 protocol 一致 -----------------------------------
    def test_doctrine_machine_facts_match_protocol(self):
        """跨文档一致性（B7/G2）：机制稿 §2.2/§8.1/§11.1 与设计稿 §1.3/§4.1 的机器事实
        必须与 `protocol/` 相同，否则「文档说的」和「代码做的」会像 dogfood 那样分叉。
        """
        checker = _load_script("wf_protocol_docs", "wf-protocol-docs.py")
        problems = checker.check(verbose=False)
        self.assertEqual(problems, [], f"上位文档与 protocol 漂移：{problems}")

    # -- ⑥ 脱敏规则只增不减 -----------------------------------------------
    def test_redaction_rules_only_tighten(self):
        """单向不变量（v36/S7）：脱敏只能加严。基线被删一条或收窄一项即判红。

        脱敏放松会同时造成泄露与无法复算，因此不许作为普通配置修改；这条测试把
        「放松」变成一次显式的基线改写（须人审），而不是悄悄改掉一条规则。
        """
        from wflib import protocol as protocol_mod

        # 走加载器而不是直接读盘：加载器自身就是「direction 必须严格加严」的把关处。
        current = protocol_mod.redaction()
        with open(os.path.join(PROTOCOL_DIR, "redaction.baseline.json"), "r", encoding="utf-8") as handle:
            baseline = json.load(handle)

        self.assertEqual(current.get("direction"), "strictly-tighten")
        self.assertEqual(baseline.get("direction"), "strictly-tighten")
        current_rules = {rule["id"]: rule for rule in current["rules"]}
        for rule in baseline["rules"]:
            live = current_rules.get(rule["id"])
            self.assertIsNotNone(live, f"脱敏规则被删除：{rule['id']}")
            self.assertEqual(live.get("effect"), rule.get("effect"), f"脱敏规则作用被改写：{rule['id']}")
            missing = set(rule.get("items") or ()) - set(live.get("items") or ())
            self.assertEqual(missing, set(), f"脱敏规则被收窄：{rule['id']} 少了 {sorted(missing)}")


if __name__ == "__main__":
    unittest.main()


class SkeletonTemplateParityTest(unittest.TestCase):
    """2026-11-21（dogfood 二轮 AC9）：发行模板键集 == config.skeleton() 键集。

    模板是手维护静态文件、无生成器，此前无一致性断言（identity_path 曾漂移）。
    """

    def test_template_keys_equal_skeleton_keys(self):
        import json
        from pathlib import Path

        repo = Path(__file__).resolve().parents[3]
        template_path = repo / "docs" / "workflows" / "wf" / "payload" / "templates" / "project-config.skeleton.json"
        template = json.loads(template_path.read_text(encoding="utf-8"))
        from wflib import config as _config

        skeleton = _config.skeleton()
        self.assertEqual(set(template), set(skeleton),
                         f"模板与 skeleton() 键集漂移：{set(template) ^ set(skeleton)}")
