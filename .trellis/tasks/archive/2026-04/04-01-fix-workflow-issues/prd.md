# 工作流修复任务 - PRD

## 目标

修复 `./docs/workflows/新项目开发工作流/` 中存在的实际问题，提升工作流的实际可用性和一致性，同时保持工作流轻量，不做增强性改动。

---

## 问题清单（按优先级排序）

### 问题1：命令描述与实际触发词不匹配 [高]

**位置**：各命令文件头部的 YAML frontmatter `description` 字段

**当前状态**：
- `feasibility.md`: "触发词：帮我评估、能做吗、新项目想法、报价"
- `brainstorm.md`: "触发词：梳理需求、讨论方案、判断要不要拆任务"
- `design.md`: "触发词：开始设计、画架构图、技术选型、设计方案"
- `plan.md`: "触发词：拆任务、做计划、工作分解、排期"
- `test-first.md`: "触发词：先写测试、TDD、测试先行、测试驱动"
- `self-review.md`: "触发词：自检、审查一下、有没有偏差、对照 spec"
- `check.md`: "触发词：补充审查、多人审查、让其他 CLI 看一下、check 一下"
- `delivery.md`: "触发词：准备交付、跑验收、整理交付物、项目收尾、做个流程复盘、记录这次踩坑"

**缺失的口语化表达**：
- feasibility: "看看这个项目"、"能不能接"、"估个价"、"接私活"、"外包项目"、"客户需求"
- brainstorm: "需求分析"、"PRD"、"需求文档"、"明确需求"
- design: "架构设计"、"技术方案"、"选型"、"接口设计"
- plan: "任务分解"、"排期"、"里程碑"、"工作计划"
- test-first: "测试用例"、"验收测试"、"先写测试"
- self-review: "自查"、"对照规范"、"检查偏差"
- check: "代码检查"、"review"、"质量检查"
- delivery: "上线"、"发布"、"部署"、"收尾"

**修复要求**：
扩展各命令的触发词，覆盖更多口语化表达，与实际开发场景中的用户口语对齐。

**具体修改**：
```yaml
# feasibility.md
description: 新项目？先评估可行性 — 合规审查、风险评估、报价输出。触发词：帮我评估、能做吗、新项目想法、报价、看看这个项目、能不能接、估个价、接私活、外包项目、客户需求

# brainstorm.md
description: 需求还不够稳？先确认需求是否准确，再判断复杂度、是否拆子任务、是否需要补信息。触发词：梳理需求、讨论方案、判断要不要拆任务、需求分析、PRD、需求文档、明确需求

# design.md
description: 需求冻结了？开始设计 — UI/UX、架构选型、接口设计、文档输出。触发词：开始设计、画架构图、技术选型、设计方案、架构设计、技术方案、选型、接口设计

# plan.md
description: 设计好了？拆任务 — AI 驱动任务拆解、排期、DoR/DoD。触发词：拆任务、做计划、工作分解、排期、任务分解、里程碑、工作计划

# test-first.md
description: 任务拆好了？先写测试 — 实现前生成测试套件作为客观验收门禁。触发词：先写测试、TDD、测试先行、测试驱动、测试用例、验收测试

# self-review.md
description: 代码写完了？自审一下 — 对照 spec 逐项核对，输出偏差清单。触发词：自检、审查一下、有没有偏差、对照 spec、自查、对照规范、检查偏差

# check.md
description: 自审完了？做任务级补充审查门禁 — 判断是否需要多 CLI 审查，生成 reviewer 指令包，汇总修复并重新验证。触发词：补充审查、多人审查、让其他 CLI 看一下、check 一下、代码检查、review、质量检查

# delivery.md
description: 开发完成？准备交付 — 验收测试、交付物生成、变更日志、经验沉淀。触发词：准备交付、跑验收、整理交付物、项目收尾、做个流程复盘、记录这次踩坑、上线、发布、部署、收尾
```

---

### 问题2：脚本路径硬编码 [高]

**位置**：各命令文件中的脚本调用

**当前状态**（以 feasibility.md 为例）：
```markdown
```bash
python3 docs/workflows/新项目开发工作流/commands/shell/feasibility-check.py --step compliance
```
```

