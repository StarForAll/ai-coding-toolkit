# OpenCode 适配

OpenCode 已具备承载这套 workflow 的原生命令、rules、agents、skills 能力，不应再按“仅靠 `instructions` 注入 markdown”的降级模式理解。
适配时应遵循 OpenCode 官方原生格式要求，但前置条件、阶段语义和初始化动作必须与 Claude Code / Codex 保持一致。

在当前 workflow 的默认安装模型里，OpenCode 不是单独安装，而是与 Claude Code / Codex 一起嵌入同一个目标项目。
这意味着要同时说清两件事：

- OpenCode 确实有自己的原生命令入口
- 但“同装”不等于“和其他 CLI 共用同一触发协议”

本目录的推荐定位是：

- workflow 命令：部署到 `.opencode/commands/trellis/`
- workflow agents：部署到 `.opencode/agents/`
- 项目级稳定规则：放在项目 `AGENTS.md`
- workflow 文档与必要补充：通过 `opencode.json` 的 `instructions` 引入
- 通用辅助脚本：继续放在 `.trellis/scripts/workflow/` 或 `docs/workflows/.../commands/shell/`

前置条件：

- 目标项目本身必须是 Git 项目
- `origin` 必须至少配置两个 push URL
- 目标项目必须已经执行过 `trellis init`
- 目标项目应能检测到 `trellis init` 产物，例如 `.trellis/.version`

这里要求同一个 `origin` 至少配置两个 push URL，是因为当前 workflow 默认服务于“同仓双推镜像”交付模型，常见配置就是 GitHub / Gitee 双推；如果你的项目没有这类远端同步要求，就不要把当前约束误解成通用 Git 最低要求。

在此前提下，正确顺序是：先完成 `trellis init`，再执行当前 workflow 自带的安装脚本；原生命令与 agents 由安装脚本按平台方式落到目标项目，并自动导入 `pack.requirements-discovery-foundation`、删除 `00-bootstrap-guidelines`。

## 安装时序

如果你的目标是让 OpenCode 在目标项目里直接可用这套 workflow，推荐做法是：

1. 确认目标项目满足 `Git + origin 至少两个 push URL + trellis init`
2. 运行：

```bash
/ops/softwares/python/bin/python3 \
docs/workflows/新项目开发工作流/commands/install-workflow.py \
--project-root <target-project> \
--cli opencode
```

3. 安装完成后，在目标项目内直接使用 `/trellis:<phase>` 或 `trellis/<phase>`；初始 spec 基线由安装脚本完成，不再手工复制

## 渐进性披露（安装后的使用层）

OpenCode 下的 MCP / skills 配置不应全部堆进 `instructions`。

这里的“渐进性披露”只描述：**当前 workflow 已经安装到目标项目之后**，OpenCode 在实际使用时如何按需展开上下文；它不替代前面的安装时序。

推荐拆分：

- 主规则层：`工作流总纲.md` + `AGENTS.md`
- 映射层：`命令映射.md` + `.opencode/commands/trellis/*.md`
- 平台展开层：本 README

其中：

- `instructions` 只负责挂载**主入口文档**与**必要补充**
- OpenCode 原生配置负责挂接平台侧能力
- 长配置示例与平台细节只保留在平台展开层，不默认注入

## 在多 CLI 同装中的定位

同一个目标项目里，默认会并存：

- `.claude/commands/trellis/*.md`
- `.opencode/commands/trellis/*.md`
- `.agents/skills/*/SKILL.md`

对 OpenCode 来说，这不改变它的原生入口判断：

- TUI 中仍按 `/trellis:start`
- CLI 中仍按 `trellis/start`
- 不应因为同项目里还安装了 Codex skills，就把 OpenCode 写成“只靠自然语言触发”

## 推荐承载方式

### 1. Commands：用 `.opencode/commands/` 承载 workflow 命令

OpenCode 原生支持项目级命令目录。对这套 workflow，推荐把命令安装为：

```text
.opencode/commands/trellis/
├── feasibility.md
├── brainstorm.md
├── design.md
├── plan.md
├── test-first.md
├── self-review.md
├── check.md
└── delivery.md
```

