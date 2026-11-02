# wf 独立框架 · 实现方案文档（PRD）

## Goal

按设计稿 §8.1 第 2 项交付《wf 独立框架实现方案》文档：把已定稿的机制设计落成文件布局、脚本接口、命令形态与发行物构成，并给出单页使用速查与首轮最小闭环清单。本阶段不写框架代码。

## Background（已核实事实）

- 仓库 `/home/xzc/projects/personal/ai-coding-toolkit`，HEAD `13965ad`，工作树干净，仅有未跟踪 `.agents/skills/grill-me/`、`.unipi/`（不动）。
- 上游三份文档已定稿：设计稿 719 行、charter 128 行、机制稿 1139 行；索引表 157 行（表格 143 行）。
- `scripts/validate-wf-design.py` 实测全绿：`机制稿：引用 555；二值场景 91/91；三档场景 13/13；输入摘要 4/4` + `OK：设计 720 行 / charter 129 行；定义位点 51+7 个；索引表 143 行；消费点缺项 0；三率：定义命中 100% / 消费点命中 100% / 引用检查残差 2 行`。
- 机制稿 §0.1 以四份上游文件 SHA-256 作为输入基线，改动任一文件即打破 `输入摘要 4/4`。因此本任务不修改四份上游文件，也不新增指向上游文件的指针。
- 机制稿 §0 明确分工：机制稿是 schema/判定唯一编码位置；实现方案负责模块拆分、完整目录布局、CLI 参数与发行物组装。
- 环境：`python3` 3.13.5、`/softwares/python/bin/python3` 3.14.7（均 ≥ 机制稿 §1.1 的 3.11）；探到的 agent CLI 只有 `claude`、`codex`、`dsh`，能否作为非交互 reviewer 未实测。

## Requirements

1. **A 模块与资产拆分**：`.wf/bin/wf.py`、`.wf/bin/repair.py`、`.wf/bin/uninstall.py`、`.wf/workflows/`、入口 skill 与审查成对副本的投放根（缺省 `.agents/skills/`）、配置/spec/任务模板子路径，逐项给出「资产类型 → 具体路径 → 所有者 → 升级/卸载是否覆盖」（机制稿 §10.1 只到类型）。
2. **B CLI 与子命令面**：入口/子命令清单与参数；每条命令映射到机制稿 §2 的状态机动作与 §3 的路径判定；输出统一为机制稿 §11.1 的 `{tier, code, object, position, next, facts, exit, prohibited_repairs, warnings}`；声明「操作名不自动新增公开命令」。
3. **C 命令引导与执行器解析**：installed 按脚本真实位置定位目标、源码入口显式给目标、异 cwd 传绝对路径；目标项目 Python 三级解析与坏配置下的独立恢复入口（回退只对 repair/uninstall 开放）；只允许 Python 标准库。
4. **D 发行物组装**：`refs/tags/wf-v<major>.<minor>.<patch>`、目标提交根 `wf-release.json`（`schema_version/version/compatibility/assets/required_steps/template_markers/gitignore_managed`）、`rules_digest` 与 `effective_rule_version` 计算落点、打包源码布局、`.gitignore` 托管段（首行 `# wf-managed-v1`、尾行 `# wf-managed-end`、段内 `/.wf-lock` 保留行、卸载后段外裸行容忍）。
5. **E 审查适配**：自有副本投放/升级/卸载覆盖、项目树外暂存目录与主会话持写权导入、自报身份字段与对象锚点（Check 内容指纹、plan_version、spec/config 哈希），并说明首轮为何必须就绪（D25/D26/D31）。
6. **F 首轮最小闭环实现清单**：按机制稿 §12.1「跨轮基础项」逐条落到文件/函数/命令；下限对齐设计稿 §8.1（任务 schema、写权与锁、状态/门禁结构判定、内容指纹与检查有效性、开工与最终门禁、策展清单与读取留痕、归档与终态）；第二、三轮条目单列并注明未交付前只报告能力不可用。
7. **G 验证与验收映射**：机制稿 §12.4 五条最小验证顺序逐条给出验证对象/夹具/初态/触发/预期输出三要素/失败归因规则；给出「门禁 → 设计稿 §8.2 场景行」的实现侧验收矩阵。
8. **H 单页使用速查**：「时刻 → 入口 → 人工动作/令牌 → 阻断出口」，含环境前提（治理面命中即复杂、复杂任务至少三个异种 CLI）、连续独立短任务优先声明为用户工作流实例、日常收工、未完成收工即关闭后的新会话恢复、对象结束后的下一对象选择与成本提示。
9. **I 正文声明遵循 charter**（设计稿 §8.1 L572）。

