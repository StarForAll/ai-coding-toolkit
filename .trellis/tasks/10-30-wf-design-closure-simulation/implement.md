# Execution Plan

## Planning gate

- [x] 用户已允许创建 Trellis 任务并限定 /tmp 模拟、不正式实现。
- [x] PRD、design、执行顺序已成形，需求已收敛，无产品决策待澄清。
- [x] 向用户展示最终规划摘要并取得其随后明确批准。
- [x] 批准后 `task.py start --allow-empty-context`；Codex inline，不派发子代理、不配置 JSONL。原命令因空清单拒绝，按显式支持的 inline 入口开工。

## Execute

- [x] 修订设计 §5.6、§8.2，保留 §6.5；同步索引。
- [x] 枚举新跨节引用及实际语义消费，保存到 research/revision-review.md。
- [x] 在 /tmp 建临时项目、最小控制模拟与行为测试，跑正常闭环及 R1–R3 正反例。
- [x] 用独立 Python 进程模拟知识消费者，明确未运行真实 AI 新会话。
- [x] 保存模拟代码重建材料和逐项结果至 research/，清理本次临时根及本会话产生的机检器字节码。

## Check

- [x] `/softwares/python/bin/python3 scripts/validate-wf-design.py`。
- [x] `git diff --check`；审阅正文/索引 diff、新任务产物和 staged/untracked 状态。
- [x] 断言 §6.5 与起始 HEAD 内容相同；核对词面与语义消费两列。
- [x] 按 trellis-check 核对本轮范围、证据边界与结果。
- [x] 报告明确模拟成功不等于框架实现验收；未独立审查、不宣称定稿。

## Finish boundary

模拟阶段未获本仓库提交授权，保留了改动供审阅。用户随后明确授权按方案提交本任务路径、归档并记录会话；按工作提交 → 归档提交 → 会话记录提交顺序执行，不推送，不纳入 `.agents/skills/grill-me/` 或 `skills-lock.json`。临时仓库实验提交仍仅为夹具验证。

已按 trellis-update-spec 复核：本轮没有新的正式 API、schema 或通用实现约定，现有修订门禁已覆盖模拟证据与运行验收的区别；本次结论留在任务研究材料，不重复新增长期 spec。