**问题**：
- 路径硬编码，如果工作流目录移动会失效
- `install-workflow.py` 会替换路径，但源文件中的示例路径容易误导

**修复要求**：
源文件中使用占位符，如 `<WORKFLOW_DIR>/commands/shell/...`，并确保 install-workflow.py 正确替换占位符。

**具体修改**：
将所有命令文件中的脚本路径从：
```
docs/workflows/新项目开发工作流/commands/shell/xxx.py
```
改为：
```
<WORKFLOW_DIR>/commands/shell/xxx.py
```

**需要修改的文件和位置**：

| 文件 | 当前路径 | 行号范围 |
|------|---------|---------|
| feasibility.md | `docs/workflows/新项目开发工作流/commands/shell/feasibility-check.py` | 41, 64, 67, 92 |
| design.md | `docs/workflows/新项目开发工作流/commands/shell/design-export.py` | 96 |
| plan.md | `docs/workflows/新项目开发工作流/commands/shell/plan-validate.py` | 217 |
| self-review.md | `docs/workflows/新项目开发工作流/commands/shell/self-review-check.py` | 39 |
| delivery.md | `docs/workflows/新项目开发工作流/commands/shell/record-session-helper.py` | 201 |

**install-workflow.py 修改**：
确认 `prepare_command_content` 函数（第149-153行）已包含占位符替换逻辑：
```python
def prepare_command_content(src: Path) -> str:
    """读取命令文件并替换路径引用。"""
    c = src.read_text(encoding="utf-8")
    c = c.replace("<WORKFLOW_DIR>/commands/shell/", ".trellis/scripts/workflow/")
    return c
```

---

### 问题3：下一步推荐表格过于冗长 [中]

**位置**：各命令文件末尾的 "## 下一步推荐" 章节

**当前状态**：
每个命令都有 5-9 行的推荐表格，内容在各命令间大量重复，信息过载。

**修复要求**：
只保留 3 个最相关的选项：默认推荐、回退、兜底。其他选项通过链接引用到命令映射表。

**具体修改模板**（以 feasibility.md 为例，其他命令类似）：

**修改前**：
```markdown
## 下一步推荐

**当前状态**: 可行性评估完成，`assessment.md` 已生成。

根据评估结果和你的意图：

| 你的意图 | Claude / OpenCode 推荐入口 | Codex 推荐入口 | 说明 |
|---------|---------------------------|----------------|------|
| 继续推进项目 | `/trellis:brainstorm` | 继续需求发现，或显式触发 `brainstorm` skill | **默认推荐**。评估通过，进入详细需求发现 |
| 信息不足，先补充再评估 | `/trellis:feasibility` | 补信息后重跑评估，或显式触发 `feasibility` skill | 默认用于 `暂停` 结论；补齐缺口、谈判后重跑 |
| 评估不通过，终止 | — | — | 记录原因，保留 `assessment.md` 作为拒绝依据 |
| 需求已经很明确，跳过 brainstorm | `/trellis:design` | 直接进入设计，或显式触发 `design` skill | 如果 PRD 内容已足够详细 |
| 需求简单，直接写代码 | `/trellis:start` | 直接进入实施，或显式触发 `start` skill | 跳过设计+拆解，适合小改动 |
| 不确定下一步 | `/trellis:start` | 描述当前意图，或显式触发 `start` skill | 用 Phase Router / skill 路由自动检测 |
```

**修改后**：
```markdown
## 下一步推荐

**当前状态**: 可行性评估完成，`assessment.md` 已生成。

| 你的意图 | Claude / OpenCode | Codex | 说明 |
|---------|------------------|-------|------|
| 继续推进 | `/trellis:brainstorm` | `brainstorm` skill | **默认推荐**。评估通过，进入需求发现 |
| 信息不足 | `/trellis:feasibility` | `feasibility` skill | 补信息后重跑评估 |
| 其他选项 | 详见 [命令映射表](../命令映射.md#分支路径速查表) | 同上 | 跳过 brainstorm、直接写代码等 |
```

**各命令简化后的保留项**：