## Constraints

- 不改 `wf-framework-charter.md`、`wf-framework-design.md`、`wf-framework-design.index.md`、`wf-framework-design.sources.md` 正文；若发现上位矛盾，出「需人裁决」，不改上位也不刷新摘要。
- 不另造判定：只定义布局、脚本接口、命令形态与发行物构成；schema/判定编码/状态机/算法一律引用机制稿章节，不复制定义，不新增 `H("wf-…")` 哈希域。
- 不新增目标外机制（charter T3 不做清单）；框架运行不依赖 MCP、hook、常驻服务；脚本只用标准库。
- 未运行的验收不得写成通过；夹具/故障注入/宿主身份/审查链路一律标「未运行」。
- 不把旧模块文档当条款来源；只作结构先例。
- 不创建框架代码、不改 `skills/` 资产、不改 `.trellis/spec/`。

## Out of Scope

- 框架代码、脚本、skill 副本、`.wf/` 目录、发行清单实例文件。
- 机制稿 §0.2 四项机检扩展（本阶段登记为后续项，见决策 3）。
- 任何提交、归档、finish 动作（未获人明确授权）。

## Acceptance Criteria

- [x] `docs/workflows/wf-framework-implementation.md` 存在，正文声明遵循 charter，且只定义布局/接口/命令/发行物构成。
- [x] 文档覆盖 A–I 九项，缺项即不通过。
- [x] 资产表逐项点到具体文件名，不止于类型。
- [x] 每条命令标注对应机制稿状态机动作与路径判定章节，无孤立命令。
- [x] 首轮清单覆盖机制稿 §12.1 全部「跨轮基础项」，第二/三轮条目单列并标未交付行为。
- [x] 五条最小验证顺序各有初态/触发/预期输出三要素与失败归因规则，且一律标「未运行」。
- [x] 速查含全部指定行（环境前提、收工、未完成收工恢复、对象结束后新对象、成本提示）。
- [x] `scripts/validate-wf-design.py` 仍全绿且输入摘要仍 4/4；`scripts/check-doc-refs.py` 0 problem(s)；`unittest scripts.tests.test_validate_wf_design` 通过。
- [x] 四份上游文件 `git diff` 为空。

## Decisions（已由人确认）

1. 建 Trellis 任务并进入规划阶段（本任务）。
2. 文档落点：新建 `docs/workflows/wf-framework-implementation.md`。
3. 单页速查：同一文件内的独立章节。
4. 机制稿 §0.2 四项机检扩展：本阶段只做文档，四项登记为后续项（charter T6.3 顺序）。
5. 会话范围：只产出实现方案文档，不写框架代码。

## Decisions（第二轮，2026-11-02 人裁，针对交付时提出的 6 项待裁决）

6. 机制稿 §0.2 四项机检扩展：**登记为后续项**（不阻塞首轮；文档 §9.2 第 1 项与任务记录为登记落点，机制稿 §0.2 原文未改）。
7. 入站指针：**只在机制稿 §12.4 加一行指针**；索引表与设计稿不改，`输入摘要 4/4` 保持。
8. `scripts/check-doc-refs.py`：**扩展 `机制稿` 前缀**（并新增列举继承规则与多文件参数）；本文纳入该脚本自检。
9. `task-retrospect`：**登记为独立机制操作 `task.retrospect`**（机制稿 §11.3、§5.1 同批），触及已审稿，须同批复审。
10. 打包脚本：**不入发行清单，只把输入输出与版本同步义务写进发行说明**（文档 §1.5）。

## 第二轮范围变更说明

第 7–9 项决定新增了对 `docs/workflows/wf-framework-mechanism.md`（3 处、6 行）与 `scripts/check-doc-refs.py` 的改动，属人明确授权对本阶段原范围（只新增实现方案文档）的扩大；charter/设计稿/索引/来源说明四份受保护文件仍未改动，`输入摘要 4/4` 复核通过。
