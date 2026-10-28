---
doc: 工作流实现方案
scope: 把 workflow-design.md 的判定与流转落到可执行的嵌入工程：模块形态、写入边界、状态与账本、机制入口、平台接入、卸载与升级
audience: 实现者（人）与 AI 执行者
environment: 单人 · 一台开发机 · 单一工作线（不切分支、不合入） · 多 CLI 交替
normative: §0–§8 为实现层规范；§9 为冲突登记与裁决留痕（§9.1–§9.4 非规范，§9.5 为已生效裁决，§9.6 为待决治理项）；附录为例示
design_source: ./workflow-design.md、./依赖机制设计说明.md
compatibility: Trellis >= 0.7.0-beta.0（变体链首次出现），实测基线 0.7.0-beta.4
---

# 工作流实现方案

> 设计稿只规定**判定与流转**，不规定工具、文件与命令。本文件规定后者：模块由哪些资产组成、写到目标项目的哪些路径、门禁用什么判、平台怎么接、怎么升级、怎么拆卸。
>
> **权威关系**：判定与流转以 [工作流整体设计](./workflow-design.md) 为准，机制细节以 [依赖机制设计说明](./依赖机制设计说明.md) 为准；两者的实现落点与工程选择以本文件为准。三者冲突时，设计层约束让设计稿优先，实现细节让本文件优先，且必须落到 §9 的冲突登记，不得静默择一。

---

## 0. 定位、来源与证据边界

### 0.1 三份文档的层级

| 层 | 文档 | 回答什么 | 不回答什么 |
|---|---|---|---|
| 设计层 | [workflow-design.md](./workflow-design.md) | 项目层怎么开始与结束、任务怎么走、顺序怎么保障、完成怎么判 | 文件、路径、命令、平台差异 |
| 机制层 | [依赖机制设计说明](./依赖机制设计说明.md) | 依赖账本的状态表、返工/替换/放弃、对账与恢复 | 安装、升级、平台接入 |
| 实现层 | **本文件** | 模块资产与路径、写入边界、账本载体与 CLI 命令面、平台矩阵、ZCode 加固、升级与拆卸、验收探针 | 另造判定；替代设计稿的状态机与完成判定 |

**上游基底**：Trellis 提供任务单元、阶段推进、上下文注入、规格、会话与日志、任务树、归档、工作流变体。本模块**只在项目层与顺序层新增**（设计稿 §1.2），不重造任务生命周期。

### 0.2 与旧实现方案的关系

本文件的工程结论由设计稿、Trellis 源码与五平台规范直接推导，**不依赖任何已删除文档**。
旧实现方案（v20 时代的零补丁方案）已退役并从仓库移除；其中与设计版本无关的少量工程结论已并入正文，
正文不再提供逐条出处，也不再保留来源映射表。

### 0.3 术语

沿用设计稿 §3 与依赖说明 §3 的全部术语（项目层任务 P、基线、任务图、依赖标识、前置集合、下一个集合、依赖账本、图内任务、图外任务、就绪、挂起、返工任务 R、替换指向、对账修复等），本文件**不新增术语**，只新增两个实现层名词：

| 词 | 含义 |
|---|---|
| **模块** | 本方案交付的全部资产：CLI（`.trellis/scripts/wf/**`）、流程变体（`.trellis/workflows/wf.md`）、skill、`AGENTS.md` 路由段、`config.yaml` 那一行、账本与派生视图 |
| **机制入口** | 模块 CLI 中会写账本或写任务记录机制字段的子命令；与之相对的是**原生入口**（直接调 `task.py`） |

### 0.4 证据分级与引用纪律

本文件每条“上游如何如何”的结论必须属于下列四档之一，混用即缺陷：

| 档 | 含义 | 本文件中的用法 |
|---|---|---|
| `实测` | 在本仓库或临时夹具上跑过命令并记录输出 | 目录结构、`task.py` 命令集与各道门、`.zcode/config.json` 现状、版本号 |
| `读码` | 读了上游源码/生成物但未在真实会话中运行 | Pi 扩展的变体解析、`workflow_selection` 链、`_validate_branch_metadata` 的分支语义 |
| `文档` | 官方文档结论 | Claude Code 读 `AGENTS.md` 的条件性、各平台 skill frontmatter 字段 |
| `推断` | 由上述推出，未验证 | 其余一切，必须显式写“推断” |

**版本事实**（`实测`，2026-10-28）：

| 对象 | 值 | 取法 |
|---|---|---|
| 本仓库 `.trellis/.version` | **0.7.0-beta.4** | `cat .trellis/.version`；该值自提交 `e8b2dae`（2026-10-15）起未变 |
| 本机 `trellis` CLI | **0.7.0-beta.4** | `trellis --version` |
| 上游参考检出 `~/projects/other/Trellis` | `feat/v0.7-beta` @ `be9e19b2` = **0.7.0-beta.4** | `git log -1` |

三者**同代同版本**。因此本文件的引用纪律是：

- 引用写“**函数名 + 正典路径**”（如 `common/task_store.py` 的 `_validate_branch_metadata`），不写行号——行号会随小版本位移，且方案不锁定参考检出；
- 上游参考仓库**只读**，不改、不提补丁建议（根 `AGENTS.md` 约束）；
- 任何版本类结论必须以“读到的命令输出”为据，不得凭记忆填写；`wf doctor` 与探针 W1/W9 都以目标项目实际版本为准。

> **勘误留痕**：本文件初稿曾把版本误记为 `0.7.0-beta.42`，并据此推出“与上游不同代”的错误前提。现按上表更正，并在 §9 的 C10 保留该条勘误记录，防止同类错误复发。

---

## 1. 实现前提与目标形态

### 1.1 三条实现前提

继承设计稿 §0，不重复论证，只列实现后果：

| 前提 | 实现后果 |
|---|---|
| 单人 + 本机 + 单一工作线 | 不引入并发写者、不引入工作单元映射、不做分支纪律；所有写操作单写者独占 |
| 只规定判定与流转 | 一切“怎么做”的选择都在本文件：文件、命令、格式、平台 |
| 基底之外只新增依赖机制 | 不新增记录类型（设计稿不变量 3）；账本是唯一新增的记录类型 |

**可卸载性**（设计稿 §1.2 模块生命周期五约束）的实现要求：

1. 卸载后基底可独立建任务、开工、归档；
2. 机制不可用时只卸载，不提供绕过路径；
3. 仅模块卸载保留项目数据，完全卸载由人显式选择；
4. 卸载入口**不依赖**机制运行时、账本或机制入口脚本；
5. 卸载恢复基底配置、移除机制 hook 与变体 pin。

### 1.2 结论：受管写入面

| 对象 | 写入面 | 数量 |
|---|---|---|
| 上游受管文件（`trellis update` 会检查的那些） | `.trellis/config.yaml` 的 `default_workflow: wf` 一行 | **1 行** |
| 上游受管文件的本地修正（仅 ZCode） | `.zcode/config.json` 的四条 hook 命令改加固形态 | **1 个文件，4 条命令** |
| 混合所有权追加 | `AGENTS.md` 块外 NL 路由段；`.trellis/.developer` 的 `workflow=wf` 行 | 2 处 |
| 模块自有路径 | CLI、变体、skill 目录、账本、派生视图、本机安装记录 | 见 §1.5 清单 |
| 任务记录机制字段 | `task.json` 的 `meta.wf.*` | 每任务 1 个键 |

“零补丁”指**上游受管文件**的正文不被改写：除上述一行与 ZCode 一个文件的命令串以外，上游生成物保持原样。模块全部语义在自有路径与 `meta` 自由区。

### 1.3 零补丁地基（实测）

三条实测结论构成地基，实现时任何“要不要改上游文件”的判断都以此为准：

| 编辑动作 | `trellis update --dry-run` 结果 | 实现含义 |
|---|---|---|
| 在 `AGENTS.md` 的 `<!-- TRELLIS:START/END -->` **块外**追加 | **无漂移**（块外字节原样保留，命中 `unchangedFiles`） | 块外追加是安全通道 |
| 修改 `.trellis/config.yaml` 任意一行 | **有漂移**（`config.yaml` 在模板文件集内，哈希不符进入 `changedFiles`） | 那一行必然被看见，必须提供还原路径 |
| 新增模板里**没有**的路径（如 `.trellis/workflows/wf.md`） | **不进漂移清单**（`analyzeChanges` 不扫目录树） | 自有路径不产生漂移 |

**推论**：模块的“可见性”与“零漂移”是两件事——配置那一行必然可见（这是想要的：让人知道自己装了模块），自有路径不可见（这是允许的：它们不属于上游）。

### 1.4 层级边界

以旧实现方案的四层为底，本轮**拆出 T0b**（上游不管理的项目自有路径）并**新增 T1c**（ZCode 受管例外）：

| 层 | 内容 | 规则 |
|---|---|---|
| **T0 上游受管、只读** | `.trellis/scripts/**`（除 `wf/`）、`.trellis/workflow.md`、`.claude/**`、`.codex/**`、`.pi/**`、`.dsh/**`、`.zcode/hooks/**`、`.zcode/skills/**`、`.agents/skills/trellis-*/**` | **模块永不写入**（它们受 `trellis update` 校验，改动即漂移） |
| **T0b 项目自有、上游不管** | `.trellis/spec/**`、`.trellis/tasks/**`、`.trellis/workspace/**` | **模块不写**；任务产物与规格回流可写（P 的技术基线与 `trellis-update-spec` 的产物落在这里），不计入漂移 |
| **T1a 混合所有权（零漂移追加）** | `AGENTS.md` 块外 NL 路由段（带 `<!-- wf-nl-routing-start/end -->` 标记）；`.trellis/.developer` 的 `workflow=wf` 行 | 只追加，不修改块内与其他行 |
| **T1b 官方旋钮（1 行）** | `.trellis/config.yaml` 的 `default_workflow: wf`；卸载时还原为上游注释行 | 期望它在 `trellis update` 的 “Modified by you” 中出现 |
| **T1c 受管例外（仅 ZCode，1 文件）** | `.zcode/config.json` 的四条 hook 命令改为加固形态（§5.2） | 必须登记漂移债务；升级后人工比对上游模板；撤销条件见 §5.5 |
| **T2 外星路径** | `.trellis/scripts/wf/**`、`.trellis/workflows/wf.md`、`.trellis/dependencies/**`、两个 skill 根下的 `wf*` 目录、`.trellis/.runtime/wf/install-record.json` | 全部模块自有，上游不扫不认 |
| **T3 交付介质** | 模块源（本仓库的产品树）+ 安装器；升级时的**新版资产输入** | 安装从模块源运行；运行时自包含；升级必须显式传入模块源 |

**T0b 的依据**（`实测`）：`.trellis/.template-hashes.json` 的 918 条受管路径中不含任何 `.trellis/spec/**` 或 `.trellis/tasks/**` 条目——上游不管这两棵树，因此它们既不是“受管写入面”，也不能算“零补丁”的破坏对象。设计稿要求 P 产出“规格骨架”（§5.2），落点正在这里。

**T1c 为什么必须存在**：旧实现方案把 `.zcode/**` 全部划进 T0，但 ZCode 的 hook 变量绑定会话 cwd（实测，见 §5.1），不改命令串就无法在目标项目稳定运行。这是**受管例外**，不是“顺手改一改”：它必须有独立的层、独立的债务登记、独立的撤销条件。冲突登记见 §9-C8。

### 1.5 写入面清单（机械可核对的唯一源）

任何模块操作**实际写入的路径**必须落在此清单内，越界 fail-closed：

```yaml
module_owned_paths:                     # T2：安装/升级本来就要写
  - .trellis/scripts/wf/**
  - .trellis/workflows/wf.md
  - .trellis/dependencies/ledger.json
  - .agents/skills/wf/**
  - .agents/skills/wf-repair/**
  - .claude/skills/wf/**
  - .claude/skills/wf-repair/**
  - .trellis/.runtime/wf/install-record.json       # 本机态，.trellis/.gitignore 已忽略 .runtime/
mixed_ownership_appends:                # T1a
  - { path: AGENTS.md, marker: "<!-- wf-nl-routing-start -->" }
  - { path: .trellis/.developer, line: "workflow=wf" }
trellis_managed_writes:                 # T1b：唯一受管写入
  - { path: .trellis/config.yaml, line: "default_workflow: wf",
      upstream_default_line: "# default_workflow: native" }
guarded_local_fix:                      # T1c：ZCode 加固（仅当平台存在）
  - { path: .zcode/config.json, change: "四条 hook 命令改为 §5.2 加固形态",
      debt: "trellis update 后人工比对模板" }
```

任务记录写入不在此清单里单列，因为它属于基底的任务文件：机制只写 `task.json` 的 `meta.wf` 键，不新增文件、不新增字段。

---

## 2. 目录布局与生命周期

### 2.1 模块源（本仓库）

**模块源占用 `docs/workflows/新项目开发工作流/`**。旧模块已退役（2026-10-28），该路径现为空，由本模块直接新建：

| 状态 | 事实 |
|---|---|
| 旧模块 | **已退役**：内容移出仓库、不入库、文档不再引用；版本库保留历史提交以备回溯 |
| 四个维护 skill | **已退役删除**（`workflow-audit` / `workflow-capability-audit` / `workflow-repair` / `workflow-scan` 及其契约 spec）。等价能力由 `wf doctor`（漂移 / 哨兵 / 债务）、`wf upgrade`、`wf embed-state` 与 W 系列探针承载（§9.5） |
| 新模块源 | 在 `docs/workflows/新项目开发工作流/` 新建；"仓库内旧路径零残留"是 P0 的完成判据之一 |

```
docs/workflows/workflow-implementation.md        # 本文件：实现层规范
docs/workflows/新项目开发工作流/                  # 模块源（下称 <MODULE_SRC>）
  module.yaml                     # module_version + verified_trellis_range + implements_design + 资产哈希 + skill 根表
  workflow.yaml                   # 机器可读的"账本状态 → 变体块 / 下一步"定义（render 与一致性检查共用）
  templates/
    wf.md.tmpl                    # → 目标项目 .trellis/workflows/wf.md（文件名稳定，不含设计版本号）
    nl-routing.md                 # → AGENTS.md 块外
    zcode-guard.json              # → .zcode/config.json 的加固命令串（占位符化）
    skills/wf/SKILL.md             # skill 正文源（含占位符；frontmatter 由渲染层注入）
    skills/wf-repair/SKILL.md
  installer/{wf_install.py,wf_upgrade.py,skill_roots.py,render.py,doctor.py,zcode_guard.py}
  tests/

```

**生命周期动作归属**：安装、升级、卸载的具体实现属 `<MODULE_SRC>`，由后续实现任务承载；本文件只规定其动作面与判据（§2.4、§7）。

### 2.2 目标项目布局（安装后）

```
.trellis/scripts/wf/                 # 模块 CLI（平台中立的 Python，仅标准库）
.trellis/workflows/wf.md             # 流程变体（含 [workflow-state:*] 块与模块版本注释行）
.trellis/dependencies/ledger.json    # 依赖账本（状态事实源；DAG 视图由 wf dag 输出，不落盘）
.agents/skills/wf/SKILL.md           # codex / zcode / pi / dsh 共用
.agents/skills/wf-repair/SKILL.md
.claude/skills/wf/SKILL.md           # Claude Code
.claude/skills/wf-repair/SKILL.md
.trellis/.runtime/wf/install-record.json        # 本机态（.trellis/.gitignore 已忽略 .runtime/）
AGENTS.md                            # 块外追加 NL 路由段
.trellis/config.yaml                 # 唯一受管写入：default_workflow: wf
.zcode/config.json                   # 仅 ZCode：四条加固命令（T1c）
```

**为什么 skill 是 2 个**：

| skill | 触发意图 | 覆盖子命令 | 副作用 |
|---|---|---|---|
| `wf` | 下一步做什么 / 当前任务什么状态 / 能不能开工 / 要不要建任务 / 交接 | `route`、`state`、`dag`（只读）；`task new`、`start`、`close`、`edge`（有副作用） | 有 |
| `wf-repair` | 对账不一致 / 替换 / 放弃 / 返工登记 / 卸载 | `rework`、`replace`、`abandon`、`repair`（有副作用）；`check`（只读） | 有 |

拆分依据是**设计稿的职责边界**：日常流转（设计稿 §5.3/§6.3）与异常处分（§6.4–§6.6、§7.7）是两套判据，混在一份正文里门禁显著性会下降。**不设 `wf-verify`**：设计稿不设验证证据链（§1.3、§4.3），没有“验证并留证”这个动作。冲突登记见 §9-C1、§9-C11。

### 2.3 进出版本库

