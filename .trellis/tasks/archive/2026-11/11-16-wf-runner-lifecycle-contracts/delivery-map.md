# 父子任务交付、依赖与分批验收

> 实施与验证已完成，任务状态以 task.json/validation.md 为准；提交与归档未执行。拆分只改变交付组织，不缩减父任务 R1–R10 / AC01–AC20。父任务 P1 优先处理清理/恢复正确性；子任务保持各自风险等级。所有新工件仍须用户审查后才可实施，不因创建子任务自动授权。

## 1. 任务树与责任

| 任务 | 范围/所有权 | 完成判据与父 AC | 明确依赖 |
|---|---|---|---|
| 父：11-16-wf-runner-lifecycle-contracts | 共享PRD/design/inventory、逐AC总账、最后跨子项集成；不直接改实现 | AC15/AC16最终全量/串并/both/candidate与所有子项证据合并；不可用子项单测总数替代 | 三个子项通过；收口前再核实际组合工作树 |
| C1：[CLI](../11-17-wf-runner-cli-contracts/prd.md) / P2 | repro/cli.py、公开run.sh解析与CLI测试；不动controller/owner/state | R4，AC11–12的公开解析/兼容，T0+真实无副作用测试 | 独立，可先验收；之后C2扩展内部frame须回归C1，不重写公开parser |
| C2：[生命周期与controller](../11-17-wf-runner-controller-lifecycle/prd.md) / P1 | execution/runner_cleanup/resource_lifecycle/results_gate/results_summary、owner/state/receipts、run_all/repro控制交接、local/结果复用/摘要与测试 | R1/R3/R5/R6/R7/R8，AC01–03/07–10/13–14；AC12内部frame及AC15/20生命周期部分；有/无scope路径、unit JSON桥接但lines五列不改、lease初始化、child/root分域、metrics身份与完整输入链、信号FD实证 | 接受C1公开parser；先定本组协议再开放C3，不把未来observe/retire伪报完成 |
| C3：[缓存与维护](../11-17-wf-runner-cache-maintenance/prd.md) / P1 | template_cache/wf_test_release恢复与checkpoint、三个材料inventory/retire/observe适配器、root observe接线、存量文档与测试 | R2/R10，AC04–06/17–19；AC09/15/20的维护消费者部分；恢复七场景、safe-legacy与manual-retained明确处置、新旧材料/观察根集合 | 依赖C2的owner/state/receipt/分类接口，不能并行改协议；接线需回归C2的最终出口与取消 |

AC16由父最终执行；AC15/20按上表分片收据并由父核“所有消费者”。复用/轮转的自动拒绝由C2交付，历史清单退役、新协议保留现场的TTY明确放弃和残留提示由C3交付；两者分别验收但父不能在C3未完时声称AC09/17/18整体闭环。R5与controller/真实清理结果强耦合，未单拆“只把pending改published”的子项，避免先修表面状态后再搬发布边界。

## 2. 串行交付与批准

推荐C1→C2→C3→父最终集成；依赖不是靠task.children表达，而以上文与各子implement为准。每次实施先按[activation.md](./activation.md)核验实际平台、模式与上下文，只start具体已获批子项，父保留规划/总账。各子[CLI执行切片](../11-17-wf-runner-cli-contracts/implement.md)、[controller执行切片](../11-17-wf-runner-controller-lifecycle/implement.md)、[维护执行切片](../11-17-wf-runner-cache-maintenance/implement.md)各自有序，命令统一引用[verification-plan.md](./verification-plan.md)，不再追溯父implement旧章节。

每个子项有独立验证记录与可审查diff。批准本套规划可以覆盖上述固定顺序，但规划阶段的启动门控见 activation.md；本轮已按 DSH inline 启动并完成实施/验证，提交与归档仍未执行。若后续改变核心controller/证据域/权限范围，先修共享方案重新审查；普通已授权实施细节不反复索要权限。没有commit/push/PR授权，不以“分批交付”为由自动提交或归档。

## 3. 检查点与回退边界

- C1完成：记录parser行为前后对照、公开参数/路径/零副作用证据。C2可消费其接口，不能回退C1用户已接受的行为。
- C2完成：owner/receipts/state/summary/controller与全部writer/reader同批；不能只回退writer。含初始化os._exit(97)+shell/FD退出、finalize部分完成与片段真实净化证据，定向/真实root故障/T0/candidate验证；C3未完不冒报维护AC，既有缓存不回归红。
- C3完成：材料owner先于build、恢复/清理/维护CLI+observer同批；manual-retained是逐次人授权，不能改变C2自动清理许可。W1–W5/O1/F1、坏journal整key reset→真重建、unproven精确确认与拒绝/T0/慢契约通过。R10策略范围已于2026-11-17确认，分支纳入C3；该确认不替代每次额外TTY/摘要确认或整套实施批准。
- 父集成：基于最终组合内容跑一次全量green串并对拍、both、candidate和仓库要求校验；最后一次修改后受影响检查必须重跑。分片通过不直接等于父通过。

需要回退时先核当下diff与各子边界，只移除本任务确认的内容；不使用reset/clean/通配删除或丢弃其他工作。C2协议升级写出的新目录在旧脚本下不得重新运行：先保留并改新路径，不能为回退批量补旧owner。方案不承诺跨多文件写入事务或任意未提交工作树的自动回滚。
