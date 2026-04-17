# Claude Code 适配

Claude Code 是当前 workflow 维护的三种原生适配之一，并保留项目命令入口承载方式；但这并不意味着所有 MCP / skills 细节都应直接写进命令正文或主 workflow 文档。
适配时应遵循 Claude Code 官方原生格式要求，但前置条件、阶段语义和初始化动作必须与 OpenCode / Codex 保持一致。

在这套 workflow 里，Claude Code 的正确承载模型是：

- `.claude/commands/trellis/`：workflow 阶段命令入口
- `AGENTS.md`：项目级长期稳定规则
- `.claude/settings.json` / `.claude/settings.local.json`：hooks、权限、工具可用性等运行时配置
- `.claude/hooks/*.py`：会话启动与子代理上下文注入
- `.claude/agents/*.md`：research / implement / check / debug 一类子代理
- skills / 通用脚本：复用能力资产，不应全部硬塞进命令正文

前置条件也要单独说清：

- 目标项目本身必须是 Git 项目
- 若是新建仓库（尚无本地提交历史），在第一次进入 workflow 前，本地主分支和初始分支必须是 `main`；若目标项目已存在本地提交历史，则不强制切换，仅记录现状
- `origin` 必须至少配置两个 push URL
- 目标项目必须已经执行过 `trellis init`
- 目标项目应能检测到 `trellis init` 产物，例如 `.trellis/.version`

这里要求同一个 `origin` 至少配置两个 push URL，是因为这套 workflow 默认按“同仓双推镜像”协作模型设计，常见场景是同时推送到 GitHub / Gitee；如果目标项目不采用这类双推同步策略，就不应直接套用当前变体。

这几个前提成立后，正确顺序是：先完成 `trellis init`，再执行当前 workflow 自带的安装脚本，由安装脚本把 Claude 所需命令入口和补丁真正落到目标项目，并自动导入 `pack.requirements-discovery-foundation`、删除 `00-bootstrap-guidelines`。

## 在多 CLI 同装中的定位

同一个目标项目里，默认会并存：

- `.claude/commands/trellis/*.md`
- `.opencode/commands/trellis/*.md`
- `.agents/skills/*/SKILL.md`

对 Claude Code 来说，这不改变它的原生入口判断：

- 用户阶段入口仍以 `/trellis:xxx` 为主
- Claude 的 hooks / settings / agents 是原生承载层
- 不应因为项目里同时安装了 Codex skills，就把 Claude Code 写成“只靠自然语言触发”

## 安装时序

若你的目标是让 Claude Code 在目标项目里直接可用这套 workflow，推荐做法是：

1. 确认目标项目满足 `Git + 新建仓库首次进入 workflow 前为 main（存量项目可保留现状） + origin 至少两个 push URL + trellis init`
2. 运行：

```bash
/ops/softwares/python/bin/python3 \
docs/workflows/新项目开发工作流/commands/install-workflow.py \
--project-root <target-project> \
--cli claude
```

3. 安装完成后，在目标项目内直接使用 `/trellis:<phase>`；初始 spec 基线由安装脚本完成，不再手工复制

## 渐进性披露（安装后的使用层）

Claude Code 下的 MCP / skills 配置，推荐按三层披露：

这里的“渐进性披露”只描述：**当前 workflow 已经安装到目标项目之后**，Claude Code 在实际使用时如何按需展开上下文；它不替代前面的安装时序。

| 层级 | 文件 | 负责内容 |
|------|------|---------|
| 主规则层 | `工作流总纲.md` `AGENTS.md` | 能力路由原则、证据边界、工具优先级 |
| 映射层 | `命令映射.md` `.claude/commands/trellis/*.md` | 阶段 × 场景 × 能力的调用规则 |
| 平台展开层 | 本 README | Claude Code 的 settings、hooks、agents、验证方法 |

约束：

- 主规则层不放长配置样例
- 命令正文只写执行规则，不复制整份 skill 或平台配置
- 具体权限与 hooks 配置留在 Claude Code 原生文件

## 推荐承载方式

### 1. Commands：用 `.claude/commands/trellis/` 承载阶段命令

Claude Code 的用户入口仍是项目命令：

```text
.claude/commands/trellis/
├── feasibility.md
├── brainstorm.md
├── design.md
├── plan.md
├── test-first.md
├── project-audit.md
├── check.md
├── review-gate.md
└── delivery.md
```