| 路径 | 进版本库 | 说明 |
|---|---|---|
| `.trellis/scripts/wf/**` | 是 | 不进库则克隆后没有 `wf` |
| `.trellis/workflows/wf.md` | 是（生成物） | 由 `wf render` 产出 |
| `.trellis/dependencies/ledger.json` | **是** | 设计稿 §3：账本是机制事实，必须持久化 |
| 两个 skill 根 | 是 | 入口层 |
| `AGENTS.md` 块外段、`config.yaml` 那一行 | 是 | T1a / T1b |
| `.trellis/tasks/**`（含 `meta.wf.*`） | 是 | 原生任务记录 |
| `.trellis/workspace/**` | 是 | 原生长期轨迹 |
| `.trellis/.runtime/wf/install-record.json` | 否（gitignore） | 本机解释器路径、模块源路径、上次升级 |
| `.trellis/.runtime/**`、`.trellis/.developer` | 否 | 上游既有的本机状态 |

**账本进库的理由**（与旧实现方案相反）：设计稿把账本列为**唯一新增记录类型**且是状态事实源；不进库则跨机/重克隆后无法判定就绪，等于把状态寄存在本机。冲突登记见 §9-C12。

### 2.4 生命周期动作面

| 动作 | 前置判据 | 写入 | 失败语义 |
|---|---|---|---|
| `wf install` | 目标项目已 `trellis init`；`.trellis/.version` 在 `verified_trellis_range` 内；未安装 | 先把 `config.yaml`（及存在时的 `.zcode/config.json`）快照到 `.trellis/.runtime/wf/pre-install/`；再写 T1a、T1b、T2 全部资产；检测到 `.zcode/` 时写 T1c | 写 `install-record.json` 的 `status=failed` 并回滚已写路径 |
| `wf uninstall --module` | 已安装 | 删 T2 资产、T1a 段、T1b 行（还原）、T1c 还原；**保留** tasks/workspace/ledger | 幂等，可重跑 |
| `wf uninstall --full` | 已安装；**需人 TTY + 令牌** | 在 `--module` 基础上再删账本（本机态目录已由 `--module` 删除；ZCode 备份须先用于还原） | 同上 |
| `wf upgrade --apply` | `--check` 通过、无活动任务、无未完成 attempt | 重渲染变体与 skill、刷新 CLI、确保 T1b 那一行存在 | 失败回滚到快照（§7.4） |
| `wf doctor` | —（只读） | 无 | 报告漂移、解析结果、CLAUDE.md 提示、ZCode 债务 |
| `wf embed-state` | —（只读） | 无 | 三态：未嵌入 / 部分嵌入 / 有效嵌入；非零退出码表示异常 |

**卸载入口独立性**（设计稿 §1.2 约束 4）：`uninstall` 必须是**独立的入口脚本**或 `wf` 中不依赖账本、不依赖变体、不依赖其他子命令的分支；即使 `ledger.json` 损坏、变体被删、CLI 其他子命令全坏，卸载仍可执行。

### 2.5 上游参考与引用纪律

| 来源 | 定位 |
|---|---|
| `~/projects/other/Trellis`（`feat/v0.7-beta` @ `be9e19b2` = `0.7.0-beta.4`） | **正典**：模板在 `packages/cli/src/templates/**`；CLI 行为在 `packages/cli/src/commands/*.ts` |
| 本机安装副本（`.trellis/scripts/**`、各平台目录） | **运行时事实**：行为实测以它为准 |

**实现参考仅限上表三类**：旧模块已退役，不得作为实现依据，也不得在文档中指向它。

**参考索引**（机制 → 正典路径）：

| 机制 | 路径 |
|---|---|
| 变体解析链（优先级 + 静默回落） | `templates/trellis/scripts/common/workflow_selection.py` |
| 阶段/步骤解析 | `templates/trellis/scripts/common/workflow_phase.py`（`get_phase_index` / `get_step`）、入口 `scripts/get_context.py` → `common/git_context.py` |
| `default_workflow` 的原始行 | `templates/trellis/config.yaml` 的 `# default_workflow: native` |
| 官方选择器写法 | `packages/cli/src/commands/workflow.ts` 的 `setProjectDefaultWorkflow` |
| `trellis update` 对 `config.yaml` / `AGENTS.md` 的处理 | `packages/cli/src/commands/update.ts` |
| 任务生命周期与 `meta` 写入 | `templates/trellis/scripts/task.py`、`common/task_store.py` |
| `task.json` 正典 schema | `packages/core/src/task/schema.ts` |
| `[workflow-state:*]` 查表 | `templates/{claude,codex,zcode}/hooks/inject-workflow-state.py`、`templates/pi/extensions/trellis/index.ts` |
| journal / index | `templates/trellis/scripts/add_session.py` |

**引用纪律**：写“上游如何”必须给 `分支 + commit + 路径`；不对齐版本的检出不得用于变体/选择器类结论。

---

## 3. 状态、账本与门禁

### 3.1 任务状态只有三个值

**实现**：`task.json.status` 只出现基底三值 `planning` / `in_progress` / `completed`〔设计稿 §4.2〕。

**门禁与就绪判定一律不读任务状态以外的私有值**，而是“任务状态 + 账本状态”二元组：

| 任务状态 | 账本状态 | 语义 |
|---|---|---|
| `planning` | 无记录 | 已登记未开工（就绪候选） |
| `planning` | 挂起 | 等待返工，且尚未开工 |
| `in_progress` | 无记录 | 执行中 |
| `in_progress` | 挂起 | 执行中但返工挂起（只挡收尾，不挡工作） |
| `completed` | 正常 | 正常完成（唯一合法完成组合） |
| `completed` | 异常 | 替换 / 放弃的异常归档（合法终态） |
| `completed` | 无记录 / 挂起 | **非法**，转对账类型 1 |

**明确不做**（旧实现方案的 A2 投影被剔除，§9-C2）：

- 不写 `wf-impl` / `wf-verify` / `wf-verified` / `wf-blocked` / `wf-paused` / `wf-terminated` 等自定义状态值；
- 不靠 `[workflow-state:<自定义值>]` 块驱动面包屑语义；
- 不提供 `wf sync` 把状态“同步回 wf-\*”。

**代价与补偿**：面包屑只能显示基底三值，看不到“等待返工”。补偿是 `wf route` / `wf state` 的输出把账本维度显式打印（`T2: in_progress · suspended (awaiting R)`），且 `AGENTS.md` 路由段写明“状态以 `wf state` 为准”。

### 3.2 依赖账本

**载体**：`.trellis/dependencies/ledger.json`，单文件、覆盖式更新、进版本库〔设计稿 §8.2：覆盖式更新，历史以版本库为准〕。

**结构**（`schema` 变更必须升版本并在 `wf doctor` 里断言）：

```jsonc
{
  "schema": 1,
  "updated_at": "2026-10-28T13:20:00Z",
  "entries": {
    "7245831927364513792": {                 // key = 依赖标识（雪花 ID）
      "task_dir": "10-28-workflow-implementation-plan",   // 缓存，仅用于展示；判定以解析结果为准
      "dep_state": "normal",                  // normal | suspended | abnormal（无记录 = 键不存在）
      "note": {
        "reason": "人判后正常归档",            // 异常时必填；正常 / 挂起可为空
        "rework": {                           // 未完成返工登记（设计稿 §7.8 返工登记准备行）
          "r_dep_id": "7245831927364513801",
          "r_slug": "rework-workflow-implementation-plan-1",   // 定位 = slug 本体，不含日期前缀
          "t_state_before": "none"            // none | suspended
        }
      },
      "replacement_target": null              // 替换指向：目标依赖标识或 null
    },
    "7245831927364513805": {
      "task_dir": "10-29-t2-old",
      "dep_state": "abnormal",
      "note": { "reason": "被新方案取代" },
      "replacement_target": "7245831927364513810"
    }
  }
}
```

**字段纪律**：

| 字段 | 写入者 | 约束 |
|---|---|---|
| `dep_state` | 收尾 / 返工 / 替换 / 放弃 / 对账修复 | 只能走表 4-2 的七行转移；表外一律拒绝 |
| `note.reason` | 异常处分、类型 1 确认异常 | 异常时必填；正常 / 挂起可为空 |
| `note.rework` | 返工登记准备 / 发布 / 取消 | 同一 T 不覆盖未完成登记；消费后移除该子对象，保留其他说明 |
| `replacement_target` | 替换、放弃-新建替代、类型 1 P 预写 | 目标标识经占用校验；类型 5 改判放弃-一般任务时置空 |
| `task_dir` | 首次登记 | **只作缓存**，重命名后由 `wf rename` 回调同步；判定不以它为准 |

**写入纪律**：只由机制入口写；**禁止手改**。人在需要修复时走 `wf repair`（设计稿 §7.7 的唯一出口）。

**DAG 视图不落盘**：视图由前置集合 + 账本实时派生，经 `wf dag`（`--json` / `--md`）输出，不写文件。理由：它是纯派生件，落盘会产生与状态变化不同步的副本，并在版本库里制造无意义 diff；设计稿 §8.3 要求的是“由机制生成、人只读”，命令输出即满足，且 `wf dag` 每次输出都可作为重建等价性的证据。

### 3.3 标识、定位与占用校验

机制用到三种“身份”，含义与生成规则必须分清：

| 身份 | 形态 | 何时产生 | 用途 | 唯一性由谁保证 |
|---|---|---|---|---|
| **依赖标识** | 雪花 ID（64 位） | 建任务或预写时由机制生成 | 前置集合、账本键、替换指向、返工来源 | 机制扫描 + 时间戳单调 |
| **任务 slug** | 纯名（无日期前缀） | `task.py create --slug` 时确定 | 目录名的稳定部分、**返工定位** | 机制在建任务前扫描两个区 |
| **任务目录** | `MM-DD-<slug>` | 基底 `create` 按**当天日期**生成 | 文件系统定位 | 基底（同日同名则拒绝） |

**依赖标识的生成**：41 位毫秒时间 + 10 位机器 + 12 位序列；`machine_id` 在首次安装时随机生成并持久化到 `.trellis/.runtime/wf/install-record.json`（避免同机多克隆撞号）。

**存储位置**（一个键，整键写入）：

```jsonc
// task.json.meta.wf.deps —— 经 task.py set-meta wf.deps '<json>' 写入
{
  "id": "7245831927364513792",     // 依赖标识
  "slug": "t2",                    // 稳定 slug
  "role": "impl",                  // project | impl | rework | tail
  "in_graph": true,                // 图内任务标记（见下）
  "prereqs": ["7245831927364513791"],
  "rework_source": null            // 仅返工/替代 R 写入
}
```

**`in_graph` 是图内/图外的唯一判据**（设计稿 §3 的图内任务集合按角色与建边史确定，落地为显式标记）：

- `wf task new` 创建图内任务时写 `true`（`--from-graph` 或显式 `--role`）；
- `wf task new --unrelated` 创建无关任务时写 `false`；
- 迭代期用 `wf edge add` 给一个尚无 `meta.wf.deps` 的任务加边时，机制**补写**该对象（生成 id、`in_graph=true`、写入新前置）；
- 判据只认这个标记，不用“`meta.wf.deps` 是否存在”或“是否有 `prereqs`”这类间接形式——避免“有 id 但无前置”的任务被误判为图外。

**占用校验**（设计稿 §7.8 的两个时点）：

| 时点 | 对象 | 规则 |
|---|---|---|
| 写入前 | 预生成依赖标识（替换 / 放弃-新建替代 / 类型 1 P 预写 / 返工登记准备 / 据指向建任务） | 扫描**活动区 + 归档区**全部 `task.json` 与账本的 `replacement_target`、`note.rework.r_dep_id`；冲突则不写入、不覆盖，重新生成后重校验 |
| 写入前 | 预生成 slug（返工登记准备、建任务） | 扫描两个区，按目录名的 slug 部分比对（**忽略日期前缀**）；冲突则换序号重生成 |
| 已落盘 | 替换指向在补建 / 重连时发现目标标识已被其他身份占用 | 类型 4 阻断；不覆盖、不当作同一继任者；原关系恢复按设计稿 §7.8 的恢复边界 |

**解析**：标识 → 任务目录：扫描活动区与归档区建索引；账本 `task_dir` 仅作快速路径，与索引不一致时以索引为准并告警。

**重命名**：`wf rename` 包装原生 `task.py rename`，随后按标识同步账本 `task_dir` 与全部引用（下游前置集合、返工来源、替换指向、`meta.wf.deps.slug`）。

### 3.4 持久化与选择性提交

设计稿 §3 对“持久化”的要求比原生强：**提交按必要变更划界，不按整份文件划界**；不得捎带无关的任务产物、工作改动或暂存内容。实现口径如下。

**机制自己提交，不等 `session_auto_commit`**：每次机制写入通过洁净检查后，立即执行 `git add <单个路径> && git commit -m "<消息>"`。基底的两处自动提交（`add_session.py` 的 journal、`task.py archive` 的归档）保持默认，它们提交的是生命周期变更，不归机制。

| 场景 | 写入对象 | 提交范围 | 提交消息 |
|---|---|---|---|
| 状态转移（收尾 / 返工 / 替换 / 放弃 / 修复） | `ledger.json` | 仅该文件 | `chore(wf): <动作> <任务目录>` |
| 任务机制字段 | 一个 `task.json` 的 `meta.wf` 键 | 仅该文件 | `chore(wf): deps <任务目录>` |
| 建任务 | 基底 `create` 写整份 `task.json` + 机制写 `meta.wf.deps` | 基底组与机制组分开 | `chore(wf): init <任务目录>` |
| 归档 | 基底 `archive`（整目录移动 + `status=completed`） | 基底组 | 基底默认消息 |

**写前洁净检查（关键）**：机制写入前检查目标文件的未提交变更是否**只**属于本次机制写入的范围：

1. `git status --porcelain -- <path>` 显示该文件已修改；
2. `git diff -- <path>` 中不属于机制字段的部分非空 → **拒绝写入**，报告“该文件存在与本动作无关的未提交变更，请先提交或回滚”，并给出路径与差异摘要；
3. 通过后写入，立即提交。

**顺序**：收尾 = 源状态校验 → 原生 `archive`（基底提交）→ 账本写“正常” → 机制提交。**账本提交永远在归档提交之后**，保证“下游看到正常”蕴含“已归档”。中途失败按 §3.8 的类型 1 恢复。

**为什么不是 hunk 级提交**：git 没有稳定的“只暂存某文件的某个 JSON 键”原语，`git add -p` 不可自动化也不可复现。因此把“不捎带”从**提交端过滤**前移到**写入端准入**（洁净检查），并用“机制自己立即提交”保证未提交窗口极短。偏离登记见 §9-C4。

**失败窗口**：洁净检查通过、写入成功、提交失败 → 工作区存在未提交的机制变更。按设计稿 §3“未提交的变更不参与判定”处理；`wf doctor` 报告“存在未提交的机制变更”，`wf repair` 提供“补齐提交”动作（只提交，不改内容）。

### 3.5 机制入口（命令面）

**唯一入口原则**：图内任务的开工与收尾只走机制入口（设计稿不变量 5，强度 = 约定）；机制入口内部调用原生命令，不重实现生命周期。

| 入口 | 类别 | 前置（fail-closed） | 对原生的调用 | 写入 | 提交组 |
|---|---|---|---|---|---|
| `wf task new` | 副作用 | **按入口类型**，见下方“四种参数化入口”的前置列（本节不重复） | `task.py create --workflow wf --base-branch <当前分支> --slug <slug>` | 整份 `task.json`（基底）+ `meta.wf.deps`（机制） | 基底组 → 机制组 |
| `wf start` | 副作用 | 图内：前置全“正常” ∧ 账本“无记录”；图外：无 | `task.py start --allow-empty-context` → `task.py set-branch <task> <当前分支>` | `task.json`（status、branch） | 基底 |
| `wf close` | 副作用 | 源状态合法（账本“无记录” ∧ 前置全“正常”）；P 还需任务图齐（§3.9）；`pr_url` 必须为空 | `task.py archive <task> --skip-branch-validation` → `add_session.py` | 原生归档 + 账本“正常” | 基底组 → 机制组 |
| `wf edge add\|rm` | 副作用 | 建边：两端活动区 ∧ 前置未完工 ∧ 目标非异常；删边：目标可已归档 | 无 | 下游前置集合（+ 需要时补写该任务的 `meta.wf.deps`） | 机制组（暂存 → 后置校验 → 提交） |
| `wf rework` | 副作用 | T 未归档 ∧ 账本 ∈ {无记录, 挂起} ∧ 无未完成登记 | 阶段内 `task.py create`（建 R） | 账本（挂起 + 登记）、R 的 `meta`、T 的前置集合 | 见 §3.12 的分步组 |
| `wf replace` | 副作用 | 旧任务未归档 ∧ 账本 ∈ {无记录, 挂起}；静态校验通过 | `task.py create`（建继任者） | 账本（异常 + 指向）、下游前置集合、继任者 `meta` | 实施组 → 重连组 → 归档组 |
| `wf abandon` | 副作用 | 同上 + 变体合法（P 只允许新建替代） | 删边变体不建任务；新建替代建任务 | 同 `replace`；删边变体 `replacement_target=null` | 同 `replace` |
| `wf baseline --light` | 副作用 | 设计稿 §5.5 轻量用法：旧任务未归档 ∧ 账本 ∈ {无记录, 挂起}；人决定“工作仍然成立” | `task.py create`（建新任务） | 新任务 `meta`（继承前置）、下游前置集合（改指新任务） | 建任务组 → 重连组 |
| `wf repair` | 副作用（**人类专用**） | 启动自检识别到类型 1–5 之一 | 视类型：`archive` / `set-meta` / 删边 | 账本 / 前置集合 / 说明字段 | 按类型分步（§3.8） |
| `wf route` / `state` / `dag` / `check` / `doctor` | **只读** | — | 读 `get_context.py --mode phase`、`task.py list/current --json`、账本 | 无 | — |

