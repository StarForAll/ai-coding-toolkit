#!/usr/bin/env python3
"""Generate compliance prompts and a structured feasibility assessment template.

用法:
  python3 feasibility-check.py --step compliance    # 合规性审查清单
  python3 feasibility-check.py --step estimate      # 生成评估模板
  python3 feasibility-check.py --step risk-analysis # 风险分析（demand-risk-assessment skill 集成）
  python3 feasibility-check.py --step risk-analysis --requirement-file <path> # 从文件读取需求
  python3 feasibility-check.py --step validate --task-dir <path>  # 验证 assessment.md 双轨字段完整性
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


VALID_ENGAGEMENT_TYPES = {"external_outsourcing", "non_outsourcing"}
VALID_EXTERNAL_TRACKS = {"hosted_deployment", "trial_authorization"}
VALID_BOOLEAN_VALUES = {"yes", "no"}
MIN_KICKOFF_PAYMENT_RATIO = 30.0


def extract_backticked_field(content: str, field_name: str) -> str | None:
    match = re.search(rf'`{re.escape(field_name)}`:\s*`?(.+?)`?(?:\n|$)', content)
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def parse_kickoff_payment_ratio(raw_value: str) -> tuple[bool, str]:
    percentages = [float(value) for value in re.findall(r"(\d+(?:\.\d+)?)\s*%", raw_value)]
    if not percentages:
        return False, "未识别到百分比"
    if min(percentages) < MIN_KICKOFF_PAYMENT_RATIO:
        return False, f"启动款比例至少应为 {int(MIN_KICKOFF_PAYMENT_RATIO)}%"
    return True, ", ".join(f"{value:g}%" for value in percentages)


def step_compliance() -> None:
    print("=== 法律与合规风险初筛清单 ===")
    print("□ 项目领域是否受法律法规限制？")
    print("□ 是否涉及数据隐私/跨境传输（GDPR、个保法）？")
    print("□ 是否涉及金融、医疗、教育等强监管行业？")
    print("□ 是否涉及知识产权风险（竞业、专利、开源许可证）？")
    print("□ 是否存在明显违法用途、灰产用途或不可接受的合规红线？")
    print()
    print("提示：本清单是 feasibility 阶段的起始硬门禁；如发现不合规，应立即终止项目。")


ASSESSMENT_TEMPLATE = """# 项目可行性评估

## 概览
- 总体决策：接 / 谈判后接 / 暂停 / 拒绝
- 是否可做：
- 是否值得做：
- 如何做更稳：
- 法律/合规风险结论：通过 / 不通过 / 待补充
- 是否允许进入 brainstorm：是 / 否
- `project_engagement_type`: `external_outsourcing` / `non_outsourcing`
- `kickoff_payment_ratio`: 例如 `30%` / `40%`（仅当 `project_engagement_type = external_outsourcing`）
- `kickoff_payment_received`: `yes` / `no`（仅当 `project_engagement_type = external_outsourcing`）
- `delivery_control_track`: `hosted_deployment` / `trial_authorization`（仅当 `project_engagement_type = external_outsourcing`）
- `delivery_control_handover_trigger`: 例如 `final_payment_received`（仅当 `project_engagement_type = external_outsourcing`）
- `delivery_control_retained_scope`: 尾款前仍由开发者保留的环境、账号、密钥、部署控制范围；若无则写 `none`（仅当 `project_engagement_type = external_outsourcing`）
- 项目类别判定：外包项目 / 非外包项目
- 交付控制轨道：托管部署 / 试运行授权 / 未确定
- 当前结论的前提：
- 场景标签：
- 总体置信度：高/中/低
- 信息充分性：X/8
- 承诺门：G0/G1/G2/G3

