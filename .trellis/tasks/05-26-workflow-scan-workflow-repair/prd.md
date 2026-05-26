# 应用系统级验证矩阵修正 workflow-scan 和 workflow-repair

## Goal

解决 workflow-scan/workflow-repair 循环中的**增量发现问题循环**（incremental discovery loop）：每次修复后重新嵌入工作流，仍然发现新问题，导致循环执行上百次而无法收敛。

核心问题：
- 每次只验证当前修复点的直接影响，缺少全局一致性检查
- 修复 A 可能破坏 B/C/D 的假设，下一轮才发现
- 缺少系统级契约测试，只有局部验证
- 测试用例不够全面，每次初始化略有不同

目标：引入**系统级验证矩阵**，一次性覆盖所有场景，打破循环。

## What I already know

### 现有 Skills 状态
- `workflow-scan` (v2.8): 扫描临时项目中的工作流问题，生成 `WORKFLOW_QUESTIONS.md`
- `workflow-repair` (v2.8): 消费扫描报告，修复源工作流文件
- 两者通过 `workflow-scan-repair-v3` 协议耦合
- 支持 `--agent` 模式（scan）和 `--auto` 模式（repair）

### 问题模式
用户描述的循环：
```bash
临时项目初始化 → workflow-scan → 发现问题 → workflow-repair → 修复
→ 重新初始化临时项目 → workflow-scan → 发现新问题 → ...
```
循环执行上百次，每次都发现新问题。

### 工作流相关脚本
- `install-workflow.py`: 安装工作流到目标项目
- `detect-embed-state.py`: 检测嵌入状态
- `upgrade-compat.py`: 升级兼容性检查
- `test_workflow_installers.py`: 安装器测试

### 用户提出的方案 A（系统级验证矩阵）
创建完整的测试矩阵，一次性覆盖所有场景：
- 不同 profile（o/s/h）
- 不同初始状态（clean/existing-trellis/existing-codex）
- 完整安装流程 + 所有验证命令
- 一次性收集所有问题，而非增量发现

## Assumptions (temporary)

1. 循环的根本原因是**验证范围不完整** + **修复引入新问题**
2. 现有 workflow-scan 和 workflow-repair 的核心逻辑是正确的，需要增强的是**验证层**
3. 系统级验证矩阵应该作为**独立的验证工具**，而非修改 scan/repair 的核心流程
4. 验证矩阵应该在**修复前**运行，一次性发现所有问题

## Open Questions

### ✅ Q1: 验证矩阵的集成点（已决定）
**决定**：新增 `workflow-validate-matrix` skill，与 workflow-scan 互补

- **workflow-scan**（保留）：快速扫描单个临时项目，5-10 秒，日常迭代使用
- **workflow-validate-matrix**（新增）：全场景矩阵验证，5-10 分钟，深度验证使用

**关系**：互补而非替代
- 类比：单元测试 vs 集成测试
- workflow-scan 用于快速反馈
- workflow-validate-matrix 用于避免循环、发布前回归测试

## Open Questions

### ✅ Q6: Skill 使用位置和扩展策略（已决定）

**使用位置**：
- Skill 安装在**源项目**（工作流开发项目）
- Skill 自动创建**临时项目**用于测试
- 验证的是"当前源项目的工作流"在不同场景下的表现

**工作流程**：
```bash
# 在源项目中
cd /ops/projects/personal/ai-coding-toolkit
/workflow-validate-matrix
  → 创建临时项目 /tmp/trellis-matrix-{timestamp}-{scenario}
  → 在临时项目中安装当前源项目的工作流
  → 验证每个临时项目
  → 汇总报告到源项目
```

**扩展策略**：
- **v1.0 (MVP)**：3 个场景，硬编码
- **v1.1**：配置文件支持（scenarios.yaml）
- **v1.2**：命令行参数（--scenarios, --profile, --cli）
- **v2.0**：完整矩阵（2 profiles × 4 states × 3 CLI 组合）
- **v2.1**：并行执行

**扩展点设计**：
- 场景定义参数化（易于添加新场景）
- 配置文件驱动（无需修改代码）
- 命令行参数覆盖（灵活选择）

### ✅ Q5: 实现方式和技术选择（已决定）
**决定**：混合方案（核心逻辑在 skill 内，标准命令通过 subprocess）

**重要约束**：
- Skill 会被全局安装到其他项目
- 必须自包含，不能依赖外部资源
- 所有 Python 脚本必须在 skill 目录内