上面这棵树表示的是**当前 workflow 分发的阶段命令资产**，其中既包含纯新增命令，也包含与 Trellis 基线同名、但由当前 workflow 提供合并语义的 `brainstorm` / `check`；它不是目标项目里的完整 Trellis 命令全集。

因为这套 workflow 是在 `trellis init` 之后嵌入的，目标项目里还会保留 Trellis 原生命令，例如：

- `start.md`：保留基线命令，再由 workflow 注入 Phase Router
- `finish-work.md`：保留基线命令，再由 workflow 注入项目化补丁
- `record-session.md`：保留基线命令，再由 workflow 注入元数据闭环补丁

其中 `start.md` 的增强还包括：

- 自动选择当前要执行的具体 task
- 自动执行 before-dev 步骤
- 自动生成或刷新当前 task 的 `before-dev.md`

因此，不要把“当前 workflow 命令树只列到 `delivery`”理解成“目标项目没有 `finish-work` / `record-session`”。

还要补一条 close-out 边界：`record-session` 虽然会被当前 workflow 注入元数据闭环补丁，但 `archive` 仍直接调用目标项目 Trellis 基线里的 `python3 ./.trellis/scripts/task.py archive`。因此，目标项目最好先升级到当前最新 Trellis；否则即使 workflow 已安装成功，收尾链路仍可能继承旧基线中的 archive metadata auto-commit 问题。

这层负责：

- 显式阶段入口
- 阶段性操作规则
- 对应 shell/helper 脚本的调用关系
- 承载 Brainstorm 完成前的项目级正式需求文档门禁：进入 design 前至少已同步 `docs/requirements/customer-facing-prd.md`；`docs/requirements/developer-facing-prd.md` 等到技术架构确认后再正式生成

对前端视觉落地链路，还要额外记一条：

- `UI 原型生成`
- `UI -> 首版代码界面`

这两个子阶段允许 Claude Code 作为主执行入口；当前 workflow 不允许 Codex 在这两步里承担主执行器。

若项目存在 `UI -> 首版代码界面` task，该 task 完成时还必须同步产出：

- `design/frontend-ui-spec.md`

供后续任意 CLI 修改前端时统一遵循。

补充边界：

- UI 原型文件、原型导出代码、临时网页源码都只属于参考资产，不能直接作为正式实现输入
- `plan` 阶段在 Claude Code 下也仍然只是规划阶段，不允许生成基础代码或直接进入 implementation
- `plan` 阶段的 `execution_authorized` 必须保持为 `false`；只有用户明确确认进入 `implementation` / `test-first` 后，才允许显式设为 `true`

这层不负责：

- 保存凭据
- 注册 MCP server
- 复制 skills 的完整正文

### 2. Rules：`AGENTS.md` 负责长期规则，`.claude/settings*.json` 负责运行时挂接

推荐分工：

- `AGENTS.md`
  - 放项目级长期稳定规则
  - 例如证据优先、联网门禁、`[Evidence Gap]` 口径、工具优先级
- `.claude/settings.json`
  - 放 repo 共享的 hooks 接线、默认 deny 或共享运行时基线
- `.claude/settings.local.json`
  - 放本机 / 本环境相关的 allowlist、MCP 可用性与调试权限扩展
- 若项目启用源码水印与归属证明门禁：
  - 长期策略（是否启用、边界、默认验证要求）放 `AGENTS.md`
  - 具体设计与交付产物放 `$TASK_DIR/design/source-watermark-plan.md`、`$TASK_DIR/delivery/ownership-proof.md`、`$TASK_DIR/delivery/source-watermark-verification.md`
  - 阶段校验使用 `.trellis/scripts/workflow/ownership-proof-validate.py`

当前仓库里的典型结构就是：

- `.claude/settings.json`：SessionStart / PreToolUse / SubagentStop hooks 与默认 deny 基线
- `.claude/settings.local.json`：允许的 MCP 与命令权限

### 3. Hooks：用 `.claude/hooks/` 做上下文注入

Claude Code 的 hooks 是这套 workflow 的关键承载层之一。当前仓库已有：

- `.claude/hooks/session-start.py`
- `.claude/hooks/inject-subagent-context.py`
- `.claude/hooks/ralph-loop.py`

推荐分工：

