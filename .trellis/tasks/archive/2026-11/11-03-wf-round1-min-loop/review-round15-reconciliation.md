# 第十五轮外部评审的复核与修正（2 项）

- 复核对象：外部评审第 15 轮 2 条（含实际入口复现）
- 处置编号 R51–R52；实施与实跑见 `validation.md` §38

## 0. 结论

| # | 原判 | 复核 | 契约依据 | 处置 |
|---|---|---|---|---|
| 1 | 复杂任务三件套完整性未进入批准/开工门禁 | **成立** | 设计稿 §4.2/§4.3（复杂三件套、模板占位判定）、机制稿 §1.3/§2.3 | R51 |
| 2 | `disable` 生成损坏 frontmatter 仍报成功 | **成立** | 机制稿 §8.4 变更须可应用；设计稿 §6.1 frontmatter 结构 | R52 |

## 1. 复核

### R51｜三件套完整性（原判 1）
`task-approve` 只校验 PRD 与 plan 块；`artifact_digests` **只收集实际存在的文件**，缺失的 design/implement 不会出现在摘要里，因此缺文件与保留占位都能通过批准与开工。探针两条都 `WF_OK`。文件摘要参与版本哈希，确实不等于「齐全且已填」。

### R52｜disable 破坏 frontmatter（原判 2）
`_rewrite_frontmatter` 写出起始 `---` 与元数据后直接接正文（`output.extend(lines[index + 1:])`），**结束分隔符被吞掉**；解析器随即报 `frontmatter not closed`，入口却返回 `WF_OK`。变更后的结构从未复验。

## 2. 处置

### R51（代码）
- 新增 `tasks.complex_artifact_problems(root, task, complexity)`：复杂度为 `complex` 时逐份检查 `design.md`/`implement.md`——缺失记 `missing`，含 `{{WF_REQUIRED:…}}` 记 `unfilled placeholders`（复用 `templates.find_markers`/`find_value_markers`）。
- `task-approve` 在复杂度确定后调用；`task-start` 在既有 PRD 占位校验之后、同一位置追加同一校验（开工复核）。
- 返回既有原因码 `WF_TEMPLATE_INCOMPLETE`（其出口文案正是「填写模板声明的待填位置」，符合语义）。

### R52（代码）
- `_rewrite_frontmatter` 在元数据后补回 `---`。
- `disable` 写盘后**重新解析**并核对 `status=disabled` 且无 problems，否则 `WF_RECORD_INVALID`，不报告成功。

## 3. 边界

- 不新增原因码或字段。
- 只对 `complex` 生效：轻量任务仍是 PRD-only（不误伤）。
- 不改模板本身：占位的是模板一行，判据用既有标记规则。

## 4. 对收口状态的影响

R51 属「已有的分级要求未落地」，R52 属「变更破坏结构仍报成功」，均收口前必修。落地后需重跑批准/开工（CP1/CP2、R15/R17/R26、R44）、spec 变更（CP3/CP5、R9/R19/R46）与三夹具全流程、F0。
