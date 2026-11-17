# wf repro CLI 参数终止性与兼容修正

> C1 / P2 / planning。父任务：[共享PRD](../11-16-wf-runner-lifecycle-contracts/prd.md)、[共享设计](../11-16-wf-runner-lifecycle-contracts/design.md)、[交付树](../11-16-wf-runner-lifecycle-contracts/delivery-map.md)。本项轻量，PRD与[执行切片](./implement.md)足以承载，不另复制复杂设计；不因建task获准实施。

## Goal / 范围

修正 repro/run.sh 公开有值参数缺值时 shift 2 不前进的死循环；公开选项统一由拟新增 repro/cli.py 解析。负责父R4/AC11–12公开解析部分；基线 c0c3a167，证据为 repro/run.sh:65–82 与前序 timeout=124。仅改公开parser、shell消费解析输出、对应测试/helper登记与直接文档。不改controller/owner/state/receipt、内部frame、缓存恢复或产品政策。

## 兼容契约

合法重复group、最后值规则、含空格路径、dev/candidate模式、--list、--help与公开错误码保持明确；内部frame仍先由runner_protocol处理，不让公开parser吞保留参数。非法/空/缺值须在scope写、取锁、build/worker前确定非零，禁靠set -e或额外超时杀进程掩盖循环。

## 验收

- [ ] 每个有值选项缺/空/后继选项都退出，真实scope/锁/cache无副作用，短deadline仅证明终止性。
- [ ] 合法公开参数保真，输出shlex数组安全；未知/保留参数明确拒绝。
- [ ] 定向行为反例在旧parser可复现；T0及公开CLI真实入口检查通过，记录本项diff与证据，不能以检查总数销账。

## 执行、依赖与边界

无实施依赖，可先完成；推荐顺序C1→C2→C3。批准后按父 [activation.md](../11-16-wf-runner-lifecycle-contracts/activation.md) 核验实际平台并激活本项；先写行为反例，再实现，最后核新增helper身份/fake-tree及T0；不启动父任务。C2随后扩内部frame须重新回归本项公开契约。无commit/push/PR/归档授权；本轮仅文档，未跑实现测试。