**Skill 结构**：
```
skills/workflow-validate-matrix/
  SKILL.md                    # Skill 定义
  validate-matrix.py          # 主逻辑（CLI 入口）
  scenario_setup.py           # 场景初始化
  validation_runner.py        # 验证执行器
  report_generator.py         # 报告生成
  constants.py                # 常量定义（不依赖 workflow_assets.py）
```

**实现策略**：
- **场景初始化**：调用标准命令（`git init`, `trellis init`）
- **工作流安装**：调用 `install-workflow.py`（通过绝对路径或环境变量）
- **验证逻辑**：在 skill 内重新实现简化版（读取文件、检查一致性）
- **报告生成**：完全在 skill 内实现

**优点**：
- 平衡自包含性和复用性
- 可以在任何项目中运行
- 不重复实现复杂的安装逻辑

### ✅ Q4: 失败处理和部分成功策略（已决定）
**决定**：继续执行（Continue on Error）

**策略**：
- 某个场景失败时，记录错误详情，继续执行其他场景
- 最大化信息收集，一次运行看到所有场景状态
- 失败本身也是有价值的信息（说明严重问题）

**失败报告格式**：
```markdown
## Scenario Results

### Scenario 1: clean
**Status**: ✅ Success
**Findings**: 5 issues found

### Scenario 2: existing-trellis
**Status**: ❌ Failed
**Error**: install-workflow.py exited with code 1
**Details**: File conflict detected at .trellis/workflow.md
**Findings**: N/A (validation incomplete)

### Scenario 3: existing-workflow
**Status**: ✅ Success
**Findings**: 8 issues found
```

**错误类型**：
- 临时项目创建失败
- trellis init 失败
- install-workflow.py 失败
- 验证命令失败（upgrade-compat, workflow-state 等）
**决定**：单一聚合报告，兼容 workflow-repair 输入格式

**报告特点**：
- 文件名：`WORKFLOW_QUESTIONS.md`（与 workflow-scan 相同）
- 协议：`workflow-scan-repair-v3`（保持兼容）
- 新增字段：`matrix-validation: true`, `scenarios-tested: 3`, `scenarios: [...]`
- 每个 finding 增加 `Scenario` 字段，标注来源场景
- 重复问题保留（说明跨场景存在，需要全场景验证修复）

**优点**：
- workflow-repair 无需修改，直接消费
- 一次性修复所有问题
- 重复问题体现真实影响范围

**报告结构示例**：
```markdown
---
document-type: workflow-questions
protocol: workflow-scan-repair-v3
matrix-validation: true
scenarios-tested: 3
scenarios: ["clean", "existing-trellis", "existing-workflow"]
total-findings: 15
...
---

### WS-001
**Scenario**: clean, existing-trellis
**Category**: Missing File
...
```
**决定**：简化版（3 个场景），分阶段扩展

**实际情况**：
- Profile 确实影响安装：`personal` vs `outsourcing`（默认）
- 完整组合：2 profiles × 4 states × 3 CLIs = 24 场景（48-72 分钟，不现实）

**MVP 范围（第一阶段）**：
- Profile: 只测试 `outsourcing`（默认，功能最全）
- 初始状态: `clean`, `existing-trellis`, `existing-workflow`（3 种）
- CLI: `--claude --opencode --codex`（全部启用）
- **总共 3 个场景**，预计 6-9 分钟

**扩展计划（第二阶段）**：
- 增加 `personal` profile
- 增加更多初始状态（`dirty-git`, `partial-install`）
- 增加单独 CLI 测试

## Requirements (Final)

### 核心需求
- [x] 新增 `workflow-validate-matrix` skill
- [x] 保留 `workflow-scan` 用于快速迭代
- [x] 矩阵验证覆盖 3 个场景组合
- [x] 一次性发现所有问题，打破增量发现循环
- [x] 输出格式兼容 workflow-repair 消费
- [x] 继续执行策略（部分失败不阻塞）

### workflow-validate-matrix Skill 需求

#### 功能需求
- [ ] 自动创建 3 个临时项目实例（对应 3 种初始状态）
- [ ] 每个实例运行完整验证链：
  - `git init` + 基础设置
  - `trellis init --claude --opencode --codex -y -u xzc`
  - `install-workflow.py --profile outsourcing --cli claude,opencode,codex`
  - `detect-embed-state.py --project-root <temp>`
  - `upgrade-compat.py --project-root <temp> --check`
  - `workflow-state.py route`（如果存在）
- [ ] 汇总所有场景的问题到单一报告（`WORKFLOW_QUESTIONS.md`）
- [ ] 支持重新验证（确认修复后无新问题）
- [ ] 清理临时项目（可选 `--keep-temp` 保留用于调试）

