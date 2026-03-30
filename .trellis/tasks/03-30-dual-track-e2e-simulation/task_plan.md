# 连锁门店巡检系统试运行交付任务拆解

## 概述

本任务围绕 `trial_authorization` 轨道完成试运行交付、授权管理、最终移交与交接文档准备。

## 任务拆解 Checklist

- [x] T1 试运行版交付任务
- [x] T2 试运行授权状态与到期行为验证
- [x] T3 永久授权切换任务
- [x] T4 源码移交任务
- [x] T5 控制权移交任务
- [x] T6 密钥配置移交任务

## 文件修改清单

- `assessment.md`
- `prd.md`
- `design/**`
- `task_plan.md`
- `delivery/test-report.md`
- `delivery/acceptance.md`
- `delivery/deliverables.md`
- `delivery/transfer-checklist.md`
- `delivery/retrospective.md`

## 验收标准

- [x] 试运行授权条款在 `assessment.md` 中完整记录
- [x] 设计文档覆盖核心功能、授权状态与最终移交边界
- [x] 任务执行矩阵将支付后移交任务与普通交付任务分离
- [x] 交付目录包含测试、验收、交付物索引、移交 checklist、复盘

## 外部项目交付控制（如适用）

- `delivery_control_track`: `trial_authorization`
- `delivery_control_handover_trigger`: `final_payment_received`
- 尾款前保留控制范围：测试环境、最终部署控制权、生产密钥、管理员账号
- 条件导入资产：
  - `spec.universal-domains.project-governance.authorization-management`
  - `spec.universal-domains.security.secrets-and-config`

## 依赖关系

- 前置任务：`assessment.md` 明确试运行授权轨与最终移交门禁
- 阻塞任务：尾款到账前，T3/T4/T5/T6 不得实际移交
- 并行任务：T1 与 T2 可并行；T4/T5/T6 在支付触发后串行推进

## 执行安排

- 当前可开始任务：无（本次模拟已完成）
- 等待中任务：无（本次模拟已完成）
- 推荐并行组：T1,T2
- 串行主链：T1 -> T2 -> T3 -> T4 -> T5 -> T6

## 任务执行矩阵

| 任务ID | 前置任务 | 当前状态 | 开始条件 | 等待原因 | 并行属性 | 冲突说明 |
|--------|----------|----------|----------|----------|----------|----------|
| T1 试运行版交付任务 | 无 | 已完成 | PRD 与试运行授权条款确认 | 已完成，无等待 | 候选可并行 | 与正式移交任务冲突，必须先完成试运行验收 |
| T2 授权状态与到期行为验证 | T1 | 已完成 | 试运行版可部署并可模拟到期 | 已完成，无等待 | 候选可并行 | 与永久授权切换任务串行，避免验证口径混淆 |
| T3 永久授权切换任务 | T2 | 已完成 | `final_payment_received` 已确认 | 已完成，无等待 | 依赖不可并行 | 与试运行状态验证冲突，必须在支付后执行 |
| T4 源码移交任务 | T3 | 已完成 | 永久授权切换完成且客户确认接收人 | 已完成，无等待 | 依赖不可并行 | 与控制权移交串行，先交源码和构建材料 |
| T5 控制权移交任务 | T4 | 已完成 | 源码移交完成且交接会议已安排 | 已完成，无等待 | 依赖不可并行 | 与密钥配置移交相关，需统一交接窗口 |
| T6 密钥配置移交任务 | T5 | 已完成 | 控制权移交清单确认并进入安全通道交付 | 已完成，无等待 | 依赖不可并行 | 与源码公开交付冲突，必须通过安全通道单独完成 |
