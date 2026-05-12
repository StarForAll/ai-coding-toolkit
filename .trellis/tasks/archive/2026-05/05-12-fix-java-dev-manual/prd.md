# 修正 Java 开发手册 MD 内容

## Goal

将 `./tmp/Java开发手册.md` 文件内容与 PDF 原文（`./tmp/Java开发手册.pdf`）进行对比，修正 MD 文件中的格式问题和内容错误，使其准确反映 PDF 原文内容。

## What I already know

- PDF 已有提取的文本文件：`./tmp/Java开发手册_extracted.txt`（2539 行）
- 现有 MD 文件：`./tmp/Java开发手册.md`（2237 行）
- MD 文件存在以下问题：
  1. **前言部分重复**：第 2-46 行和第 49-57 行出现了两次前言内容
  2. **版本表格重复**：版本历史表格出现了两次（第 115-117 行和第 121-123 行）
  3. **格式差异**：MD 文件使用了 markdown 格式（粗体、代码块），而提取的文本是纯文本
  4. **多余空行**：MD 文件中段落间有多余的空行
  5. **页码和页眉**：提取的文本中有页码（如 "1/44"）和页眉（"Java 开发手册"）需要移除

## Requirements

1. 移除 MD 文件中的重复内容（前言、版本表格）
2. 保持 MD 文件的 markdown 格式（粗体、代码块等）
3. 确保内容与 PDF 原文一致
4. 移除提取文本中的页码和页眉
5. 清理多余空行，保持合理的段落间距

## Acceptance Criteria

- [ ] 前言部分只出现一次
- [ ] 版本表格只出现一次
- [ ] 所有章节内容与 PDF 原文一致
- [ ] markdown 格式正确（粗体、代码块等）
- [ ] 没有多余的空行
- [ ] 没有页码和页眉残留

## Definition of Done

- MD 文件内容与 PDF 原文一致
- markdown 格式规范
- 文件可正常渲染

## Technical Approach

1. 使用 pdfplumber 重新提取 PDF 文本（如果需要）
2. 对比现有 MD 文件和提取的文本
3. 修正 MD 文件中的问题
4. 验证修正后的内容

## Decision (ADR-lite)

**Context**: 用户需要修正 Java 开发手册 MD 文件内容，使其与 PDF 原文一致
**Decision**: 保持现有的 markdown 格式（粗体、代码块等），便于阅读和渲染
**Consequences**: 需要保留 markdown 格式标记，同时修正内容错误

## Out of Scope

- 不修改 PDF 文件本身
- 不添加 PDF 中没有的内容
- 不改变文档的整体结构

## Technical Notes

- PDF 文件路径：`./tmp/Java开发手册.pdf`
- 提取的文本路径：`./tmp/Java开发手册_extracted.txt`
- MD 文件路径：`./tmp/Java开发手册.md`
- 使用 pdfplumber 进行文本提取
