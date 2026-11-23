#!/usr/bin/env python3
"""断言卫生扫描（十三轮 b-P0 的批次纪律）：测试里的"恒真断言"不得再靠下一轮审查发现。

已发生过两次同型事故（帮助契约对委托型命令空跑、派生矩阵里的 `assertEqual(x, x)`），
所以把它机械化：AST 层扫 `self.assertX(<表达式>, <同一表达式>)` 这一类自比较，
以及 `assertTrue(True)` / `assertFalse(False)` / `assertEqual(x, x)` 的常量同义形态。

误报边界写死在这里：只认**字面同构 + 纯表达式**（两侧 dump 完全一致，且表达式里没有
函数/方法调用）。`assertEqual(x + 1, x + 1)` 会被抓；`assertEqual(self.key(), self.key())`
不会——那是"同一输入两次调用结果相同"的**稳定性断言**，语义正当。
"""
import ast
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
# 覆盖全部 wf 测试树：scripts/tests/ 根（发行链/构建链）+ wf_runtime/ + wf_review/。
# 只扫"自己刚写的目录"会让同类恒真断言在范围外重生（十四轮 b-P1）。
TESTS_ROOT = os.path.dirname(HERE)
ROOTS = (TESTS_ROOT,)
TRIVIAL = {"True", "False", "None", "0", "1", "''", '""'}


def _dump(node):
    try:
        return ast.dump(node, annotate_fields=False)
    except TypeError:      # pragma: no cover - 老解释器
        return ast.dump(node)


def tautologies(path):
    try:
        with open(path, encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
    except SyntaxError:     # pragma: no cover - 语法错误由别的检查负责
        return []
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        name = node.func.attr
        args = node.args
        if name in ("assertTrue", "assertFalse", "assertIsNone", "assertIsNotNone") and len(args) == 1:
            literal = _dump(args[0])
            if name in ("assertTrue", "assertFalse") and literal in {"Constant(True)",
                                                                    "Constant(False)"}:
                found.append((node.lineno, f"{name} 常量恒真"))
            continue
        if name in ("assertEqual", "assertNotEqual", "assertIs", "assertIsNot") and len(args) >= 2:
            left, right = _dump(args[0]), _dump(args[1])
            if left != right:
                continue
            if left in {"Constant(True)", "Constant(False)", "Constant(None)"}:
                found.append((node.lineno, f"{name} 常量自比较"))
                continue
            if isinstance(args[0], ast.Name):
                continue        # assertEqual(x, x)：名字重复多是笔误但误报率高，放过
            # 含调用/属性/下标就可能"每次取值不同"（稳定性断言、属性计算、缓存对象），不判恒真
            if any(isinstance(item, (ast.Call, ast.Attribute, ast.Subscript))
                   for item in ast.walk(args[0])):
                continue
            found.append((node.lineno, f"{name} 两侧为同一纯表达式"))
    return found


class AssertionHygieneTest(unittest.TestCase):
    def test_no_tautological_assertions_in_test_tree(self):
        offenders = []
        for root in ROOTS:
            for base, _dirs, files in os.walk(root):
                if "__pycache__" in base:
                    continue
                lowered = base.lower()
                if any(part in lowered for part in ("fixtures", "fixture", "tmp")):
                    continue
                for name in sorted(files):
                    if not name.endswith(".py"):
                        continue
                    path = os.path.join(base, name)
                    if path == os.path.abspath(__file__):
                        continue
                    for line, reason in tautologies(path):
                        offenders.append(f"{os.path.relpath(path, HERE)}:{line}: {reason}")
        self.assertFalse(offenders, "\n".join(offenders[:20]))

    def test_scanner_catches_the_known_pattern(self):
        """扫描器自身要有用：喂一段恒真断言必须报出来（否则它也是"空转的测试"）。"""
        import tempfile

        source = (
            "import unittest\n"
            "class T(unittest.TestCase):\n"
            "    def test_x(self):\n"
            "        self.assertEqual(1 + 1, 1 + 1)\n"
            "        self.assertTrue(True)\n"
            "        value = 1\n"
            "        self.assertEqual(value, value)\n"
        )
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as handle:
            handle.write(source)
            path = handle.name
        try:
            found = tautologies(path)
        finally:
            os.unlink(path)
        self.assertTrue(any("两侧为同一纯表达式" in reason for _line, reason in found))
        self.assertTrue(any("常量恒真" in reason for _line, reason in found))


if __name__ == "__main__":
    unittest.main()