## 关键字段快照
| 关键字段 | 状态(明确/暗示/缺失/冲突) | 证据锚点 | 关键假设/缺口备注 |
|----------|---------------------------|----------|------------------|
| 范围边界 | ... | ... | ... |
| 项目类别判定 | ... | ... | ... |
| 交付物清单 | ... | ... | ... |
| 验收口径 | ... | ... | ... |
| 付款结构 | ... | ... | ... |
| 工期/里程碑 | ... | ... | ... |
| 源码移交时点 | ... | ... | ... |
| 管理员权限/密钥移交时点 | ... | ... | ... |
| 托管部署或试运行授权方案 | ... | ... | ... |
| 授权到期行为/永久授权触发条件 | ... | ... | ... |
| 关键依赖 | ... | ... | ... |
| 数据合规要点 | ... | ... | ... |
| 决策/验收负责人 | ... | ... | ... |

## Trial Authorization Terms（仅当 `delivery_control_track = trial_authorization`）
- `trial_authorization_terms.validity`: ...
- `trial_authorization_terms.clock_source_or_usage_basis`: ...
- `trial_authorization_terms.expiration_behavior`: ...
- `trial_authorization_terms.renewal_policy`: ...
- `trial_authorization_terms.permanent_authorization_trigger`: ...

## 项目类别与控制字段速查
| 字段 | 最低要求 | 下游影响 |
|------|----------|----------|
| `project_engagement_type` | 所有项目必填；外包项目填 `external_outsourcing`，其余填 `non_outsourcing` | 决定是否启用外包项目商务与交付控制门禁 |
| `kickoff_payment_ratio` | 外包项目必填，且最低不少于 `30%` | 决定 implementation / test-first 的开工前提 |
| `kickoff_payment_received` | 外包项目必填，取值为 `yes` / `no` | 决定是否允许开工 |
| `delivery_control_track` | 外包项目必填，取值为 `hosted_deployment` / `trial_authorization` | 决定 design 阶段的交付治理 spec 选择 |
| `delivery_control_handover_trigger` | 外包项目必填，明确最终控制权移交触发条件 | 决定 plan / delivery 阶段何时允许最终移交 |
| `delivery_control_retained_scope` | 外包项目必填，写清尾款前保留的环境、账号、密钥、部署控制范围 | 决定 retained-control 交付边界 |
| `trial_authorization_terms.*` | 若走 `trial_authorization` 则不得留空 | 决定授权管理 spec、到期行为和永久授权切换门禁 |

## 红线检查
✅ 通过 / ❌ 不通过 / ⚠️ 信息不足需补充
- [检查项]: 通过/不通过/不足 - 证据锚点或缺口

## 踩坑信号扫描
- 命中: [话术/信号] - 证据锚点 - 影响

## 冲突检测
- 命中项: ...（证据锚点）
- 影响: ...

## 评分总览（如适用）
总分(base): XX/100 | 区间(best~worst): AA~BB/100

| 维度(权重) | 维度得分(0-5) | 贡献分(/100) | 置信度 | 证据/缺口/冲突 |
|------------|---------------|--------------|--------|----------------|
| 合规风险(30) | x | yy.y | ... | ... |
| 可交付性(20) | x | yy.y | ... | ... |
| 工期可行性(20) | x | yy.y | ... | ... |
| 价格与收益匹配(20) | x | yy.y | ... | ... |
| 协作与沟通风险(10) | x | yy.y | ... | ... |

## Pre-mortem：最可能的失败链路
1. ...
2. ...
3. ...

## 风险登记表
| 风险 | 影响类型 | 概率(1-5) | 影响(1-5) | 优先级(P*I) | 缓解动作 | Kill Criteria |
|------|----------|-----------|-----------|--------------|----------|--------------|
| ... | ... | ... | ... | ... | ... | ... |

## 必须谈判条件
- [ ] 条件 1（映射：失败链路/风险项）
- [ ] 条件 2

若项目采用双轨交付控制，上述条件至少应覆盖：

- [ ] 选择哪条交付控制轨道：托管部署 / 试运行授权
- [ ] 尾款比例、触发条件、逾期处理
- [ ] 源码仓库、源码包、管理员账号、密钥、生产权限的移交时点
- [ ] 若采用试运行授权：有效期、续期方式、到期行为、永久授权交付条件
- [ ] 若采用托管部署：演示/试运行环境的访问范围、SLO、数据责任边界

