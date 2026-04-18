# Codex CLI 适配

Codex 对这套 workflow 的正确承载模型不是 `.claude/commands/` 式自定义 slash command，而是：

- `AGENTS.md`：项目级长期稳定规则
- `.codex/config.toml`：项目级 Codex 配置与 `AGENTS.md` fallback
- `.codex/hooks.json` + `.codex/hooks/*.py`：会话启动时注入 Trellis 上下文
- `.agents/skills/*/SKILL.md` 或 `.codex/skills/*/SKILL.md`：workflow 入口与阶段技能
- `.codex/agents/*.toml`：research / implement / check 一类子代理

Codex 官方确实有 built-in slash commands，但那是 Codex 自身的交互控制能力，不等于“项目自定义 workflow 命令分发目录”。
适配时应遵循 Codex 官方原生格式要求，但前置条件、阶段语义和初始化动作必须与 Claude Code / OpenCode 保持一致。

在当前 workflow 的默认安装模型里，Codex 不是单独安装，而是与 Claude Code / OpenCode 一起嵌入同一个目标项目。
因此这里必须额外强调：

- 同一个项目里同时存在 `.claude/commands/trellis/`、`.opencode/commands/trellis/`、`.agents/skills/*`
- 这**不代表** Codex 也获得了项目级 `/trellis:xxx` 命令目录
- Codex 在该项目中的 workflow 入口依然是 skills / AGENTS / hooks / subagents
- 并且这些 skills 里有一部分来自 Trellis 原生基线，有一部分才是当前 workflow 额外嵌入的阶段资产

前置条件也必须说清：

- 目标项目本身必须是 Git 项目
- 若是新建仓库（尚无本地提交历史），在第一次进入 workflow 前，本地主分支和初始分支必须是 `main`；若目标项目已存在本地提交历史，则不强制切换，仅记录现状
- `origin` 必须至少配置两个 push URL
- 目标项目必须已经执行过 `trellis init`
- 目标项目应能检测到 `trellis init` 产物，例如 `.trellis/.version`

这里要求同一个 `origin` 至少配置两个 push URL，是因为当前 workflow 默认面向“同仓双推镜像”的协作方式，常见就是 GitHub / Gitee 双推；若你的 Codex 目标项目只维护单一远端，这条约束并不是通用 Git 规则，而是当前 workflow 变体的安装前提。

在此前提下，正确顺序是：先完成 `trellis init`，再执行当前 workflow 自带的安装脚本；真正的 skills、hooks、agents 由安装器和项目配置落到目标项目，并自动导入 `pack.requirements-discovery-foundation`；若目标项目存在 `00-bootstrap-guidelines`，安装脚本会一并清理，否则跳过。

## 安装时序

如果你的目标是让 Codex 在目标项目里直接可用这套 workflow，推荐做法是：

1. 确认目标项目满足 `Git + 新建仓库首次进入 workflow 前为 main（存量项目可保留现状） + origin 至少两个 push URL + trellis init`
2. 运行：

```bash
/ops/softwares/python/bin/python3 \
docs/workflows/新项目开发工作流/commands/install-workflow.py \
--project-root <target-project> \
--cli codex
```

3. 安装完成后，在目标项目内通过 skills / AGENTS / hooks / subagents 直接使用这套 workflow；初始 spec 基线由安装脚本完成，不再手工复制

## 在多 CLI 同装中的定位

当前安装器会把阶段命令源文件转换为 `.agents/skills/<phase>/SKILL.md`，让 Codex 与其他 CLI 在同一个项目中共存。

这层转换的正确理解是：

- 它是**共存适配层**
- 它不是“Codex 也支持 `.claude/commands/` 风格项目命令”的证据
- 它也不意味着用户应该在 Codex 中输入 `/trellis:start`

> 关于 `.agents/skills/` 的真实归属：
>
> - `.agents/skills/` 并不是 Codex 专属路径，它是“跨 CLI skills”的通用位置。OpenCode 官方 skills 文档（<https://opencode.ai/docs/skills/>）明确说明，OpenCode 会沿项目向上扫描并加载 `.agents/skills/*/SKILL.md`
> - 因此当前 workflow 部署到 `.agents/skills/` 下的阶段 skills，会同时出现在 OpenCode 与 Codex 的可发现范围内
> - 升级/核对 skills 漂移时，必须把 OpenCode 也算在影响面内，而不是仅把 `.agents/skills/` 当作 Codex 的内部实现细节

