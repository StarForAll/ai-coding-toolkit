# backlog：dogfood 二轮修正（11-21）遗留跟进项

> 来源：2026-11-21 任务 `11-21-wf-dogfood-fixes-round2` 收口前的第三轮外部审查
> （两份报告）。本轮已修项见该任务 implement.md「第三轮审查补充」；
> 本文件只登记**裁决延后**的项。处理时机：下一轮 wf 任务（建议与 0.1.5 同批）。

## 1. help 覆盖 21/48（P0，下一轮优先）

- 现状：`COMMAND_HELP` 21 条 vs `COMMANDS` 48 个；`wf help writer` 等仍报
  `WF_PATH_INVALID unknown command for help`（cli.py 的 help 分支）。
- dogfood 对应失败：AI 现场读源码才知道怎么调入口（最贵的"发现路径"成本）。
- 处置建议：补齐 27 条缺失条目（writer/writer-handover/status/gate/task-rework/
  task-attribute/task-replan/review-accept-unknown/run/dep/spec/enable/verify/version），
  并加注册表断言（`COMMANDS - set(COMMAND_HELP)` 为空），防回潮。

## 2. vendor_dirty 消费点（P1）

- 现状：`.wf/**` vendor 边界正确（不进交付/材料/指纹），`vendor_dirty` 只在
  status/judgments 展示，无门禁、无人确认消费点——dogfood"业务任务里修框架"
  路径仍可静默重演（4/5 时间耗在此）。
- 处置建议：task-check/archive 的 facts 出 `vendor_dirty` + 一次人确认记录
  （不新增命令/skill、**不做硬阻断**——"该不该回源仓库"仍是人判）。
  登记链走机制稿 §1.1（写者/消费点/失败出口）。

## 3. 主会话五轴复核粒度（P1，设计变更）

- 现状：`validate_main_review` 要求五轴全填 + 每轴 basis，草稿只给 blocking 占位
  （review.py）。复杂任务 3 轮 = 40 条 basis 的"满足格式"空转。
- 处置建议：保留"主会话判 pass 必须自己给依据"，允许与采信报告一致的轴用
  `sources` 表达、basis 一句指向；劳动集中到有分歧的轴。需改机制稿 §9.2 与
  `review.py` 校验（含夹具）。

## 4. §1.1 内容归位（P2）

- "执行器解析（唯一定义）/命令启动/分支边界"三段属机制契约，放在 §1.1
  核心原则表后冲淡 AI 指导要点；建议移至 §1.3 或机制稿（同步索引与引用方）。

## 6. 第四轮审查延后项（2026-11-21 收口前登记）

- **未知参数静默忽略**（P0 级风险）：`Args.used`/`rest()` 定义但未消费，`stop --prevew`
  拼错会静默走真实处置。处置建议：`main()` 对各命令注册的合法 flag 集做残留校验，
  未知 flag 报错并给"最近似拼写"提示；需逐命令登记合法参数表（中等工作量，涉及
  全部命令与既有夹具调用面）。
- **缺 usage 类原因码**：`WF_PATH_INVALID` 兼作"缺参数/未知子命令/help 不存在"
  （lib 内 126 处中约 55 处），码级 exit/prohibited_repairs 指向"路径 glob"话术，
  误导 AI 去改触碰面。码表闭集只增不改——新增 `WF_USAGE_INVALID` 类码并迁移
  用法类错误；需机制稿码表登记 + 消费方迁移。
- **现场出口大面积缺失**：check/review/spec/tasks 合计 387/588 处错误无 next_/exits。
  最痛实例：review-import"摘要已锁定"缺"开新一轮 review-launch、旧报告保留原轮"出口。
  处置建议：按"阻断三要素"逐码补齐高频路径（可按 dogfood 触碰频率排序分批）。
- **curation.py 死模块**：全树无 import，实际逻辑在 tasks.py/spec.py 内联；发行清单
  仍投放。处置：删除 + dev-manifest 去登记 + 重建发行。
- **发行件引用未发行上位稿**：skills/workflows 内 16 处"机制稿/设计稿 §x"动作型指针
  在目标项目不可达（且设计稿无 §4.9）。处置：改为就地可执行文字或指向 `.wf/workflows/`
  本地文档；涉及 wf-continue 异常归档行、maintenance-flow 锁异常行等。
- **repo_rules 确认时点**：确认只在归档提交发生，"环境级规则变更确认"保护不到
  变更生效前。属设计变更（改前确认/写入前置阻断需回机制稿 K6 定义），本轮不改授权模型。
- **范围内缺陷的 blocking 引用死路**：wf-review-action 要求"批准判据外但仍在批准
  触碰面内的缺陷继续修、不降级"，但 blocking finding 必须 cite 已批准集合的
  assertion_ref（review.py assertion_index/K4c）——无对应判据时缺陷无法进入审查
  记录。处置建议：扩展 assertion_index 增加"批准触碰面内路径"类引用（如
  `t:<path>`，与既有 `p:` 证据引用同族），机制稿 K4c 同批修订；属机制变更，需人裁。

## 7. 已裁决不做（勿重复提议）

- 同轮报告条件重导入（未被引用且未判定时允许 supersedes）：用户 11-21 裁决
  **维持"导入后不可覆盖"声明边界**，本 backlog 不重开。
- `upgrade --apply`：第三轮能力桩，属已知交付计划；0.1.3→0.1.4 已按
  "卸载重装/整树手工投放"如实声明。