#### 场景定义（MVP）
1. **clean**: 空目录 + `git init`
2. **existing-trellis**: 已运行 `trellis init`
3. **existing-workflow**: 已安装旧版本工作流（模拟升级场景）

#### 报告格式
- 文件名：`WORKFLOW_QUESTIONS.md`
- 协议：`workflow-scan-repair-v3`
- 新增字段：
  - `matrix-validation: true`
  - `scenarios-tested: 3`
  - `scenarios: ["clean", "existing-trellis", "existing-workflow"]`
- 每个 finding 增加 `Scenario` 字段

#### 错误处理
- 继续执行策略：某场景失败不阻塞其他场景
- 失败报告包含：场景名、错误类型、详细信息
- 成功场景正常输出 findings

#### 技术实现
- Skill 自包含（所有代码在 skill 目录内）
- 混合方案：
  - 核心逻辑在 skill 内实现
  - 标准命令通过 subprocess 调用
  - 工作流安装调用 `install-workflow.py`（绝对路径）

#### 边界处理
- [ ] 磁盘空间预检查（至少 500MB）
- [ ] 唯一临时目录名（加时间戳避免冲突）
- [ ] 基本超时保护（每步骤 5 分钟）
- [ ] `--keep-temp` 选项（保留临时目录用于调试）

### 验证矩阵参数（MVP）
- **Profile**: `outsourcing`（默认，功能最全）
- **初始状态**: 3 种（clean, existing-trellis, existing-workflow）
- **CLI**: `--claude --opencode --codex`（全部启用）
- **验证点**: detect-embed-state, install-workflow, upgrade-compat, workflow-state
- **总场景数**: 3 个
- **预计时间**: 6-9 分钟

## Acceptance Criteria

### 功能验收
- [ ] `workflow-validate-matrix` skill 可以成功运行
- [ ] 自动创建 3 个临时项目（clean, existing-trellis, existing-workflow）
- [ ] 每个场景都执行完整验证链
- [ ] 生成 `WORKFLOW_QUESTIONS.md` 报告
- [ ] 报告包含所有场景的问题汇总
- [ ] 报告格式兼容 `workflow-repair` 输入
- [ ] 某个场景失败不阻塞其他场景
- [ ] 失败场景有清晰的错误报告

### 质量验收
- [ ] 单次运行能发现所有问题（不再需要循环）
- [ ] 修复后重新运行，不应再发现新问题（收敛验证）
- [ ] 临时目录使用唯一名称（避免冲突）
- [ ] `--keep-temp` 选项可以保留临时目录
- [ ] 磁盘空间不足时有友好提示
- [ ] 超时场景有明确报告

### 集成验收
- [ ] 生成的报告可被 `workflow-repair` 直接消费
- [ ] 修复后的工作流通过矩阵验证（0 问题）
- [ ] 与现有 `workflow-scan` 输出格式一致

### 性能验收
- [ ] 3 个场景总时间 < 10 分钟
- [ ] 每个场景失败后能快速跳过（< 30 秒）

## Definition of Done

- 验证矩阵脚本实现并测试通过
- workflow-scan 或 workflow-repair 集成验证矩阵（根据 Q1 决定）
- 文档更新（使用说明、集成方式）
- 在真实临时项目上验证：运行一次后不再发现新问题

## Expansion Sweep (Diverge → Converge)

在确定 MVP 范围前，让我考虑三个类别以避免后续返工：

### 1. Future Evolution（未来演进）
- **扩展到更多场景**：
  - 第二阶段：增加 `personal` profile
  - 第三阶段：增加更多初始状态（`dirty-git`, `partial-install`）
  - 第四阶段：增加单独 CLI 测试（只 claude、只 codex）
- **性能优化**：
  - 并行执行多个场景（当前串行）
  - 增量验证（只验证变更部分）
- **报告增强**：
  - 生成 HTML 可视化报告
  - 趋势分析（对比历史验证结果）

**MVP 中保留的扩展点**：
- 场景配置可参数化（易于添加新场景）
- 报告格式向后兼容（可增加新字段）

### 2. Related Scenarios（相关场景）
- **与现有 skills 的一致性**：
  - `workflow-scan`：快速单场景扫描
  - `workflow-validate-matrix`：深度多场景验证
  - `workflow-repair`：修复问题
  - `workflow-audit`：综合审计
  - 需要保持命名和输出格式一致
- **用户工作流**：
  - 开发中：`workflow-scan` → `workflow-repair`
  - 发布前：`workflow-validate-matrix` → `workflow-repair` → 再次 `workflow-validate-matrix`
  - 升级后：`workflow-validate-matrix` 确认兼容性