- `session-start.py`：注入 Trellis 会话上下文与 workflow 启动说明
- `inject-subagent-context.py`：对子代理注入 implement / check / debug 上下文
- `ralph-loop.py`：在特定审查收口点执行自动循环或门禁逻辑

### 4. Agents：用 `.claude/agents/*.md` 承载角色，而不是把所有能力塞进命令正文

如果某能力是“阶段内角色分工”，更适合放在 agents：

```text
.claude/agents/
├── research.md
├── implement.md
├── check.md
└── debug.md
```

这层适合放：

- research / implement / check / debug 的职责拆分
- 角色级工具暴露
- 子代理工作边界

### 5. Skills / MCP：定义路由规则与运行时挂接，不混写

在 Claude Code 下，MCP / skills 推荐这样拆：

- **路由规则**：
  - 写在 `AGENTS.md` 与 workflow 文档
  - 例如：
    - 代码上下文定位优先 `ace.search_context`
    - 第三方官方文档优先 `Context7`
    - 最新信息优先 `grok-search > exa > 内置 Web tools`
    - 浏览器交互优先 `agent-browser` skill
- **运行时挂接与权限**：
  - 写在 `.claude/settings.json` / `.claude/settings.local.json`
  - 负责 allow / deny、hooks、生效的工具范围
- **复用能力本体**：
  - 写在 skills / agents / 通用脚本
  - 不要把 skill 全文复制进 `/trellis:*` 命令正文

## 推荐部署映射

| 工作流资产 | Claude Code 目标位置 | 说明 | 安装器管理 |
|-----------|----------------------|------|-----------|
| 阶段命令 | `.claude/commands/trellis/*.md` | 用户显式触发的 workflow 命令 | ✅ `install-workflow.py` |
| Trellis 原生命令基线 | `.claude/commands/trellis/start.md` `finish-work.md` `record-session.md` | 由 `trellis init` 提供；当前 workflow 会对 `start` / `finish-work` / `record-session` 注入补丁，但不重新定义完整基线 | ✅ 补丁由安装器注入 |
| 项目长期规则 | `AGENTS.md` | 稳定执行规则、证据门禁、能力优先级 | ❌ 手动维护 |
| 共享运行时基线 | `.claude/settings.json` | hooks 接线、默认 deny / shared baseline | ❌ 手动维护 |
| 本机权限扩展 | `.claude/settings.local.json` | MCP allowlist、本地调试权限 | ❌ 手动维护 |
| 会话与子代理 hooks | `.claude/hooks/*.py` | 会话启动、上下文注入、收口逻辑 | ❌ 手动维护 |
| 子代理定义 | `.claude/agents/*.md` | research / implement / check / debug | ❌ 手动维护 |
| 通用辅助脚本 | `.trellis/scripts/workflow/` | 校验、导出、静态验证脚本 | ✅ `install-workflow.py` |
| 源码水印与归属证明产物 | `$TASK_DIR/design/`、`$TASK_DIR/delivery/` | 设计计划、提取验证、交付证明 | ❌ 人工维护 / workflow 阶段产出 |

## 何时仍可用脚本降级

即使 Claude Code 具备原生命令、hooks 与 agents，脚本层仍然有价值：

- workflow 静态校验
- plan / design / delivery 产物检查
- provider 或网络不可用时的最低限度门禁

脚本层在 Claude Code 中应被视为 **补充验证层**，不是主要 workflow 承载层。

## `/tmp` 最小验证建议

### 静态装配验证

```bash
test -f AGENTS.md
test -f .claude/settings.json
test -f .claude/hooks/session-start.py
test -f .claude/hooks/inject-subagent-context.py
test -f .claude/commands/trellis/start.md
test -f .claude/agents/implement.md
```

### 配置层验证

至少确认：

- `AGENTS.md` 负责的是长期规则，不是平台私有凭据
- `.claude/settings.json` 已接上 SessionStart / PreToolUse hooks
- `.claude/settings.local.json` 中的工具 allowlist 与 workflow 需要的 MCP 能力一致

## 当前结论

Claude Code 对这套 workflow 的正确描述应该是：

- **不是**“只有命令目录”
- **不是**“把所有 MCP / skills 细节都塞进命令正文”
- 而是“用 `.claude/commands/` 承载阶段入口，用 `AGENTS.md` 承载长期规则，用 `.claude/settings*.json` 与 `.claude/hooks/` 承载运行时挂接，用 `.claude/agents/` 承载角色能力，并通过渐进性披露控制上下文体积”
