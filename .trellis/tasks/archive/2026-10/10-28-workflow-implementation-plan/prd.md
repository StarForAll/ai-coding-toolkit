# 工作流实现方案：基于当前设计稿全新实现方案文档

## Goal

产出一份**全新的、自洽的实现方案文档**：把当前设计稿（[workflow-design.md](../../../docs/workflows/workflow-design.md) 正文 §1–§9 与配套 [依赖机制设计说明.md](../../../docs/workflows/依赖机制设计说明.md)）落到可执行的嵌入工程上，同时继承 [1.2-零补丁嵌入方案.md](../../../docs/workflows/1.2-零补丁嵌入方案.md) 中**约四成与设计版本无关的嵌入工程契约**。

文档必须显式支持 **claude code / codex / zcode / pi / dsh** 五个平台；其余 agent 按通用特性（AGENTS.md + 通用 skill 目录 + CLI）给予**通用性支持**而非逐平台适配。文档还需承载 `.zcode/config.json` 的 `ZCODE_PROJECT_DIR` 加固要求。

所有与设计稿冲突、或与当前仓库事实不符的条目，集中登记为**待人工判断清单**，不在文档内静默取舍。

## Background / 已核实事实

来源文档：

| 文档 | 体量 | 性质 | 本文档的用法 |
|---|---|---|---|
| `docs/workflows/workflow-design.md` | 850 行 / 97 KB | 设计骨干部署（§1–§9 规范，附录例示） | **规范来源**：判定、状态、流转、关卡、入口三段、卸载 |
| `docs/workflows/依赖机制设计说明.md` | 约 350 行 | 依赖机制配套（状态表、返工/替换/放弃、对账恢复） | **规范来源**：机制细节以它为准，设计层约束以设计稿为准 |
| `docs/workflows/1.2-零补丁嵌入方案.md` | 1327 行 | 旧实现方案（v4，绑定 v20 设计） | **仅取工程契约**：约四成与设计版本无关的部分 |

仓库事实（本轮实测）：

| 事实 | 证据 |
|---|---|
| 本仓库 Trellis 版本 `0.7.0-beta.42`；上游参考仓库 `~/projects/other/Trellis` 检出 `feat/v0.7-beta` @ `be9e19b2` = `0.7.0-beta.4` | `.trellis/.version`；上游 `git log -1` |
| 变体解析链仍存在：per-task pin → `.developer` → `config.yaml default_workflow` → 全局 `.trellis/workflow.md` | `.trellis/scripts/common/workflow_selection.py:1-25` |
| `.trellis/workflows/` **当前不存在**（变体机制尚未使用） | `ls .trellis/workflows` 退出码 2 |
| `task.py` 命令集：`create/start/current/finish/workflow/set-branch/set-base-branch/set-scope/set-meta/rename/archive/list/*-context/list-archive` | `task.py --help` |
| `task.py start` 有 context-manifest 门（seeded 但无条目即拒绝），`--allow-empty-context` 为显式豁免 | `task.py:197-218` |
| `task.py archive` 强制写 `status=completed` + `completedAt` 后再移动目录；另有分支门（`branch == base_branch` 拒绝、`branch` 缺失 + 有 `base_branch` + 有 remote 拒绝） | `common/task_store.py:1246-1275,1382-1383` |
| 平台目录现状：`.claude/`（skills/agents/commands/hooks）、`.codex/`（skills/agents/hooks + config.toml + hooks.json）、`.pi/`（extensions/prompts/agents + settings.json）、`.dsh/skills/`（6 个）、`.agents/skills/`（14 个）、`.zcode/`（skills 9 个 + hooks 4 个 + config.json） | `find` 各目录 |
| `.zcode/config.json` 四条 hook 命令已被本地加固（`git rev-parse --show-toplevel` 兜底 + 失败 `exit 0`），并登记为**受管文件漂移的已注册例外** | `.zcode/config.json`；`.trellis/spec/platforms/zcode-workflow-behavior.md` 的 Local Hardening Record |
| ZCode 的 `${ZCODE_PROJECT_DIR}` 绑定会话实时 cwd（`/opt/ZCode/resources/glm/zcode.cjs`），无固定项目根变量 | 同上 spec |
| 上游参考仓库为**只读**，禁止改动；不得提议上游补丁 | 根 `AGENTS.md` Repository Scope 段 |

## Requirements

**R1 全新性**：交付物是新文档，不得是 1.2 的改写/裁剪；1.2 的版本绑定内容（v3→v4 收敛、D20/D21/D22/D23 决策、审查记录十一轮）不进入新文档正文，只允许作为工程契约的**来源标注**。

**R2 设计层对齐**：文档的判定与流转必须与设计稿一致，且逐条可回溯到设计稿章节（§2 不变量、§4.2 两层状态、§4.4 表 4-1/4-2、§4.5 关卡、§5 项目层、§6 任务层、§7 依赖机制、§8 记录、§9 入口/旁路/卸载）。设计稿规定"不动"的东西（任务状态机、完成判定、记录源）不得在实现层另造。