## 最小补充信息集
1. ...（关联维度/为什么会改结论）

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
        assessment.write_text(ASSESSMENT_TEMPLATE, encoding="utf-8")
        print(f"已创建 {assessment} 模板")


def step_validate(task_dir: Path) -> int:
    """验证 assessment.md 是否满足 feasibility 阶段的通用门禁与外部项目附加字段。"""
    print("=== Feasibility 门禁验证 ===")

    assessment = task_dir / "assessment.md"
    if not assessment.exists():
        print(f"❌ {assessment} 不存在")
        return 1

    content = assessment.read_text(encoding="utf-8")
    errors: list[str] = []
    warnings: list[str] = []

    decision_match = re.search(r'总体决策[：:]\s*(\S+)', content)
    if not decision_match:
        errors.append("缺少 `总体决策` 字段")
    else:
        decision_value = decision_match.group(1)
        valid_decisions = ["接", "谈判后接", "暂停", "拒绝"]
        if decision_value not in valid_decisions:
            errors.append(f"`总体决策` 值异常: {decision_value}")
        else:
            print(f"✅ `总体决策`: {decision_value}")

    legal_match = re.search(r'法律(?:/|与)?合规风险结论[：:]\s*(\S+)', content)
    if not legal_match:
        errors.append("缺少 `法律/合规风险结论` 字段")
    else:
        legal_value = legal_match.group(1)
        valid_legal = ["通过", "不通过", "待补充"]
        if legal_value not in valid_legal:
            errors.append(f"`法律/合规风险结论` 值异常: {legal_value}")
        else:
            print(f"✅ `法律/合规风险结论`: {legal_value}")

    brainstorm_match = re.search(r'是否允许进入 brainstorm[：:]\s*(\S+)', content)
    if not brainstorm_match:
        errors.append("未明确标注 `是否允许进入 brainstorm`")
    else:
        brainstorm_value = brainstorm_match.group(1)
        if brainstorm_value not in ["是", "否"]:
            errors.append(f"`是否允许进入 brainstorm` 值异常: {brainstorm_value}")
        else:
            print(f"✅ `是否允许进入 brainstorm`: {brainstorm_value}")

    redline_match = re.search(r'## 红线检查(?P<section>.*?)(?:\n## |\Z)', content, re.S)
    if not redline_match:
        errors.append("缺少 `## 红线检查` 章节")
    else:
        redline_section = redline_match.group("section")
        if "✅ 通过" in redline_section:
            print("✅ `红线检查`: 通过")
        elif "❌ 不通过" in redline_section:
            print("✅ `红线检查`: 不通过（已记录）")
        elif "⚠️ 信息不足需补充" in redline_section:
            print("✅ `红线检查`: 信息不足需补充（已记录）")
        else:
            errors.append("`## 红线检查` 章节未明确写出结论（✅/❌/⚠️）")

    engagement_type = extract_backticked_field(content, "project_engagement_type")
    if engagement_type is None:
        errors.append("缺少 `project_engagement_type` 字段")
        is_external_project = False
    elif engagement_type not in VALID_ENGAGEMENT_TYPES:
        errors.append(
            "`project_engagement_type` 值无效: "
            f"{engagement_type}，应为: {', '.join(sorted(VALID_ENGAGEMENT_TYPES))}"
        )
        is_external_project = False
    else:
        is_external_project = engagement_type == "external_outsourcing"
        print(f"✅ `project_engagement_type`: {engagement_type}")

    if not is_external_project:
        print("ℹ️ 项目类别判定为非外包项目（内部项目/自有项目）；继续使用通用 workflow 主链，不启用首/尾款控制门禁")
    else:
        print("检测到外包项目，开始验证开工款与交付控制字段...")

        kickoff_ratio = extract_backticked_field(content, "kickoff_payment_ratio")
        if kickoff_ratio is None:
            errors.append("缺少 `kickoff_payment_ratio` 字段")
        else:
            ratio_ok, ratio_message = parse_kickoff_payment_ratio(kickoff_ratio)
            if not ratio_ok:
                errors.append(f"`kickoff_payment_ratio` 无效: {ratio_message}")
            else:
                print(f"✅ `kickoff_payment_ratio`: {ratio_message}")

        kickoff_received = extract_backticked_field(content, "kickoff_payment_received")
        if kickoff_received is None:
            errors.append("缺少 `kickoff_payment_received` 字段")
        elif kickoff_received not in VALID_BOOLEAN_VALUES:
            errors.append("`kickoff_payment_received` 只能填写 `yes` / `no`")
        else:
            print(f"✅ `kickoff_payment_received`: {kickoff_received}")
            if kickoff_received == "no":
                warnings.append("外包项目尚未确认启动款到账；后续不得进入 implementation / test-first")

        track_value = extract_backticked_field(content, "delivery_control_track")
        if track_value is None:
            errors.append("缺少 `delivery_control_track` 字段")
        elif track_value not in VALID_EXTERNAL_TRACKS:
            errors.append(
                "`delivery_control_track` 值无效: "
                f"{track_value}，应为: {', '.join(sorted(VALID_EXTERNAL_TRACKS))}"
            )
        else:
            print(f"✅ `delivery_control_track`: {track_value}")

        trigger_value = extract_backticked_field(content, "delivery_control_handover_trigger")
        if trigger_value is None:
            errors.append("缺少 `delivery_control_handover_trigger` 字段")
        elif trigger_value in {"...", "", "例如"}:
            errors.append("`delivery_control_handover_trigger` 未填写具体值")
        else:
            print(f"✅ `delivery_control_handover_trigger`: {trigger_value}")

        scope_value = extract_backticked_field(content, "delivery_control_retained_scope")
        if scope_value is None:
            errors.append("缺少 `delivery_control_retained_scope` 字段")
        elif scope_value in {"...", ""}:
            errors.append("`delivery_control_retained_scope` 未填写具体值（若无保留范围，应写 `none`）")
        else:
            print(f"✅ `delivery_control_retained_scope`: {scope_value}")

        if track_value == "trial_authorization":
            print("\n检测到试运行授权轨道，检查授权条款...")
            required_terms = [
                "trial_authorization_terms.validity",
                "trial_authorization_terms.clock_source_or_usage_basis",
                "trial_authorization_terms.expiration_behavior",
                "trial_authorization_terms.renewal_policy",
                "trial_authorization_terms.permanent_authorization_trigger",
            ]

            for term in required_terms:
                term_value = extract_backticked_field(content, term)
                if term_value is None:
                    errors.append(f"缺少 `{term}` 字段")
                elif term_value in {"...", "", "."}:
                    errors.append(f"`{term}` 未填写具体值")
                else:
                    print(f"✅ `{term}`: {term_value}")

    print("\n" + "=" * 40)
    if warnings:
        print(f"⚠️  警告 ({len(warnings)}):")
        for warning in warnings:
            print(f"  - {warning}")

    if errors:
        print(f"❌ 错误 ({len(errors)}):")
        for error in errors:
            print(f"  - {error}")
        print("\n❌ Feasibility 门禁验证未通过，请补充 assessment.md 后重试")
        return 1

    if not warnings:
        print("✅ Feasibility 门禁验证通过")
    else:
        print("✅ Feasibility 门禁基本通过，但有警告")

    return 0


