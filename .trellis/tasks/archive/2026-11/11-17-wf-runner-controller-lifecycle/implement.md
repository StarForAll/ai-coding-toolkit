# C2 生命周期与controller实施验证切片

> planning / 未执行。依赖C1公开parser已验收，不实现C3事务/maintenance CLI/observer。

## 必读输入与进入条件

读本目录prd/design/implement，再读父 [activation.md](../11-16-wf-runner-lifecycle-contracts/activation.md)、[共享设计](../11-16-wf-runner-lifecycle-contracts/design.md)第1–4.1/5.2/6–6.1节和spec。用户批准后按实际平台启动本子项；隔离与命令在 [verification-plan.md](../11-16-wf-runner-lifecycle-contracts/verification-plan.md)。

## 有序实施

1. 核C1接口和工作树，列AC01–03/07–10/13–14、AC12内部frame、AC15/20生命周期分片；建立producer/reader/删除者/错误出口表。
2. 先补receipt三域及有scope/无scope路径矩阵、started/finished写失败、owner初始化窗口；盘点direct API/CLI/audit/worker全部调用。普通TemporaryDirectory/用户可写目录、缺失父链、相对log与目标cwd差异不改成scope用例；坏scope/managed不得fallback，库异常语义保持。
3. 实现lease唯一Python begin_run、owner/state及消费者，意图先于state/prepare，正式记录前禁pyc。三个checkpoint用helper os._exit(97)，shell非零原样退出不清理；首次/计划转执行/重用逐点等待最外public终止，核现场及FD/锁实际释放、新入口不降级，controller不重复prepare。
4. 实现三域receipt/local pending及unit_execution JSON桥接：lines五列不改，run_one逐phase唯一--result，原unit结果附当前invocation/顺序引用/行投影，prep失败也写终态；写者串行，audit核预期ID不捡历史绿。local根先归属后内容，HOME唯一不reset旧保留根、stage有marker与租约；补direct/继承/忙锁/锁序对照。
5. 扩同C进程runner_control/CancellationScope，统一assess/finalize/summary/finished，去shell成功/EXIT删除及root cleanup聚合；同一child reader不含root，最终root终态显式传入。observe调用位在C2仅返回disabled/not-enabled且零扫描，C3未完成不能伪造计数；按共享design第6.1节实现metrics write/read、身份/摘要/必需字段、gate事实来源及summary input_evidence；成组更writer/reader/登记/fake-tree，保留债务与卫生，full/repro投影分别验证。
6. 按共享design第5.2节实现scope受限root/G/S与metrics有限故障，另加delete-after-first：真实setup至少两项owned资源，唯一角色序删除循环核第一项消失、第二项/后项保留及逐项报告；单根rmtree内部部分失败另测。不传任意路径/payload，不sleep/外部kill竞速，失败原rc保留、无成功/自动重试。
   同步修慢契约teardown：class-cost写失败显式失败并保留scope，先做leftover/FD/宿主保护断言再决定回收，不能先rmtree。
7. prepare/prune/bootstrap/teardown只消费完整许可。C3所需分类/处置建议接口明定，但不伪报未来manual-retained工具/observe已实现，也不为接C3恢复自动删除。

## 本项验证与交付

1. V-C2定向→V-T0；覆盖普通无scope/scope越界、库异常/父链、五列+unit JSON、metrics、children/root、初始化真死亡与finalize部分完成；teardown class-cost写失败/leftover/FD/host变化保留scope并非零；验证文档片段在定向层核marker先验和环境净化行为，不执行真实suite求此证据。新增测试进入发现范围，不用不存在测试名背书。
2. V-CONTRACT跑该时点既有完整类和新增C2真实root/初始化/取消用例、subset；C2 root断言observe调用次数=0且输出明确disabled/not-enabled，不读取配置根；尚未加入的C3 W1–W5/O1/F1/observe/retire不要求本项通过，不据此skip既有整类。
3. 回归C1公开parser和相关candidate/fake-tree/身份；suite字节变动才按现有生成器更新相应审计；文档改动跑V-DOC首条并加实际README/spec。
4. validation逐AC分片记pass/fail/not-run、反例/正常/命令/路径和实际diff；本项自动保留拒绝可验，未来C3人工处置AC仍未完成。父最终另跑V-FULL/V-CANDIDATE/V-RELEASE/V-DOC。
5. 核共享接口变动先修方案，未经授权不commit/archive，不回掉C1或用户新工作；owned scope的未知现场保留。