**`wf task new` 的四种参数化入口**（这是 `task new` 前置条件的唯一源；主表不重复，避免两处不一致）：

| 用法 | 前置（fail-closed） | 适用 | prereqs 来源 |
|---|---|---|---|
| `wf task new --role project` | **无 P 时允许**（首个 P 必须能建）；已有未归档 P 或账本异常的 P → 拒绝并指引 `wf route` | 启动项目层（链头） | 空 |
| `wf task new --from-graph <key>` | P 已归档且账本正常；图块存在该 key；该 key 的前置任务均已建 | P 归档后按图建实现任务与收尾任务 | 读 P 的 `design.md` 图块，解析该 key 的 `prereqs`（任务定义类，不走建边校验） |
| `wf task new --prereq <id\|slug> [--role tail]` | P 已归档且账本正常；被引用的前置任务存在 | 重定义收尾任务（设计稿 §6.7）、手工补图外的图内任务 | 显式指定；属任务定义类，不走 §7.5 建边校验，但仍须无自环、不成环 |
| `wf task new --unrelated` | P 已归档且账本正常 | 插入图外工作 | `in_graph=false`，无 prereqs |

**`--from-graph` 的 slug 规则**：默认取图 key；可用 `--slug` 覆盖，但须过 §3.3 的唯一性校验。

**上游三条硬门与处置**（`实测` `0.7.0-beta.4`，`common/task_store.py` 的 `cmd_start` / `cmd_archive` / `_validate_branch_metadata`）：

| 上游约束 | 实际行为 | 处置 |
|---|---|---|
| `task.py start` 的 context-manifest 门：`implement.jsonl` / `check.jsonl` 已创建但无条目时拒绝 | 硬拒绝，需 `--allow-empty-context` | `wf start` 固定传该 flag。**明确决策，不是绕过**：本模块不派 Trellis 子代理，manifests 天然为空，该门保护的对象不存在 |
| `task.py archive` 先强制写 `status=completed` + `completedAt` 再移动目录 | 无条件写入 | 与设计稿的终态一致；`wf close` 的顺序必须是“先判定源状态合法 → 再调 archive” |
| `task.py archive` 的分支元数据门：① `branch == base_branch` → **Error + 拒绝归档**（`return False`）；② `branch` 缺失 + 有 `base_branch` + 仓库有 remote → **Error + 拒绝归档**；③ 已记录分支在本地不存在 → **Warning only** | 两条硬拒绝、一条警告 | **`wf close` 固定传 `--skip-branch-validation`**，并在调用前断言 `pr_url` 为空（见下） |

**为什么 `--skip-branch-validation` 是正确用法，而不是绕过**：

- 该 flag 的帮助文本是 `only if this task was never PR-backed`；本设计**单一工作线、不切分支、不建 PR**（设计稿 §1.1），任务恒为 never PR-backed，语义完全吻合；
- 不传它没有可行替代：`create` 的 fallback 会把 `base_branch` 写成 `origin/HEAD` 或当前分支，`start` 会把 `branch` 写成当前分支——单工作线下两者必然相等，第一道硬门必然命中。把字段清空也不可行：`set-branch` / `set-base-branch` 都拒绝空值（`common/task_store.py`）；
- 因此把该门视为**“PR 档案完整性门”而非“工作线门”**：模块在 `wf close` 内的断言顺序是 ① `pr_url is None`（模块不创建 PR，若出现值即说明有人走了别的路径，**拒绝 skip 并报告**）→ ② 传 skip → ③ archive。`wf doctor` 另有一项检查：`completed` 任务若 `pr_url` 非空却被机制归档过，报告为异常组合。

**分支零假设**：模块不建分支、不切分支、不要求、不检查、不记录“任务分支”；`task.json` 的 `branch` 与 `base_branch` 只是上游字段，值等于当前工作线；模块只负责在归档时用 skip 明确表达“本任务不参与 PR 档案门”。

**全部子命令提供 `--json`**，供 AI 机读；人类输出不求机读兼容。

**基线变更的两种路径（设计稿 §5.5）**：**仍然成立** → `wf baseline --light`：新建任务继承旧任务当前前置集合，默认把**全部未归档下游**重连到新任务，**旧任务保留在图中且不产生异常**（账本仍为无记录 / 挂起；就绪与否按公式判，挂起前须先按 §3.7 清挂起）；人要保留部分下游时，用 `wf edge add` 逐条建边到新任务、`wf edge rm` 从旧任务删边。**不再成立** → `wf replace` / `wf abandon`（旧任务异常归档，下游重连或删边）。两条路径互斥，由人在发起时选定；**不得**把旧任务直接归档（会命中“已归档 + 无记录”非法组合），也**不得**对旧任务自动放弃。

### 3.6 门禁不依赖“谁触发”

skill 会被模型自动触发，而**没有任何平台能让 CLI 判断调用者是模型还是人**。因此：

1. **只读子命令**（`route` / `state` / `dag` / `check` / `doctor` / `embed-state`）自动触发无风险，允许；
2. **有副作用子命令**的准入**只依赖状态**，不依赖调用者身份；
3. **破坏性 / 不可逆动作**（`uninstall --full`、`repair` 的确认异常改写、`upgrade --apply`）要求**人在交互式终端**执行：双 `isatty`（stdin + stdout）+ 手输令牌（`UNINSTALL-FULL` / `REPAIR <type>` / `UPGRADE <M_inst> -> <M_src>`）。AI 不得代跑、不得设 env 绕过；
4. 每个 skill 正文显式标注其子命令属“只读”或“有副作用”，并在有副作用处写明“需先满足的状态”。

**为什么这套门禁够用**：设计稿 §1.3 明确本设计**不防对抗**，只防意外与误报。状态型门禁挡的是“顺序错位”（未满足前置就开工、无源状态就收尾），这正是机制承诺的部分。

### 3.7 就绪、选择与下沉

**入口判定的三段式**（设计稿 §9.1，逐段判定、命中即停；`wf route` 的输出结构即此表）：

| 段 | 命中条件 | `wf route` 的下一步 |
|---|---|---|
| **第一段 全局旁路** | ① 模块不可用（账本不可解析、CLI 自检失败）→ 只卸载（§7.5），不绕过；② 完整性分流：字段/角色/登记信息非法 → 类型 4；有合法未完成返工登记 → 类型 2；其他未完成替换/放弃或类型 1 后续处分 → 类型 5；已归档但账本无记录/挂起 → 类型 1；③ 需要改基线 → 回设计稿 §5.5（本模块只输出“回到基线变更”指引，不实现基线流程） | 报告命中的旁路项 + 对应的 `wf repair` / `wf uninstall` 指引；**不进入普通选择** |
| **第二段 挂起** | 第一段未命中，且（当前任务按设计稿 §3 有效且挂起）或（无当前任务但存在挂起任务，按创建时间取最早） | 按设计稿 §9.1 第二段四行处置：有未归档 R → 进入 R；满足 §6.4 第 5 步 → 清挂起（表 4-2 行 3）；有返工记录但前置不全正常 → 逐项分流（递归）；无返工记录 → 类型 2 |
| **第三段 非挂起** | 前两段未命中 | 项目层未收尾 → 按“只执行 P / 取最早就绪图内任务 / 等前置”三行；已收尾 → 取最早就绪图内任务（含返工与收尾）→ 无就绪则判收尾是否完成 → 迭代期普通任务 |

**`wf route` 的输出契约**（机读字段）：`segment`（1/2/3）、`matched_row`（对应设计稿 §9.1 的行标识）、`current_task`（id + 任务状态 + 账本状态）、`next_action`（命令或“报告阻塞”）、`why`（引用的设计稿/依赖说明章节号）。人可通过 `why` 回溯判定依据——这是“只留痕、不担保真实”的可核对面。

**就绪判定**（唯一公式，实现为一个纯函数 `is_ready(task)`）：

```
is_ready = 任务未归档(未 completed)
         ∧ 账本状态 == 无记录
         ∧ 前置集合中每个标识解析到的任务：已归档 ∧ 账本 == 正常
         （公式对象是图内任务；图外任务不走本公式，按原生流程直接可做）
```

“正常但未归档”不算满足（设计稿 §4.3）；账本“异常”不算就绪（§7.4）；挂起不算就绪。

**选择规则**〔设计稿 §7.6〕：就绪集按**任务创建时间**升序取最早；不引入优先级字段。P 不在就绪集内（其推进由 §9.1 未收尾表的“只执行 P”行承担）。

**下沉**〔设计稿 §9.1〕：当前任务进行中但前置不全正常时，工作不停、只挡收尾；沿未完成前置链下行取链上最早就绪的图内任务先开工，完成后回本任务收尾。下沉目标本身挂起时以它为“对应 T”回到挂起段（§3.8 第二段）。终止性由 DAG 无环保证。

### 3.8 启动自检与对账修复

**启动时自检**（`wf check`，只读；`wf route` 内部先跑一遍）分两步：

**第一步 分类前置守卫**（依设计稿 §7.7）：先排除未完成返工登记（→ 类型 2）与字段/角色完整性不一致（→ 类型 4）；再判其余。**除“派生清除挂起”外，启动只识别与报告，不写账本、不改任务状态**。

**第二步 组合分类**（读账本 + 任务状态，设计稿 §7.7 的组合表逐行对齐）：

| 任务状态 | 账本 | 判定 | 出口 |
|---|---|---|---|
| `completed` | 正常 ∧ 前置全正常 | 合法 | — |
| `completed` | 正常 ∧ 前置含非正常 | 非法 | 类型 4 |
| `completed` | 挂起 / 无记录 | 非法 | 类型 1 |
| `completed` | 异常 | 合法（替换/放弃结果） | 未完成的转类型 5 |
| 未归档 | 正常 | 不一致 | 类型 3 |
| 未归档 | 挂起 | 合法（等待返工） | §3.7 的返工评估 / 进入 R |
| 未归档 | 异常 | 替换/放弃未完成 | 类型 5 |
| 未归档 | 无记录 ∧ 前置全正常 | 合法（就绪） | — |
| 未归档 | 无记录 ∧ 前置含非正常 | 等待 | 不修复，等前置完成 |
| 项目层已收尾 ∧ 无收尾对象 ∧ 尾端异常已终态 | — | 不一致 | 人重定义收尾 |

**`wf repair` 的类型面**（设计稿 §7.7 逐条）：

| 类型 | 判据 | 机制动作 | 提交组 |
|---|---|---|---|
| 1 | 已归档但账本无记录 / 挂起 | 人确认正常/异常；确认异常先落账本（含标记）再动下游（一般任务删边；P 建继任者并重连） | 账本组 → 下游组 |
| 2 | 返工登记未完成 / 挂起无返工记录 | 有标记按 §3.7 登记序列恢复或取消；无标记人确认补建或清挂起 | 按 §6.4 分步 |
| 3 | 正常但未归档 | 人确认重新归档（前置须全正常）或改回无记录 | 单组 |
| 4 | 无法解析 / 非法的记录或边 | 按 §6.1 恢复边界修字段，或删非法边 | 单组 |
| 5 | 替换 / 放弃未完成 | 先补建/重连、后归档；改判放弃只在继任者不存在时由人决定 | 补建组 → 重连组 → 归档组 |

**写入纪律**（设计稿 §7.7）：识别所依赖的标记（替换指向 / 原因 / 说明）必须与第一步状态写入**同次持久化**；逐窗口给出残留识别项；不回退、不重跑已完成确认。

### 3.9 项目层 P、任务图与基线

**四段结构的承载**（设计稿 §4.1）：项目层 = `role=project` 的任务、任务层 = 由 P 的图产出的 `role=impl` 任务、收尾层 = `role=tail` 任务、持续使用 = `in_graph=false` 的普通任务。四段**不是四种状态或四套机制**，而是任务角色 + 依赖边的组合；模块不为任何一段新增状态机。

**任务图是全部任务定义的唯一载体**（设计稿 §5.2 要求任务图含“全部实现任务、每个任务的前置集合、收尾任务定义”）：

- **落点**：P 的 `$TASK_DIR/design.md` 内一个固定标记的机检块（下称**图块**）；
- **收尾任务在此定义为图中的一个 `role: tail` 节点，不是“已建的任务目录”**——任务目录在 P 归档后由 `wf task new --from-graph` 按图创建。这样既满足“P 收尾时任务图齐”，也不与 `wf task new` 的“项目层已过”门禁冲突；
- **机检格式**（`wf check --graph` 与 `wf close`（P）按此校验）：

````markdown
<!-- wf:task-graph -->
```yaml
tasks:
  - key: t1
    title: 接口层
    role: impl        # impl | tail
    prereqs: []       # 图内 key 列表；P 隐含为所有根节点的前置
  - key: t2
    title: 业务层
    role: impl
    prereqs: [t1]
  - key: deliver
    title: 验收、交付与发布
    role: tail
    prereqs: [t2]
```
<!-- /wf:task-graph -->
````

**图块的校验规则**：key 唯一；恰有一个 `role: tail`；`prereqs` 只能引用块内 key（或留空）；无环；每个 impl 节点的 `title` 非空。校验失败时 P 不得收尾。

**P 的产物与“齐”的判据**（设计稿 §5.2）：

| 产物 | 落点 | 齐的判据 |
|---|---|---|
| 需求基线（范围 / 不做的事 / 验收口径） | `$TASK_DIR/prd.md` 的三个对应小节 | 三节均非空 |
| 技术基线（架构 / 外部依赖 / 风险与回退 / 规格骨架） | `$TASK_DIR/design.md` 的四个对应小节 + `.trellis/spec/**` | 四节非空，且至少一个 spec 文件被引用 |
| 任务图 | `design.md` 的图块 | 图块存在 ∧ 校验规则全过 |
| DAG 视图 | `wf dag` 输出 | 由前置集合 + 账本派生，可重建（`wf dag --check` 报告图与记录偏差） |
| 基线载体 | 项目文档（`prd.md` + `design.md`）与规格（`.trellis/spec/**`） | 两者都存在且互相引用 |

**P 收尾后的建任务顺序**：`wf task new --from-graph <key>` 要求该 key 的前置任务**已建**（因为要写依赖标识），因此按图块拓扑序创建（`t1 → t2 → tail`）。**图块中 `prereqs` 为空的根节点，其前置集合写成 `{P 的依赖标识}`**（设计稿 §5.6：所有 0→1 实现任务直接或间接依赖 P）；`prereqs` 非空的节点只写图内前置，不再重复写 P——间接依赖已由链传递。全部任务可以一次性建完（都处于 `planning`），之后按 §3.7 的就绪规则逐个开工——串行由依赖边保证，不靠创建顺序。

**不设 `.wf/contract.yaml`**：契约内容（范围基线 + 验收面 + 受管资产清单 + 人确认）分别落在 P 的 `prd.md` / `design.md` 与设计稿 §5.5 的基线变更流程里；新增一个模块自有文件会造出**第二套项目级状态**，与设计稿不变量 2（单一状态源）冲突。冲突登记见 §9-C3。

**“未定标不许开任务”的落点**：**除 `--role project`（建链头本身，见 §3.5 参数化入口的前置）外**，`wf task new` 一律要求“存在 `role=project` 且已归档、账本为正常的 P”。P 归档的前置是任务图齐（§4.5 项目层收尾关卡），因此“能建后续任务”⇒“图已齐”。不额外引入“契约确认”这一步。

### 3.10 状态派生与视图

| 派生结论 | 判据 |
|---|---|
| 待办 | `status == planning` ∧ 账本无记录 |
| 可开工 | `is_ready(task)`（§3.7 公式） |
| 等待前置 | 未归档 ∧ 无记录 ∧ 前置含非正常 |
| 等待返工 | 未归档 ∧ 账本挂起 |
| 异常待处置 | 账本异常（按 §7.4 字段判终态/未完成） |
| 已完成 | `completed` ∧ 账本正常 |
| 异常归档 | `completed` ∧ 账本异常 |

**收尾对象与项目完成**（设计稿 §6.7 的唯一源，实现落点）：**收尾对象** = 沿继任链取 `role=tail` 的末端任务，且（未归档且账本非异常）或（已归档且账本正常）；**收尾完成** = 存在收尾对象 ∧ 该对象已归档 ∧ 账本为“正常”。收尾任务被放弃且无继任者时，项目层判定失去对象，按 §3.8 组合表的“待重定义”行由人重建 tail 任务（`wf task new --prereq <最后实现任务> --role tail`）。

