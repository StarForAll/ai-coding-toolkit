# brainstorm: 评估双轨交付控制对应 spec 是否规范

## Goal

从实际使用与开发实践角度，评估 `docs/workflows/新项目开发工作流/` 中“`双轨交付控制`”依赖的 `trellis-library` 资产是否规范、是否与工作流场景匹配，并在修改前先收敛出一套合理调整方案供确认。

## What I already know

- 工作流总纲明确要求：外部项目在设计阶段导入以下资产：
  - `spec.universal-domains.project-governance.delivery-control`
  - `spec.universal-domains.project-governance.authorization-management`
  - `checklist.universal-domains.project-governance.transfer-checklist`
- `design.md`、`plan.md`、`delivery.md`、`feasibility.md` 都把这组三件套视为“外部项目双轨交付控制”的核心资产。
- `delivery-control` 与 `authorization-management` 都已在 `trellis-library/manifest.yaml` 注册，`transfer-checklist` 也已注册，且 `trellis-library/cli.py validate --strict-warnings` 当前通过。
- 已发现一个明显适配风险：
  - 工作流把 `authorization-management` 作为所有外部项目的额外必选 spec。
  - 但 `authorization-management` 自身边界只适用于 `trial_authorization` 轨道，不适用于默认 `hosted_deployment`。
- 已发现一个明显验证契约风险：
  - `delivery-control/verification.md` 通过 `grep "delivery_control_track"`、`grep "trial_authorization_terms"` 检查 `assessment.md`
  - 但 `feasibility.md` 当前要求的 `assessment.md` 最低字段契约使用的是中文自然语言字段，如“交付控制轨道：托管部署 / 试运行授权 / 未确定”，两者未统一。

## Assumptions (temporary)

- 用户希望先做“方案收敛”，暂不直接修改 `trellis-library` 或工作流文档。
- 本轮重点不是检查“文件是否存在”，而是评估这些资产在真实工作流中的适配度、边界清晰度、验证可执行性。
- 若后续执行修改，大概率会同时涉及：
  - `trellis-library/specs/universal-domains/project-governance/*`
  - `trellis-library/checklists/universal-domains/project-governance/transfer-checklist.md`
  - `docs/workflows/新项目开发工作流/*.md`
  - 可能还包括 `trellis-library/manifest.yaml`

## Open Questions

- 本轮最终输出要做到哪一层：
  - 仅给评估报告与调整方案
  - 还是确认后直接落地修改 `trellis-library` 与 workflow 文档

## Requirements (evolving)

- 识别“双轨交付控制”在工作流中的实际使用点与门禁点。
- 评估三项资产是否覆盖这些使用点。
- 从实际开发/交付实践角度识别结构性问题，而不是只做字面比对。
- 先提出可执行的调整方案与取舍，再等用户确认是否实施。
- 采用方案 B：按真实交付场景重构该组资产，而不是只做最小修补。
- 重构后必须满足“基础必选 + 条件必选”的导入模型：
  - 外部项目基础必选：`delivery-control`
  - 仅试运行授权轨条件必选：`authorization-management`
  - `transfer-checklist` 需明确适配最终移交与非一次性全量移交场景
- 对齐 workflow 与 `trellis-library` 的字段契约、依赖关系与验证门禁，避免“工作流写法”和“spec 校验写法”不一致。

## Acceptance Criteria (evolving)

- [ ] 明确列出工作流对双轨交付控制资产的实际要求
- [ ] 明确列出当前 spec/checklist 与这些要求之间的匹配点和缺口
- [ ] 至少提出 2 个可行调整方案，并说明推荐方案与取舍
- [ ] 在用户确认前，不直接实施规范修改
- [ ] 方案 B 的重构边界、目标状态与实施顺序明确

## Definition of Done (team quality bar)

- 结论基于仓内文档与资产，不靠猜测
- 若提出“规范不匹配”，必须指出具体文件与契约冲突点
- 若进入实施阶段，需同步考虑 spec / workflow / manifest 的一致性

## Out of Scope (explicit)

- 当前不评估与双轨交付控制无关的其他 workflow spec 质量
- 当前不做客户合同文本设计
- 当前不做运行时代码层面的 license 实现审计
- 当前不新增完整“法务/合同模板资产体系”，只处理与双轨交付控制直接耦合的 spec/checklist/workflow

## Technical Approach

按“总控 spec / 条件 spec / 交付 checklist / workflow 门禁”四层收敛：

1. `delivery-control` 作为外部项目双轨交付控制的总控规范
   - 负责轨道选择、默认规则、尾款触发移交、禁止项、门禁时点
2. `authorization-management` 作为 `trial_authorization` 专用条件规范
   - 不再被 workflow 表述为所有外部项目必选
3. `transfer-checklist` 调整为能区分：
   - 最终全量移交
   - 托管持续期内的有限移交 / 责任边界说明
4. workflow 文档改成条件导入与条件校验
   - `feasibility`：产出统一字段契约
   - `design` / `plan`：按轨道导入必选/条件必选 spec
   - `delivery`：按轨道执行不同门禁与 checklist

## Decision (ADR-lite)

**Context**:
当前 workflow 将三项资产整体视为所有外部项目的固定必选集，但实际资产边界并不对齐，导致条件 spec 被强制导入、验证字段不一致、最终 checklist 偏单一移交模型。

**Decision**:
采用方案 B，对双轨交付控制相关资产做场景化重构：保留 `delivery-control` 作为总控，将 `authorization-management` 降为试运行授权轨专用条件 spec，并重构 `transfer-checklist` 与 workflow 门禁表达。

**Consequences**:
- 优点：更符合真实外部项目实践，资产职责更清晰，后续扩展成本更低
- 代价：需要同步修改 `trellis-library` spec/checklist、`manifest.yaml` 依赖语义，以及 `docs/workflows/新项目开发工作流/` 中多处说明

## Technical Notes

- 关键工作流证据：
  - `docs/workflows/新项目开发工作流/工作流总纲.md`
  - `docs/workflows/新项目开发工作流/commands/feasibility.md`
  - `docs/workflows/新项目开发工作流/commands/design.md`
  - `docs/workflows/新项目开发工作流/commands/plan.md`
  - `docs/workflows/新项目开发工作流/commands/delivery.md`
- 关键资产证据：
  - `trellis-library/specs/universal-domains/project-governance/delivery-control/*`
  - `trellis-library/specs/universal-domains/project-governance/authorization-management/*`
  - `trellis-library/checklists/universal-domains/project-governance/transfer-checklist.md`
  - `trellis-library/manifest.yaml`
- 初步观察：
  - `delivery-control` 更像“轨道选择 + 付款触发移交”的总控 spec
  - `authorization-management` 更像仅在“试运行授权轨”启用的条件 spec
  - `transfer-checklist` 偏最终移交时点，但对“托管部署长期不移交 / 分阶段移交”支持不够明确
  - `delivery-control/verification.md` 与 `feasibility.md` 的 `assessment.md` 字段契约当前不一致，需要统一为同一套机器可检索 + 人可读格式
