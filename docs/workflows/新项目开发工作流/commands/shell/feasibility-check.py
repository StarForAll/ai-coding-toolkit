#!/usr/bin/env python3
"""Generate compliance prompts and a structured feasibility assessment template.

用法:
  python3 feasibility-check.py --step compliance    # 合规性审查清单
  python3 feasibility-check.py --step estimate      # 生成评估模板
"""
from __future__ import annotations

import argparse
from pathlib import Path


def step_compliance() -> None:
    print("=== 合规性审查清单 ===")
    print("□ 项目领域是否受法律法规限制？")
    print("□ 是否涉及数据隐私/跨境传输（GDPR、个保法）？")
    print("□ 是否涉及金融、医疗、教育等强监管行业？")
    print("□ 是否涉及知识产权风险（竞业、专利、开源许可证）？")
    print()
    print("提示：如发现不合规，应立即终止项目。")


TEMPLATE = """# 项目可行性评估

## 概览
- 总体决策：接 / 谈判后接 / 暂停 / 拒绝
- 是否可做：
- 是否值得做：
- 如何做更稳：
- 是否允许进入 brainstorm：是 / 否
- 当前结论的前提：

## 需求摘要
- 核心目标：
- 目标用户：
- 核心功能（≤3）：
- 技术约束：
- 时间窗口：

## 红线与关键信号
- 合规红线：
- 付款 / 验收 / 范围风险：
- AI / LLM 特有风险（如适用）：

## 关键风险 Top 5
| 风险 | 类型 | 级别 | 应对 |
|------|------|------|------|

## 成本估算
- 人力成本：
- AI 成本：
- 总成本区间：

## 必须谈判条件
- 条件 1：
- 条件 2：

## 最小补充信息集
- 缺口 1：
- 缺口 2：

## 下一步建议
- 若允许进入 brainstorm：带着哪些边界与假设继续
- 若不允许：补信息 / 谈判 / 终止
"""


def step_estimate(task_dir: Path) -> None:
    task_dir.mkdir(parents=True, exist_ok=True)
    assessment = task_dir / "assessment.md"
    if assessment.exists():
        print("当前 assessment.md 内容：")
        print(assessment.read_text(encoding="utf-8"))
    else:
        assessment.write_text(TEMPLATE, encoding="utf-8")
        print(f"已创建 {assessment} 模板")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="可行性评估辅助")
    parser.add_argument("--step", default="compliance", choices=["compliance", "estimate"])
    parser.add_argument("--task-dir", type=Path, default=Path("."))
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.step == "compliance":
        step_compliance()
        return 0
    if args.step == "estimate":
        step_estimate(args.task_dir)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
