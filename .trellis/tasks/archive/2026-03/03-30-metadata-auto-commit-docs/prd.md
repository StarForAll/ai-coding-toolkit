# 补充元数据自动提交辅助流程文档

## 目标

为"元数据自动提交辅助流程"创建独立的精简版文档，并同步更新相关联的工作流文档。

## 需求

### 功能需求

1. **新增独立文档** `docs/workflows/新项目开发工作流/commands/metadata-auto-commit.md`
   - 精简版（2-3页）
   - 包含核心流程、校验清单、失败处理
   - 符合现有 commands/ 文档结构

2. **同步更新关联文档**
   - `docs/workflows/新项目开发工作流/工作流总纲.md` §7.4
   - `docs/workflows/新项目开发工作流/commands/delivery.md` Step 10
   - `docs/workflows/新项目开发工作流/命令映射.md`

### 非功能需求

- 保持文档风格与现有工作流文档一致
- 使用中文编写
- 添加适当的交叉引用

## 验收标准

- [ ] 新增 `metadata-auto-commit.md` 文档，结构完整
- [ ] 工作流总纲 §7.4 更新为引用新文档
- [ ] delivery.md Step 10 更新为引用新文档
- [ ] 命令映射.md 补充约束部分更新
- [ ] 所有文档通过格式校验

## 技术要点

- 参考现有 `.agents/skills/record-session/SKILL.md` 的实现细节
- 基于 `.trellis/scripts/common/git.py::auto_commit_paths()` 的实现
- 保持与 `task.py archive` 和 `add_session.py` 的行为一致

## 相关文件

- `.agents/skills/record-session/SKILL.md`
- `.trellis/scripts/common/git.py`
- `.trellis/scripts/task.py`
- `.trellis/scripts/add_session.py`
