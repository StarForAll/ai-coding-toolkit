# Research: Gap #17 总工时估算缺标准化机器字段

- **Query**: total_effort_hours / total_effort 机器字段是否已添加到 feasibility-check.py、workflow-state.py、brainstorm.md、plan.md 中
- **Scope**: internal
- **Date**: 2026-05-09

## Findings

### Files Found

| File Path | Description |
|---|---|
| `/tmp/trellis-0.5.9-2/.trellis/scripts/workflow/feasibility-check.py` | 安装后的 feasibility-check |
| `/tmp/trellis-0.5.9-2/.trellis/scripts/workflow/workflow-state.py` | 安装后的 workflow-state |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/brainstorm.md` | 安装后的 brainstorm |
| `/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/brainstorm.md` | 源码 brainstorm |
| `/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/plan.md` | 源码 plan |

### `total_effort_hours` 字段覆盖状态

#### 1. feasibility-check.py

- ASSESSMENT_TEMPLATE (line 115): `- \`total_effort_hours\`: \`16\`（项目级正式粗估总工时；若只能区间估算，写中位值并在"当前结论的前提"说明上下界）`
- step_validate (line 316-322): 校验 total_effort_hours 字段存在且为数字格式
  ```python
  total_effort_hours = extract_backticked_field(content, "total_effort_hours")
  if total_effort_hours is None:
      errors.append("缺少 `total_effort_hours` 字段")
  elif not re.fullmatch(r"\d+(?:\.\d+)?", total_effort_hours.strip()):
      errors.append("`total_effort_hours` 只能填写数字小时值（如 `16` / `24.5`）")
  else:
      print(f"✅ `total_effort_hours`: {total_effort_hours}")
  ```
  **判定: ✅ 完整覆盖。字段名 `total_effort_hours`，带格式校验。**

#### 2. workflow-state.py

- TASK_ESTIMATE_MARKERS (line 72-80): 包含 `"total_effort_hours"` 作为项目级粗估标记
- validate_project_doc_boundary (line 737-745): 当 stage 在 PROJECT_ESTIMATE_REQUIRED_STAGES（= STAGES - {"feasibility", "brainstorm"}）时，检查 prd.md 是否包含 TASK_ESTIMATE_MARKERS 中的所有标记
  ```python
  missing_task_markers = find_missing_markers(task_prd, TASK_ESTIMATE_MARKERS)
  if missing_task_markers:
      errors.append(f"{TASK_PRD.as_posix()} 缺少项目级粗估字段: {', '.join(missing_task_markers)}")
  ```
  **判定: ✅ 完整覆盖。通过 find_missing_markers 检查 prd.md 中是否包含 total_effort_hours。**

  注意：PROJECT_ESTIMATE_REQUIRED_STAGES = STAGES - {"feasibility", "brainstorm"}，即从 design 阶段开始校验 prd.md 中的 total_effort_hours。feasibility 阶段由 feasibility-check.py 的 assessment.md 校验覆盖。

#### 3. brainstorm.md

安装后的 brainstorm.md:
- Step 8 (line 298-326): "在进入 design、plan 或任何执行阶段前，必须先产出不可跳过的项目级粗估"
- "由 workflow-state.py validate 强制检查项目级粗估门禁"
- 但 brainstorm.md 本身**没有显式提到 `total_effort_hours` 字段名**

源码 brainstorm.md: 同样没有显式提到 `total_effort_hours` 字段名

**判定: ⚠️ 部分覆盖。brainstorm.md 通过"项目级粗估"概念间接覆盖，但没有显式写出字段名。**

#### 4. plan.md (源码)

源码 plan.md:
- 前置条件 (line 39): "若属于外包、定制开发或新客户项目（外部项目），已在 assessment.md 中明确 delivery_control_track"
- Step 4 task_plan.md 摘要结构 (line 352-355): 外部项目交付控制包含 milestone_payment_schedule / non_payment_remedy_path / dispute_escalation_path
- 但 plan.md **没有显式提到 `total_effort_hours` 字段名**

**判定: ⚠️ 部分覆盖。plan.md 通过引用 assessment.md 和 prd.md 间接覆盖，但没有显式写出字段名。**

### `total_effort` vs `total_effort_hours` 命名

当前采用的字段名是 `total_effort_hours`（带单位后缀），而非 `total_effort`。这与上次审计建议的"总工时估算缺标准化机器字段"方向一致，但具体命名采用了更明确的 `total_effort_hours`，避免了 `total_effort` 的歧义（工时 vs 人天 vs 人月）。

## 判定: ✅ 已修复

### 修复证据

1. feasibility-check.py 的 ASSESSMENT_TEMPLATE 和 step_validate 均已包含 total_effort_hours 字段及其格式校验
2. workflow-state.py 的 TASK_ESTIMATE_MARKERS 包含 total_effort_hours，并通过 validate_project_doc_boundary 在 design 及后续阶段强制校验 prd.md 中是否存在该标记
3. 字段命名选择了 total_effort_hours（带单位），比 total_effort 更无歧义

### 残留缺口

- brainstorm.md 和 plan.md 没有显式写出 `total_effort_hours` 字段名，仅通过"项目级粗估"概念间接引用。这可能造成填写者不知道具体应使用哪个字段名。
- 但实际上，brainstorm.md Step 8 引用了 `workflow-state.py validate` 作为门禁执行者，而 workflow-state.py 会检查 prd.md 中是否包含 `total_effort_hours` 字符串。因此，即使 brainstorm.md 没有显式写出字段名，门禁机制仍能强制校验。

## Caveats / Not Found

- 无新增发现