上面这棵树表示的是**当前 workflow 额外嵌入的阶段命令**，不是目标项目里的完整 Trellis 命令全集。

因为这套 workflow 是在 `trellis init` 之后嵌入的，目标项目原本还会有 Trellis 基线命令，例如：

- `start.md`：保留基线命令，再由 workflow 注入 Phase Router
- `finish-work.md`：保留基线命令，再由 workflow 注入项目化补丁
- `record-session.md`：保留基线命令，再由 workflow 注入元数据闭环补丁

所以看到自定义命令树只列到 `delivery`，不能推导出“这个项目没有 `finish-work` / `record-session`”。

在 Trellis 约定中，这一层负责承载“用户显式调用的阶段命令”。

命令路径语法也要与 Claude / Codex 风格区分开：

- Claude Code 文档通常写成 `/trellis:start`
- OpenCode CLI 的 `run --command` 入口实际使用 `trellis/start`

也就是说，目录命名空间 `trellis/start.md` 在 OpenCode CLI 中对应的命令标识应按 `trellis/start` 理解，而不是直接照搬冒号语法；同项目里即使同时存在 Codex 的 `start` skill，也不影响 OpenCode 继续使用命令入口。

### 2. Rules：`AGENTS.md` + `opencode.json.instructions`

OpenCode 的规则层不要只靠单一入口。

推荐分工：

- `AGENTS.md`：放项目级长期稳定规则，例如执行原则、验证门禁、语言策略、风险边界
- `opencode.json.instructions`：挂载主入口文档与必要补充，不默认全量挂载所有阶段文档
- 平台原生 MCP / provider 配置：负责把 workflow 需要的能力真正启用

`instructions` 更适合加载“主入口 + 当前会话真正需要的补充”，而不是替代命令系统。

推荐默认策略：

- 常驻挂载：`多CLI通用新项目完整流程演练.md`
- 按需补充：`命令映射.md` 或当前正在执行的单个阶段命令
- 不要默认把 `工作流总纲.md` 与全部阶段命令一次性挂进 `instructions`

示例：

```json
{
  "instructions": [
    "docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md",
    "docs/workflows/新项目开发工作流/命令映射.md",
    "docs/workflows/新项目开发工作流/commands/brainstorm.md"
  ]
}
```

上例表示：

- 主入口文档始终可用
- `命令映射.md` 作为必要补充，帮助做阶段路由
- 当前只额外挂载 `brainstorm` 阶段，不默认把其他阶段一起塞进会话

### 3. Agents：用 `.opencode/agents/` 承载子代理

如果目标项目需要像 Trellis 这样做多阶段工作流，推荐单独部署 workflow agents，例如：

```text
.opencode/agents/
├── dispatch.md
├── research.md
├── implement.md
├── check.md
└── debug.md
```

这层负责 planner / research / implement / check 一类子代理职责，不应混在命令文案里。

### 4. Skills：保留技能层，而不是把所有逻辑硬塞进命令

OpenCode 可以复用技能目录与项目内现有技能资产。对这套 workflow，像 `multi-cli-review`、`multi-cli-review-action`、`verification-before-completion` 这类能力仍应按 skill 组织，而不是全部写死在命令正文中。

## 与 Claude Code 的关键差异

OpenCode 不应被写成“和 Claude 完全等价”，因为它在 hook / subagent 注入链路上存在重要差异。

当前仓库的已知现实约束是：

- OpenCode 可以原生命令化，也可以原生定义 agents
- 但项目级 plugin 对 subagent hook 的拦截能力有限
- 如果 workflow 依赖“对子代理自动注入上下文”，仅靠项目内 `.opencode/plugin/` 可能不够

当前仓库里已经把这个限制显式记录在：

- `.opencode/plugin/inject-subagent-context.js`
- `.opencode/lib/trellis-context.js`

因此，对 OpenCode 的正确定位是：

- **命令层**：可原生承载
- **rules 层**：可原生承载
- **agents 层**：可原生承载
- **subagent hook 注入层**：需额外验证，不应默认与 Claude 等价

