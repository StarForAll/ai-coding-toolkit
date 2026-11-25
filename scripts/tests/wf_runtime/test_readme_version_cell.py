"""README「目标版本」单元必须保持可读，轮次流水沉淀到独立文件（2026-11-25）。

上一轮把六~八轮与第四轮叙述迁到 `analysis/round-history.md` 后，README 单元从 2288 字符
收到 789 字符；但该收敛只写在文档头里，没有机械护栏——下一轮很容易又堆回去。
这里锁两件可稳定计算的事：单元长度上限、迁移文件存在且被单元链接。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
README = REPO / "docs" / "workflows" / "wf" / "README.md"
HISTORY = REPO / "docs" / "workflows" / "wf" / "analysis" / "round-history.md"
MAX_CELL = 1400


class ReadmeVersionCellTest(unittest.TestCase):
    def cell(self):
        for line in README.read_text(encoding="utf-8").splitlines():
            if line.startswith("| 目标版本 |"):
                return line
        self.fail("README 缺少机器可读的目标版本行")

    def test_cell_stays_short(self):
        self.assertLessEqual(len(self.cell()), MAX_CELL,
                             "目标版本单元又变成长流水账：把轮次叙述追加到 analysis/round-history.md")

    def test_round_history_is_linked_and_exists(self):
        self.assertIn("analysis/round-history.md", self.cell())
        self.assertTrue(HISTORY.is_file())
        # 迁移文件自己也不该反向变薄：至少保留迁出时的两段轮次叙述
        text = HISTORY.read_text(encoding="utf-8")
        self.assertIn("dogfood 六~八轮", text)
        self.assertIn("第四轮独立复审", text)


if __name__ == "__main__":
    unittest.main()