**视图**：`wf dag` 输出就绪/阻塞与组件划分；`wf state` 输出当前任务的完整二元组；两者都 `--json`。视图由已提交事实重建，不反向写事实。

### 3.11 旁路与禁止路径的实现对应

**表 9-1 任务级旁路**（设计稿 §9.2）：

| 旁路 | 实现入口 | 恢复 |
|---|---|---|
| 无关任务 | `wf task new --unrelated`（要求 P 已归档；写 `in_graph=false`，无 prereqs） | 完成后回 DAG 顺序 |
| 迭代任务 | `wf task new`（不建边）或 `wf edge add` 后续补边 | 普通流程 |
| 替换 / 放弃 | `wf replace` / `wf abandon` | 旧任务异常归档；下游重连或删边；实施后只向前完成 |

**表 9-2 依赖级旁路**（设计稿 §9.2）：

| 旁路 | 实现入口 | 校验 |
|---|---|---|
| 挂起 | `wf rework` 的登记准备（写账本挂起） | 清除按 §3.7 的评估点，不另设命令 |
| 建边 / 删边 | `wf edge add` / `wf edge rm` | 建边两端活动区、前置未完工、目标非异常、无环；删边目标可已归档；一律先暂存、后置校验、通过才提交 |
| 重连 | `wf replace` / `wf abandon` 实施第 3 步、`wf baseline --light` | 两端存在、无环；不改变原任务已实施的“异常” |

**禁止路径的护栏**（设计稿 §9.3，逐条给实现拦截点）：

| 禁止路径 | 拦截点 |
|---|---|
| 用任务状态表达依赖状态 | §3.1：只有三值可写；`wf doctor` 检出非三值即报告 |
| 图内任务走原生开工 / 收尾 | 不阻断（§3.6），但 `wf doctor` 比对“账本有条目却无机制入口记录”的历史并报告 |
| 手改账本 | 无法技术上禁止；`wf doctor` 用 `git diff` 检出人工编辑的账本变更并报告（账本变更必须伴随机制提交组） |
| 跨项目依赖 | 标识解析只在本项目索引内；跨项目标识解析失败即报告 |
| 用编号顺序替代依赖边 | 不读任务目录名做顺序判定（只读前置集合） |
| 把异常改写成正常绕过重连 | W13：表 4-2 无“异常 → 正常”，机制入口拒绝 |
| 写入表 4-2 之外的转移 | 同上（唯一合法转移集） |
| 替换 / 放弃实施后回退 | W20：`wf repair` 不提供改回路径 |
| 机制不可用时绕过开工 | §3.7 第一段：模块不可用只卸载 |
| 卸载留下阻断基底的残留 | W16：卸载后基底可建任务/开工/归档 |

### 3.12 返工登记的实现序列与定位规则

设计稿 §6.4 把返工的**动作序列与窗口**定为唯一源，并把“定位格式 / 命令”委派给实现方案。本节就是该委派的答案。

**定位规则（最关键的一条）**：**定位 = 任务 slug，不含日期前缀。**

上游 `task.py create` 的目录名是 `{今天 MM-DD}-{slug}`
（`common/task_store.py` 的 `cmd_create`），且明确拒绝用 `--slug` 指定非今天的日期前缀（“task.py create always uses today's date”），也没有“在指定路径建任务”的参数。因此**任何把日期写进定位的设计都必然在跨日恢复时失配**。机制的做法是：

| 环节 | 规则 |
|---|---|
| 生成 | 登记准备时生成 `r_slug`（形状 `<T 的 slug 前 24 字>-rework-<序号>`）与 `r_dep_id`；`r_slug` 必须通过 §3.3 的 slug 占用校验（忽略日期前缀比对） |
| 找回 | 先按 `r_dep_id` 扫描两个区的 `meta.wf.deps.id`；未命中则按**目录名的 slug 部分等于 `r_slug`** 扫描：命中 1 个 → 复用；命中 0 个 → 创建；命中多个 → 类型 4 阻断 |
| 创建 | `task.py create --slug <r_slug> --description <R 的描述> --workflow wf`；目录日期前缀由**创建当天**决定，不参与匹配，跨日不构成失配 |
| 位置占用 | 同 slug 已存在但 `rework_source` 不是 T（或 id 不符）→ 视为创建失败，类型 4 阻断，不覆盖 |
| 标识占用 | `r_dep_id` 与既有身份冲突 → 重新生成并重写标记（本次改写立即自成提交组），再从新值继续 |

**序列**（分步提交组）：

| 步 | 动作 | 写入 | 提交组 |
|---|---|---|---|
| 1 准备 | 校验 T 的适用状态与无未完成登记；预生成 `r_dep_id` + `r_slug` + 定位 | 账本：T 的 `dep_state=suspended` + `note.rework`（同次） | 机制组（账本） |
| 2 创建或找回 | 按上表规则读回或创建 R | R 的 `task.json.meta.wf.deps`（id / slug / role=rework / rework_source / 继承前置） | 机制组（R 的 task.json） |
| 3 发布 | 把 R 加入 T 的前置集合，消费登记标记 | T 的 `meta.wf.deps.prereqs` + 账本的 `note.rework` 移除 | 机制组（T 的 task.json）→ 机制组（账本） |
| 4 执行 | 按普通图内任务执行 R；完成按 §3.7 | — | — |
| 5 清除 | 按设计稿 §6.4 第 5 步判据评估 | 账本：T 的 `dep_state` 挂起 → 无记录（表 4-2 行 3） | 机制组（账本） |

**逐窗口恢复**（残留一律向前完成，不回退、不重跑已完成的确认）：

| 窗口 | 已提交的识别项 | 恢复 |
|---|---|---|
| 准备提交前 | 无本次标记、状态未变 | 本次尚未实施，不声称已有返工 |
| 准备后、创建前 | T 挂起 + 登记（`r_dep_id` / `r_slug`） | 继续步骤 2；人确认取消时按取消路径 |
| 创建调用中断 | 标记在；按 slug 扫描可能命中 0 或 1 个 | 命中 1 个即复用；0 个则创建；扫描异常（多个）→ 类型 4 |
| **跨日恢复** | 标记在，`r_slug` 不变 | **按 slug 找回，日期前缀不参与匹配**；若未创建则用当天前缀创建 |
| 创建成功、发布未提交 | R 存在且 `meta` 已写，T 的前置集合未含 R | 只补发布（步骤 3），不重建 R |
| 发布提交后、视图未重建 | 标记已消费，R 身份与边已生效 | 重建视图，按正常返工继续 |
| R 已归档、账本“正常”未提交 | R 未满足依赖 | 类型 1 修复 R；T 保持挂起 |
| R 正常已提交、T 未清挂起 | 无当前标记，R 已归档正常 | 按步骤 5 评估；有其他活动 R 或前置不全正常则不清 |
| 取消提交前 / 后 | 前：标记保留；后：标记已消费且原状态已恢复 | 前仍按登记恢复，后不重复取消；原挂起不得误清 |

**为什么这套规则不依赖跨系统原子**：每个窗口的识别项都是**已提交**的字段（`r_dep_id` / `r_slug` / `rework_source` / 前置集合），恢复动作只读已提交事实并向目标态推进；创建与发布分成两个提交组，正是为了不假设 `create` 与账本写入原子。

---

## 4. 平台支持

### 4.1 平台矩阵（数据，不是代码）

模块只承认**五平台显式支持**；其余 agent 走 §4.9 的通用路径。下表是本文件里**唯一**允许出现平台差异的位置：

| 平台 | skill 根（投放） | 命令/提示根 | 注入通道 | `AGENTS.md` | 证据 |
|---|---|---|---|---|---|
| **Claude Code** | `.claude/skills/` | `.claude/commands/`（可选） | `.claude/hooks/` + `settings.json`（SessionStart / UserPromptSubmit / PreToolUse） | ⚠️ 条件性（无 `CLAUDE.md` 时读 `AGENTS.md`） | `实测`（本仓库目录）+ `文档`（条件性） |
| **Codex** | `.agents/skills/` | 无 | `.codex/hooks/` + `hooks.json`（需用户级 `features.hooks=true` + 一次性 `/hooks` 审批） | ✅ | `实测`（目录）+ `读码`（hook 生效条件） |
| **ZCode** | `.agents/skills/`（可被 `.zcode/skills/` 同名遮蔽） | `.zcode/commands/` | `.zcode/hooks/` + `config.json`（四条命令） | ✅ | `实测`（目录、hook 漂移、2026-10-28 会话中 `AGENTS.md` 注入） |
| **Pi** | `.agents/skills/` | `.pi/prompts/` | `.pi/extensions/trellis/index.ts`（原生扩展） | ✅（同族约定，`推断`） | `读码`（`resolveWorkflowMd` 实现变体链） |
| **DSH** | `.agents/skills/` | `.dsh/skills/`（命令即 skill） | 无项目级 hook | ✅ 每会话读 | `实测`（本会话观测） |
| **通用 agent** | `.agents/skills/`（若该 agent 读） | 无 | 无 | ✅（若读） | `推断` |

**投放决策**：

| 决策 | 取值 | 理由 |
|---|---|---|
| 投 `.dsh/skills/` 吗 | **不投** | DSH 的 `.dsh/skills/` 优先级高于 `.agents/skills/`（rank-100 遮蔽），同内容投两份会制造第二份同步资产 |
| 投 `.pi/prompts/` 吗 | **不投** | 同上：skill 已覆盖，命令面是重复资产 |
| 投 `.zcode/skills/` 吗 | **不投** | ZCode 同时扫描两个根，`wf` 与 Trellis 的 `trellis-*` 不同名，不存在遮蔽冲突，`.agents/skills/` 足够；投 `.zcode/skills/` 只会多一份同步面（且该目录是 Trellis 受管路径） |
| 投 `.zcode/commands/` 吗 | 可选（默认不投） | `.zcode/commands/` 当前承载 Trellis 的 `/trellis:*`；模块走 skill-first，不新增命令文件 |
| 投 `.codex/skills/` 吗 | **不投** | Codex 只用 `.agents/skills/` |

### 4.2 新增平台的接入四条件

加一行平台只是**登记**；接入一个平台必须同时满足四条，缺一即**声明该平台不受支持**（不是降级使用）：

| # | 条件 | 判据 | 失败处置 |
|---|---|---|---|
| 1 | **skill 发现** | 该平台确实读取我们投放的根（真实会话中能被加载/触发） | 不投放该根，声明不受支持 |
| 2 | **frontmatter 兼容** | 渲染出的 frontmatter 被正确解析（未知字段静默忽略） | 退化为最小 `name` + `description` 并记录 |
| 3 | **变体解析（硬门槛）** | 该平台经 `get_context.py --mode phase` 读到 `.trellis/workflows/wf.md`（哨兵串验证） | **声明不受支持**，不降级 |
| 4 | **CLI 冒烟** | 在该平台真实会话里跑通 `wf route`（只读）至少一次 | 未冒烟前不写入“已支持”清单 |

**第 3 条为什么是硬门槛**：变体链是本方案“零补丁”的承重结构。只读全局 `.trellis/workflow.md` 的平台无法在不改上游文件的前提下拿到本流程文本——那就必然回到补丁模式，与设计稿 §1.2 的模块边界冲突。

### 4.3 skill 面与 frontmatter 渲染

**同一份正文，按平台注入 frontmatter**：

| 平台 | frontmatter 字段 | 正文 |
|---|---|---|
| Claude Code | `name` + `description` + `allowed-tools`（可选，减少授权打断） | 同一份 |
| Codex / ZCode / Pi / DSH | `name` + `description` | 同一份 |
| 未知/未来平台 | 保守取 `name` + `description` | 同一份 |

**正文占位符**（由渲染层替换，正文不出现平台分支）：

| 占位符 | 值 | 理由 |
|---|---|---|
| `{{PYTHON_CMD}}` | 目标项目解析出的解释器（Trellis 的 `TRELLIS_PYTHON_CMD` 同源） | `python3` 在 Windows 上通常不存在；写死会让整条链路不可执行 |
| `{{MODULE_VERSION}}` | `module.yaml` 的 `module_version` | |
| `{{VERIFIED_RANGE}}` | `verified_trellis_range` | |
| `{{CLI_PATH}}` | `.trellis/scripts/wf/wf.py` | |

**description 必须写清与上游 skill 的分工**（否则模型在同一意图上随机选）：

| 模块 skill | 重叠的上游 skill | 分工写法要点 |
|---|---|---|
| `wf` | `trellis-start`、`trellis-continue` | “本项目**下一步做什么以 `wf route` 为准**；`trellis-start/continue` 是上游 Trellis 流程入口，本项目不使用其阶段语义” |
| `wf-repair` | `trellis-check`、`trellis-finish-work` | “本 skill 只做**依赖账本对账与异常处分**；代码质量检查仍用 `trellis-check`，收口记录仍用 `trellis-finish-work`” |

同一分工表同步写进 `AGENTS.md` 的 NL 路由段（§6.5）——skill 可能不被触发，而 `AGENTS.md` 每会话必读。

### 4.4 Claude Code

- **入口面**：`.claude/skills/wf/`、`.claude/skills/wf-repair/`；命令面可选不投。
- **必需能力**：变体解析（`实测`：`workflow_selection.resolve_workflow_md` 与 `workflow_phase._workflow_md_path` 同源）、`get_context.py` / `task.py` 可执行、任务记录可提交。
- **增强能力**：SessionStart 注入变体 Phase Index、UserPromptSubmit 注入 `[workflow-state:*]` 面包屑、PreToolUse 注入子代理上下文（均由 `.claude/hooks/` 承担；本模块不新增 hook）。
- **验收判据**：G0 四项在本平台的可执行形式（§4.10）。
- **注意**：若目标项目根存在 `CLAUDE.md`，`AGENTS.md` 的 NL 路由对 Claude Code **可能不生效**；安装器与 `wf doctor` 必须显式提示“在 `CLAUDE.md` 中 import `AGENTS.md`，或把 Project instructions 切为'两个都读'”。**推断**成分：Claude Code 的条件性读法来自官方文档，未在本机版本实测。

### 4.5 Codex

- **入口面**：`.agents/skills/`（共享层，Codex 读取由用户确认）。
- **必需能力**：同 §4.4。Codex 无命令面，`AGENTS.md` + `.codex/config.toml` 是主要通道。
- **增强能力**：`.codex/hooks.json` 的 `SessionStart` / `UserPromptSubmit` / `PreToolUse`。**生效条件**：仓库被信任 ∧ 用户级 `features.hooks=true` ∧ 完成一次性 `/hooks` 审批。三者缺一，增强通道静默缺失。
- **验收判据**：G0 四项；增强通道按“能力分级”记录（未开 hook 时记 N/A，不记失败）。
- **不投**：`.codex/skills/`（即使 `trellis init` 创建了该目录也不放内容）。

### 4.6 ZCode

- **入口面**：`.agents/skills/`（ZCode 同时扫描 `.zcode/skills/` 与 `.agents/skills/`，同名时前者优先；`wf*` 无同名冲突）。
- **命令面**：不投（默认）；`.zcode/commands/trellis/` 仍是 Trellis 的命令面，模块不介入。
- **注入通道**：`.zcode/hooks/` 四个脚本（`session-start.py`、`inject-workflow-state.py`、`inject-subagent-context.py`、`inject-shell-session-context.py`）+ `.zcode/config.json` 的命令串。**这是本平台唯一需要受管修正的通道**，加固要求见 §5。
- **必需能力**：变体解析（`读码`：与 Claude/Codex 共用 `get_context.py` 链路）、`task.py` 可用、任务记录可提交。
- **增强能力**：依赖 hook 生效；加固后 hook 在 cwd 漂移时仍能解析到项目根（§5.6 验收）。
- **已知平台事实**（`实测`，本仓库 2026-10-25 记录）：`${ZCODE_PROJECT_DIR}` 绑定会话实时 cwd，不是固定项目根；hook 脚本缺失时命令以退出码 2 结束，宿主将其解释为“阻断”，曾导致会话死锁。
- **验收判据**：G0 四项（§4.10）＋ ZCode 加固五项 Z1–Z5（§5.6）；其中“增强通道”一项必须通过（加固后可用），不得记 N/A。
- **不投**：`.zcode/skills/`（见 §4.1 决策表）。

### 4.7 Pi

- **入口面**：`.agents/skills/`。
- **命令面**：不投 `.pi/prompts/`（已有 `trellis-*.md` 三份，属 Trellis 原生）。
- **注入通道**：`.pi/extensions/trellis/index.ts` 的 `resolveWorkflowMd` **完整实现了变体解析链**，并按 `task.json.status` 原样查 `[workflow-state:*]`（`读码`，未在真实 Pi 会话实测）→ 本方案对它同样成立。
- **必需能力**：同 §4.4。
- **增强能力**：扩展提供的每轮面包屑与 SessionStart 索引。
- **验收判据**：G0 四项；“变体实际解析”一项必须在真实 Pi 会话中跑出哨兵串才可写“已支持”。

