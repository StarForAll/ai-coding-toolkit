# 验证已安装 dsh-trellis 对 Codex+Trellis 的对等性与补足（独立复验）

## Goal

对**当前已安装**的 `dsh-trellis` 做一次独立、可复现、多角度的真实运行验证，回答三个问题：

1. 是否达到 Codex 使用 Trellis 的同等效果；
2. 是否补足 DSH 裸用 Trellis（无插件、仅 class-2 pull）的不足，且尽可能弥补；
3. 是否还有其它缺漏、退步或误导性行为。

判断基准必须同时来自 **DSH 宿主机制**（0.2.1-rc.2 的事件、工具、投影、子代理、命令、settings、webServer）与 **Trellis 上游机制**（0.7.0-beta.4 的脚本、模板、hook/class-2 契约、workflow 状态模型），不能只拿 Codex 行为当唯一标尺。最终交付问题清单与执行方案；**用户确认前不修复任何问题、不改本仓库代码**。

## Background（本轮起点事实，2026-10-23 实测采集）

- 运行时：DSH `0.2.1-rc.2`；Trellis CLI `0.7.0-beta.4`；Codex CLI `0.163.0`；Node `v24.20.0`。
- 上游只读参考 `~/projects/other/Trellis`：tags/package 均为 `0.7.0-beta.4`，只读政策不变。
- 已安装副本：`~/.dsh/profiles/web/node_modules/dsh-trellis` = **0.1.6**（web profile 的 `package.json` 以 git path 依赖安装）。
- 本仓库源码 `dsh-plugins/dsh-trellis` = **0.1.7**。`lib/` 与已安装副本逐字节一致，唯一差异是 `lib/client.js` 的 `PLUGIN_VERSION`（0.1.7 vs 0.1.6）；README/package.json 有 0.1.7 文档差异（headless 命令限制、模式切换边界）。
- `~/.dsh/profiles/headless/` 存在但**未安装** dsh-trellis（裸 DSH 行为）。
- Trellis 0.7.0-beta.4 原生支持 DSH class-2 pull：`.agents/skills/`、`.dsh/skills/trellis-start|continue|finish-work|agent-*`、`.dsh/DSH.md`、`get_context.py --platform dsh`、`task.py` 会话指针；插件是**可选伴侣**，不是前置条件。
- 上一轮归档任务 `10-23-dsh-trellis-016-installed-verify` 对 0.1.6 的结论是"主链路无 P0/P1/P2，F1/F2 为 P3 文档边界"。本轮**不复用其结论**，只把其场景与断言当作待复核清单，并对该档案未覆盖的角度重新设计。
- 本仓库当前有用户未提交文件 `docs/capability-inventory.md`、`dsh-plugins/plugin-create.md`，任何阶段都不得改动。

## Requirements

