# 两 agent 审查的裁定与实际修正（2026-11-09）

**判据**：以质问角度核每一条（先读码/跑 grep，不信审查结论）；修正只治根因，不打补丁；
不引入新问题；目标仍是"指导 AI 并放大其能力"，不是加刚性枷锁。

## 逐条裁定

| 审查条目 | 核实结果 | 处置 | 提交 |
|---|---|---|---|
| **b-P1 抽样门禁死锁**（门禁读 `sampling.frozen.picks`，`freeze` 写扁平键，`picks` 从不落盘） | ✅ **属实，且是最重的一处**。`freeze` 写 `{seed, events, frozen_at}`；`picks` 只进回显；`record_result` 零调用方 | **根因修**：`sampling.frozen()` 定为唯一形状，新增 `selection()`/`record_picks()`；门禁与 CLI 只经访问器；`sampling pick` 在锁内落盘选样；门禁出口改**一跳**（`--freeze`） | `fbfae48` |
| **b-P2 evaluate/reviewed/prefs 无入口** | ✅ 属实（三个库函数 grep 无调用方） | 补 `sampling evaluate`、`sampling reviewed`、`prefs set|show`，均走锁 + 动作记录 | `12af742` |
| **a-P2 锚点异常静默成"无变化"** | ✅ 属实（`return []` + 预览仅在非空时显示） | `_anchor_part_names` 失败返回 **`None`**；预览区分两态：`[不变] 字段清单不可得（锚点计算失败）；不代表没有变化` vs 正常照列 | `12af742` |
| **b-P5 三类事件池恒空** | ✅ 属实（`fix_scope`/`standard_changes`/`repo_rule_files` 硬编码 `[]`） | 从记录派生：扩面/标准变更 ← judgments；repo 规则文件 ← `authorize.repo_rule_paths` | `6f50d02` |
| **b-P5 预览缺「偏好行」** | ✅ 属实 | 骨架带 `prefs`（只在本机），预览照实显示 `[偏好] …` | 本轮 |
| **b-P6 .gitignore / README 旧路径** | ✅ 属实 | 改为 `docs/workflows/wf/` | `e9cd7ec` |
| **b-P4 上位文档漏登记** | ✅ 属实 | 机制稿补 `task.judge`、`task.sampling.freeze/evaluate/reviewed` 的主记录归属；§9.4 列 judgment 与 `task.sampling` 字段清单 | `e9cd7ec` |
| **b-P3 standard_drift 挂载点** | ⚠️ **部分采纳**：判定侧保持在 `decide`（v42 约束的是"产出 pass"），但导入侧也把漂移**标成事实**（`entry.standard_drift`）。不把阻断提前到导入，否则"导入 → 判断 → 判定"的正常顺序会被卡住，那就是新的死锁 | 事实双点可见、阻断仍只在产出结论处 | `e9cd7ec` |
| **b-P5 预览「判断质量对照/依据对照」缺失** | ✅ 属实 | **未做**：需要跨任务历史对照（v42 §5.3），属新机制，需先写进上位文档；已登记为遗留 | — |

## 结论

- 审查里 7 条实质缺陷全部属实并已修（其中 P1 是会**卡死每个任务**的死锁）。
- 1 条部分采纳并说明理由（P3），1 条登记遗留（判断质量对照），均为避免"为修一个坑引入另一个坑"。
- 共同根因：**形状/事实没有单一来源**（抽样状态、锚点清单、事件池）——三处都是"两处各自拼键"或"硬编码占位"。
  修法一律收敛到访问器/派生，不新增第二份真相。