### 多 skills 目录同步（安装器行为）

`trellis init` 可能同时创建 `.agents/skills/` 与 `.codex/skills/`。本仓库实际观察到的例子是：主体 skills 落在 `.agents/skills/`，而 `parallel` 落在 `.codex/skills/`。

当前安装器（`install-workflow.py`）对 Codex 的处理策略：

- 通过 `list_all_codex_skills_dirs` 获取**所有存在的 skills 目录**（`.agents/skills/` + `.codex/skills/`）
- 阶段 skills：向**所有目录同步写入**，确保两边内容一致
- `finish-work` 补丁：**只在存在 finish-work 基线的目录**注入；若某目录没有该基线，则跳过（不报错）
- `parallel` 禁用覆盖：**只在存在 parallel 的目录**执行禁用；若不存在则跳过
- `upgrade-compat.py --check`：对**所有 skills 目录**分别检查内容、补丁、禁用覆盖

这意味着不再有"活动目录"与"影子目录"之分；安装器对两边一视同仁。但有一个重要边界：

- `trellis init` 未必在每个 skills 目录都写入相同的基线集合（例如 `.codex/skills/` 可能没有 `finish-work`）
- 因此安装器不会强制要求"所有目录都必须有 finish-work"，而是按"有就打补丁，没有就跳过"处理

装后/升后核对仍建议显式检查两条路径，确认两边内容一致：

```bash
test -d .agents/skills || test -d .codex/skills
ls .agents/skills/parallel/SKILL.md 2>/dev/null
ls .codex/skills/parallel/SKILL.md 2>/dev/null
# 两者同时存在时，应确认内容已由安装器同步为一致状态
```

在 Codex 中，推荐使用方式应是：

- 直接用自然语言描述需求，由 skill 自动匹配
- 或显式触发对应 skill
- 必要时再配合 Codex 自身的 built-in slash commands 管理会话、模型或 subagents

还要补一层边界：

- `feasibility`、`brainstorm`、`design`、`plan`、`test-first`、`check`、`review-gate`、`delivery` 这类阶段技能，通常来自当前 workflow 的嵌入资产
- `start`、`finish-work`、`record-session` 这类技能/入口，默认应先理解为 **Trellis 基线能力**；其中当前 workflow 会在目标项目已有 `finish-work` skill 时注入项目化补丁，其余入口继续按基线能力与 workflow 文档约束承载
- `start` 在当前 workflow 里的增强包括：自动选择具体 task、自动执行 before-dev 步骤、自动生成或刷新当前 task 的 `before-dev.md`

如果忽略“先有 Trellis，再嵌入 workflow”这层关系，就会误把继承资产看成 workflow 漏装或少定义。

还要补一条 close-out 边界：`record-session` 仍按 Trellis 基线能力与 workflow 文档约束承载，而最终的 `archive` 继续直接调用目标项目 Trellis 基线里的 `python3 ./.trellis/scripts/task.py archive`。因此，目标项目最好先升级到当前最新 Trellis；否则即使 workflow 已安装成功，收尾链路仍可能继承旧基线中的 archive metadata auto-commit 问题。

## 渐进性披露（安装后的使用层）

Codex 下的 MCP / skills 配置也不应全部堆进 `AGENTS.md` 或启动注入内容。

这里的“渐进性披露”只描述：**当前 workflow 已经安装到目标项目之后**，Codex 在实际使用时如何按需展开上下文；它不替代前面的安装时序。

推荐拆分：

- 主规则层：`工作流总纲.md` + `AGENTS.md`
- 映射层：`命令映射.md` + skills / hooks 注入的阶段说明
- 平台展开层：本 README

其中：

- `AGENTS.md` 负责稳定规则与能力路由原则
- hooks / skills 负责把 workflow 入口与上下文挂进 Codex
- 平台私有的 MCP / provider 启用细节应留在 Codex 原生配置面，不写进主规则层
- 若项目启用源码水印与归属证明门禁：
  - 长期策略（是否启用、零宽字符边界、不起眼代码标识禁区）放 `AGENTS.md`
  - 设计 / 交付产物继续放 `$TASK_DIR/design/source-watermark-plan.md`、`$TASK_DIR/delivery/ownership-proof.md`、`$TASK_DIR/delivery/source-watermark-verification.md`
  - `plan` 阶段继续按 workflow 规则拆出：可见源码水印、零宽字符水印（若启用）、隐蔽代码标识（若启用）、水印验证、归属证明包任务
  - 静态校验通过 `.trellis/scripts/workflow/ownership-proof-validate.py` 执行

