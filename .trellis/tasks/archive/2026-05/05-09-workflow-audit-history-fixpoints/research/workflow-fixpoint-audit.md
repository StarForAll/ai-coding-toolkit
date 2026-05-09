# Research: 工作流修复点审计

- **Query**: 深度分析6个历史修复点，判断当前工作流是否真正满足要求
- **Scope**: 内部（代码 + 文档交叉比对）
- **Date**: 2026-05-09

## Findings

---

### 修复点 1: 前置校验 — Git 项目 + 多 remote push URL + 参考命令

**是否满足**: ✅ 已满足

**证据**:

| 文件 | 位置 | 说明 |
|---|---|---|
| `install-workflow.py` | L631-653 `ensure_project_prereqs()` | 检查 `.git` 存在、`.trellis/` 存在、`.trellis/.version` 存在、`origin` push URL 数量 >= 2 |
| `install-workflow.py` | L112-113 | 常量 `_ORIGIN_REMOTE_NAME = "origin"`, `_MIN_ORIGIN_PUSH_URLS = 2` |
| `install-workflow.py` | L550-580 `count_origin_push_urls()` | 解析 `.git/config`，统计 `[remote "origin"]` 下的 `pushurl` 条目数 |
| `install-workflow.py` | L643-650 | 不满足时输出错误信息含完整参考命令: `git remote add origin <URL>`, `git remote set-url --add --push origin <URL>`, `git remote set-url --add --push origin <URL>` |
| `工作流总纲.md` | L29-43 | "使用前提与安装时序"节明确列出：目标项目必须是 Git 项目、origin 至少两个 push URL、已执行 trellis init；附参考命令 `git remote set-url --add --push origin` |

**详细分析**:

- `ensure_project_prereqs()` 在 `main()` L1550 处被调用，是安装脚本的第一个前置检查
- 错误信息中的参考命令与修复点要求的 `git remote set-url --add --push origin` 格式一致
- `工作流总纲.md` L36-40 也给出了同样的参考命令

---

### 修复点 2: 初始阶段导入 spec 应通过脚本导入而非用户输入提示

**是否满足**: ✅ 已满足

**证据**:

| 文件 | 位置 | 说明 |
|---|---|---|
| `install-workflow.py` | L1344-1378 `import_requirements_foundation()` | 调用 `trellis-library/cli.py assemble --target <root> --pack pack.requirements-discovery-foundation --auto` |
| `install-workflow.py` | L110 | 常量 `_REQUIREMENTS_FOUNDATION_PACK = "pack.requirements-discovery-foundation"` |
| `install-workflow.py` | L1648-1655 | `main()` 中在 CLI 资产部署成功后自动调用 `import_requirements_foundation()` |
| `工作流总纲.md` | L263-266 | "若已嵌入对应的自定义工作流，安装脚本应**立即通过脚本导入** trellis-library 中的需求发现基础资产；导入方式：使用 `trellis-library/cli.py assemble`，不靠人工复制资产或自然语言提示'补装'" |
| `workflow-installed.json` (临时项目) | L66 | `"initial_pack": "pack.requirements-discovery-foundation"` — 安装记录确认实际导入 |
| `library-lock.yaml` (临时项目) | 存在 | 22615 字节，确认 trellis-library assemble 已实际执行 |

**详细分析**:

- 安装脚本在 `main()` 的第 1648 行自动调用 `import_requirements_foundation()`，无需用户手动干预
- 使用 `--auto` 参数确保非交互式导入
- 若导入失败，安装流程终止并标记 embed attempt 为 failed
- `工作流总纲.md` 明确写"不靠人工复制资产或自然语言提示'补装'"

---

### 修复点 3: 00-bootstrap-guidelines 删除 + finish-work 中 pnpm 校验删除

**是否满足**: ✅ 已满足

**证据**:

#### 3a: bootstrap task 删除

| 文件 | 位置 | 说明 |
|---|---|---|
| `install-workflow.py` | L1473-1498 `remove_bootstrap_task()` | 删除 `.trellis/tasks/00-bootstrap-guidelines/`；返回 "removed" / "absent" / "dry-run-removed" |
| `install-workflow.py` | L611-628 `clear_bootstrap_current_task_if_needed()` | 若 `.current-task` 指向 bootstrap task，清空引用 |
| `install-workflow.py` | L1659 | `main()` 中调用 `remove_bootstrap_task()` |
| `workflow-installed.json` (临时项目) | L67-68 | `"bootstrap_task_removed": true`, `"bootstrap_cleanup_status": "removed"` |
| `/tmp/trellis-0.5.9-2/.trellis/tasks/` | 目录为空 | bootstrap task 已被删除 |

#### 3b: pnpm 校验删除