RISK_ANALYSIS_PROMPT = f"""## 风险分析执行指引

请使用 `demand-risk-assessment` skill 执行以下风险评估流程：

### 执行步骤

1. **阶段0：结构化抽取**
   - 从需求文本中抽取关键字段（范围边界、交付物清单、验收口径、付款结构、工期/里程碑、关键依赖、数据合规要点、决策/验收负责人）
   - 为每个字段标注状态：明确/暗示(假设)/缺失/冲突
   - 输出信息充分性评分：X/8

2. **阶段0.25：踩坑信号扫描**
   - 检查是否存在常见踩坑信号（如"合同后补"、"结果付款+验收不清"、"应急插队"等）
   - 输出命中的踩坑信号及证据锚点

3. **阶段0.5：冲突检测**
   - 检测关键冲突（如范围与工期矛盾、预算与复杂度不匹配等）
   - 输出冲突项及影响

4. **阶段1：红线检查**
   - 检查是否存在红线问题（如违法用途、严重合规风险等）
   - 输出红线检查结果：✅ 通过 / ❌ 不通过 / ⚠️ 信息不足需补充

5. **阶段2：结构化评分（仅当红线未命中时）**
   - 按维度评分：合规风险(30%)、可交付性(20%)、工期可行性(20%)、价格与收益匹配(20%)、协作与沟通风险(10%)
   - 输出总分及区间

6. **阶段3-5：Pre-mortem → 风险登记表 → 决策/谈判条件**
   - 输出最可能的失败链路
   - 输出风险登记表
   - 输出决策结论及谈判条件

### 输出格式

请将分析结果写入 `assessment.md`，格式如下：

```markdown
{ASSESSMENT_TEMPLATE}
```

### 约束
- `是否允许进入 brainstorm = 否` 时，不应直接进入 `/trellis:brainstorm`
- `总体决策 = 暂停` 时，下一步默认是"补信息后重跑 feasibility"
- `总体决策 = 拒绝` 时，下一步默认是"终止项目并保留 assessment 记录"
"""


