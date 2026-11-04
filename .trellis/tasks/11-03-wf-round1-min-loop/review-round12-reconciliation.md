# 第十二轮外部评审的复核与修正（2 项）

- 复核对象：外部评审第 12 轮 2 条（含隔离探针）
- 处置编号 R47–R48；实施与实跑见 `validation.md` §35

## 0. 结论

| # | 原判 | 复核 | 契约依据 | 处置 |
|---|---|---|---|---|
| 1 | spec 读取入口跟随链接读到项目外文件 | **成立** | 设计稿 §3.1「不通过符号链接把写入引出项目边界」、§6.1 真实落点 | R47 |
| 2 | spec 写入未拒绝嵌套仓库目标 | **成立** | 设计稿 §6.1「工作树内任一目录含 `.git` 即视为嵌套仓库根…不可路由」、机制稿 §3.1 | R48 |

## 1. 复核

**R47**：`cmd_spec` 只做 `paths.normalize`，随后 `load_spec` 直接打开文件；`.wf/spec/link.md → /tmp/…` 的链接被正常读取，正文与完整读取侧车都落了盘。真实落点从未核对。

**R48**：`validate_changes` 校验了「仍在项目根内」，但没有消费已有的 `paths.nested_repo_boundary()`；构造 `.wf/spec/child/.git/` 后仍可写入 `.wf/spec/child/new.md`，宽 `touch_paths`（`.wf/spec/**`）也挡不住。

两条都是**既有边界函数未被这两条路径消费**，不是新增加固建议。

## 2. 处置

### R47｜读取侧真实落点（代码）
- 新增 `spec.path_violation(root, relative)`：`realpath` 必须仍在项目根内，且 `paths.nested_repo_boundary()` 为空。
- `load_spec` 在读取前调用它：违规时返回 `routable: false` + `violation` 文案，不返回 metadata/正文/摘要。
- `cmd_spec` 遇到 `violation` 直接 `WF_PATH_INVALID`（facts 给原因与路径），由此**不会写完整读取侧车**、不返回正文；`match`/`all_specs` 也因此把越界链接视为不可路由，避免它混进匹配。

### R48｜写入侧嵌套仓库（代码）
- `validate_changes` 在既有 `realpath` 核对之后追加 `paths.nested_repo_boundary()` 判定，命中即 `WF_PATH_INVALID`（reason 带嵌套根路径），零写入。
- 覆盖改名旧端与新端、删除目标与新增目标（同一循环）。

## 3. 边界

- 不新增原因码：沿用 `WF_PATH_INVALID`。
- 不自动删除越界链接或嵌套根：只拒绝并报告。
- 不改 `.wf/spec/**` 的类别规则：边界判定与类别判定互相独立，同时生效。

## 4. 对收口状态的影响

两条都属「既有边界未落实到具体入口」，属正确性缺陷，收口前必修。落地后需重跑：spec 读取（F1 生命周期、R13/R18/R43）、spec 写入（CP3/CP5、R8/R9/R17/R19/R26）、三夹具全流程与 F0。
