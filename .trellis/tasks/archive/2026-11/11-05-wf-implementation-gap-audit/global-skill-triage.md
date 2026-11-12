# 全局旧 skill 处置对照（multi-cli-review* / workflow-scan / workflow-repair）

> 只做现状取证与替代面分析，不执行删除。删除位置在仓库外（用户全局），须人授权。

## 1. 三层载体，别混为一谈

| 层 | 位置 | 是否在仓库 | 谁能发现 |
|---|---|---|---|
| 仓库源资产 | `skills/multi-cli-review{,-action}/` | 是（Git 跟踪） | 不进宿主技能根，除非另行部署 |
| 用户全局共享库 | `/home/xzc/ops/data/ai/skills/agents-skills/`（`~/.claude/skills/*` 是指向它的符号链接） | 否 | 所有会话（本会话的技能目录即来自这里） |
| wf 模块自有副本 | `docs/workflows/新项目开发工作流/skills/wf-review`、`wf-review-action` | 是 | 装到目标项目后按 `--platform` 落点 |

`sha256` 实测：仓库 `skills/multi-cli-review/SKILL.md` 与用户全局同名文件**逐字节相同**（`6d409e74…`）；`-action` 同样（`e882c998…`）。因此**只删仓库副本不会让这两条 skill 消失**——会话仍能发现、仍可按旧协议发起。

## 2. `multi-cli-review` / `multi-cli-review-action`

- **仓库层**：设计稿 §6.5 定为"一次性适配源"，§7.4 要求"适配完成后按既有清理计划移除，清理不得早于自有副本投放与验收完成"。投放（55 资产）与验收（`validation.md` §19：codex + pi 两异种 reviewer 全链路 pass）均已完成 → **清理条件成立，但未执行**。
- **用户全局层**：不属设计稿 §7.4 的"本仓库全局"范围。它是通用能力（wf 之外也在用），删掉会失去非 wf 场景的用法。
- **建议**：仓库层删 + 同批改 12 处引用（见清单 R1-1）；用户全局层**保留**，除非你明确要清空。

## 3. `workflow-scan` / `workflow-repair`

### 3.1 仓库侧已退役（不是遗留）
- 2026-10-28 的 `10-28-legacy-workflow-retirement` 任务已把 `skills/workflow-repair/`（71 文件）、`skills/workflow-scan/`（21 文件）连同四个 spec 契约一起 `git rm`（该任务 `implement.md` 第 9 步、`prd.md` 判据 A5）。
- 同一退役把它们的**误报守卫**蒸馏为路径无关的规范：`.trellis/spec/docs/workflow-asset-audit-guards.md`，开头即写"apply them when auditing any authored workflow asset set, **including the future `wf` module**"。
- `.trellis/spec/skills/index.md:23-26` 已记录"四个 legacy 维护 skill 于 2026-10-28 退役"。
- 所以：**仓库里没有残留，知识也没有丢**。

### 3.2 仍存活的是用户全局副本
`/home/xzc/ops/data/ai/skills/agents-skills/workflow-scan/`（754 行）、`.../workflow-repair/`（1630 行），并 `~/.claude/skills/` 符号链接暴露给所有会话。

### 3.3 它们的对象已经不存在
两个 skill 的前置条件（`compatibility` 字段原文）都是：
- 需要 `trellis` 在 PATH 上；
- 需要一个"embedded Trellis temp project"夹具——即**旧内嵌 Trellis 模块**装进临时项目后的运行态；
- repair 的修复目标写死为 `docs/workflows/新项目开发工作流/`。

现状：旧内嵌模块 2026-10-28 退役；`docs/workflows/新项目开发工作流/` 现在是**独立 wf 框架**，与旧模块共享的只有路径名。**按旧规则修这个目录 = 用另一套产品的语义改新框架**，这正是保留它们的最大风险（不是"多占地方"，是"触发器仍然有效、目标已换成别的产品"）。

### 3.4 新框架的替代面（逐项对）

| workflow-scan 的能力 | 新框架对应物 | 是否等价 |
|---|---|---|
| 扫描"已安装态 vs 源树"的资产漂移 | `install.py` 投放后自检 + `gates.support_report` + 清单哈希 | 覆盖资产层面，**不覆盖语义缺陷分类** |
| 产出分级报告（confirmed-defect / design-debt / evidence-gap）+ 版本戳 + 陈旧报告阻断 | 无 | **无替代**（`wf-review` 只审任务 diff，且要求 2 个异种 CLI；`inspect` 只查项目记录） |
| 源树自身的结构一致性 | `validate-wf-design.py`、`check-doc-refs.py`、`validate-skills.sh`、`build-wf-release.py --verify` | 覆盖结构，**不覆盖语义** |
| 在夹具里跑通整条工作流并观察 | `scripts/tests/wf_runtime/full/`（55 套） | 覆盖行为，**不产出可交接报告** |
| workflow-repair：按报告逐条本地核实→安全修复→有界收敛 | `.wf/bin/repair.py`（**对象不同**：修项目记录，不修源码）；源码修复 = 普通任务（本次审计就是） | **无专用资产** |

结论：**没有对等替代**。但"没有替代"不等于"必须保留"——因为它的对象（内嵌模块的安装态）已经不存在，而它要产出的那类"对源树做语义级扫查"的活动，现阶段由普通任务 + `wf-review` 承担。

## 4. 三个选项

| 选项 | 动作 | 代价 |
|---|---|---|
| **A（建议）删除** | 删用户全局两份；在 `.trellis/spec/docs/workflow-asset-audit-guards.md` 或 journal 记一笔"与 10-28 退役同批清理用户全局残留" | 失去"对源树做结构化扫查/按报告修复"的现成入口；知识面不丢（guards 已在 spec） |
| B 保留但封口 | 保留，改 description/前置，明确"只适用于已退役的内嵌模块，禁止用于 `docs/workflows/新项目开发工作流/` 的新框架" | 需要维护一份永不使用的 skill；description 是触发面，改写后仍是死资产 |
| C 重写为新资产 | 按新对象（发行树 + `install.py` 安装态 + 测试夹具 + `wf-release.json`）重写；属**新机制**，须过 charter T2/T5 并登记 | 显著工作量；不在首轮范围；先要人裁"是否要这个能力" |

我的判断：选 A。理由是**对象消失 + 知识已另行保留 + 目标路径已被另一个产品占用**，三条同时成立时保留没有正面价值，只有误用风险。若你认为"对源树做语义扫查"仍值得常备，那应走 C（新机制、新登记），不能用旧的两个顶替。

## 5. 跨仓库边界

- 删除对象在 `/home/xzc/ops/data/ai/skills/agents-skills/` 与 `~/.claude/skills/` 符号链接，**不在本仓库**，需你明确授权后我才能执行。
- 仓库内与它们相关的只剩历史登记（`.trellis/spec/skills/index.md:23-26`、`workflow-asset-audit-guards.md` 的"retired pair"说明），这些**应保留**，删掉反而丢失退役事实。
