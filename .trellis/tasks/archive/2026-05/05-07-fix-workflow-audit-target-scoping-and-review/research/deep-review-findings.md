# workflow-audit 深审记录

## 已确认问题

### 1. 目标范围声明与执行语义不一致

* `workflow_path` 默认值已固定为 `docs/workflows/新项目开发工作流/`，但 skill 顶部描述、
  trigger wording、Step 1 target resolution 仍保留泛化 `docs/workflows/*` 语义。
* 结果是：自然语言触发时，执行者可能把 repo root / current project 当成主要审计对象。

### 2. repo root / workflow root / target project 边界仍然容易混淆

* 现有 skill 已有 `source repo` / `generated target project` / `runtime command output`
  标签要求，但没有把“静态审计默认只读固定 workflow root 及其引用链”写成强约束。
* `this repository`、`repo-local platform directories` 等表述在没有配套限制句时，会放大
  歧义。

### 3. 测试覆盖对默认目标解析不足

* 现有测试大量显式写出 `docs/workflows/新项目开发工作流/` 或 `workflow_path:`。
* 尚未覆盖“用户只说 audit this workflow / workflow-audit 默认运行”时，skill 必须显式
  解析并报告固定 workflow root，而不是自行把 repo root 当目标。

## 待在实现中复核的问题

* `.claude/skills/workflow-audit/` 是否与 `.agents/skills/workflow-audit/` 完全同构。
* references 与 tests 中是否还残留 `docs/workflows/*` 泛化表述。
* 是否存在 source-of-truth 漂移：spec 已收紧但 skill copy 未收紧，或反之。
