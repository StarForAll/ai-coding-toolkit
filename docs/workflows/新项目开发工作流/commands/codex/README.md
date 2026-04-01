# Codex CLI 适配

Codex 对这套 workflow 的正确承载模型不是 `.claude/commands/` 式自定义 slash command，而是：

- `AGENTS.md`：项目级长期稳定规则
- `.codex/config.toml`：项目级 Codex 配置与 `AGENTS.md` fallback
- `.codex/hooks.json` + `.codex/hooks/*.py`：会话启动时注入 Trellis 上下文
- `.agents/skills/*.md` 或 `.codex/skills/*.md`：workflow 入口与阶段技能
- `.codex/agents/*.toml`：research / implement / check 一类子代理

Codex 官方确实有 built-in slash commands，但那是 Codex 自身的交互控制能力，不等于“项目自定义 workflow 命令分发目录”。

## 推荐承载方式

### 1. Rules：`AGENTS.md` 作为项目主规则文件

Codex 官方支持 `AGENTS.md` 指令链。对 Trellis workflow，推荐把长期稳定规则放在项目根的 `AGENTS.md`：

- 语言策略
- 证据优先
- 风险边界
- 验证门禁
- 项目级开发规范

当前仓库的实际做法也是如此：

```toml
# .codex/config.toml
project_doc_fallback_filenames = ["AGENTS.md"]
```

### 2. Hooks：用 `.codex/hooks.json` 在会话启动时注入 Trellis 上下文

Codex 支持 hooks。对这套 workflow，推荐在 `SessionStart` 阶段注入：

- `.trellis/workflow.md`
- `.trellis/spec/` 索引
- 当前任务状态
- `start` skill 指令

当前仓库已有对应实现：

- `.codex/hooks.json`
- `.codex/hooks/session-start.py`

这条链路的作用是：把 Trellis workflow 运行时所需的上下文自动装进 Codex 会话，而不是要求用户每次手动粘贴。

### 3. Skills：workflow 阶段入口由 skills 承载

对 Codex，这套 workflow 的推荐入口不是项目自定义 slash commands，而是 skills：

- `.agents/skills/start/SKILL.md`
- `.agents/skills/brainstorm/SKILL.md`
- `.agents/skills/finish-work/SKILL.md`
- `.agents/skills/check/SKILL.md`
- `.agents/skills/update-spec/SKILL.md`

在当前仓库里，`session-start.py` 还显式写了：

- Codex uses skills, not slash commands

这正是 Codex 与 Claude/OpenCode 的关键差异。

### 4. Subagents：用 `.codex/agents/*.toml` 承载研究/实现/检查角色

Codex 官方支持 subagents。对 Trellis workflow，推荐用它承载：

- `research`
- `implement`
- `check`

当前仓库已有对应定义：

```text
.codex/agents/
├── research.toml
├── implement.toml
└── check.toml
```

这层负责“阶段内角色分工”，不负责对用户暴露 workflow 命令入口。

## Built-in slash commands 与 workflow 技能的边界

Codex 官方内建 slash commands 是平台级控制能力，例如：

- `/agent`
- `/plan`
- `/review`
- `/model`
- `/status`
- `/init`

这类命令的定位是：

- 管理 Codex 自身会话
- 管理模型、审查、代理和计划模式

它们**不是**当前项目 workflow 的阶段命令映射层。

对 Trellis 来说，正确做法是：

- 用 Codex built-in slash commands 管理 Codex 本身
- 用 `AGENTS.md + hooks + skills + subagents` 承载 Trellis workflow

## 推荐部署映射

| 工作流资产 | Codex 目标位置 | 说明 |
|-----------|----------------|------|
| 项目长期规则 | `AGENTS.md` | 长期稳定的项目规则和执行原则 |
| Codex 项目配置 | `.codex/config.toml` | 指定 `AGENTS.md` fallback 等项目级配置 |
| 会话启动注入 | `.codex/hooks.json` + `.codex/hooks/*.py` | 自动注入 Trellis workflow 上下文 |
| workflow 技能 | `.agents/skills/*/SKILL.md` 或 `.codex/skills/*/SKILL.md` | `start`、`brainstorm`、`finish-work` 等阶段入口 |
| 子代理 | `.codex/agents/*.toml` | research / implement / check |
| 辅助脚本 | `.trellis/scripts/` 或 `commands/shell/` | 校验、导出、静态验证脚本 |