### 4.8 DSH

- **入口面**：`.agents/skills/`；`.dsh/skills/` 由 Trellis 自身投放（`trellis-*`），模块不投。
- **注入通道**：**无项目级 hook**。每轮提示只能靠 skill + `AGENTS.md`。
- **必需能力**：同 §4.4（`实测`：本会话中 `get_context.py`、`task.py` 均可用）。
- **增强能力**：无。G0 的“增强通道”项记 **N/A**，不得写成“全绿”。
- **验收判据**：G0 的前三项必须通过；“增强通道”记 **N/A**（无项目级 hook），不得写成“全绿”。
- **设计后果**：DSH 上“必须先做的事”全部写在 skill 正文与 `wf route` 输出里，不依赖 hook。这正是 §4.2 第 3 条硬门槛要保证的：即使没有 hook，变体文本仍然通过 `get_context.py` 送达。

### 4.9 通用 agent（不逐平台适配）

对未在上表登记任何行的 agent，模块提供**通用性支持**，分两级：

| 级别 | 条件 | 能力 | 声明 |
|---|---|---|---|
| **L1 文件级** | 该 agent 读 `AGENTS.md` 与/或 `.agents/skills/`，且当前会话可执行 shell | 全部能力（路由、开工、收尾、对账） | “通过通用约定支持，未做平台验收” |
| **L2 纯 CLI** | 该 agent 只能执行命令，不读上述文件 | 全部能力，但“该先加载 skill”这一步由人保证 | “仅 CLI 可用；门禁仍生效（状态型），但不保证顺序被发现” |

**L2 的风险要写清**：门禁是状态型的，绕过顺序不会被**阻断**，只会让 `wf doctor` 报告“跳过了前置”；设计稿 §1.3 把这类情形归为“只留痕”，不承诺阻断。**不得**把 L1/L2 写成“已支持五平台之外的一切 agent”。

### 4.10 平台接入验收（G0）

“目录存在 + CLI 引用正确”不算支持一个平台。五平台各自必须在**真实会话**里过四项，缺一不写入“已支持”清单：

| 验收项 | 判据 | 适用 |
|---|---|---|
| skill 可加载 | 该平台会话里 `wf` skill 能被加载（手动触发即可） | 五平台全部 |
| 变体实际解析 | `wf route` 输出的哨兵串与 `get_context.py --mode phase` 一致（证明读到的是 `wf` 变体而非全局 `workflow.md`） | 五平台全部 |
| CLI 冒烟 | 该平台会话里成功跑通 `wf route`（只读）至少一次 | 五平台全部 |
| 增强通道 | 面包屑 / SessionStart 按能力分级：支持的平台必须通过，不支持的记 N/A | Claude / Codex / ZCode / Pi 通过；DSH 记 N/A |

**执行时点**：G0 必须在 P0 阶段跑完（§8.2）。理由：对 Pi / DSH / ZCode 的部分结论来自读码或目录实测，若结论不成立，受影响的是“五平台支持”这个目标本身。

**跨 CLI 接手判据**：同一任务由 CLI-A 实施 → CLI-B 接手 → 继续实施；一致性判据是 `task.json` 的 `status` + `meta.wf.deps` + 账本该任务的条目 + `get_context.py` 输出在两端一致。

---

## 5. ZCode 加固（安装期必做）

### 5.1 问题

`实测`（本仓库 2026-10-25，宿主源码 `/opt/ZCode/resources/glm/zcode.cjs` 的 hook 环境构造 `ZCODE_PROJECT_DIR: t.cwd || n`）：

1. **变量绑定会话实时 cwd**，不是固定项目根；Claude Code 的 `CLAUDE_PROJECT_DIR` 才是固定项目根。ZCode 没有提供固定项目根的变量。
2. ZCode 的 Bash 工具**跨调用保持 cwd**。一旦会话 cwd 漂到仓库根以外的任何目录（**包括仓库内的子目录**，如 `docs/workflows`），后续每个配置 hook 都会把 `${ZCODE_PROJECT_DIR}` 解析到漂移目录，找不到 `.zcode/hooks/*.py`。
3. 找不到脚本时 `python3 <missing>` 退出码 **2**，被 ZCode 的 hook 契约解释为“故意阻断”：`UserPromptSubmit` 失败会**挡住输入本身**，形成**会话死锁**（模型想 `cd` 回来也被 `PreToolUse` 挡住）。

**模板原形**（`trellis init` 生成）：`python3 "${ZCODE_PROJECT_DIR}/.zcode/hooks/<script>.py"` —— 在上述语义下必然失败。

### 5.2 加固命令模板（四条，逐字可用）

```sh
f=".zcode/hooks/<script>.py"; d="${ZCODE_PROJECT_DIR:-}"; if [ -z "$d" ] || [ ! -f "$d/$f" ]; then d="$(git rev-parse --show-toplevel 2>/dev/null)"; fi; if [ -n "$d" ] && [ -f "$d/$f" ]; then ZCODE_PROJECT_DIR="$d" exec {{PYTHON_CMD}} "$d/$f"; fi; exit 0
```

四条 `<script>` 取值与事件绑定（与 `trellis init --zcode` 的配置一致）：

| 事件 | matcher | `<script>` | 超时 |
|---|---|---|---|
| `SessionStart` | `startup\|clear\|compact` | `session-start.py` | 30s |
| `UserPromptSubmit` | — | `inject-workflow-state.py` | 15s |
| `PreToolUse` | `Agent\|Task` | `inject-subagent-context.py` | 30s |
| `PreToolUse` | `Bash` | `inject-shell-session-context.py` | 5s |

**每条分句的作用**（改动时不得删句）：

| 分句 | 作用 |
|---|---|
| `d="${ZCODE_PROJECT_DIR:-}"` | 取宿主给的候选根 |
| `[ -z "$d" ] \|\| [ ! -f "$d/$f" ]` → `git rev-parse --show-toplevel` | 候选根不含脚本时（cwd 已漂移），退到 git 仓库根——从仓库内任意子目录都能正确解析 |
| `ZCODE_PROJECT_DIR="$d" exec ...` | **必须回写**：`session-start.py` 直接把该变量当项目根（`project_dir / ".trellis"`），不做向上查找 |
| `exit 0` | 解析失败也不阻断输入（把退出码 2 的死锁语义消掉） |

**为什么不改 hook 脚本本身**：`.zcode/hooks/*.py` 是 Trellis 受管文件（`.trellis/.template-hashes.json` 跟踪），改脚本会制造第二处漂移；命令串改在 `config.json` 里只有一处，且卸载/升级时有明确还原点。冲突与债务见 §9-C8。

**解释器**：模板用 `{{PYTHON_CMD}}` 渲染。**本仓库实例当前写死 `python3`**（历史加固时未参数化），这属 §9-C13 的已知小偏差；模块安装器生成时必须参数化。

### 5.3 安装期步骤

`wf install` 检测到目标项目存在 `.zcode/` 时，按顺序执行：

1. 读 `.zcode/config.json`；若不存在对应 hook 条目 → 跳过并报告“该平台未配置 hook，仅 skill 通道可用”（不创建 hook）；
2. 对四条命令做**原形识别**：命令串等于模板原形，或已等于加固形态 → 继续；其他形态 → **停止并报告**（不覆盖人的自定义）；
3. 备份原文件到 `.trellis/.runtime/wf/pre-install/zcode-config.json`（本机态快照，与 §7.5 的卸载还原同源）；
4. 写入加固形态（保留 JSON 其余字段、键顺序、`enabled` 与 `timeout`）；
5. 自检：四条命令都能在“cwd = 仓库根”“cwd = 仓库内子目录”“cwd = 仓库外”三种情形下执行到正确分支（§5.6）；
6. 写入 `install-record.json` 的 `zcode_guard.applied_at`。

**卸载**：`wf uninstall --module` 按 §7.5 的**还原依据三级顺序**取得基线（本机快照 → git 历史 → fail-closed）后把四条命令还原为原形，随后移除本机快照。还原失败时报错并保留现场，不静默留半套。

### 5.4 漂移债务

加固后 `.zcode/config.json` 与 Trellis 模板不再字节一致，`trellis update` 会把它归为 `skip-modified`（保留本地版本，不再自动接收上游更新）。**债务登记**：

| 项 | 内容 |
|---|---|
| 债务性质 | 受管文件的本地修正（T1c），非模块自有路径 |
| 谁承担 | 目标项目的维护者 |
| 何时偿还 | 每次 `trellis update` 之后 |
| 怎么偿还 | `trellis update --dry-run` 看该文件是否出现在变更清单 → 有则把上游模板的 config.json 与本文件 diff → 只把**非我们改动的部分**（如新增 hook 项、字段改名）人工搬过来；搬完重跑 §5.6 自检 |
| 何时可撤销加固 | 上游提供任一条件时：① 模板命令自带 git-root 兜底；② hook 缺失不再以退出码 2 阻断；③ ZCode 提供固定项目根变量。三者任一落地，删除本节加固、恢复模板原形、在 `install-record.json` 标记 `zcode_guard.dropped` |

### 5.5 撤销条件与回滚

| 触发 | 动作 |
|---|---|
| 上游修复（§5.4 三条任一） | 还原模板原形，`wf doctor` 不再报债务 |
| 加固导致 hook 行为异常（如正常 cwd 下输出变化） | 从安装前快照还原原形，报告为“平台不兼容”，不尝试第三种写法 |
| 项目不再用 ZCode | 还原原形（保持与模板一致），随 `--module` 卸载一并执行 |

**验证方式**（加固后必须跑一次）：`实测` 判据——① cwd = 仓库根：四条命令的 stdout/stderr 与原形**逐字节相同**；② cwd = 仓库内子目录（如 `docs/workflows`）：`SessionStart` 与 `UserPromptSubmit` 正常产出 `additionalContext` JSON；③ cwd = 仓库外或异仓：四条命令退出码 0、无输出。

### 5.6 ZCode 验收判据

| # | 判据 | 方法 |
|---|---|---|
| Z1 | 四条命令均为加固形态 | `grep` 命令串含 `git rev-parse --show-toplevel` 与 `exit 0` |
| Z2 | cwd 漂移下不阻断输入 | 在子目录会话里发一条 prompt，能正常收到回复且面包屑仍出现 |
| Z3 | 正常 cwd 行为未变 | 与原形输出逐字节对比（同一 payload） |
| Z4 | 卸载后回到原形 | `uninstall --module` 后 `git diff .zcode/config.json` 为空（相对安装前基线） |
| Z5 | 债务可见 | `wf doctor` 在 ZCode 项目上输出“config.json 为受管修正”一行 |

---

## 6. 记录、证据与写入纪律

### 6.1 记录与事实源

与设计稿 §8.1 一一对应，不新增记录类型：

| 记录 | 实现落点 | 归属 | 写入者 |
|---|---|---|---|
| 任务记录 | `task.json`（含 `meta.wf.deps`） | 基底 + 机制 | 基底生命周期动作 + 机制入口 |
| 依赖账本 | `.trellis/dependencies/ledger.json` | 依赖机制 | 机制入口（禁止手改） |
| 项目基线 | `$TASK_DIR/prd.md` + `design.md` + `.trellis/spec/**` | 基底 | 人与 AI |
| 会话日志 | `.trellis/workspace/<dev>/journal-N.md` + `index.md` | 基底 | `add_session.py`（`wf close` 调用） |
| 规格 | `.trellis/spec/**` | 基底 | 人与 AI |

**人判不新增记录类型**（设计稿 §8.1）：人判是基底 check 之后的原生人工环节——在本模块中体现为“人显式调用 `wf close`”。命令调用本身不是证据，痕迹在会话日志与版本库。

**不设操作日志、不做追加式对账记录**（设计稿 §8.2）：覆盖式更新，历史以版本库为准；收尾失败按 §3.8 恢复，不重放。

### 6.2 完成判定（与“证据层”的区别）

设计稿 §4.3 的判定：**任务完成 = 基底完成实施与检查 ∧ 人判 ∧ 已归档**。实现层不引入任何“验证记录”，也不引入信任根：

| 旧实现方案的做法 | 本方案的做法 | 取舍理由 |
|---|---|---|
| `wf declare` 写 `meta.wf.impl_sha` + `status=wf-verify` | **不存在** | 设计稿不设“待验证”状态；任务状态只有三值 |
| `wf verify --checks` 写 `meta.wf.verification = {sha, checks, result, level}` | **不存在** | 设计稿 §1.3 明写“不做验证证据链”；完成判定不含证据 |
| `wf close` 要求 `verification.sha == HEAD ∧ result == pass` | `wf close` 只校验**源状态合法性**（账本无记录 ∧ 前置全正常） | 强证据会在单工作线下把“人判”替换成“机器判”，与设计稿的取舍相反 |
| `wf self-hash` / `--from-anchor` / 信任根 | **整组不存在**（含 `wf self-hash` 本身） | 信任根要防的是“用被本任务改过的脚本给自己判分”；本方案没有任何自写的判定产物参与判定，因此无对象可防。保留一个没有消费者的哈希输出只会让实现者误以为存在证据链 |
| `wf self-test` | **保留** | 它是模块自检（CLI 能否跑通、变体能否渲染、账本能否解析），服务于 `wf doctor` 与探针，不参与任何判定 |

**代价要写清**：模块无法回答“这个任务是凭什么算完成的”。它只能回答“这个任务在何时被谁归档、归档时前置是否全正常、账本是否为正常”。其余依赖会话日志、journal 与版本库。这是设计稿有意为之的边界（§1.3“只留痕”），实现层不得自行加固。

**冲突登记**：§9-C1。

### 6.3 原生字段纪律

**判据**：模块不得在任何上游字段上定义自己的语义；可用空间只有两个：

| 空间 | 归属 | 允许的用法 | 不允许的用法 |
|---|---|---|---|
| `task.json.status` | 上游字段，上游只解释 `planning` / `in_progress` / `completed` | 只用这三个值 | 写入 `wf-*` 或任何私有值 |
| `task.json.meta` | 上游显式保留的自由区（`meta: Record<string, unknown>`） | `meta.wf.deps` 存依赖标识、前置集合、返工来源（序列化为 JSON 字符串，经 `task.py set-meta` 写入） | 用它承载“判定结果”或替代账本状态 |

**明确禁止的一张表**：

| 上游字段 | 看似可用 | 为什么不允许 |
|---|---|---|
| `commit` | “存被验证的提交 sha” | 上游从未写入它（`create` 写死 `null`，全库无写入点），语义未定义；写它就等于定义一个上游随时会按自己理解使用的字段 |
| `pr_url` | — | 预留语义；模块不创建 PR |
| `worktree_path` | “存准洁净临时检出” | 上游语义是“任务工作单元路径”；本方案的临时目录用完即删，不构成任务身份（且准洁净验证已剔除，§9-C14） |
| `notes` / `relatedFiles` / `scope` | — | 上游语义；模块只读不写（`scope` 若需写，走原生 `set-scope`，语义与上游一致） |
| `branch` / `base_branch` | — | 由原生 `start` / `set-branch` / `set-base-branch` 写，模块只调用不解释 |
| `.trellis/config.yaml` 的其他键 | — | 除 `default_workflow` 那一行外一律不碰 |

**“原生优先”与“原生字段纪律”是同一原则的两面**：前者管“别重实现”，后者管“别挪用”。只做前者，会出现“看起来零补丁、实际把耦合藏进字段语义”的写法。

### 6.4 提交归属与顺序可恢复

| 候选护栏 | 保留 | 理由 |
|---|---|---|
| 内容扫描（密钥/敏感串） | 不内置，只在 `wf doctor` 给一次建议 | 模块不接管 git hook；接管 `core.hooksPath` 会让 husky / lefthook 失效，单人自用场景下不是必需项 |
| 非交互推送拦截 | 不保留 | 设计稿写明推送由人执行；该护栏对 AI 无效，只剩提醒价值，不足以引入整套 hook 机制 |
| 分支纪律 / 推送纪律 | 不保留 | 设计稿 §1.1：单一工作线，推送由人执行 |
| **零受管漂移防护** | **保留（唯一）** | 原生能力 + 一条解析断言：`wf doctor` 跑 `trellis update --dry-run`，断言 “Modified by you” 只含预期项（`config.yaml`，ZCode 项目再加 `config.json`），并断言当前解析结果确实是 `wf` 变体 |
| 探针写盘纪律 | 保留 | 凡写盘的检查在临时目录/临时 git 仓库中执行，用完即删（失败也删）；`wf doctor` **默认只读** |
| 远端加固 | 只给建议命令 | 改远端是外部副作用；设计稿承认无法强制 |

**顺序可恢复（不是“顺序无关”）**：