| 命令 | 默认推荐 | 回退 | 兜底 |
|------|---------|------|------|
| feasibility | brainstorm (继续推进) | feasibility (信息不足) | 命令映射表 |
| brainstorm | design (做设计) | brainstorm (继续澄清) | 命令映射表 |
| design | plan (拆任务) | design (回退修改) | 命令映射表 |
| plan | test-first (测试先行) | plan (重新拆解) | 命令映射表 |
| test-first | start (开始实现) | test-first (补测试) | 命令映射表 |
| self-review | check (补充审查) | start (修复偏差) | 命令映射表 |
| check | finish-work (提交检查) | start (修复) | 命令映射表 |
| delivery | record-session (收尾) | break-loop (排障) | 命令映射表 |

---

### 问题4：MCP能力路由"按需"过于模糊 [中]

**位置**：各命令文件中的 MCP 能力路由表

**当前状态**（以 design.md 为例）：
```markdown
| 场景 | 调用能力 | 调用级别 | 说明 |
|------|---------|---------|------|
| 参考 GitHub 开源架构 | `deepwiki` | 按需 | 回退：`exa_search` |
| 技术选型深度研究 | `exa_create_research` | 按需 | 回退：`grok-search` |
| 复杂架构推理 | `sequential-thinking` | 按需 | 当架构决策涉及 ≥3 个技术方案对比或推理步骤 >3 步时触发 |
```

**问题**："按需"没有明确判定标准，AI可能跳过应该使用的MCP。

**修复要求**：
将"按需"改为明确的触发条件描述。

**具体修改**：

**design.md / plan.md 等文件的 MCP 路由表统一修改**：

```markdown
| 场景 | 调用能力 | 触发条件 | 说明 |
|------|---------|---------|------|
| 参考 GitHub 开源架构 | `deepwiki` | 当需要参考/调研外部开源项目时 | 回退：`exa_search` |
| 技术选型深度研究 | `exa_create_research` | 当需要进行技术方案深度调研时 | 回退：`grok-search` |
| 复杂架构推理 | `sequential-thinking` | 当涉及 ≥3 个技术方案对比或推理步骤 >3 步时 | 复杂决策场景 |
| 架构图可视化 | `markmap` | 当需要生成架构图/模块依赖图时 | 技术栈确认 |
| 框架/SDK API 文档 | `Context7` | 当需要查询第三方库/框架官方文档时 | 技术选型必查 |
```

**brainstorm.md 的 MCP 路由表修改**：
```markdown
| 场景 | 调用能力 | 触发条件 | 说明 |
|------|---------|---------|------|
| 需求模糊、需增强 | `ace.enhance_prompt` | 当需求描述不够清晰需要增强时 | 回退：`sequential-thinking` |
| L2 复杂任务发散推理 | `sequential-thinking` | 当需求拆解涉及 ≥3 个决策分支或依赖链 >3 层时 | 复杂任务场景 |
| 可视化需求关系 | `markmap` | 当需要生成需求层级图时 | 需求 → 功能 → 验收标准 |
```

**feasibility.md 的 MCP 路由表修改**：
```markdown
| 场景 | 调用能力 | 触发条件 | 说明 |
|------|---------|---------|------|
| 竞品分析、技术方案深度调研 | `exa_create_research` | 当需要进行竞品分析或技术调研时 | 回退：`grok-search` |
| 风险评估复杂推理 | `sequential-thinking` | 当风险评估涉及 ≥3 个决策分支或推理步骤 >3 步时 | 复杂风险场景 |
| 参考 GitHub 开源项目 | `deepwiki` | 当需要参考外部开源项目时 | 回退：`exa_search` |
```

---

### 问题5：Skills调用机制不统一 [低]

**位置**：各命令文件中的 Skill 调用说明

**当前状态**：
多处重复"若该 skill 不可用，降级为手动..."，描述冗长且不统一。

**修复要求**：
统一 skill 调用描述格式，简化降级说明。

**具体修改模板**：

**修改前**：
```markdown
**调用 Skill**：使用 Skill 工具执行 `demand-risk-assessment`，按其框架判断接/谈判后接/暂停/拒绝。若该 skill 不可用，降级为手动按合规/可交付性/工期/价格/协作五维度做结构化评估，并标记 `[Skill Gap: demand-risk-assessment]`。
```

**修改后**：
```markdown
**调用 Skill**：`demand-risk-assessment` — 按框架执行风险评估，输出决策建议。降级：手动五维度评估。
```