| 文件 | 位置 | 说明 |
|---|---|---|
| `finish-work-patch-projectization.md` | 全文 | 补丁内容不含任何 `pnpm` 字样；使用 `<your-quality-platform-gate-command-here>` 占位 |
| `finish-work-patch-projectization.md` | L1-3 | "不要继续沿用 Trellis 基线里的默认包管理器占位命令" |
| `finish-work-patch-projectization.md` | L20-22 | "这里不再保留任何默认包管理器占位" |
| `test_workflow_installers.py` | L499, 620-621, 763, 2171 | 测试断言 `assertNotIn("pnpm lint", ...)` / `assertNotIn("pnpm test", ...)` |

**详细分析**:

- bootstrap task 删除功能完整：删除目录 + 清理 `.current-task` 悬空引用 + 记录清理状态到 `workflow-installed.json`
- finish-work 补丁完全移除了 pnpm 占位，改为要求项目在 design 3.7 阶段定义真实检查矩阵
- 测试代码明确验证了 pnpm 不再出现在部署后的 finish-work 中

---

### 修复点 6: 初始阶段校验 main 分支 + 技术架构确认后写真实命令/替代门禁

**是否满足**: ✅ 已满足

**证据**:

#### 6a: main 分支校验

| 文件 | 位置 | 说明 |
|---|---|---|
| `install-workflow.py` | L522-547 `enforce_initial_main_branch_policy()` | 无本地提交历史 + 非 main 分支 → `sys.exit`；有历史 → 仅 warn |
| `install-workflow.py` | L509-519 `has_local_commit_history()` | 通过读取 HEAD ref 和 packed-refs 判断是否有提交历史 |
| `install-workflow.py` | L652 | `ensure_project_prereqs()` 末尾调用 `enforce_initial_main_branch_policy()` |
| `feasibility.md` | L32-33, L45-46 | Step 0: "新建仓库，主分支必须为 main"；"已有本地提交历史的项目不强制切换" |
| `工作流总纲.md` | L233-234 | "若目标项目是新建仓库...必须为 main"；"已有本地提交历史...不强制切换" |

#### 6b: 技术架构确认后写真实命令 + SonarQube / 替代门禁

| 文件 | 位置 | 说明 |
|---|---|---|
| `design.md` (源) | L379-394 | "自动化检查矩阵要求...采用 Sonar 的项目必须写真实命令，未采用时必须写替代门禁和原因"；含 `sonar-scanner` 命令骨架 |
| `design.md` (部署版) | L379-394 | 同上，命令在部署后目标项目中保持一致 |
| `工作流总纲.md` | L1621-1626 | "不再允许使用'默认 Lint''基础检查已覆盖'这类模糊表述...采用 Sonar 的项目必须写真实命令，未采用时必须写替代门禁和原因" |
| `finish-work-patch-projectization.md` | L20-22 | "必须有明确质量平台门禁；采用 Sonar 的项目必须写真实命令，未采用时必须写替代门禁和原因" |

**详细分析**:

- main 分支门禁逻辑精确区分了"新建项目"和"已有历史项目"两种场景
- feasibility 命令的 Step 0 和安装脚本的 `enforce_initial_main_branch_policy()` 口径一致
- Sonar/SonarQube 真实命令骨架在 `design.md` 中给出（`sonar-scanner -Dsonar.projectKey=...`），并明确要求"未采用时必须写替代门禁和原因"
- 该约束同时在 `工作流总纲.md` §3.7、`design.md` 和 `finish-work-patch-projectization.md` 三处保持一致

---

### 修复点 14: feasibility 阶段不可跳过性

**是否满足**: ⚠️ 部分满足

**证据**:

| 文件 | 位置 | 说明 |
|---|---|---|
| `feasibility.md` | L11 (Gate Rule) | "对于新项目 / 新客户需求 / 首次立项，`/trellis:feasibility` 是进入 `/trellis:brainstorm` 前的**强制前置门禁**" |
| `feasibility.md` | L137 | "若哪些前提变化，必须回到 `/trellis:feasibility`" |
| `brainstorm.md` (部署版) | L8, L25 | brainstorm 的前置条件: "前: `/trellis:feasibility`"；"若 `assessment.md` 不允许进入 brainstorm，先回 feasibility" |
| `brainstorm.md` (部署版) | L32-33 | "若当前项目尚未形成有效 `assessment.md`...必须先回 `/trellis:feasibility`" |
| `工作流总纲.md` | L355 | "前置条件：新项目默认已完成阶段一可行性评估...否则应先回到 `/trellis:feasibility` 补做评估" |
| `阶段状态机与强门禁协议.md` | L9-13 | 强门禁模式总则："每个阶段都必须有明确的进入条件" |

**缺口描述**:

1. **缺少机器强制的可行性检测**：当前 feasibility 的"不可跳过性"仅通过文档约束（feasibility.md Gate Rule、brainstorm.md 前置条件）表达。`workflow-state.py validate` 在后续阶段会校验 `assessment.md` 中的粗估门禁，但没有证据表明 `workflow-state.py validate` 或任何脚本会**在 brainstorm 入口处自动检测并阻断**缺少有效 `assessment.md` 的场景。