> 任何一次 `trellis update` 之后，必须立即跑 `wf doctor`；若 `default_workflow` 那一行丢失、或解析结果不是 `wf` 变体，按 `wf upgrade --plan` 的预览回放那一行。

两种顺序都支持，但都要跟一次验证：`trellis update → wf doctor`；或 `wf upgrade → trellis update → wf doctor`。验收场景见 §8.1 的 W9 / W15。

### 6.5 `AGENTS.md` 块外 NL 路由

**它是什么**：`trellis init` 在 `AGENTS.md` 里写受管块 `<!-- TRELLIS:START -->…<!-- TRELLIS:END -->`；块外内容由 `trellis update` 保留（§1.3 实测）。模块在块外追加一段带自有标记 `<!-- wf-nl-routing-start -->…<!-- wf-nl-routing-end -->` 的“意图 → 入口”路由表。

**三个作用**（都不依赖 hook 与 skill 触发）：

1. **补齐无 hook 平台的通道**：DSH 无项目级 hook；Codex 的 hook 需用户级开关 + 审批。两者在 hook 未生效时，唯一稳定的会话期通道就是 `AGENTS.md`；
2. **承载硬约束**：“不得直接调用 `task.py start/archive` 改图内任务状态（单写者）”“不得写 T0 文件”“不得手改账本”“依赖状态以 `wf state` 为准”；
3. **可发现性（含升级）**：给出人类可读的意图→入口映射，并写明升级 skill 需手工复制到 `.agents/skills/`（它不随安装器分发）。

**覆盖范围**：

| 平台 | 是否读 `AGENTS.md` | 依据 |
|---|---|---|
| DSH | ✅ 每会话读 | `实测`（本会话系统提示注入项目 `AGENTS.md`） |
| Codex | ✅ | `读码`（Trellis 平台表 + `project_doc_fallback_filenames`） |
| ZCode | ✅ | `实测`（2026-10-28 的 ZCode 会话系统提示中注入了本项目 `AGENTS.md`） |
| Pi | ✅ | `推断`（与 Codex 同族约定） |
| Claude Code | ⚠️ **条件性**：仓库无 `CLAUDE.md` 时把 `AGENTS.md` 当作项目指令（需较新版本，且 `/config` 的 Project instructions 可切为“只读 CLAUDE.md”） | `文档` |

**因此该段不是任何门禁的唯一载体**：它只承担“路由提示 + 硬约束声明”，权威判定一律在 `wf` CLI。

**安装期必查**：目标项目根存在 `CLAUDE.md` 时，安装器与 `wf doctor` 必须明确提示“NL 路由对 Claude Code 可能不生效；如需生效请在 `CLAUDE.md` 中 import `AGENTS.md`”。

### 6.6 写入纪律汇总

- 覆盖式更新；历史以版本库为准；
- 机制写入的提交范围按 §3.4；不设追加式对账记录；
- 不保留操作日志；收尾失败按 §3.8 对账；
- 禁止手改账本；替换 / 放弃实施后禁止回退到替换前；
- 机制只写 `meta.wf.deps` 与账本；不写任何 T0 文件（ZCode 的 T1c 例外见 §5）。

---

## 7. 升级与拆卸

### 7.1 三轴版本

| 轴 | 来源 | 用途 |
|---|---|---|
| `T_target` | 目标项目 `.trellis/.version` | 目标所处 Trellis 代 |
| `M_inst` | 变体文件头部注释行：`.trellis/workflows/wf.md` 的 `<!-- wf:module_version=… -->` | 已装模块版本（不再需要独立的 lock 文件） |
| `M_src` + `[T_min, T_max]` | 模块源 `module.yaml` | 模块源版本与验证区间 |

**`T_min` 的确定方式**：变体解析链（`workflow_selection.py`）首次出现的版本。`实测`（2026-10-28）：本仓库 `0.7.0-beta.4` 存在该模块；`0.6.x` 没有（旧实现方案用 tag 验证过）。因此：

- `T_min = 0.7.0-beta.0`（保守取首次落地版本）；
- `T_target < T_min` → `wf install` 直接拒绝，要求先升 Trellis；
- **`T_max` 当前声明为 `0.7.0-beta.4`**（唯一实测过的版本，封闭区间）；每验证一个新版本才上移。目标项目版本高于 `T_max` 时 `wf install` 不拒绝，但 `wf doctor` 必须提示“超出已验证区间”，并把变体哨兵（W1/W2）与账本探针（W13）作为回归必跑项；
- **治理提示**：该机制上游有 revert 先例（引入 → revert → `0.7.0-beta.0` 重新落地），`capability-digest.md` 必须登记这段历史，且每次升级都把变体哨兵（W1/W2）当作“变体链还在不在”的哨兵。

**入口 × 状态矩阵**（`wf upgrade --check` 的输出即此表）：

| 状态 | `wf install` | `upgrade --check` | `upgrade --apply` |
|---|---|---|---|
| 未安装 | ✅ | ✅（只读） | ❌ 应先 `install` |
| 有效已安装 | ❌ 拒绝重复安装 | ✅ | ✅ |
| 安装/升级不完整（attempt `status ∈ {in_progress, failed}`） | ❌ | ✅（只读，输出差异） | ❌ 先 `--rollback` 或人工清理，不提供绕过开关 |
| 存在活动任务（`status ∉ {planning, completed}` 且未处于暂停） | —（新装无任务） | ✅（只读，列出活动任务） | ❌ 先收口，或显式暂停后重跑 |

### 7.2 契约探针与能力发现

**原则**：能用原生命令判的，不再自造断言。探针清单见 §8.1（W 系列，按本方案重编）。

**`capability-digest.md`**（模块源内人工维护）：记录“各 Trellis 版本新增/变动的公开契约”，`wf upgrade --digest` 按需截取，**只报告不自动采用**。首条必须是变体机制的演化史（§7.1）。

**不设兼容垫片表**：模块只依赖**一个**公开契约（变体链）与**两个**原生命令族（`task.py`、`get_context.py`），差异用“是否满足 `[T_min, T_max]`”表达即可。

### 7.3 升级 SOP

**A. 模块侧发布（本仓库）**：`wf render` 重渲染变体与 skill → 在**三个 Trellis 基线**跑 `tests/` + 探针（`T_min`、当前实测版本、下一版本分支）→ `module.yaml` bump（`module_version` + `verified_trellis_range` + 资产哈希）→ 产出自包含介质。

**B. 目标项目侧升级（人执行 / skill 承载）**：

| 步 | 动作 | 判据 |
|---|---|---|
| S0 | 记录三轴与探针基线 | `wf version`、`wf doctor` |
| S1 | `wf upgrade --check`（只读，默认不落盘） | 输出入口 × 状态矩阵的当前行 |
| S2 | `wf upgrade --plan`（只读）列出将新增/替换/删除的每个文件 + `AGENTS.md` 追加段 + `config.yaml` 那一行 + ZCode 命令串 | 清单即“实际写入清单”，直接驱动快照与回滚 |
| S3 | **人在终端**跑 `wf upgrade --apply`（令牌 `UPGRADE <M_inst> -> <M_src>`） | AI 不得代跑、不得设 env 绕过 |
| S4 | `wf upgrade --verify`（必需探针 + `wf self-test` + `wf doctor`） | 全绿 |
| S5 | `wf upgrade --digest`（对比 `T_target` 与验证区间，列出上游新增公开契约） | 只报告，不自动采用 |
| S6 | 写升级报告与安装记录 | `install-record.json` 更新 |

**升级 skill 的位置**：源在本仓库 `skills/wf-module-upgrade/`，**不随安装器分发**；需要时由人复制到 `.agents/skills/`（Claude Code 另复制到 `.claude/skills/`）。第一步自检：目标项目是否已装模块（`install-record.json` 与 `.trellis/scripts/wf/` 是否存在）；未装则输出“先运行模块源安装器”并停止。

**禁止事项**：不得写 T0 文件；不得用 `--force` 掩盖必需探针失败；不得在非 TTY 环境重试同一效果；不得声称“升级已生效”而不跑 S4。

### 7.4 资产输入与回滚

| 项 | 规定 |
|---|---|
| 资产输入 | `wf upgrade --from <模块源目录>`；`wf install` 把该路径记进 `install-record.json`，升级时作为默认值并要求人在预览里确认 |
| 版本判定 | 源 `module.yaml` 提供 `module_version` + `verified_trellis_range` + 资产哈希清单；与变体头部 `M_inst` + 当前工作区资产哈希比对，得出“新增/替换/删除”三类清单 |
| 完整性校验 | 应用前校验源资产哈希（源自身一致）；应用后写新的 `M_inst` 与哈希；不符即拒绝应用（fail-closed） |
| 回滚 | 应用前对**清单里的每个路径**做快照（`.trellis/.runtime/wf/upgrade-backup-<ts>/`，gitignore）；任一步失败自动回滚并保留现场；成功后保留最近一次备份，由 `wf doctor` 提示可清理 |
| 提交时机 | `--apply` **不自动提交**（提交是检查点）。`upgrade-attempt.json` 只表示“进行中/失败”，验证成功即清除 |
| 失败语义 | 先写 `status: in_progress` → 失败置 `failed` 并保留（下次 `--check` 判为“不完整”，拒绝再次 `--apply`）→ 验证成功即清除。**不允许半升级后静默可用** |

### 7.5 拆卸契约（对齐设计稿 §9.4 的两种卸载模式）

设计稿 §9.4 定义两种模式与五条硬约束；旧实现方案给出逐对象处置。合并为下表（**本表是实现层唯一源**）：

**还原依据的获取顺序**（`.trellis/config.yaml` 的那一行与 `.zcode/config.json` 共用；越靠前越可信）：

| 级 | 依据 | 适用场景 | 校验方式 |
|---|---|---|---|
| 1 | `.trellis/.runtime/wf/pre-install/` 的本机快照 | 本机安装过且未清理 `.runtime` | 当前文件 == 快照 + 我们改的那一处 |
| 2 | **git 历史**：`git log --reverse -S "<我们写入的那一行 / 那段命令串>" -- <path>` 的首个提交，取其 **parent** 版本的该文件 | **新克隆**、`.runtime` 被清理、换机 | 同上 |
| 3 | 两级都不可得（该改动在仓库初始提交里、或历史被改写） | 少见 | **fail-closed**：不修改文件，输出预览（当前 diff、目标行位置、建议的人工操作），等人裁决 |

**新克隆是常态，不是异常**：`.runtime/` 是 gitignored 的本机态，任何一次全新克隆都没有第 1 级依据；此时必须落到第 2 级（git 历史），**不得直接判失败**，也不得跳过还原。只有当历史里也定位不到引入提交时才走第 3 级。

| 对象 | 仅模块卸载（默认） | 完全卸载 | 说明 |
|---|---|---|---|
| `.agents/skills/{wf,wf-repair}/`、`.claude/skills/{同名}/` | 删除 | 删除 | 只删我们投放的目录；`trellis-*` 一律不动 |
| `.trellis/scripts/wf/**`、`.trellis/workflows/wf.md` | 删除 | 删除 | 模块自有资产 |
| `.trellis/dependencies/ledger.json` | **保留** | 删除 | 账本是项目数据；仅模块卸载后重装可继续用 |
| `.trellis/.runtime/wf/install-record.json`、`upgrade-backup-*`、`upgrade-attempt.json` | 删除 | 删除 | 本机态，无保留价值 |
| `.trellis/.developer` 的 `workflow=wf` 行 | 删除该行（文件保留） | 同左 | 删除后解析回落到 `config.yaml` 的团队默认 |
| `.trellis/config.yaml` 的 `default_workflow: wf` 行 | 按上文**还原依据的三级顺序**取得基线：一致则还原为基线，不一致则走第 3 级预览 | 同左 | 不依赖读取 Trellis 模板（模板路径随版本变化，且不保证可访问）；本机快照不进库，靠 git 历史兜底 |
| `.zcode/config.json` 的四条命令 | 按上文**还原依据的三级顺序**取得基线后还原为原形 | 还原 | T1c 的唯一还原点；`.zcode/hooks/*.py` 一律不动 |
| `AGENTS.md` 的 `<!-- wf-nl-routing-start/end -->` 段 | 删除该段（块外其余保留） | 删除该段 | |
| `task.json` 的 `meta.wf.deps` | **保留** | **保留** | 原生字段的一部分；删除等于篡改历史。完全卸载也不删任务记录 |
| 图内任务的账本状态 | 保留（账本保留） | 随账本删除 | |
| `task.json` 的 `workflow=wf` pin | 清除（原生 `task.py workflow --clear`） | 清除 | 上游原生命令 |
| `core.hooksPath` | **不触碰** | 不触碰 | 模块不接管 git hook |
| `.trellis/tasks/**`、`.trellis/workspace/**`、`.trellis/spec/**` | **保留** | **保留** | 基底与项目数据，不属模块 |

**完全卸载的边界（需要人裁决）**：设计稿 §9.4 的表述是“删除模块 + 项目数据”，可被读成“连任务与规格一起删”。本方案的实现取**窄解释**：只删模块引入的数据（账本与安装记录），保留基底的任务、日志、规格与基线。理由：设计稿同节又写“两种模式都必须满足：卸载后原生 Trellis 可独立完成建任务、开工、归档”，删掉 `tasks/` 会让基底从零开始，与“基底可独立使用”相悖。冲突登记见 §9-C5；该条已于 2026-10-28 裁决为**窄解释**（§9.5）。

**卸载健壮性**（设计稿 §9.4）：卸载入口不得依赖机制运行时、账本或机制入口脚本——实现为**独立脚本** `uninstall.py`（不 import `wf` 包的账本模块），且步骤可重复执行（幂等），每步完成后基底仍可用。

### 7.6 往返验收

两条必须全过：

1. **基本往返**：`install` → 建一个任务 → 走完开工/收尾 → `uninstall --module` → `trellis update --dry-run` 相对安装前基线**无新增漂移** → 该任务仍能被原生 `task.py archive` 正常归档；
2. **跨版本往返**：`install` → `trellis update`（模拟上游改模板）→ `uninstall` → **无新增漂移**；若 `config.yaml` 已被上游改写，按 §7.5 的还原依据比对规则**停止 + 预览**，不强行还原。
3. **新克隆往返**：克隆一份已安装的仓库（`.trellis/.runtime/` 不存在）→ `uninstall --module` → 两个受管修正都经第 2 级依据（git 历史）还原 → `trellis update --dry-run` 相对安装前基线无新增漂移。

---

## 8. 验收与实施路线

### 8.1 探针清单

**语义**：**必需探针失败 = fail-closed**；**增强探针在支持的平台上必须通过，不支持的平台记 N/A**。编号按本方案重编（W 系列），删去旧实现方案中依赖证据层与 `.wf/contract.yaml` 的 P6/P10/P12/P13/P17/P18，新增依赖机制与 ZCode 相关项。

