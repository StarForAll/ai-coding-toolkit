# C1 公开CLI实施与验证切片

> planning / 未执行。本项轻量；独立操作清单不包含C2/C3未来功能。

## 必读输入与激活

先读本项 [prd.md](./prd.md)，再读父 [activation.md](../11-16-wf-runner-lifecycle-contracts/activation.md)、共享design第6节CLI契约、scripts spec与 [verification-plan.md](../11-16-wf-runner-lifecycle-contracts/verification-plan.md) 第1节。获用户批准后按实际会话的平台分支激活本子项；不硬编码Codex/ZCode，不激活父任务。

## 有序实施

1. 核工作树和C1所有权：repro公开parser、run.sh消费、test_repro*.py及必要helper登记/直接文档；controller/receipt/缓存恢复不在本项。
2. 先补每个有值选项的缺/空/后继选项、重复group、含空格路径、--list/--help、保留frame参数的行为对照；非法调用在取锁/结果/cache写入前非零退出。
3. 实现唯一公开parser及shell安全数组消费，保持runner_protocol先剥内部frame；新helper进入proof输入/fake-tree，不造fake豁免。
4. 按共享验证目录依次V-C1、V-T0、V-DOC首条；每个真实CLI反例用case自己的owned scope，记实际退出和零写入事实。
5. 正常repro --list与非法缺参真实入口核对；不要求C2 controller故障或C3事务窗口已经实现。失败先诊断，不降验收求绿。
6. 本项validation按AC11/12公开分片记反例/正常/命令rc/evidence/diff；C2后续改内部frame还要回归本项。未经授权不commit/archive，C1通过不等于父完成。