def step_risk_analysis(task_dir: Path, requirement_file: Path = None) -> None:
    """生成风险分析提示词并引导 AI 执行 demand-risk-assessment skill"""
    task_dir.mkdir(parents=True, exist_ok=True)
    
    # 读取需求文本
    requirement_text = ""
    if requirement_file and requirement_file.exists():
        requirement_text = requirement_file.read_text(encoding="utf-8")
        print(f"已从 {requirement_file} 读取需求文本")
    else:
        print("请输入需求文本（按 Ctrl+D 结束输入）：")
        try:
            requirement_text = sys.stdin.read()
        except KeyboardInterrupt:
            print("\n已取消输入")
            return
    
    if not requirement_text.strip():
        print("错误：需求文本为空，无法进行风险分析")
        return
    
    # 生成风险分析指引
    risk_analysis_guide = f"""# 风险分析指引

## 需求文本

{requirement_text}

{RISK_ANALYSIS_PROMPT}
"""
    
    # 写入风险分析指引文件
    guide_file = task_dir / "risk-analysis-guide.md"
    guide_file.write_text(risk_analysis_guide, encoding="utf-8")
    print(f"已生成风险分析指引：{guide_file}")
    
    # 检查是否存在 assessment.md
    assessment = task_dir / "assessment.md"
    if not assessment.exists():
        assessment.write_text(ASSESSMENT_TEMPLATE, encoding="utf-8")
        print(f"已创建 {assessment} 模板")
    
    print()
    print("=== 下一步操作 ===")
    print("1. 请使用 Skill 工具执行 demand-risk-assessment")
    print(f"2. 参考 {guide_file} 执行风险分析")
    print(f"3. 将分析结果写入 {assessment}")
    print("4. 运行验证: python3 feasibility-check.py --step validate --task-dir <path>")
    print("5. 根据分析结论决定是否进入 /trellis:brainstorm")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="可行性评估辅助")
    parser.add_argument("--step", default="compliance", choices=["compliance", "estimate", "risk-analysis", "validate"])
    parser.add_argument("--task-dir", type=Path, default=Path("."))
    parser.add_argument("--requirement-file", type=Path, help="需求文本文件路径")
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
    if args.step == "risk-analysis":
        step_risk_analysis(args.task_dir, args.requirement_file)
        return 0
    if args.step == "validate":
        return step_validate(args.task_dir)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