| # | 类别 | 断言 | 判据来源 |
|---|---|---|---|
| **W1** | 必需 | `get_context.py --mode phase` 的输出含变体哨兵串 | 原生命令 |
| **W2** | 必需 | `get_context.py --mode phase --step <X.Y>` 返回变体正文 | 原生命令 |
| **W3** | 必需 | 任务状态只写三值时，`task.py list/current --json` 与 `get_context.py` 不报错、不覆写 | 原生命令 |
| **W4** | 必需 | `set-meta wf.deps` 写入后能被读回；`archive` 后仍在归档的 `task.json` 里 | 原生命令 |
| **W5** | 必需 | `task.json`、`.trellis/workspace/**`、`ledger.json` 未被 `.gitignore` / 全局 excludes 命中 | `git check-ignore` |
| **W6** | 必需 | `wf self-test` 全绿：CLI 可执行、变体可渲染、账本可解析、`--json` 输出可被重新读入 | 自检 |
| **W7** | 增强 | 该平台的 `inject-workflow-state` 通道能为三值状态取回对应块 | 平台能力（DSH 记 N/A） |
| **W8** | 增强 | SessionStart 通道注入变体索引与 `Status:` 回显 | 同上 |
| **W9** | 必需 | 按当期实际投放的 skill 集 × 实际存在的 skill 根，加 `AGENTS.md` 块外段与 `.developer` 行后，`trellis update --dry-run` 的 “Modified by you” **只含 `config.yaml`**（ZCode 项目另含 `config.json`） | 原生命令 |
| **W10** | 必需 | `wf close` 在源状态非法（账本非“无记录”或前置不全正常）时**拒绝**归档；合法时**在 `branch == base_branch` 的常态下仍能归档**（机制传 `--skip-branch-validation`，归档后 `status=completed`、账本为“正常”）；`pr_url` 非空时**拒绝**该 skip 路径 | 自测 + 原生 |
| **W11** | 治理 | 每个 skill 根存在，且 skill 内引用的子命令都存在于 CLI `--help` | 自测 |
| **W12** | 必需 | **就绪门**：前置未全正常时 `wf start` 拒绝；全正常后放行 | 自测 |
| **W13** | 必需 | **账本转移门**：表 4-2 七行之外的任何转移被拒绝（含“异常 → 正常”、“已归档直接返工”） | 自测 |
| **W14** | 必需 | **可见性顺序**：模拟“归档成功、账本提交失败”，下游必须仍视为未满足（`wf state` 报“归档待对账”） | 自测 + 模拟 |
| **W15** | 必需 | **新克隆无快照**：全新克隆目录里 `trellis update --dry-run` 的 “Modified by you” 只含 `config.yaml` | 原生命令 |
| **W16** | 必需 | **卸载后基底可独立使用**：`uninstall --module` 后能 `task.py create/start/archive` 成功，且 `trellis update --dry-run` 无新增漂移 | 自测 |
| **W17** | 必需 | **ZCode 加固**：§5.6 的 Z1–Z5 全过（四条加固形态、漂移不阻断、正常行为不变、卸载还原、债务可见） | 自测 + 会话实测 |
| **W18** | 必需 | **图内 / 图外分流**：按 `meta.wf.deps.in_graph` 判定（不用字段存在性）；`in_graph=false` 的任务走原生流程不被拦；`in_graph=true` 的任务被机制门禁覆盖；`wf edge add` 给无标记任务加边后该任务被补写为图内 | 自测 |
| **W19** | 必需 | **返工登记窗口**：在“准备后、创建前”“创建调用中断”“创建成功、发布未提交”三个窗口各模拟一次崩溃，另加**跨日恢复**（把标记日期前提推到次日）一次，`wf check` 都能识别并按 §3.12 的窗口表向前完成，不重复建 R、不因日期前缀失配 | 自测 + 夹具 |
| **W20** | 必需 | **替换不回退**：替换实施后 `wf repair` 不提供把“异常”改回“正常”的路径；只能补建 / 重连 / 改判放弃 | 自测 |
| **W21** | 必需 | **选择性提交准入**：目标文件已有无关未提交变更时，机制写入被拒绝并给出指引；洁净时写入并只提交该文件 | 自测 |
| **W22** | 必需 | **任务图门**：P 的 `design.md` 无图块、图块校验失败（key 重复 / 无 tail / 成环 / 引用块外 key）时 `wf close`（P）**拒绝**；图块齐全时放行，且 `wf task new --from-graph` 能按拓扑序建出全部任务 | 自测 |
| **W23** | 必需 | **新克隆的卸载还原**：删除 `.trellis/.runtime/wf/`（模拟全新克隆）后执行 `uninstall --module`，两个受管修正（`config.yaml` 那一行、`.zcode/config.json` 四条命令）都能经 git 历史依据还原；历史定位不到时走第 3 级——输出预览且**不修改文件** | 自测 + 夹具 |

**探针执行纪律**：① 凡写盘的探针一律在**隔离夹具**（临时目录 + 临时 git 仓库）中执行，绝不写目标项目，用完即删（失败也删）；② `wf doctor` 只读；③ `wf upgrade --check` 默认不写盘，落盘须显式 `--report <path>`。

### 8.2 实施阶段

每阶段必须有可执行的完成判据，且**能被一个真实任务验证**。

| 阶段 | 内容 | 完成判据 |
|---|---|---|
| **P0 骨架与零补丁** | ① **旧模块退役已完成**（2026-10-28：内容移出仓库、不入库、文档零引用），本阶段只在该路径**新建模块源骨架**；② 模块源骨架（`module.yaml` / `workflow.yaml` / `render.py` / `skill_roots.py` / `wf_install.py`）；③ 变体渲染（含 `[workflow-state:*]` 三值块与版本注释行）；④ `AGENTS.md` 块外 NL 路由；⑤ `wf route` / `state` / `dag` / `check` / `doctor` / `embed-state`（只读，全 `--json`；**依赖账本读取**：解析 `ledger.json`，键缺失按“无记录”处理）；⑥ `wf task new` / `start`（含 `--base-branch` 与 `set-branch`）；⑦ `wf install` / `uninstall`（两模式 + 安装前快照还原）；⑧ **ZCode 加固**（`zcode_guard.py` + §5.6 自检）；⑨ 投放 `wf` skill（`wf-repair` 留到 P2）；⑩ 探针 **W1–W6、W9–W12、W14–W17、W21–W23**；⑪ **五平台 G0**；⑫ 往返验收（§7.6 两条，**收尾走最小 `wf close`**） | 该阶段首次可执行的探针全绿；五平台各自完成“skill 可加载 / 变体解析 / CLI 冒烟”；`install → task new → start → close → uninstall → trellis update --dry-run 无新增漂移 → 原生 archive 正常` 往返通过；ZCode Z1–Z5 通过 |
| **P1 账本与正常流转** | **账本写入**（读取已随 P0 落地）；`wf dag` 派生视图细化；任务图解析与 `wf task new --from-graph`；`wf edge add/rm`（含 **W18**）；`wf baseline --light`；`wf repair` 的类型 1 / 3；投放 `wf-repair` skill | W13、W18 全绿；一个真实项目从 P 建图到首个任务收尾；`wf dag --check` 无偏差 |
| **P2 异常处分** | `wf rework`（§3.12 的五步序列与窗口表，含跨日恢复）；`wf replace`；`wf abandon`（两变体）；`wf repair` 的类型 2 / 4 / 5 | W19、W20 全绿；§3.12 窗口表的每一行都能被夹具复现并向前完成 |
| **P3 真实项目走查 + 跨 CLI 接手** | 在一个真实项目上从 P 走到收尾；同一任务由 CLI-A 实施 → CLI-B 接手 | 全链走通；两端 `status` + `meta.wf.deps` + 账本条目 + `get_context.py` 输出一致 |
| **P4 升级链路** | `wf upgrade --check/--plan/--apply/--verify/--rollback/--digest`；升级 skill；`capability-digest.md` | 入口 × 状态矩阵四行都可达；回滚后探针全绿；升级后在三个基线版本上通过 |
| **P5 可选硬化** | 第三方 agent 的 L1/L2 支持说明、`wf doctor` 的建议命令、模块打包成独立介质 | 需要真实需求驱动；不得提前实现 |

**每阶段必跑**：`wf doctor`（T0 路径不得出现在 `git diff` 中）+ 当期必需探针 + 升级演练（在上一版本 Trellis 基线上）。

### 8.3 复杂度闸门

- 每阶段开工前回答“**这一阶段能否被一个真实任务验证**”；答不上来就把该阶段内容推迟，而不是把设计稿的节点删掉。
- P0 只交付最小可用集，不得提前实现 P1–P5 的机制。
- 凡遇“这里似乎需要一个子机制”时，先按设计稿 §0.4 的判据回答“**原生是否已经能做**”；能做就不实现。
- **不新增的机制清单（实施时不要再加回来）**：分支与工作单元、合入链路、交集判定、验证证据链、准洁净分级、微变更白名单、git hook 接管、第二套记录存储。
- **“不引入”不等于“不执行”**：设计稿的节点（项目层、任务层、收尾层、返工/替换/放弃）照常执行，只是由人或由基底承载。

---

## 9. 冲突登记与裁决

> 本节**不是规范**：它登记三方（设计稿 / 旧实现方案契约 / 当前仓库事实）不一致的条目。全部条目已于 2026-10-28 裁决（§9.5），正文按裁决书写；本节保留选项与理由，供日后复核。正文中凡引用本节处均写 `§9-Cn`。
>
> 分类：**A 设计层互斥**（必须人裁决）；**B 事实不符**（按事实改写，仅登记）；**C 实现不可行 / 需偏离**（给近似实现 + 偏离登记）。

### 9.1 A 类：设计层互斥

| ID | 冲突点 | 三方立场 | 影响 | 建议处置 | 选项与裁决（2026-10-28） |
|---|---|---|---|---|---|
| **C1** | 是否保留验证证据（`impl_sha` / `verification` / 一票否决） | 设计稿 §1.3/§4.3：完成 = 人判 + 归档，**不做证据链**；旧实现方案：**必须保留**一条记录 + 一句断言，否则“答不了凭什么算完成” | 决定 `wf declare` / `wf verify` 是否存在、`meta.wf` 的 schema、skill 数量 | **采纳设计稿**：删除证据层（正文 §6.2） | **已采纳①**（2026-10-28）。 ① 按建议（无证据层）；② 保留“实施 sha”只作展示、不参与判定（低成本折中，但会造出“有记录却无判定”的歧义） |
| **C2** | 任务状态是否扩展 `wf-*` 值 | 设计稿 §4.2：任务状态**只有三个值**，依赖状态不许写进任务状态；旧实现方案：A2 混合投影，用 `wf-impl` / `wf-verify` / `wf-verified` 等驱动面包屑 | 决定面包屑能否显示“待验证/等待返工”，以及是否要依赖 hook 查表 | **采纳设计稿**：只用三值；账本维度由 `wf state` 输出（正文 §3.1 的代价与补偿） | **已采纳①**（2026-10-28）。 ① 按建议；② 允许一个 **只读派生块**（hook 侧不写状态，只显示账本），但需改 Trellis hook 之外的通道，属新增机制 |
| **C3** | 项目级契约是否有独立文件 | 设计稿 §5.2：基线 = 项目文档 + 规格，由 P 承载，“齐”的判据四条；旧实现方案（D23）：**必须**落 `.wf/contract.yaml`，未定标不许开任务 | 决定是否新增模块自有文件与“契约确认”步骤 | **并入 P 产物**（正文 §3.9），不新增文件；“未定标不许开任务”由“P 已归档”承载 | **已采纳①**（2026-10-28）。 ① 按建议；② 恢复 `contract.yaml`（会引入第二套项目级状态，与不变量 2 张力） |
| **C5** | “完全卸载”删不删项目数据 | 设计稿 §9.4：完全卸载 = 模块 + **项目数据**，保留“仅基底与项目代码”；旧实现方案：逐对象处置，明确保留 `meta.wf.*` | 决定 `--full` 是否删 `.trellis/tasks/**`、`.trellis/workspace/**`、`.trellis/spec/**` | **窄解释**：只删模块引入的数据（账本、DAG、安装记录），保留基底数据（正文 §7.5 末段） | **已采纳①**（2026-10-28）。 ① 按建议；② 宽解释（连任务/日志/规格一起删）——需先确认“基底可独立使用”如何满足；③ 拆成三档（模块 / 模块+模块数据 / 全清） |
| **C6** | 图内任务是否必须被“阻断”在原生入口之外 | 设计稿 不变量 5（强度=约定）：图内开工与收尾**只走机制入口**；旧实现方案：没有任何平台能让 CLI 判断调用者是谁，门禁只能靠状态 | 决定是否投入 hook 级拦截（各平台能力不等） | **约定层**：机制入口是 CLI；原生直调不被阻断，但 `wf doctor` 报告“未走机制入口的归档”（正文 §3.6） | **已采纳①**（2026-10-28）。 ① 按建议；② 在支持的平台加 PreToolUse 拦截（Claude/Codex/ZCode 可，Pi/DSH 不可 → 平台不对等）；③ 完全放弃检测 |
| **C7** | 是否需要“降级兜底” | 设计稿 §9.4：机制不可用时**只卸载，不降级**；旧实现方案：`status == in_progress` 时提示 `wf sync` 修复（降级兜底） | 决定是否保留 `wf sync` 与“降级”概念 | **不设降级**：`wf sync` 改名 `wf repair` 的类型 3（正常但未归档的反向场景），不作为日常修复通道 | **已采纳①**（2026-10-28）。 ① 按建议；② 保留 `wf sync` 作为便捷修复（会与“唯一修复入口”冲突） |

### 9.2 B 类：与当前事实不符（按事实改写）

| ID | 冲突点 | 事实 | 处置 |
|---|---|---|---|
| **C9** | 支持平台是四个还是五个 | 旧实现方案：claude / codex / pi / dsh；本轮要求增加 **zcode** | 按五平台写（正文 §4）。`AGENTS.md` 覆盖已获 `实测`（2026-10-28 ZCode 会话系统提示注入本项目 `AGENTS.md`）；“变体哨兵”仍属 `读码`（共用 `get_context.py`），**必须在 P0 的 G0 中用真实会话补齐**，补齐前不得写“五平台已支持” |
| **C10** | 版本基线（**证据勘误，非设计冲突**） | 草案初稿把本仓库版本误记为 `0.7.0-beta.42`，并据此推出“与上游不同代”的错误前提；`实测` 三者同为 `0.7.0-beta.4`（`.trellis/.version`、`trellis --version`、上游检出 `be9e19b2`） | 全部版本声明按 `0.7.0-beta.4` 更正；`T_max` 下修为实测值 `0.7.0-beta.4`；引用纪律的动机改为“行号随小版本位移且不锁定参考检出”，不再依赖“不同代”这一错误前提；保留本条以记录错误来源并防止复发 |
| **C11** | skill 粒度与职责 | 旧实现方案：`wf` / `wf-verify`（2 个，按证据层切）；本设计无证据层 | 改为 `wf` / `wf-repair`（按“日常流转 / 异常处分”切，正文 §2.2、§4.3）；数量仍为 2 |
| **C13** | ZCode 加固模板的解释器 | 模板应渲染 `{{PYTHON_CMD}}`（旧实现方案的理由：Windows 无 `python3`）；本仓库实例写死 `python3` | 模块模板参数化；本仓库实例登记为本行已知偏差，不改本仓库文件（改它属另一任务） |

### 9.3 C 类：实现不可行 / 需偏离

| ID | 冲突点 | 冲突内容 | 影响 | 建议处置 | 选项与裁决（2026-10-28） |
|---|---|---|---|---|---|
| **C4** | 提交粒度 | 设计稿 §3：**提交按必要变更划界，不按整份文件划界**，不得捎带同文件其他变更；git 无“只提交某 JSON 键”的稳定原语 | 机制写入与无关变更共存时无法精确分离 | **写前洁净 + 机制立即提交**（正文 §3.4）：机制写入后立刻 `git add <单路径>` 并单独提交，不依赖 `session_auto_commit`。偏离登记：无法做到 hunk 级分离，改为“写入端准入 + 短窗口” | **已采纳①**（2026-10-28）。 ① 按建议；② 设 `session_auto_commit: false` 并让基底也交给机制提交（改变基底默认行为，影响面更大）；③ 把机制字段拆到独立文件（会新增记录类型，违反不变量 3） |
| **C8** | ZCode 受管文件例外 | 旧实现方案：`.zcode/**` 属 T0，永不写入；本轮要求 + 平台事实：不改命令串则 hook 在 cwd 漂移时失效并可能死锁 | 需要一处受管文件修正 | **新增 T1c 层**（正文 §1.4、§5）；登记漂移债务与撤销条件 | **已采纳①**（2026-10-28）。 ① 按建议（接受 1 个文件的债务）；② 不改 config.json，改为在 `AGENTS.md` 里要求“cwd 必须停在仓库根”（纯纪律，死锁仍可能发生）；③ 改 hook 脚本本身（制造第二处漂移，更差） |
| **C12** | 账本载体与进库 | 设计稿 §3 要求账本持久化进版本库；旧实现方案的整体方向是“记录轨原生化、不造第二套存储” | 单文件 vs 每任务一文件；进库 vs 本机 | **单文件 `ledger.json` + 进库**（正文 §2.3、§3.2）；理由：设计稿把账本定为唯一新增记录类型，且状态判定必须跨机可复现 | **已采纳①**（2026-10-28）。 ① 按建议；② 每任务一文件（`dependencies/<id>.json`，减少单文件冲突，但单人单线无并发收益，反而增加文件数）；③ 账本不进库（重克隆后判定不可复现） |
| **C14** | 准洁净验证 | 旧实现方案用 `git worktree` 做准洁净验证；本设计无验证环节 | 随 C1 连带失效 | **剔除**；不提供 `--level quasi-clean` | **已随 C1 裁决：剔除**（2026-10-28） |
| **C15** | 卸载入口的独立性 | 设计稿 §1.2 约束 4：卸载入口**不得依赖**机制运行时、账本或机制入口脚本；旧实现方案的实现是 `wf uninstall`（在 CLI 内） | CLI 自身损坏时无法卸载 | **独立脚本** `uninstall.py`，不 import 账本模块（正文 §2.4、§7.5） | **已采纳①**（2026-10-28）。 ① 按建议；② 允许 `wf uninstall` 但要求它有“最小自检后降级为纯文件删除”的分支（复杂度更高） |
| **C16** | 归档的分支元数据门与单工作线不兼容 | 上游 `task.py archive` 在 `branch == base_branch` 时**硬拒绝**归档（`_validate_branch_metadata` 返回 False），而单工作线下这两个字段必然相等；本设计不切分支、不建 PR，因此该门的前提（PR 档案）不成立 | 机制入口的收尾若不处理则该门必然命中，`wf close` 在主路径上跑不通 | **`wf close` 固定传 `--skip-branch-validation`**，调用前断言 `pr_url is None`；`wf doctor` 检出“有 PR 痕迹却被机制归档”的组合（正文 §3.5） | **已采纳①**（2026-10-28）。 ① 按建议（把该门定位为 PR 档案门）；② 让 `create` 不传 `--base-branch` 并把两个字段清空——不可行：`set-branch`/`set-base-branch` 拒绝空值；③ 向上游提出“单工作线豁免”——超出本仓库权限（上游只读） |