## 何时仍可用脚本降级

即使采用 Codex 原生适配，脚本层仍然保留价值：

- workflow 静态校验
- plan / design / delivery 产物检查
- provider 或网络不可用时的最低限度流程门禁

脚本层在 Codex 中应被视为 **补充验证层**，不是主要 workflow 承载层。

## 已知限制

### 1. Codex 官方有 built-in slash commands，但当前没有官方证据表明应把项目 workflow 阶段映射成 `.claude/commands/` 风格目录

因此，本 README 不建议为 Codex 设计一套与 Claude 完全平行的“自定义 slash command 文件分发”模型。

这里的结论来自两部分证据：

- 官方明确文档化了 built-in slash commands、AGENTS、hooks、subagents
- 当前仓库真实实现选择了 `AGENTS + hooks + skills + agents`，而不是 `.claude/commands` 镜像

### 2. 非交互执行仍受 provider / 网络 /账户状态影响

`codex exec` 可以启动非交互会话，但完整执行仍取决于：

- 当前环境是否已登录或具备可用凭据
- provider 是否可达
- 外部 MCP / 网络链路是否可用

### 3. Skills 触发是 workflow 设计问题，不是平台原生 slash command 问题

也就是说：

- “Codex 支不支持 slash commands” 与
- “Trellis workflow 在 Codex 上如何触发”

是两个不同问题。

Codex 有 slash commands，但当前 workflow 入口更适合建成 skills。

## `/tmp` 最小验证建议

### 静态装配验证

```bash
test -f AGENTS.md
test -f .codex/config.toml
test -f .codex/hooks.json
test -f .codex/hooks/session-start.py
test -f .agents/skills/start/SKILL.md
test -f .codex/agents/implement.toml
```

### CLI 基础可执行验证

```bash
HOME="$TMP_ROOT/home" codex --help
HOME="$TMP_ROOT/home" codex exec --help
```

### Workflow 链路验证

最小目标不是验证“自定义 slash command”，而是验证：

1. Codex 会话可在目标项目启动
2. `AGENTS.md` / hooks / skills 链路可装配
3. 非交互执行能进入会话阶段

建议命令：

```bash
HOME="$TMP_ROOT/home" codex exec \
  -c 'mcp_servers={}' \
  --skip-git-repo-check \
  -C "$TMP_ROOT/project" \
  --json \
  "If you received a <ready> block from session-start hook, reply READY_ONLY. Otherwise reply MISSING_ONLY."
```

若执行失败，应区分：

- CLI 本身不可运行
- hook 未触发
- `AGENTS.md` 未被加载
- provider / 认证不可用
- 外部 MCP 或网络链路失败

补充建议：

```bash
HOME="$TMP_ROOT/home" codex exec \
  -c 'mcp_servers={}' \
  --skip-git-repo-check \
  -C "$TMP_ROOT/project" \
  "According to this project's instructions, which language should user-facing responses default to? Answer with one word only."
```

这条命令可用于验证项目级 `AGENTS.md` 是否被加载。

若要单独验证 hook 文件本身是否能生成 Trellis 注入上下文，可直接按 hook 协议执行：

```bash
printf '{"cwd":"'"$TMP_ROOT"'/project"}' | python3 "$TMP_ROOT/project/.codex/hooks/session-start.py"
```

## 当前结论

Codex 对这套 workflow 的正确描述应该是：

- **不是**“没有统一命令扩展机制”
- **不是**“只能靠脚本 + markdown 上下文注入”
- 而是“具备 AGENTS / hooks / skills / subagents / built-in slash commands 的强 workflow 承载能力，但 workflow 入口应按 skills 模型设计，而不是照搬 Claude 命令目录”

当前 `/tmp` smoke test 的额外发现：

- `codex exec` 可完整运行并读取项目 `AGENTS.md`
- `SessionStart` hook 文件本身可按协议生成 Trellis 上下文
- 但在非交互 `codex exec` 中，是否把 hook 注入后的 `<ready>` 块暴露给模型，需要单独验证，不能直接假定与交互式会话完全一致