- **R1 安装态一致性**：确认验证对象是已安装副本（0.1.6），并核实它与源码（0.1.7）的运行时/文档差异边界；所有 S1 结论必须来自已安装副本，不得用源码直载冒充。
- **R2 三臂对照**：同一临时项目分别以 (a) Codex + Trellis（真实 `codex exec`/hook，无法触发时记录限制并用真实 payload 直调补偿）、(b) DSH 裸用（无插件 headless profile）、(c) DSH + 已安装插件 三臂运行，逐维度对照。
- **R3 Codex 对等性矩阵**：覆盖 bootstrap、每轮 workflow-state 面包屑、任务状态（no_task/planning/in_progress/completed/stale/task_error）、路径级 spec deny-once/静默窗口/spec 变更重注入、子代理上下文 push 与角色契约、角色识别、dispatch 守卫、命令面、会话身份、项目配置（`dsh.dispatch_mode` inline/auto）、安装/升级形态、settings/doctor/版本监控/冲突检测。结论分级：达到同等效果 / DSH 增强 / DSH 不及 / 双方共同缺陷 / 宿主限制 / 上游只读观察。
- **R4 补足度评估**：先实测 DSH 裸用的缺口（无注入、spec 被违反、无 push、无守卫、无命令、无身份等），再逐项判定插件为已补足 / 部分补足 / 未补足 / 宿主限制，并给出可行动建议。
- **R5 真实运行验证**：在 `/tmp` 新建临时 Trellis 项目（`trellis init` 同时带 codex 与 dsh 面），用真实 DSH 会话（真实 LLM、真实工具调用）执行场景；不得以单测、静态阅读或模拟输出冒充真实会话结论。
- **R6 新角度覆盖**：至少覆盖前轮未深入或未完成的：真实 compaction/reset、跨进程 resume 的 projection/去重与 spec 分片持久化、双会话并发隔离、inline/auto 全链路、`trellis_wait` 真实汇合与 fail-closed、非 Trellis 项目零干扰、无 git 项目、嵌套/子目录 cwd、升级（`trellis update`）后行为、duplicate plugin 冲突检测、doctor/version 路由、headless 命令面限制。
- **R7 证据分级**：所有结论标注 S1（真实 DSH/Codex 会话）/S2（已安装模块或真实 hook payload 直载执行）/S3（源码、模板、脚本契约比对）/S4（单测）。S3/S4 不得冒充 S1；未覆盖项必须写明限制与补偿证据。
- **R8 单任务约束**：只使用本任务，不创建其他 Trellis 任务；验证过程不修改本仓库代码/文档（`/tmp` 实验区除外）。
- **R9 修复闸门**：用户确认问题清单与执行方案之前，零修复、零提交、零推送；问题按 P0–P3 分级，每项含复现步骤、证据位置、影响面、候选方案与推荐项。
- **R10 无问题路径**：若某维度未发现问题，必须写明"测了什么、证据在何处、为何判定达标"，不允许"看起来没问题"式结论。
- **R11 安全与卫生**：凭据只经环境变量注入子进程，不出现在命令行、日志、报告或仓库；不读取/复述用户凭据值；验证结束保留可复现证据路径，但不污染仓库工作树。

## Non-Goals

- 本阶段不实现修复、不提交、不推送、不改写历史。
- 不验证与 Trellis 集成无关的能力（GUI 视觉、通用 DSH 功能、MCP 工具本身）。
- 不绕过 DSH Web 本地鉴权去验证 UI；若无法在凭据安全前提下进入，如实记录为验证限制并给出 S2 补偿。
- 上游 `~/projects/other/Trellis` 只读：其行为差异只记为边界观察（O 系列），不作为问题或修复项，不提上游补丁。
- 不把 Windows 路径/编码、与该插件无关的第三方插件问题纳入。
- 不因鸡毛蒜皮（措辞、排版、非契约性文档差异）制造问题项。

## Acceptance Criteria

- [ ] 验证报告（`research/verification-report.md`）：含 S1–S4 分级证据、逐维度判定与证据位置。
- [ ] Codex vs DSH(+插件) 对照矩阵，覆盖 R3 全部维度。
- [ ] 裸用 DSH → 插件补足度评估表（已补足/部分/未补足/宿主限制）。
- [ ] 安装态核对：已安装 0.1.6 ↔ 源码 0.1.7 运行时一致性与文档差异说明。
- [ ] 问题清单：唯一编号、P0–P3、复现步骤、证据路径、影响面、候选修复方案（含推荐项与取舍）。
- [ ] 待用户确认的执行方案；确认前 `git status` 证明仓库零改动。
- [ ] 未覆盖项/验证限制清单及补偿证据。
- [ ] 无问题维度逐条给出具体验证结果与证据路径。
- [ ] 不触碰用户未提交文件，不泄露任何凭据值。

## Key Decisions

- **验证对象**：以 `~/.dsh/profiles/web/node_modules/dsh-trellis` 的 0.1.6 实体为准；源码 0.1.7 仅用于差异边界说明，若发现 0.1.7 已修复而安装态未生效，按"安装滞后"单列事实，不当作新缺陷夸大。
- **不做全量重复**：前轮已覆盖且本轮环境未变的场景可做**抽样复测**，但必须至少各命中一次 S1；新角度（R6）必须实际执行。
- **失败也是结果**：若真实 Codex hook、Web GUI、compaction 等无法在安全/可行条件下触发，记录限制与 S2/S3/S4 补偿，不伪造 S1。
- **修复方案呈报**：仅列出候选与推荐，等待用户逐项确认后再进入修复任务。

## Open Questions

（无阻塞问题。验证计划本身待用户审阅；修复范围在问题清单交付后由用户决定。）
