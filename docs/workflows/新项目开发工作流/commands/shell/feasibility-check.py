#!/usr/bin/env python3
"""可行性评估辅助脚本。

用法:
  python3 feasibility-check.py --step compliance    # 合规性审查清单
  python3 feasibility-check.py --step estimate      # 生成评估模板
"""
import argparse
import sys
from pathlib import Path


def step_compliance():
    print("=== 合规性审查清单 ===")
    print("□ 项目领域是否受法律法规限制？")
    print("□ 是否涉及数据隐私/跨境传输（GDPR、个保法）？")
    print("□ 是否涉及金融、医疗、教育等强监管行业？")
    print("□ 是否涉及知识产权风险（竞业、专利、开源许可证）？")
    print()
    print("提示：如发现不合规，应立即终止项目。")


TEMPLATE = """# 项目可行性评估

## 需求摘要
- 核心目标：
- 目标用户：
- 核心功能：
- 技术约束：
- 时间窗口：

## 工作量评估
| 模块 | 开发 | 评审 | 测试 | 文档 | 小计 |
|------|------|------|------|------|------|

## 风险评估
| 类型 | 描述 | 级别 | 应对 |
|------|------|------|------|

## 成本估算
- 人力成本：
- AI 成本：
- 总成本区间：

## 报价方案
- 基础版范围：
- 变更单价规则：
- 交付 SLO 草案：
"""


def step_estimate(task_dir: Path):
    assessment = task_dir / "assessment.md"
    if assessment.exists():
        print("当前 assessment.md 内容：")
        print(assessment.read_text(encoding="utf-8"))
    else:
        assessment.write_text(TEMPLATE, encoding="utf-8")
        print(f"已创建 {assessment} 模板")


def main():
    parser = argparse.ArgumentParser(description="可行性评估辅助")
    parser.add_argument("--step", default="compliance", choices=["compliance", "estimate"])
    parser.add_argument("--task-dir", type=Path, default=Path("."))
    args = parser.parse_args()

    if args.step == "compliance":
        step_compliance()
    elif args.step == "estimate":
        step_estimate(args.task_dir)


if __name__ == "__main__":
    main()