**统一格式**：
```markdown
**调用 Skill**：`<skill-name>` — <一句话描述用途>。降级：<简要降级方案>。
```

**需要统一修改的命令文件**：
- feasibility.md (第89行)
- brainstorm.md (第70行)
- design.md (第30行, 第83行)
- plan.md (第61行)
- test-first.md (第28行)
- self-review.md (第36行, 第46行)
- delivery.md (第40行, 第82行, 第117行, 第121行)

---

### 问题6：Shell脚本缺少错误处理 [低]

**位置**：`commands/shell/*.py`

**当前状态**：
- `feasibility-check.py` 第142行开始的验证函数没有异常处理
- `plan-validate.py` 直接 `sys.exit(1)` 没有友好的错误信息

**修复要求**：
增加 try-except 包裹和友好的错误提示。

**具体修改**：

**feasibility-check.py**：
在 `step_validate` 函数（第142行）添加异常处理：
```python
def step_validate(task_dir: Path) -> int:
    """验证 assessment.md 中双轨交付控制字段的完整性"""
    print("=== 双轨交付控制字段验证 ===")
    
    try:
        assessment = task_dir / "assessment.md"
        if not assessment.exists():
            print(f"❌ {assessment} 不存在")
            return 1
        
        content = assessment.read_text(encoding="utf-8")
        # ... 原有验证逻辑 ...
        
    except Exception as e:
        print(f"❌ 验证过程出错: {e}")
        return 1
```

**plan-validate.py**：
在 `main()` 函数（第89行）添加异常处理：
```python
def main() -> int:
    try:
        task_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
        plan_file = task_dir / "task_plan.md"
        # ... 原有验证逻辑 ...
    except FileNotFoundError as e:
        print(f"❌ 文件未找到: {e}")
        return 1
    except PermissionError as e:
        print(f"❌ 权限错误: {e}")
        return 1
    except Exception as e:
        print(f"❌ 验证过程出错: {e}")
        return 1
```

**其他脚本类似处理**：
- `design-export.py`
- `self-review-check.py`
- `delivery-control-validate.py`
- `record-session-helper.py`

---

## 关联文件清单

### 主要修改文件（8个命令文件）
1. `commands/feasibility.md`
2. `commands/brainstorm.md`
3. `commands/design.md`
4. `commands/plan.md`
5. `commands/test-first.md`
6. `commands/self-review.md`
7. `commands/check.md`
8. `commands/delivery.md`

### 辅助脚本（6个shell脚本）
1. `commands/shell/feasibility-check.py`
2. `commands/shell/plan-validate.py`
3. `commands/shell/design-export.py`
4. `commands/shell/self-review-check.py`
5. `commands/shell/delivery-control-validate.py`
6. `commands/shell/record-session-helper.py`

### 安装脚本
1. `commands/install-workflow.py`（确认占位符替换逻辑）

---

## 验收标准

- [ ] 所有命令文件的触发词已扩展，覆盖常见口语表达
- [ ] 所有脚本调用路径已改为 `<WORKFLOW_DIR>` 占位符格式
- [ ] 下一步推荐表格已简化至3行以内
- [ ] MCP能力路由表中的"按需"已改为明确触发条件
- [ ] Skill调用描述已统一为简洁格式
- [ ] Shell脚本已增加基本异常处理
- [ ] 安装脚本能正确处理新的占位符格式

---

## 约束

- **只做修复，不做增强**：不增加新功能，只修复现有问题
- **保持轻量**：不增加工作流复杂度
- **向后兼容**：修复后的工作流应与现有安装项目兼容

---

## 修复顺序建议

1. **先修复问题2（脚本路径）** - 影响 install-workflow.py 的替换逻辑
2. **同时修复问题1（触发词）和问题3（推荐表格）** - 都是命令文件的文本修改
3. **然后修复问题4（MCP路由）和问题5（Skill调用）** - 表格和描述格式统一
4. **最后修复问题6（脚本错误处理）** - 独立的脚本修改

---

## 下一步推荐

| 意图 | 命令 |
|------|------|
| 开始修复 | `/trellis:start` |
| 查看任务列表 | `python3 ./.trellis/scripts/task.py list` |
