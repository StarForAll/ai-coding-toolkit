# 完善 multi-cli-review 和 multi-cli-review-action 支持任务级多 reviewer 模式

## Goal

将 `multi-cli-review` 和 `multi-cli-review-action` 从"单 run-id、单报告"协议升级为"任务级总目录下的多 reviewer 协作协议"，支持多个 AI CLI 并行独立审查、统一聚合与执行。

## Requirements

### 1. multi-cli-review 必须补充的内容

#### 目录协议
- 任务级目录：`tmp/multi-cli-review/<task-id>/`
- 轮次目录：`tmp/multi-cli-review/<task-id>/review-round-<N>/`
- 输出文件：`<reviewer-id>.md`
- 旧协议仅作兼容，默认使用新协议

#### 显式参数
| 参数 | 必需 | 说明 |
|------|------|------|
| `--task-dir` | 是（多 reviewer 模式） | 任务总目录路径 |
| `--reviewer-id` | 否 | 默认使用当前 CLI 名称 |
| `--round` | 否 | 默认自动递增 |
| `--output` | 否 | 直接指定输出文件路径 |

#### 输出文件元数据（必须包含）
```yaml
task-id: <任务标识>
round: <轮次>
reviewer-id: <审查者 ID>
source-cli: <CLI 名称>
review-time: <ISO 时间>
review-focus: <本次审查重点>
```

#### 每次执行必须回显
- task-dir
- round
- reviewer-id
- 实际输出文件路径

#### 规则
- 多 reviewer 模式下，禁止使用"最新 run-id 自动兜底"
- 若 reviewer-id 冲突，应报错或要求显式覆盖策略
- 报告中保留"必须解决原因"和"建议修复方向"
- 只负责产出当前 reviewer 的缺陷报告，不承担聚合、去重、冲突裁决职责

### 2. multi-cli-review-action 必须补充的内容

#### 输入方式
- 支持输入任务总目录（扫描同轮所有 reviewer 报告）
- 支持显式传入多个 md-a 文件路径

#### 聚合与去重
- 同一问题被多个 reviewer 提到时，合并为一项
- 合并时保留所有来源的"建议修复方向"
- 标记去重合并的原因

#### 冲突标记
- 若两个 reviewer 对同一问题给出互斥建议，标记为冲突
- 不得自动决定，由人工裁决
- 冲突问题单独列出

#### 决策类型
- **采纳**：直接执行
- **忽略**：记录忽略原因，避免下一轮重复触发
- **需人工裁决**：冲突或边界不清

#### 输出文件
- `summary-round-<N>.md`：聚合后的问题清单、去重结果、冲突标记
- `action.md`：当前 CLI 的决策与执行记录

#### 已处理记录
- 支持"已处理记录"或等价机制
- 避免同一 reviewer 文件被重复消费
- 记录每份报告的处理状态

#### 人工介入阈值
- 达到轮次上限
- 高优先级问题长期未收敛
- reviewer 建议互斥
- 当前 CLI 无法判断是否属于本任务边界

#### 修复后必须验证
- 完成统一修复后，明确要求当前 CLI 重跑该任务原本的 review/验证

#### 每次执行必须回显
- 本次读取的 reviewer 文件列表
- 去重后的问题数
- 冲突问题数
- 已采纳/已忽略/待人工决策数量
- 实际写入的汇总文件路径

### 3. 两个 skill 共同边界

#### 协议优先级
- 显式路径/任务目录优先
- 旧的 run-id 仅作为兼容模式
- 新协议为默认

#### 角色分工
- 其他 CLI 是 reviewer，不修改代码
- 当前 CLI 是唯一修复者

#### reviewer 文件命名
- reviewer-id 显式指定优先
- CLI 名称仅作为默认值

#### 输入标准化
- 多 reviewer 模式下，输入来自当前 CLI 生成的标准化审查包
- 不是完整会话上下文

## Acceptance Criteria

- [ ] multi-cli-review 支持任务级目录协议
- [ ] multi-cli-review 支持显式 reviewer-id（默认 CLI 名称）
- [ ] multi-cli-review 输出包含完整元数据
- [ ] multi-cli-review 每次执行回显必要信息
- [ ] multi-cli-review-action 支持读取任务总目录下多个 reviewer 报告
- [ ] multi-cli-review-action 实现去重机制
- [ ] multi-cli-review-action 实现冲突标记
- [ ] multi-cli-review-action 支持采纳/忽略/人工决策三种结果
- [ ] multi-cli-review-action 输出 summary 和 action 文件
- [ ] multi-cli-review-action 支持已处理记录机制
- [ ] multi-cli-review-action 定义并实现人工介入阈值
- [ ] 两个 skill 兼容旧协议
- [ ] 文档中明确新旧协议优先级
- [ ] 文档中明确角色分工

## Technical Notes

- 涉及文件：skills/multi-cli-review/SKILL.md、skills/multi-cli-review-action/SKILL.md
- 可能需要补充辅助脚本（如有）
- 参考：.trellis/spec/skills/index.md 中的 SKILL.md 规范
