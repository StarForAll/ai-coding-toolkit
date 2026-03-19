# 支持多次拉取 spec 的模拟-执行两阶段流程

## Goal

实现 trellis-library 中将 spec 拉取到目标项目时的**两阶段流程**：先模拟对比、再用户确认、最后执行。支持同一项目中分批次拉取不同资产的场景，并正确处理本地文件冲突。

## Requirements

### 核心流程

1. **阶段 1 - 模拟 (Simulate)**：执行完整的 dry-run 分析，收集所有资产的对比结果
   - 三方对比：源 (trellis-library) vs 目标 (target project) vs 基准 (lock 中的 checksum)
   - 检测本地文件（不在 lock 中的 .trellis/ 下文件）
   - 分类每个资产：New / Identical / Source Updated / Target Modified / Both Modified / Local-Conflict
   - 输出完整模拟报告

2. **决策点**：
   - 全部为平凡场景 (New + Identical + Existing) → 直接进入阶段 2
   - 存在非平凡场景 → 展示报告 → 用户逐项确认处理方式

3. **阶段 2 - 执行 (Execute)**：按用户确认的方案批量执行
   - 文件操作：Copy / Merge / Skip / Backup+Copy / Convert+Copy / Preserve+Copy
   - Lock 合并：selection 并集、import 去重、history 保留

### 场景处理

| 场景 | 分类 | 默认行为 |
|------|------|---------|
| 首次拉取（目标不存在） | New | 自动复制 |
| 源更新了，目标未改 | Source Updated | 手动审查 |
| 源未变，目标被修改 | Target Modified | 手动审查 |
| 双方都改了 | Both Modified | 手动审查 |
| 内容完全一致 | Identical | 自动跳过 |
| 已在 lock 中 | Existing | 自动跳过 |
| 本地文件无路径冲突 | Local-Only | 自动保护 |
| 目录型资产覆盖本地文件 | Local-Conflict | 手动审查 + 警告 |
| 文件型资产与本地文件同名 | Local-Conflict | 手动审查 + 警告 |
| Lock 丢失 | — | 自动初始化 |
| Lock 损坏 | — | 报错退出 |

### CLI Flags

- 默认：两阶段流程（模拟 → 有冲突则交互 → 执行）
- `--analyze-only` / `--dry-run`：仅模拟，不执行
- `--auto`：跳过交互，无冲突自动执行
- `--force`：跳过模拟，直接覆盖
- `--json`：JSON 输出

## Acceptance Criteria

- [ ] 新建 `analyze-library-pull.py`，实现三方对比分析
- [ ] 修改 `write-library-lock.py`，支持 `--merge` 模式
- [ ] 修改 `assemble-init-set.py`，集成两阶段流程
- [ ] 修改 `cli.py`，透传新 flags
- [ ] 首次拉取（无 lock）正常工作
- [ ] 多次拉取不同资产，lock 正确合并（不丢失已有数据）
- [ ] 重复拉取同一资产，正确检测变更并提示
- [ ] 本地文件冲突场景正确检测和提示
- [ ] Lock 损坏时给出清晰错误提示
- [ ] `--dry-run` / `--json` / `--force` 正常工作
- [ ] 通过 `python3 trellis-library/cli.py validate --strict-warnings` 验证

## Technical Notes

- 模拟阶段不修改任何文件（纯分析）
- Lock 合并是加法操作：selection 取并集、import 按 asset_id 去重、history 保留
- 本地文件检测：扫描 .trellis/ 下所有文件，与 lock imports 交叉比对
- 三方对比基准从 lock 的 source_checksum / last_local_checksum 获取
- 本地文件用户选项：Preserve / Backup / Convert / Overwrite / Skip

## Out of Scope

- 版本迁移（manifest 大版本升级、资产重命名/ID 映射）
- 资产回滚/移除子命令
- 条件性拉取（--exclude 选项）
- Git merge 冲突解决工具
- Markdown 语义级合并（section-level merge）的自动实现 — 本次仅提供框架，用户手动决策