**R3 工程契约抽取**：从 1.2 中抽取与设计版本无关的嵌入工程契约，抽取面覆盖且仅覆盖下列类别（对应 1.2 的行范围，合计约占正文四成）：
- 零补丁地基与受管写入边界（1.2 §2.2、§4.1）
- 模块源/目标项目目录布局与进出库流向（§4.2）
- 上游 `task.py` 集成约束与三条硬门（§4.3.1、§4.3.2）
- 平台接入契约（skill 根映射、四条件、frontmatter 渲染、G0 验收）（§4.4、§4.6、§4.6.1）
- 门禁不依赖"谁触发"（§4.7）
- 护栏取舍与顺序可恢复（§4.8）
- `AGENTS.md` 块外 NL 路由（§4.9）
- 原生字段纪律（§4.12）
- 升级机制：三轴版本、契约探针、升级 SOP、资产输入与回滚、拆卸契约（§5.1–§5.7）
- 证据/记录边界与引用纪律（§9，去掉版本绑定条目）
明确**不抽取**：v20 特有节点、D20/D21/D22/D23 决策文本、`wf-*` 状态投影（属设计版本选择）、审查记录 §10。

**R4 平台支持**：五平台各成一节，给出：入口面（skill 根 / 命令 / 注入通道）、必需能力、增强能力、验收判据；平台差异只用数据（映射表 + frontmatter 渲染）表达，正文不得出现平台分支。第六类"其他 agent"给通用性支持路径与降级声明。

**R5 ZCode 加固**：`ZCODE_PROJECT_DIR` 不固定问题的成因、加固后的命令形态（四条 hook 全量）、落点文件、与 `trellis update` 的漂移债务、撤销条件，必须在方案中作为**安装期必做步骤**写清，并给出可复制模板。

**R6 冲突登记**：所有"设计稿要求 × 1.2 契约 × 当前仓库事实"三方不一致项登记成表，每条含：冲突点、来源、影响、建议处置、待人工裁决的选项。不得在正文里静默择一。

**R7 可消费性**：文档必须给出实现层可直接执行的要素——命令面（子命令 + 读写对象 + 门禁）、路径清单、状态派生规则、探针/验收清单、实施阶段划分。禁止只写原则不写落点。

**R8 约束**：不修改 `workflow-design.md`、`依赖机制设计说明.md`、`1.2-零补丁嵌入方案.md`；不修改本仓库任何平台目录与 `.zcode/config.json`；不实现安装器/CLI 代码。

## Acceptance Criteria

- [ ] **A1** 新文档落盘，含完整章节骨架：设计前提 / 嵌入边界 / 平台支持 / ZCode 加固 / 状态与门禁实现 / 依赖机制实现 / 卸载拆卸 / 升级 / 验收探针 / 冲突登记。
- [ ] **A2** 每条工程契约标注 1.2 来源章节；抽取面与 R3 清单逐条对应，且能指出未抽取的版本绑定内容去向。
- [ ] **A3** 五平台（claudecode/codex/zcode/pi/dsh）各成一节，每节含入口面、必需能力、增强能力、验收判据四要素；另有"通用 agent"一节。
- [ ] **A4** ZCode 一节包含四条 hook 的加固命令模板（与当前仓库 `.zcode/config.json` 等价）、漂移债务说明、撤销条件、验收判据。
- [ ] **A5** 冲突登记表至少覆盖：设计稿 §3"持久化"的选择性提交与原生 `archive` 自动提交的关系；设计稿 §9.4 卸载 vs 1.2 §5.7 拆卸契约；设计稿"图内任务只走机制入口" vs 无 hook 平台；`wf-*` 状态投影 vs 设计稿"任务状态只有三个值"；ZCode 加固 vs 受管文件纪律。
- [ ] **A6** 文档内无未标注的 TBD/占位；所有"上游行为"表述可追溯到本轮实测或标注为读码/推断。
- [ ] **A7** 设计稿可判定条款（不变量 1–12、表 4-2 七行转移、§4.5 四道关卡、§9.1 三段入口）在方案中有明确实现落点或明确"由原生承载"的声明。

## Out of Scope

- 实现安装器、CLI、skill 正文、变体 markdown（本任务只出方案）。
- 替换或删除 1.2 文档；改动设计稿与依赖机制说明。
- 改动本仓库 `.zcode/config.json`、`.trellis/**` 运行时、平台目录。
- 目标项目侧的迁移执行（方案只给步骤与判据）。
- 上游 Trellis 参考仓库的任何修改或补丁建议。

## Constraint / Risk Notes

- 1.2 基于 `0.7.0-beta.4`，本仓库为 `0.7.0-beta.42`：其中行号级引用不可直接沿用，方案中一律改为"函数名 + 正典路径"，并在冲突表登记版本差异。
- 1.2 §9 已自述多项未实测（Pi 变体解析为读码结论、Codex hook 未实跑、Claude Code 读 AGENTS.md 为条件性）。新方案必须保留这些证据边界标注，不得升级为"已验证"。

## Decision Log

- **落点与命名（已定 2026-10-28）**：`docs/workflows/workflow-implementation.md`，与 `workflow-design.md` 对称，同在 `docs/workflows/` 顶层。