## 推荐部署映射

| 工作流资产 | OpenCode 目标位置 | 说明 |
|-----------|------------------|------|
| 阶段命令 | `.opencode/commands/trellis/*.md` | 用户显式触发的 workflow 命令 |
| Trellis 原生命令基线 | `.opencode/commands/trellis/start.md` `finish-work.md` `record-session.md` | 由 `trellis init` 提供；当前 workflow 会对 `start` / `finish-work` / `record-session` 注入补丁，但不重新分发完整基线 |
| 子代理定义 | `.opencode/agents/*.md` | research / implement / check / debug / dispatch |
| 项目长期规则 | `AGENTS.md` | 稳定执行规则、风险边界、语言策略 |
| workflow 文档注入 | `opencode.json.instructions` | 只挂主入口与必要补充，不默认全量挂载所有阶段文档 |
| 通用脚本 | `.trellis/scripts/workflow/` 或 `commands/shell/` | 被命令或人工直接调用 |

## 何时仍可用脚本降级

即使采用 OpenCode 原生适配，Python shell/helper 脚本仍然有价值：

- 做文档结构校验
- 做 plan / delivery / design 这类静态验证
- 在模型不可用或联网受限时，保留最低限度的流程门禁

也就是说，脚本层应是 **补充验证层**，不是 OpenCode 的主要 workflow 承载层。

## 已知限制

### 1. CLI 启动依赖外部连通性

当前环境下，即使运行 `opencode --help`，CLI 也可能先探测远端服务（如 `models.dev`）。因此：

- `CLI 可执行` 不等于 `模型交互可用`
- 完整在线验证前，需要先确认网络和 provider 配置

### 2. 全局状态库可能影响调试命令

当前环境里，`opencode debug config`、`opencode debug skill`、`opencode agent list` 可能受全局状态库影响而失败。做 workflow 验证时，建议优先在 `/tmp` 下使用纯净目录与独立 `HOME`。

### 3. Subagent 上下文注入不能默认等同 Claude

若目标项目的 workflow 强依赖 hook 自动注入子代理上下文，应在真实项目里额外验证：

- 项目级 plugin 是否足够
- 是否需要额外的全局插件链
- 当前 OpenCode 版本下 subagent 行为是否符合预期

## `/tmp` 最小验证建议

### 静态装配验证

在纯净目录中检查以下内容是否齐全：

```bash
test -f .opencode/commands/trellis/start.md
test -f .opencode/commands/trellis/check.md
test -f .opencode/agents/dispatch.md
test -f AGENTS.md
test -f opencode.json
```

### CLI 基础可执行验证

建议在独立 `HOME` 下验证，避免受现有全局状态污染：

```bash
TMP_ROOT=/tmp/opencode-workflow-smoke
mkdir -p "$TMP_ROOT/home" "$TMP_ROOT/project"

HOME="$TMP_ROOT/home" opencode --help
HOME="$TMP_ROOT/home" opencode run --help
HOME="$TMP_ROOT/home" opencode debug config
HOME="$TMP_ROOT/home" opencode agent list
```

其中：

- `opencode debug config` 用于确认 `opencode.json.instructions` 已被解析
- `opencode agent list` 用于确认 `.opencode/agents/` 已被识别

### Workflow 命令可用性验证

若网络与 provider 已就绪，再继续验证命令调用链：

```bash
HOME="$TMP_ROOT/home" opencode run \
  --dir "$TMP_ROOT/project" \
  --command trellis/start \
  "请按当前项目 workflow 开始会话并说明下一步"
```

若这一步失败，应区分是以下哪一层失败：

- 命令未被识别
- rules / instructions 未加载
- provider / 网络不可用
- 全局状态库或插件链异常

## 当前结论

OpenCode 对这套 workflow 的正确描述应该是：

- **不是**“命令系统 TBD”
- **不是**“只能靠 instructions + 自然语言触发”
- 而是“具备原生命令 / rules / agents / skills 能力，`instructions` 只挂主入口和必要补充，hook / subagent 注入链路另行验证”