2. **brainstorm 命令内部虽写了前置判定（L82-96）**，但这是给 AI 阅读的自然语言指令，不是脚本级硬门禁。AI 仍可能在未读 feasibility 前置条件时直接进入 brainstorm 流程。

3. **feasibility.md L11 的 Gate Rule 覆盖范围**为"新项目 / 新客户需求 / 首次立项"，但未明确"非新项目但首次使用本 workflow"的强制覆盖。工作流总纲 L232-233 有部分覆盖，但二者措辞不完全一致。

**建议**: 在 `workflow-state.py validate` 中增加 `brainstorm` 入口的 `assessment.md` 存在性与有效性检查；或在 `brainstorm.md` 中增加一个显式的校验步骤调用 `feasibility-check.py` 做前置验证。

---

### 修复点 20: 初始化项目后 .current-task 应为空 + 无两个远程仓库时提示命令

**是否满足**: ⚠️ 部分满足

**证据**:

#### 20a: 安装后 .current-task 应为空

| 文件 | 位置 | 说明 |
|---|---|---|
| `install-workflow.py` | L611-628 `clear_bootstrap_current_task_if_needed()` | 若 `.current-task` 指向 bootstrap task，清空引用（写空字符串） |
| `/tmp/trellis-0.5.9-2/.trellis/` | .current-task 文件不存在 | 安装后确认无 `.current-task` 文件 |

**缺口描述**:

- `clear_bootstrap_current_task_if_needed()` 只在 `.current-task` **指向 bootstrap task** 时才清理。如果 `.current-task` 指向其他任务（理论上不太可能，因为新项目只有 bootstrap），则不会清空。
- 更重要的缺口：该函数将 `.current-task` 写为**空字符串**（L626: `current_task_file.write_text("", encoding="utf-8")`），而不是**删除文件**。这意味着安装后 `.current-task` 文件仍然存在，只是内容为空。根据修复点 20 的要求"`.current-task` 应该为空"，空字符串在语义上满足"为空"，但从阶段状态机协议来看（`阶段状态机与强门禁协议.md` L35-41），`.current-task` 不能为空时应"不允许识别当前阶段"——空字符串文件存在时，读取结果为空，效果等同于不存在。不过，临时项目实际验证结果为 `.current-task` 文件完全不存在（`find` 未找到），说明当 bootstrap task 被删除时，`.current-task` 可能已被完全移除或本来就不存在。

**验证结果**: 临时项目安装后 `.current-task` 文件不存在 ✅

#### 20b: 无两个远程仓库时提示远程仓库创建命令

| 文件 | 位置 | 说明 |
|---|---|---|
| `install-workflow.py` | L643-650 | `ensure_project_prereqs()` 在 push URL < 2 时 `sys.exit` 并输出完整参考命令 |

**缺口描述**:

- 当前逻辑在 push URL 不满足时**直接终止安装**（`sys.exit`），而非仅"提示"后继续。这与修复点 20 的"提示对应的远程仓库创建命令"措辞有微妙差异：修复点说"提示"，当前实现是"阻断 + 提示"。
- 从安全角度看，"阻断 + 提示"比"仅提示"更严格。修复点 20 的意图是确保用户知道如何配置多 push URL，当前实现已满足该意图，只是执行方式为硬阻断而非软提示。

**总结**: 20a 在实践中已满足（`.current-task` 不存在）；20b 在功能上已满足（输出参考命令），但执行方式为硬阻断而非软提示——更严格，可视为满足。

---

## 汇总表

| # | 修复点 | 是否满足 | 关键缺口 |
|---|---|---|---|
| 1 | 前置校验: Git + 多 remote + 参考命令 | ✅ 已满足 | 无 |
| 2 | 初始阶段 spec 通过脚本导入 | ✅ 已满足 | 无 |
| 3 | bootstrap 删除 + pnpm 校验删除 | ✅ 已满足 | 无 |
| 6 | main 分支校验 + 真实命令/替代门禁 | ✅ 已满足 | 无 |
| 14 | feasibility 不可跳过性 | ⚠️ 部分满足 | 仅文档级约束，缺少脚本级硬门禁在 brainstorm 入口自动检测 assessment.md |
| 20 | .current-task 为空 + 无双 remote 提示命令 | ⚠️ 部分满足 | 20a 实测已满足但仅清理 bootstrap 引用而非通用清空；20b 以硬阻断代替软提示，功能满足但语义更严 |

## Caveats / Not Found

- 未找到 `workflow-state.py` 源码（它在 `commands/shell/` 下），无法确认 `validate` 子命令是否包含 brainstorm 入口的 `assessment.md` 检查
- 修复点 20 中提到的 "`.current-task`" 已被 Trellis 0.5.9 的 session-scoped runtime 取代，但 `.current-task` 文件在旧基线中仍可能存在；修复点原文已注明这只是"记录旧 workflow 的历史修复点"
