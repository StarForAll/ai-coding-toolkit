# Research: Gap #23 安装后提示未显式提醒 README.en.md

- **Query**: install-workflow.py 安装完成提示是否提及 README.en.md（双语提示）
- **Scope**: internal
- **Date**: 2026-05-09

## Findings

### Files Found

| File Path | Description |
|---|---|
| `/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/install-workflow.py` | 源码安装脚本 |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/design.md` | 安装后的 design 命令 |

### install-workflow.py 安装完成提示分析

源码 install-workflow.py 安装完成后的提示 (line 1711-1712):

```python
if not args.dry_run:
    info("后续 design 阶段请记得补齐项目根 README.md 与 README.en.md（块 C 英文补充版属于正式产物）")
```

**这已经同时提到了 README.md 和 README.en.md**，并注明"块 C 英文补充版属于正式产物"。

而"下一步（推荐）"部分 (line 1739):

```
print("    4. 在目标项目根 README.md 中说明 todo.txt 的存在与用途")
```

此处**只提到了 README.md**，没有提及 README.en.md。

### 上下文分析

1. Line 1712 的 info 提示是独立的、醒目的，明确提到 README.md **与** README.en.md
2. Line 1739 的"下一步"第 4 条只提到 README.md，但这条的具体内容是"说明 todo.txt 的存在与用途"，这是一个操作指引，不是文件生成提醒
3. design.md 块 C (line 331-337) 中明确要求生成 `README.md`（默认中文版）和 `README.en.md`（英文补充版）
4. workflow-state.py 的 `validate_project_doc_boundary` (line 766-770) 在 design 退出时校验 README.md **和** README.en.md 是否存在

### 对比上次审计

上次审计发现："install-workflow.py 行 1736 提示仅提及 README.md"。

当前状态下：
- 行 1712（独立 info 提示）：已提及 README.md **和** README.en.md ✅
- 行 1739（下一步第 4 条）：仅提及 README.md ⚠️

## 判定: ⚠️ 部分改善

### 修复证据

1. install-workflow.py line 1712 已新增独立的 info 提示，同时提到 README.md 和 README.en.md
2. design.md 块 C 已要求生成 README.en.md
3. workflow-state.py 已在 design 退出时校验 README.en.md 存在性

### 残留缺口

1. "下一步"列表中的第 4 条 (line 1739) 仅提及 README.md，没有提及 README.en.md。虽然该条是关于"在 README.md 中说明 todo.txt 的存在与用途"这一具体操作，但如果用户只看"下一步"列表，可能不会注意到 README.en.md 也需要处理。
2. 不过，独立 info 提示 (line 1712) 已覆盖了 README.en.md 的提醒，且 design 阶段的门禁机制也会强制校验，因此实际遗漏风险较低。

### 新发现

- 无

## Caveats / Not Found

- "下一步"第 4 条未提及 README.en.md 是一个小的信息不对称，但已被独立 info 提示和门禁机制双重覆盖，实际影响有限
