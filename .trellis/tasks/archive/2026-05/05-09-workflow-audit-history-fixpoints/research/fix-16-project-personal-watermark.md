# Research: 修复点 #16 项目个人水印

- **Query**: 审计修复点 #16，检查工作流是否支持项目个人水印机制
- **Scope**: internal
- **Date**: 2026-05-09

## Findings

### 安装后产物

| File Path | Description |
|---|---|
| `/tmp/trellis-0.5.9-2/.trellis/workflow-docs/源码水印与归属证据链执行卡.md` | 水印机制完整执行卡 |
| `/tmp/trellis-0.5.9-2/.trellis/scripts/workflow/ownership-proof-validate.py` | 归属证明校验脚本，全阶段覆盖 |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/feasibility.md` | feasibility 阶段水印字段冻结 |
| `/tmp/trellis-0.5.9-2/.trellis/scripts/workflow/feasibility-check.py` | 验证 assessment.md 水印字段 |

### 源码文件

| File Path | Description |
|---|---|
| `docs/workflows/新项目开发工作流/源码水印与归属证据链执行卡.md` | 水印执行卡源码 |
| `docs/workflows/新项目开发工作流/commands/feasibility.md` | 源码版可行性评估命令 |
| `docs/workflows/新项目开发工作流/工作流总纲.md` | 源码版工作流总纲 |

### 水印机制的完整证据链

1. **水印档位体系 (源码水印与归属证据链执行卡.md 行 42-55)**: 四档模型 `none / basic / hybrid / forensic`，每档有明确最低要求
2. **四层水印分层 (执行卡.md 行 57-127)**:
   - W0: 可见源码水印（版权/作者/年份/WMID）
   - W1: 零宽字符水印（仅允许注释/文档字符串/Markdown）
   - W2: 不起眼代码标识（模块私有常量/注释碎片/metadata片段）
   - W3: 零水印记录（选择文件、片段组成、checksum、提取步骤）
3. **阶段动作覆盖 (执行卡.md 行 130-171)**:
   - feasibility: 冻结 `source_watermark_level`, `source_watermark_channels`, `zero_width_watermark_enabled`, `subtle_code_marker_enabled`, `ownership_proof_required`
   - design: 生成 `source-watermark-plan.md`，包含 WMID、通道、边界、排除路径
   - plan: 拆分为 5 类任务（可见/零宽/隐蔽/验证/归属证明包）
   - delivery: 产出 `ownership-proof.md`, `source-watermark-verification.md`
4. **feasibility.md 行 133**: "当前 workflow 默认启用作者归属保护；除非项目明确写 `ownership_proof_required = no`，否则 `source_watermark_*` 与 `ownership_proof_required` 都必须在本阶段显式冻结"
5. **feasibility.md 行 147-153**: 离开 feasibility 前必须执行 `ownership-proof-validate.py --phase feasibility`
6. **ownership-proof-validate.py**: 全阶段校验脚本，覆盖 feasibility/design/plan/delivery 四阶段
   - feasibility: 校验 assessment.md 水印字段完整性与一致性（行 112-188）
   - design: 校验 `source-watermark-plan.md` 存在且包含 WMID/排除路径/提取/验证说明（行 203-287）
   - plan: 校验 `task_plan.md` 包含水印任务拆分（行 290-330）
   - delivery: 校验交付产物完整性（行 333-443）
7. **工作流总纲.md 行 296-318**: 所有权属保护字段的详细说明，包括默认启用、适用范围、试运行授权下的水印场景

### 机器强制执行

- `feasibility-check.py --step validate` 验证 5 个水印相关字段的存在性和取值有效性（行 383-443）
- `ownership-proof-validate.py` 可独立执行也可被 `delivery-control-validate.py` 联动
- `workflow-state.py validate` 在后续阶段入口强制检查水印字段

### 与"个人"水印的关联

- WMID 机制（执行卡.md 行 72: `wm_<stable-id>`）是项目+作者维度的稳定标识
- 水印执行卡明确声明适用范围包括"个人开发项目"（执行卡.md 行 12）
- `ownership_proof_required` 默认值为 `yes`，个人项目默认也启用

## 审计判定

- **是否满足**: ✅ 已满足
- **证据**: 源码水印与归属证据链执行卡.md 全文; ownership-proof-validate.py 全文; feasibility.md 行 133-153, 217-221; feasibility-check.py 行 383-443; 工作流总纲.md 行 296-318
- **与上次对比变化**: 上次审计未单独标记此项有问题；本次确认水印机制从 feasibility 到 delivery 全阶段覆盖，且有独立校验脚本强制执行

## Caveats / Not Found

- 水印的实际嵌入（W0/W1/W2）仍依赖 AI 或人工在代码中手动执行，脚本只校验产物存在性
- 零宽字符水印的"仅允许注释/文档字符串/Markdown"边界在 `ownership-proof-validate.py` design 阶段校验中有检查（行 246-271），但实际代码中的零宽字符放置是否合规仍依赖人工审查