## 审查后修正（2026-10-28 第二轮）

外部审查提出 4 个主问题 + 3 个次要问题，逐条核实后按“重写受影响的节”而非加注的方式修正：

| # | 判断 | 核实结论 | 修正落点 |
|---|---|---|---|
| 1 | archive 分支门被误判为“只告警” | **成立**：`_validate_branch_metadata` 对 `branch == base_branch` 返回 False（硬拒绝）；只有“分支本地不存在”是 Warning。本仓库任务 `branch=main, base_branch=main` 即会命中 | §3.5 重写（固定传 `--skip-branch-validation` + `pr_url` 断言）、W10、§9-C16、附录 C |
| 2 | 版本声明与仓库不符 | **成立**：`.trellis/.version` 与 `trellis --version` 均为 `0.7.0-beta.4`，与上游检出同代同版本 | §0.4 重写（版本事实表 + 勘误留痕）、§7.1、§9-C10 改为证据勘误、附录 C |
| 3 | 返工“稳定基底定位”未定义 | **成立**：`create` 目录名用当天日期前缀且拒绝跨日 `--slug`，原方案只存示例值 | 新增 §3.12（定位规则 + 五步序列 + 逐窗口，含跨日恢复）、§3.2 schema 改 `r_slug`、W19 |
| 4 | 收尾任务创建时机与 `task new` 门禁互锁 | **成立** | §3.9 重写（任务图机检块、`role: tail` 定义、`--from-graph` 拓扑序创建）、§3.5 参数化入口、§3.10 收尾对象解析、W22 |
| 5 | `wf self-hash` 前后矛盾 | **成立** | §6.2 统一为“信任根与 self-hash 整组不存在，self-test 保留”；W6、附录 A 同步 |
| 6 | W18 判据形式化错误 | **成立** | §3.3 引入 `in_graph` 为唯一判据；W18 改写 |
| 7 | ZCode 读 `AGENTS.md` 已有实测 | **成立**（用户提供的 ZCode 会话观察） | §4.1、§6.5 升为实测；§9-C9 去掉该待办 |

连带收口（审查未提但不修会遗留）：

- **DAG 视图不落盘**：原设计写 `.trellis/dependencies/dag.md` 进库，会让派生件制造无意义 diff；改为 `wf dag` 输出，同步 §1.5 / §2.2 / §2.3 / §7.5 / 附录 B。
- **卸载还原改用安装前快照**：原写“与当前 Trellis 模板三方比对”，模板路径不可靠；改为 `.trellis/.runtime/wf/pre-install/` 快照比对，同步 §2.4 / §5.3 / §7.5 / §7.6。
- **机制自己提交**：为满足“不捎带”，明确机制写入后立即单路径提交，不依赖 `session_auto_commit`；同步 §3.4 与 §9-C4。

## 裁决结果（2026-10-28）

- C1、C2、C3、C6、C7、C16：按默认（建议项 ①）
- C4、C5、C8、C12：按建议项 ①
- C14 随 C1 剔除；C9/C10/C11/C13 为事实类，无需裁决

已落地：§9.1–§9.4 每行标注「已采纳①（2026-10-28）」，新增 §9.5 裁决记录与 §9.6 治理期/实施期待决清单（G1–G6）。正文未因裁决发生实质变化（原本即按建议书写），仅把"待裁决"标记收敛为"已裁决"。

## 治理与位置裁决（2026-10-28 追加）

- G1 不登记文档索引。
- G2 `1.2-零补丁嵌入方案.md` 由使用者后续删除 → 文档去除对该文件的链接依赖（§0.2 改纯路径 + 声明正文自足）。
- G3 模块源位置改为 `docs/workflows/新项目开发工作流/`；现有旧模块整体移入 `tmp/新项目开发工作流/`（gitignored，只读参考）。§2.1、§2.5、§2.2、§8.2 P0、附录 B.1 同步。
- G4 关键约束沉淀到 `.trellis/spec/docs/workflow-implementation-constraints.md`，并在 `.trellis/spec/docs/index.md` 登记。
- G5 变体正文不在本任务决定；G6 P0 拆任务未定。

## 审查后修正（2026-10-28 第三轮）

两条判断均成立，按“消除重复表述 / 补齐必然分支”处理：

1. **`wf task new` 前置两处冲突**：主表写“项目层已过”，参数化表又允许 `--role project` 无 P 启动 → 字面实现会让首个 P 建不出来。
   修正：主表前置列改为“按入口类型，见下方参数化表”；参数化表新增“前置”列，成为唯一源，并显式写明 `--role project` 无 P 时允许；§3.9 的“未定标不许开任务”同步加该例外。
2. **新克隆的卸载还原未明说**：`.runtime/` 是 gitignored 本机态，新克隆没有快照，必然落入 fail-closed 分支。
   修正：§7.5 新增“还原依据的三级顺序”（本机快照 → git 历史 parent → 预览且不改文件），明确“新克隆是常态、必须落到第 2 级”；`config.yaml` 与 `.zcode/config.json` 两行共用该规则；§5.3 卸载段同步；新增探针 **W23** 与 §7.6 第三条往返；spec 同步两条约束。
