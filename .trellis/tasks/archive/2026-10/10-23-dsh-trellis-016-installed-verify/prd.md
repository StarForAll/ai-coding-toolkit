# 验证已安装 dsh-trellis 0.1.6 的 Codex 对等性与 DSH Trellis 补足

## Goal

对**已安装**的 `dsh-trellis 0.1.6`（`~/.dsh/profiles/web/node_modules/dsh-trellis`）做一次独立、可复现、全方位的真实运行验证：

1. 是否达到 Codex 使用 Trellis 的同等效果；
2. 是否补足 DSH 直接使用 Trellis 的不足（以"尽可能弥补"为评估标准）；
3. 是否存在其他缺漏或不足。

判断依据必须同时结合 **DSH 宿主机制**（事件、工具、投影、子代理、命令、shellEnv、settings）与**上游 Trellis 0.7.0-beta.4 机制**（脚本、模板、hook 契约、原生 DSH class-2 支持），不把 Codex 行为当作唯一标准。产出问题清单与执行方案；**用户确认之前不修改任何插件/仓库代码**。

## Background（本轮起点事实，2026-10-23 实测采集）

- DSH `0.2.1-rc.2`（`/softwares/nodeNpm/nodejs/bin/dsh`）；Trellis CLI `0.7.0-beta.4`；Codex CLI `0.163.0`。
- 上游只读参考 `~/projects/other/Trellis`：`packages/cli`、`packages/core` 均为 `0.7.0-beta.4`（只读政策不变）。
- 插件源码 `dsh-plugins/dsh-trellis` = `0.1.6`；已安装 web profile `~/.dsh/profiles/web/node_modules/dsh-trellis` = `0.1.6`，`lib/` 与源码逐字节一致（diff -rq 为空）。
- `~/.dsh/profiles/headless/` 当前**未安装** dsh-trellis（上轮的 trellis-headless profile 已不在，待核实是否为缺漏）。
- 上一轮任务（归档 `10-23-dsh-trellis-parity-verify`）修复 C1/C2/C3/C6/C7 并发布 0.1.6；其真实会话复测基于当时的 trellis-headless profile，web profile 彼时仍为 0.1.5。**本轮不复用其结论，只把其全部断言当作待复核清单**，且必须对"已安装 web 副本"重新实测。

## Requirements

- **R1 安装态机制对照**：逐项对照 Codex 与 DSH（含插件）在 Trellis 中的接入面：会话/每轮上下文注入（breadcrumb/bootstrap）、任务状态、路径级 spec 注入（deny-once/ticket/refresh）、子代理上下文 push 与守卫、角色识别、命令面、会话身份、项目级配置（`dsh.dispatch_mode` inline/auto）、升级/安装形态、settings/doctor/版本监控。
- **R2 0.1.6 修复回归**：对上轮 C1（角色误判）、C2（子目录 spec 并集匹配）、C3（默认 inline + 不写 tracked config）、C6（安装版本一致性）、C7（文档契约）逐项在已安装副本上用真实会话复核。
- **R3 真实运行验证**：在 `/tmp` 新建临时 Trellis 项目（`trellis init` 带 codex+dsh 面），用真实 DSH 会话（真实 LLM、真实工具调用）验证；Codex 侧同样用真实 `codex exec`/hook 实际执行对照，不允许只读文档下结论。
- **R4 双机制判断**：以 DSH 宿主机制 + Trellis 0.7.0-beta.4 原生 DSH 支持（class-2 pull：`.agents/skills`、`.dsh/skills`、`.dsh/DSH.md`、`get_context.py --platform dsh`、`task.py` 闸门）为基准评估"补足"程度；插件 push 层与原生 pull 层的叠加不得互相破坏。
- **R5 补足评估**：明确列出 DSH 裸用 Trellis 的不足项，逐项判定：已补足 / 部分补足 / 未补足 / 宿主限制无法补足，并给出补足差距的可行动建议。
- **R6 全方位证据分级**：所有结论标注证据等级——S1（真实 DSH/Codex 会话）、S2（已安装模块直载执行）、S3（源码/模板/脚本契约比对）、S4（单测）；不得以 S3/S4 冒充 S1。
- **R7 缺漏扫描（新角度）**：覆盖此前轮次未深入的面：compaction/会话恢复后的状态重置与去重、多会话并发 spec 状态分片、inline/auto 双模式全链路、`trellis_wait` 伴侣能力是否存在与可用、headless profile 无插件的影响、非 Trellis 项目零干扰、版本监控/冲突检测路由。
- **R8 单任务约束**：只使用本任务；不创建其他 Trellis 任务。
- **R9 修复闸门**：用户确认问题清单与执行方案之前，不修改本仓库任何代码/文档；`/tmp` 临时项目与证据目录不受此限。
- **R10 无问题路径**：若某维度未发现问题，报告必须写明具体验证结果（测了什么、证据在哪、为何判定达标），不允许"看起来没问题"式结论。