**MVP 中的一致性保证**：
- 使用相同的协议版本（`workflow-scan-repair-v3`）
- 输出格式兼容 `workflow-repair`

### 3. Failure & Edge Cases（失败和边界情况）
- **环境问题**：
  - 磁盘空间不足（需要 ~500MB × 3 场景）
  - Python 版本不兼容
  - trellis 命令不在 PATH
- **并发冲突**：
  - 多个矩阵验证同时运行（临时目录冲突）
  - 解决：使用唯一的临时目录名（加时间戳或随机后缀）
- **部分失败**：
  - 某个场景失败不应阻止其他场景（已决定）
  - 需要清晰的失败报告
- **清理失败**：
  - 临时目录删除失败（权限问题、文件被占用）
  - 解决：提供 `--keep-temp` 选项保留临时目录用于调试
- **超时处理**：
  - 某个场景卡住（如 trellis init 等待用户输入）
  - 解决：为每个步骤设置超时（默认 5 分钟）

**MVP 中的边界处理**：
- 磁盘空间预检查
- 唯一临时目录名（避免冲突）
- 继续执行策略（部分失败不阻塞）
- `--keep-temp` 选项（调试用）
- 基本超时保护

---

## Converge to MVP

基于上述扩展思考，**MVP 应该包含**：

### 包含（In Scope）
- ✅ 3 个场景验证（clean, existing-trellis, existing-workflow）
- ✅ 单一聚合报告（兼容 workflow-repair）
- ✅ 继续执行策略（部分失败不阻塞）
- ✅ 基本错误处理和报告
- ✅ 唯一临时目录名（避免冲突）
- ✅ `--keep-temp` 选项（调试用）

### 不包含（Out of Scope - 第二阶段）
- ❌ 并行执行（串行足够，6-9 分钟可接受）
- ❌ HTML 可视化报告（文本报告足够）
- ❌ 趋势分析（需要历史数据存储）
- ❌ `personal` profile（先验证 `outsourcing`）
- ❌ 更多初始状态（3 个场景足够验证概念）

## Technical Approach

### 架构设计

```
workflow-validate-matrix (Skill)
  ↓ 调用
validate-matrix.py (CLI 入口)
  ↓ 使用
scenario_setup.py      # 场景初始化
validation_runner.py   # 验证执行
report_generator.py    # 报告生成
constants.py           # 常量定义
```

### 核心流程

```python
def main():
    # 1. 预检查
    check_disk_space()
    check_trellis_available()
    
    # 2. 场景定义
    scenarios = [
        {"name": "clean", "setup": setup_clean},
        {"name": "existing-trellis", "setup": setup_existing_trellis},
        {"name": "existing-workflow", "setup": setup_existing_workflow},
    ]
    
    # 3. 执行矩阵验证
    results = []
    for scenario in scenarios:
        temp_dir = create_unique_temp_dir(scenario["name"])
        try:
            scenario["setup"](temp_dir)
            findings = run_validations(temp_dir)
            results.append({
                "scenario": scenario["name"],
                "status": "success",
                "findings": findings
            })
        except Exception as e:
            results.append({
                "scenario": scenario["name"],
                "status": "failed",
                "error": str(e)
            })
        finally:
            if not args.keep_temp:
                cleanup(temp_dir)
    
    # 4. 生成报告
    generate_report(results, output_path)
```

### 场景初始化

#### Scenario 1: clean
```python
def setup_clean(temp_dir):
    subprocess.run(["git", "init"], cwd=temp_dir)
    subprocess.run(["git", "remote", "add", "origin", "..."])
    subprocess.run(["trellis", "init", "--claude", "--opencode", "--codex", "-y", "-u", "xzc"])
```

#### Scenario 2: existing-trellis
```python
def setup_existing_trellis(temp_dir):
    setup_clean(temp_dir)  # 复用 clean 逻辑
    # 已经有 trellis init，直接安装工作流
```

#### Scenario 3: existing-workflow
```python
def setup_existing_workflow(temp_dir):
    setup_existing_trellis(temp_dir)
    # 安装旧版本工作流（模拟升级）
    install_old_workflow(temp_dir)
```

### 验证执行

