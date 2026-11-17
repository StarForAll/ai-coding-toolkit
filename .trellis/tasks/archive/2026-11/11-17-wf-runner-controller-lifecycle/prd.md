# wf 命令证据与 controller 生命周期收口

> C2 / P1 / planning。共享规范：[父PRD](../11-16-wf-runner-lifecycle-contracts/prd.md)、[父设计](../11-16-wf-runner-lifecycle-contracts/design.md)、[交付树](../11-16-wf-runner-lifecycle-contracts/delivery-map.md)。本项三件套引用共享规范中的精确责任，不复制第二套协议。

## Goal / 范围

负责R1/R3/R5/R6/R7/R8与资源/证据跨层契约：同一execution.py C进程runner_control收口，managed/root/standalone全命令receipt，owner schema2初始化、run-state、本地资源保留、复用/轮转、full/repro最终摘要。AC归属：01–03/07–10/13–14；12内部frame和15/20生命周期消费面。基线证据沿父PRD，不把新方案声称已实现。

仅改execution、runner_cleanup、拟resource_lifecycle、fixture_scope生命周期部分、run_all/repro控制交接、worker/harness、summary、相关测试/身份/fake-tree/直接文档。standalone receipt采用父design规定的log同目录隐藏唯一JSON sibling，并盘点repro glob、prepare、summary、candidate audit等消费者；不新增commands子目录。采用C1公开parser接口；不实现C3缓存恢复/maintenance CLI/observer，也不引入新controller进程或通用注入框架。

## 验收

- [ ] runner_control的真实full/独立repro/内嵌路径通过，目标signal policy/rc、FD、mask恰一次对拍；只有C最终发布。
- [ ] managed/root/standalone分别先登记再启动，写失败不启动，坏managed不可fallback；API参数与rc/status/seconds兼容；审计只引用当前command证据。
- [ ] 盘点execution直接调用者/log路径类型；有scope核scope，无scope按显式log真实父目录锚定，保留安全创建缺失父目录与库异常语义。普通无scope TemporaryDirectory/用户可写目录/相对log与目标cwd不同保持成功；坏scope/权限/类型/链接及scope越界拒绝，不能全迁scope假装兼容。standalone hidden sibling不进case枚举；prepare仅在许可后清。
- [ ] run_one为install或fixture/init及test逐命令显式传唯一--result；既有`<unit>.test.log.json`串行附加unit_execution schema1（prep失败也有明确终态），command_evidence列本次引用。lines保留五列，audit显式接预期invocation_id核阶段/ID/结果行，旧JSON或旧绿行不冒充当前；unit JSON发布失败非零。旧receipt只留历史，不扫删。
- [ ] lease持锁一次调Python begin_run写意图/state/prepare，三个点只在helper os._exit(97)，不raise；shell保留97退出、不接管/清理。首次/计划转执行/重用×三点等待public整体退出，核身份现场、实际FD/lease释放与新入口拒绝降级；controller不重做，正常cleaned可复用。
- [ ] retained_paths对每个local根给出owned结果锚点或独立fixture marker；HOME同log重复调用不抹前次保留目录，direct harness stage先归属后内容，沿用fixture租约并验证独立/继承/忙锁/锁序。C3可处置独立根，C2不伪报维护已实现。
- [ ] 真实root按父design第5.2节注入聚合异常/非法返回/删除与发布失败、G/S固定点故障，不依赖sleep/外部kill；正常对照、T0、慢契约及相关candidate回归有证据。
- [ ] delete-oserror首删前与delete-after-first真实已删一项再失败分验；用例实际有至少两项owned资源，removed/failed/not-attempted及marker/retained_paths对账，失败即停、不重建/重删、原rc保持；单根部分rmtree失败另验。验证片段的marker检查/逐调用环境净化与文字一致，普通命令不继承故障/locator。
- [ ] 慢契约teardown证据写失败不吞：class-cost报告失败显式记录，先完成进程/FD/宿主保护断言；证据失败、leftover或host变化时保留scope和诊断，禁止先rmtree再断言或以空报告/正常rc掩盖。
- [ ] 内层不聚合root started；children-only读取投影由同一lifecycle分域，正常无常驻unknown，最终root缺失/unknown仍拒绝。full/repro摘要与返回值一致；full metrics schema1原子交接、核本代ID与输入摘要，gate/cleanup只由controller的当前证据派生。旧/缺/半写/错类型/摘要不符与写失败均有定向和真实入口反例；全部字段读回，保留债务/卫生与正常复用对照。父AC逐项validation，不冒报C3。

## 依赖与授权

实施接受C1 parser契约；C3依赖本项owner/receipt/分类/最终化接口。共享设计变动先修父设计和所有消费者，不能在本项自行选另一controller架构。用户批准后按[共享激活门控](../11-16-wf-runner-lifecycle-contracts/activation.md)核验实际平台才激活本项；本轮所有实现和测试未执行，无commit/push/归档授权。