## Non-Goals

- 本阶段不实现修复、不提交、不推送、不改写历史。
- 不验证与 Trellis 集成无关的插件能力（纯 GUI 样式、通用 DSH 功能）。
- 不绕过 DSH Web 本地鉴权去验证 UI（若无法在凭据安全前提下进入，如实记录为验证限制）。
- 上游 Trellis（`~/projects/other/Trellis`）只读：其行为差异只记录为边界观察（O 系列），不作为问题或修复项。
- 不把模拟结果、单测结论冒充真实会话结论。

## Acceptance Criteria

- [ ] 验证报告（`research/verification-report.md`）：含 S1–S4 分级证据、每个维度的明确判定与证据位置。
- [ ] Codex vs DSH(+插件) 逐项对照矩阵：达到同等效果 / DSH 增强 / DSH 不及 / 双方共同缺陷 / 宿主限制 / 上游只读观察。
- [ ] 0.1.6 修复回归表：C1/C2/C3/C6/C7 逐项在已安装副本上的复核结果。
- [ ] DSH 裸用不足 → 插件补足程度评估表（已补足/部分/未补足/宿主限制）。
- [ ] 问题清单：每项有唯一编号、严重级别（P0–P3）、复现步骤、证据位置、影响面、候选修复方案（含推荐项与取舍）。
- [ ] 待用户确认的执行方案；未确认前零代码修改（`git status` 可证）。
- [ ] 无问题维度逐条写明具体验证结果与证据路径。
- [ ] 不改动用户已有的未提交文件（`docs/capability-inventory.md`、`dsh-plugins/plugin-create.md`）；不泄露任何凭据值。

## Decisions

- **2026-10-23（E3 闸门，初轮确认）**：F1/F2/F3 曾确认为不处理。
- **2026-10-23（用户后续修订，最终生效）**：
  - F1（headless 文本不路由 /trellis-* 命令）：改为**补充文档说明**（插件 README「headless 文本限制」节，含等价 shell 命令；仓库 spec 同步记录）。
  - F2（切换 dispatch_mode 后历史旧 banner 误导）：改为**补充文档说明**（同会话避免中途切换；必须切换时优先新开会话，或明确告知模型旧 banner 已过期、以当前配置为准；README + spec 同步）。
  - F3（~/.dsh/profiles/headless 无插件）：**保持现状**（仅 web profile 使用 Trellis）。
  - 实施：文档 + 版本号变更轮，插件版本 `0.1.6 → 0.1.7`（package.json/README/LOCAL_CHANGES/docs/validation-0.1.7-local.md 一致，client bundle 重印）；无 lib 逻辑/测试变更（仅 `lib/client.js` 的 `PLUGIN_VERSION` 版本 stamp 随构建变化），单测维持 350/346/0/4；已安装 web 副本仍 0.1.6（无运行时变化，不因文档重装）。