### 9.4 已判定不采纳的旧实现方案内容（汇总）

| 旧实现方案内容 | 不采纳的理由 | 本方案替代 |
|---|---|---|
| §4.3 的 `wf-*` 状态投影与 `[workflow-state:<自定义值>]` 块 | 违反“任务状态只有三个值” | 三值 + 账本二元组（§3.1） |
| §4.5 的证据层、一票否决、信任根 | 设计稿不做证据链 | 人判 + 归档（§6.2） |
| §4.2.1 的 `.wf/contract.yaml` | 造第二套项目级状态 | P 任务产物（§3.9） |
| §4.3.2.1 的准洁净分级 | 无验证环节 | 剔除 |
| §4.8 的 `wf sync` 降级兜底 | 禁止降级 | `wf repair` 类型 3（§9-C7） |
| §0.1 / §0.3 / §6 的 D1–D23 决策登记 | 版本绑定 | 只保留结论，不保留编号 |
| 旧实现方案的旧模块解剖与审查记录 | 属历史过程，不属契约 | 不进入正文 |

### 9.5 裁决记录

| 日期 | 条目 | 结论 |
|---|---|---|
| 2026-10-28 | C1、C2、C3、C6、C7、C16 | 采纳建议项 ①：删证据层（完成 = 人判 + 归档）／任务状态只三值／不建独立契约文件／不阻断原生入口（只报告）／不设降级／归档门固定 `--skip-branch-validation` |
| 2026-10-28 | C4、C5、C8、C12、C15 | 采纳建议项 ①：写前洁净 + 文件级即时提交／完全卸载取窄解释（只删模块数据）／ZCode 受管例外 T1c（接受 1 个文件的漂移债务）／账本单文件进库／独立 `uninstall.py` |
| 2026-10-28 | C14 | 随 C1 裁决：剔除准洁净验证 |
| 2026-10-28 | C9、C10、C11、C13 | 事实类，已按实测与设计稿改写，无需裁决 |
| 2026-10-28 | G3（模块源位置） | **改判**：旧模块已退役并移出仓库（不入库、文档不引用）；模块源沿用 `docs/workflows/新项目开发工作流/` 新建 |
| 2026-10-28 | M1、M2、M3 | 采纳建议项 ①：账本**读取**与最小 `wf close` 并入 P0；W18 随 `wf edge` 归 P1，W10 / W12 / W14 归 P0；§8.2 两行与探针归属已同步改写 |
| 2026-10-28 | 四个维护 skill | **退役删除**（`workflow-audit` / `workflow-capability-audit` / `workflow-repair` / `workflow-scan` 及其契约 spec）；等价能力由 `wf doctor` / `wf upgrade` / `embed-state` / W 系列探针承载；删前已摘录通用误报守卫 |
| 2026-10-28 | `commands/shell/init-trellis-temp-project.sh` | **退役删除**：它只调用旧产品的 `commands/{detect-embed-state,install-workflow,upgrade-compat}.py`，且把仓库路径写死成已失效的绝对路径；README 双语与 `spec/commands` 同步改述 |

**裁决即生效**：正文各节已按上表书写，本节只作留痕。后续若要改变其中任一条，必须**同时**修改正文对应节与本节记录，不得只改一处——否则会出现“正文按 A 写、登记说 B”的静默漂移。

**仍未决的事项**（不阻塞本文档定稿，属文档治理与实施衔接）：见 §9.6。

### 9.6 治理与实施决策清单

| 项 | 内容 | 状态（2026-10-28） |
|---|---|---|
| G1 | 是否把本文件登记进仓库文档索引（`docs/README.md`；涉及根 `README.md` 时须双语同步） | **已裁决：不登记** |
| G2 | 旧实现方案的处置 | **已执行（2026-10-28）：已删除并从仓库移除**。本文件已去除对它的全部出处标注与来源映射表；正文自足，删除后无死链 |
| G3 | 模块源位置 | **已改判（2026-10-28）**：旧模块已退役并移出仓库（内容不入库、文档不引用）；模块源沿用 `docs/workflows/新项目开发工作流/` 新建（§2.1） |
| G4 | 关键约束是否沉淀进 `.trellis/spec/` | **已裁决：沉淀**，落 `.trellis/spec/docs/workflow-implementation-constraints.md`（本轮完成） |
| G5 | 变体 `.trellis/workflows/wf.md` 的正文内容（Phase Index 与设计稿 §4.1 四段的映射、三段入口提示词） | **已裁决（2026-10-28）：正文已产出**，暂存 `docs/workflows/wf-variant.md`（该位置由 §9.7 的 T2 迁入 `templates/wf.md.tmpl`）；哨兵串、三值状态块、版本注释行与三层映射见 §9.7 |
| G6 | 是否拆出 P0 实现任务（本文只交付方案，不含代码） | **已裁决（2026-10-28）：拆三段，资产先行**（T1 资产段 → T2 交接与骨架 → T3 最小闭环机制面），边界、依赖与验收见 §9.7 |

### 9.7 P0 实施拆分（G6 裁决，2026-10-28）

> 本节是 P0 实施边界的唯一源；§8.2 已按本节裁决同步改写（M1–M3 已生效，见 §9.5）。

**裁决**：P0 拆成三个任务，按 T1 → T2 → T3 串行；每段以"能被一个真实任务验证"划界。

| 任务 | 边界（对应 §8.2 的 P0 条目） | 依赖 | 验收要点 | 完成时仍不可用的能力 |
|---|---|---|---|---|
| **T1 资产段**（已完成） | ③ 的正文内容（变体）；不建模块源、不写 CLI | — | 临时夹具内 `get_context.py --mode phase` 含哨兵串（W1）、`--mode phase --step <X.Y>` 返回变体正文（W2）；三值块仅 `planning` / `in_progress` / `completed`；含 `<!-- wf:module_version=… -->`；无平台分支、无证据链环节 | 无渲染器、无安装器、无 CLI |
| **T2 骨架与迁入** | ①② 的"新建模块源骨架"部分；把 T1 的变体迁入 `templates/wf.md.tmpl` | T1 | `docs/workflows/新项目开发工作流/` 只有新模块源，且仓库内旧路径**零残留**；`render` 幂等，渲染物在夹具内 W1/W2 复跑通过 | 有变体源与渲染器、无机制：`wf` 的判定与生命周期命令全部不可用 |
| **T3 最小闭环机制面** | ⑤⑥⑦⑧⑨⑩⑪⑫，含 M1（账本读取）与 M2（最小 `wf close`） | T2 | 临时目标项目上一条闭环 `install → task new → start → close → uninstall`，`trellis update --dry-run` 无新增漂移，原生 `archive` 仍可用；当期必需探针全绿；五平台 G0 各自通过 | 任务内部"只读命令面先绿、写命令面后绿"，但首个可见里程碑即"能装能收尾" |

**为什么切在这里**：

- T1 的全部判据只依赖原生命令（`get_context.py`），不需要任何尚未存在的 CLI —— 纯资产放在最前，"做完了"可被机械证明。
- 旧模块退役已由独立任务完成（删除 + 文档零引用），T2 因此**不再包含交接步骤**，回滚范围更小、验收更硬（旧路径零残留）。
- T3 用"一条能跑通的闭环"而非 §8.2 的名词清单定义边界，并已吸收 M1–M3。

**已裁决的修正（2026-10-28，§9.5 留痕）**：

| # | 原问题 | 裁决 |
|---|---|---|
| **M1** | §8.2 把只读命令放进 P0，却把"账本读写"放进 P1；而 §3.7 的三段判定与 §3.8 的组合分类都要读账本 | 账本**读取**并入 P0（⑤）；账本**写入**仍属 P1 |
| **M2** | P0 ⑫ 要求 §7.6 往返验收"走完开工/收尾"，而 `wf close` 在 P1 | 最小 `wf close`（源状态校验 → `pr_url is None` 断言 → `archive --skip-branch-validation` → 账本写"正常"）并入 P0（⑫）；P1 移除该项 |
| **M3** | P0 ⑩ 收了 W18（断言含 `wf edge add`），而 `wf edge` 在 P1；P0 有 `wf start` 却把 W12 排在 P1 | W18 随 `wf edge` 归 P1；W10、W12、W14 归 P0 |

**传递到后续任务的决策**：

| ID | 内容 | 承接 |
|---|---|---|
| G5 落点 | 变体正文现暂存 `docs/workflows/wf-variant.md`；T2 迁入 `templates/wf.md.tmpl`，届时 `{{MODULE_VERSION}}` 由 render 替换为 `module.yaml` 的 `module_version` | T2 |
| 作者侧审计资产 | 四个维护 skill 已退役；将来若需要 wf 模块的作者侧审计，按新结构新写（P5 可选硬化），不修补旧契约 | P5 |

---

## 附录 A：命令面

**类别**：只读 / 副作用 / 人类专用 / 生命周期 / 生成自检。全部子命令支持 `--json`。

| 子命令 | 类别 | 依赖的原生能力 | 写入 |
|---|---|---|---|
| `wf route` | 只读 | `get_context.py --mode phase`、`task.py list/current --json`、账本 | — |
| `wf state` | 只读 | 同上（含任务状态 × 账本状态的二元组判定） | — |
| `wf dag` | 只读 | 前置集合 + 账本（`--json` / `--dot` / `--check`） | — |
| `wf check` | 只读 | 启动自检的类型分类（§3.8） | — |
| `wf doctor` | 只读 | `trellis update --dry-run`（漂移断言）、变体哨兵断言、`CLAUDE.md` 提示、ZCode 债务 | — |
| `wf embed-state` | 只读 | 三态判定（未嵌入 / 部分嵌入 / 有效嵌入），非零退出码表示异常 | — |
| `wf self-test` / `version` | 只读 | 模块自检（不含哈希信任根，见 §6.2） | — |
| `wf task new` | 副作用 | `task.py create --workflow wf --base-branch <当前分支> --slug <slug>`；参数化入口见 §3.5 | `task.json` + `meta.wf.deps` |
| `wf start` | 副作用 | `task.py start --allow-empty-context` → `task.py set-branch` | `task.json` |
| `wf close` | 副作用 | `task.py archive --skip-branch-validation`（前提：`pr_url` 为空）→ `add_session.py` | 原生归档 + 账本“正常” |
| `wf edge add\|rm` | 副作用 | — | 下游前置集合（暂存 → 后置校验 → 提交） |
| `wf rework` | 副作用 | 阶段内 `task.py create`（建 R） | 账本 + T 前置集合 + R 的 `meta` |
| `wf replace` | 副作用 | `task.py create` | 账本 + 下游前置集合 + 继任者 `meta` |
| `wf abandon` | 副作用 | 视变体 | 同上（删边变体不建任务） |
| `wf baseline --light` | 副作用 | `task.py create` | 新任务 `meta` + 下游前置集合（重连） |
| `wf repair` | 副作用（**人类专用**） | 按类型 | 账本 / 前置集合 / 说明字段 |
| `wf install` | 生命周期 | `trellis update --dry-run`、`git` | T1a / T1b / T1c / T2 |
| `wf uninstall`（+ 独立 `uninstall.py`） | 生命周期 | 无（独立入口） | 删除 / 还原；`--full` 需 TTY 令牌 |
| `wf upgrade --check/--plan/--verify/--digest` | 生命周期（只读） | `trellis update --dry-run` | `--report <path>` 时才写盘 |
| `wf upgrade --apply/--rollback` | 生命周期（**人类专用**） | 同上 | 快照 / 恢复 |
| `wf render` | 生成 | — | 变体与 skill（源侧） |
| `wf rename` | 副作用 | `task.py rename` | 账本 `task_dir` 与全部引用同步 |

**入口 × 状态矩阵**见 §7.1；**人类专用入口的令牌**：`UNINSTALL-FULL` / `REPAIR <type>` / `UPGRADE <M_inst> -> <M_src>`。

---

## 附录 B：路径清单

### B.1 模块源（`docs/workflows/新项目开发工作流/`，旧模块退役后由本模块新建）

| 路径 | 作用 |
|---|---|
| `docs/workflows/新项目开发工作流/module.yaml` | 版本 + 验证区间 + 实现的设计稿版本 + 资产哈希 + skill 根表 |
| `…/workflow.yaml` | 账本状态 → 变体块 / 下一步（render 与一致性检查共用） |
| `…/templates/wf.md.tmpl` | 变体源（含哨兵串与三值状态块） |
| `…/templates/nl-routing.md` | `AGENTS.md` 块外段源 |
| `…/templates/zcode-guard.json` | ZCode 加固命令串（占位符化，§5.2） |
| `…/templates/skills/{wf,wf-repair}/SKILL.md` | skill 正文源（占位符化） |
| `…/installer/wf_install.py` | 安装 / 卸载（调用 `uninstall.py`） |
| `…/installer/wf_upgrade.py` | 升级（check / plan / apply / verify / rollback / digest） |
| `…/installer/uninstall.py` | **独立卸载入口**（不 import 账本模块） |
| `…/installer/skill_roots.py` | 平台 → skill 根的映射数据（§4.1） |
| `…/installer/render.py` | 占位符渲染 + frontmatter 注入 |
| `…/installer/doctor.py` | 漂移断言 / 哨兵断言 / 债务报告 |
| `…/installer/zcode_guard.py` | ZCode 加固的原形识别、写入、还原、自检 |
| `…/capability-digest.md` | 各 Trellis 版本的公开契约变动（人工维护） |

### B.2 目标项目（安装后）

| 路径 | 归属层 | 进库 |
|---|---|---|
| `.trellis/scripts/wf/**` | T2 | 是 |
| `.trellis/workflows/wf.md` | T2 | 是 |
| `.trellis/dependencies/ledger.json` | T2 | 是 |
| `.agents/skills/{wf,wf-repair}/**` | T2 | 是 |
| `.claude/skills/{wf,wf-repair}/**` | T2 | 是 |
| `AGENTS.md` 块外段 | T1a | 是 |
| `.trellis/.developer` 的 `workflow=wf` | T1a | 否 |
| `.trellis/config.yaml` 的 `default_workflow: wf` | T1b | 是 |
| `.zcode/config.json` 四条命令 | T1c | 是（带债务） |
| `.trellis/.runtime/wf/install-record.json` | T2（本机态） | 否 |

### B.3 依赖关系

```
task.json.meta.wf.deps.id  ──┐
task.json.meta.wf.deps.prereqs ──┤
task.json.meta.wf.deps.rework_source ──┼──→  ledger.json 的 entries
ledger.json.entries[*].replacement_target ──┘        │
                                                     ↓
                                        wf dag --json（视图不落盘）
```

判定只读“任务记录的事实”与“账本”，视图永远可重建。

---

## 附录 D：与设计稿的条款对照

| 设计稿条款 | 本文件落点 | 承载方式 |
|---|---|---|
| 不变量 1（基底是任务生命周期的唯一承载） | §3.5（只包装不改写）、§6.3 | 实现约束 |
| 不变量 2（单一状态源） | §3.1（任务状态三值）、§3.2（账本） | 实现约束 |
| 不变量 3（单一记录源，除账本不新增记录类型） | §6.1、§9-C3 | 实现约束 |
| 不变量 4（DAG 无环） | §3.5 边变更校验、§3.7 | 校验点 |
| 不变量 5（图内任务只走机制入口） | §3.5、§3.6、§9-C6 | 约定 + 检测 |
| 不变量 6（完成 = 人判 + 归档） | §6.2 | 实现约束 |
| 不变量 7（项目层用任务承载） | §3.9 | 实现选择 |
| 不变量 8（基线是活的） | §3.9、§6.1 | 实现选择 |
| 不变量 9（任一节点不依赖单一 CLI） | §4.1–§4.9、§4.10 的跨 CLI 接手 | 平台矩阵 |
| 不变量 10（模块可卸载） | §7.5、§9-C15 | 拆卸契约 |
| 不变量 11（替换/放弃只向前） | §3.5、§3.8、W20 | 校验点 |
| 不变量 12（账本写入必须合法） | §3.2、§3.5、W13 | 校验点 |
| 表 4-1（任务状态流转） | §3.1 | 由基底承载，模块只调用 |
| 表 4-2（账本七行转移） | §3.2、§3.8 | 校验点（唯一合法转移集） |
| §4.5 四道关卡 | §3.5（开工/完成）、§3.9（项目层收尾）、§3.10（收尾对象） | 实现落点 |
| §7.7 完整性分类（类型 1–5） | §3.8 的 `wf repair` 类型面 | 唯一修复入口 |
| §9.1 三段入口 | §3.6、§3.7、§3.8 | `wf route` 判定顺序 |
| §9.4 卸载五约束 | §2.4、§7.5 | 拆卸契约 |