## 推荐承载方式

### 1. Rules：`AGENTS.md` 作为项目主规则文件

Codex 官方支持 `AGENTS.md` 指令链。对 Trellis workflow，推荐把长期稳定规则放在项目根的 `AGENTS.md`：

- 语言策略
- 证据优先
- 风险边界
- 验证门禁
- 项目级开发规范
- 工具优先级与 `[Evidence Gap]` 口径

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
- `.agents/skills/project-audit/SKILL.md`
- `.agents/skills/check/SKILL.md`
- `.agents/skills/review-gate/SKILL.md`
- `.agents/skills/update-spec/SKILL.md`

在当前仓库里，`session-start.py` 还显式写了：

- Codex uses skills, not slash commands

这正是 Codex 与 Claude/OpenCode 的关键差异。

在“多 CLI 同装”场景下，也应继续坚持这个差异：

- Claude / OpenCode：以项目命令为主入口
- Codex：以 skills 为主入口

对 `brainstorm` skill 还要额外强调一条阶段门禁：完成需求澄清后，不能只停留在 `task_dir/prd.md`。进入 design 前，目标项目至少需要先产出并同步：

- `docs/requirements/customer-facing-prd.md`
- `task_dir/prd.md` 中的 `## 项目级粗估`
- `docs/requirements/customer-facing-prd.md` 中的 `## 项目级粗估摘要`

而 `docs/requirements/developer-facing-prd.md` 应等到技术架构确认后再正式生成。

### 3.1 设计与前端视觉落地的执行边界

虽然 `design` 作为阶段 skill 会继续安装到 Codex，但这不等于 Codex 可以承担设计阶段里的所有子任务。

当前 workflow 对前端视觉落地链路有明确限制：

- `UI 原型生成`（例如 `uiprompt.site -> Stitch`）阶段，Codex **不能**作为主执行器
- `UI -> 首版代码界面` 阶段，Codex **也不能**作为主执行器

Codex 在这两步里只允许承担：

- 设计文档整理
- `STITCH-PROMPT` 文本润色
- 外部原型结果回收与结构化沉淀

真正的主执行入口必须切换到：

- Claude Code
- OpenCode

另外，如果目标项目存在 `UI -> 首版代码界面` task，该 task 完成时必须同步产出：

- `design/frontend-ui-spec.md`

后续任何 CLI 再修改前端时，都默认要以这份文档作为统一约束来源，避免样式和效果漂移。

补充边界：

- UI 原型文件、原型导出代码、临时网页源码都只属于参考资产，Codex 不应把它们直接当作正式实现输入
- `plan` skill 在 Codex 下也只能做任务划分与规划，不允许生成基础代码或直接进入 implementation
- `plan` 阶段的 `execution_authorized` 必须保持为 `false`；只有用户明确确认进入 `implementation` / `test-first` 后，才允许显式设为 `true`

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

当前 workflow 已将 `.codex/agents/*.toml` 中的 `research` / `implement` / `check` 纳入兼容治理，并与 Claude / OpenCode 的 implementation 内部角色链对齐。

source-of-truth 边界同样要明确：

- 当前 workflow 安装链实际读取的是 `docs/workflows/新项目开发工作流/commands/codex/agents/*.toml`
- 目标项目 `.codex/agents/*.toml` 是安装结果，不是当前 workflow 的唯一源层
- 若后续要继续收敛，也应优先在 workflow 命令目录内完成，而不是上收到仓库根目录

这里的对齐规则不是“复制 Claude 的 hook 机制”，而是：

- 对齐 agent 角色语义
- 对齐安装 / 升级 / 漂移检测
- 继续遵循 Codex 官方 `subagents` / `hooks` 边界

其中：

- `research.toml`：保持只读，但必须遵守统一证据门禁
  - 外部技术搜索优先 `exa`
  - 第三方库 / 框架 / SDK 官方文档必须先 `Context7`
  - 未经过 `Context7`，不得输出 API / 配置 / 版本结论；若能力不可用，必须标记 `[Evidence Gap]`