```python
def run_validations(temp_dir):
    findings = []
    
    # 1. detect-embed-state
    result = run_command([
        PYTHON_BIN,
        WORKFLOW_ROOT / "commands/detect-embed-state.py",
        "--project-root", temp_dir
    ])
    findings.extend(parse_detect_output(result))
    
    # 2. install-workflow
    result = run_command([
        PYTHON_BIN,
        WORKFLOW_ROOT / "commands/install-workflow.py",
        "--project-root", temp_dir,
        "--profile", "outsourcing",
        "--cli", "claude,opencode,codex"
    ])
    findings.extend(parse_install_output(result))
    
    # 3. upgrade-compat
    result = run_command([
        PYTHON_BIN,
        WORKFLOW_ROOT / "commands/upgrade-compat.py",
        "--project-root", temp_dir,
        "--check"
    ])
    findings.extend(parse_compat_output(result))
    
    # 4. workflow-state (如果存在)
    if (temp_dir / ".trellis/scripts/workflow/workflow-state.py").exists():
        result = run_command([
            PYTHON_BIN,
            temp_dir / ".trellis/scripts/workflow/workflow-state.py",
            "route"
        ])
        findings.extend(parse_state_output(result))
    
    return findings
```

### 报告生成

```python
def generate_report(results, output_path):
    # 汇总所有 findings
    all_findings = []
    scenario_results = []
    
    for result in results:
        if result["status"] == "success":
            for finding in result["findings"]:
                finding["scenario"] = result["scenario"]
                all_findings.append(finding)
            scenario_results.append({
                "scenario": result["scenario"],
                "status": "✅ Success",
                "findings_count": len(result["findings"])
            })
        else:
            scenario_results.append({
                "scenario": result["scenario"],
                "status": "❌ Failed",
                "error": result["error"]
            })
    
    # 生成 WORKFLOW_QUESTIONS.md
    report = generate_workflow_questions_md(
        all_findings,
        scenario_results,
        matrix_validation=True,
        scenarios_tested=len(results)
    )
    
    output_path.write_text(report)
```

### 关键决策

1. **临时目录命名**：`/tmp/trellis-matrix-{timestamp}-{scenario}`
2. **超时设置**：每个验证步骤 5 分钟
3. **错误处理**：捕获异常，记录详情，继续下一个场景
4. **清理策略**：默认删除，`--keep-temp` 保留

## Decision (ADR-lite)

**Context**: 
- 当前 workflow-scan/repair 循环执行上百次仍发现新问题
- 每次只验证单一场景，修复可能破坏其他场景
- 需要全面验证避免循环

**Decision**: 
- 新增 `workflow-validate-matrix` skill
- 保留 `workflow-scan` 用于快速迭代
- MVP 覆盖 3 个关键场景
- 继续执行策略（部分失败不阻塞）
- 混合实现（skill 自包含 + subprocess 调用标准命令）

**Consequences**:
- **优点**：
  - 一次性发现所有问题，打破循环
  - 与现有 workflow-repair 无缝集成
  - 可扩展到更多场景
- **缺点**：
  - 运行时间较长（6-9 分钟 vs 5-10 秒）
  - 需要维护场景定义
- **风险**：
  - 场景覆盖可能仍不完整（第二阶段扩展）
  - 临时目录管理可能有边界情况

## Out of Scope (explicit)

### 第一阶段不包含
- 修改 workflow-scan/repair 的核心扫描逻辑
- 重构整个工作流安装流程
- 解决所有历史遗留问题（只关注循环问题）
- 并行执行多个场景（串行足够，6-9 分钟可接受）
- HTML 可视化报告（文本报告足够）
- 趋势分析（需要历史数据存储）
- `personal` profile 测试（先验证 `outsourcing`）
- 更多初始状态（dirty-git, partial-install）
- 单独 CLI 测试（只 claude、只 codex）
- 配置文件驱动（v1.1 功能）
- 命令行参数（v1.2 功能）

### 明确边界
- 只创建新 skill，不修改现有 workflow-scan/repair
- 只验证工作流安装结果，不修复问题（修复由 workflow-repair 负责）
- 只支持 Linux/macOS（Windows 支持留待后续）
- 临时项目路径固定为 `/tmp/trellis-matrix-*`（不支持自定义）

## Technical Notes

### 相关文件
- `skills/workflow-scan/SKILL.md`
- `skills/workflow-repair/SKILL.md`
- `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- `docs/workflows/新项目开发工作流/commands/detect-embed-state.py`
- `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`

### 用户原始命令序列
```bash
cd /tmp
rm -rf /tmp/trellis-$(trellis -v)-2
mkcd /tmp/trellis-$(trellis -v)-2
git init
trellis init --claude --opencode --codex -y -u xzc
# ... 安装工作流
# ... 运行验证
```

### 关键约束
- 临时项目路径: `/tmp/trellis-{VERSION}-2`
- Python 解释器: `/ops/softwares/python/bin/python3`
- 工作流根目录: `/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流`