- `implement.toml`：保持 `workspace-write`
- `check.toml`：改为 `workspace-write` 的可修复 implementation-stage check-agent

需要特别区分：

- `check.toml`：implementation 内部链的自修复检查角色
- `/trellis:check`：implementation 之后的正式质量门禁阶段

二者不是同一层能力。

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
- 不把其他 CLI 的 `/trellis:xxx` 文案误当成 Codex 的项目命令协议

补充边界：

- Trellis 原生 `plan agent` / `dispatch agent` 不属于当前 workflow 主链
- 当前 workflow 不采用 `parallel/worktree` 驱动的 `plan -> dispatch -> create-pr` 流水线
- implementation 阶段只保留 `research -> implement -> check-agent` 这一组内部角色链

## 推荐部署映射

> 完整的三平台资产分类矩阵见 [CLI原生适配边界矩阵.md](../../CLI原生适配边界矩阵.md)。

| 工作流资产 | Codex 目标位置 | 说明 | 安装器管理 |
|-----------|----------------|------|-----------|
| 项目长期规则 | `AGENTS.md` | 长期稳定的项目规则和执行原则 | ❌ 手动维护 |
| Codex 项目配置 | `.codex/config.toml` | 指定 `AGENTS.md` fallback 等项目级配置 | ❌ 手动维护 |
| 会话启动注入 | `.codex/hooks.json` + `.codex/hooks/*.py` | 自动注入 Trellis workflow 上下文 | ❌ 手动维护 |
| workflow 技能 | `.agents/skills/*/SKILL.md` 或 `.codex/skills/*/SKILL.md` | `start`、`brainstorm`、`finish-work` 等阶段入口；若已有基线 `finish-work` skill，则由安装器追加项目化补丁 | ✅ `install-workflow.py` |
| 子代理 | `.codex/agents/*.toml` | `research` / `implement` / `check` 由 workflow source-of-truth `commands/codex/agents/` 部署 | ✅ 部分由 `install-workflow.py` 管理 |
| 辅助脚本 | `.trellis/scripts/workflow/` | 校验、导出、静态验证脚本 | ✅ `install-workflow.py` |
| 源码水印与归属证明产物 | `$TASK_DIR/design/`、`$TASK_DIR/delivery/` | 设计计划、提取验证、交付证明 | ❌ 人工维护 / workflow 阶段产出 |

**安装器不负责的 Codex 原生资产**（需手动维护）：

- `.codex/config.toml` — Codex 项目级配置
- `.codex/hooks.json` + `.codex/hooks/*.py` — 会话启动 hooks
- 其他非 `research / implement / check` 的 `.codex/agents/*.toml`
- `AGENTS.md` — 项目级长期规则

这些文件缺失不表示安装失败，但会导致 Codex 无法完整运行 workflow。

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

### 安装器产物验证

以下文件由 `install-workflow.py` 负责部署，缺失表示安装未完成：

```bash
test -f .agents/skills/start/SKILL.md 2>/dev/null || test -f .codex/skills/start/SKILL.md
test -f .agents/skills/brainstorm/SKILL.md 2>/dev/null || test -f .codex/skills/brainstorm/SKILL.md
test -f .agents/skills/check/SKILL.md 2>/dev/null || test -f .codex/skills/check/SKILL.md
test -f .codex/agents/research.toml
test -f .codex/agents/implement.toml
test -f .codex/agents/check.toml
```

### 平台前置资产验证

以下文件由项目开发者手动维护，缺失不表示安装失败，但会导致 Codex 无法正常运行：

```bash
test -f AGENTS.md
test -f .codex/config.toml
test -f .codex/hooks.json
test -f .codex/hooks/session-start.py
```

### CLI 基础可执行验证

```bash
HOME="$TMP_ROOT/home" codex --help
HOME="$TMP_ROOT/home" codex exec --help
```

### Workflow 链路验证

> 下面这些 `/tmp` smoke test 命令只用于隔离环境验证 Codex 自身加载链路，**不是**真实目标项目的嵌入前提说明。
> 真实目标项目仍然必须满足“Git 仓库 + 已执行 `trellis init`”。

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
