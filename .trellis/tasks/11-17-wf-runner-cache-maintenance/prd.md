# wf 缓存恢复与存量处置契约

> C3 / P1 / planning。共享：[父PRD](../11-16-wf-runner-lifecycle-contracts/prd.md)、[父design](../11-16-wf-runner-lifecycle-contracts/design.md)、[交付树](../11-16-wf-runner-lifecycle-contracts/delivery-map.md)。未启动实施。

## Goal / 范围

负责R2/R10：模板获取先恢复后命中/清理、两缓存finish保留失败索引、确定性W1–W5/O1/F1、历史与新协议保留材料的inventory/明确处置、root浅层observe。AC04–06/17–19和AC09/15/20维护消费者部分。

依赖C2的owner/run-state/receipt/分类与单controller接口；不能把C2尚未稳定的协议边写边改。文件包括template_cache、wf_test_release、fixture_scope维护CLI/产物消费、root observe接线、对应测试/README/spec及条件审计。沿用现有恢复算法，明确两缓存新摘要确认时机不同；不重写监督器/扩大同UID恶意威胁模型、不清真实用户存量。

R10规划决策已于2026-11-17由用户确认：历史wf归属无法证实的缓存材料允许在路径、UID、锁、活引用等硬检查通过后，以额外TTY及所选集合摘要确认显式放弃。该分支纳入本项验收；归属仍标unproven，每次操作都须确认，自动/safe-legacy路径仍拒绝，结果/fixture的owner要求不变。此处确认的是策略范围，当前仍未授权启动实施或清理真实缓存。

## 验收

- [ ] W1–W5五恢复场景、O1 journal前孤儿、F1材料清完journal仍在，共七场景/六点逐行实证；模板从run_all、发行从ensure重入，点未到达不算覆盖。
- [ ] 新事务删除失败不丢索引；重复恢复核字节/marker/meta/root，无关key/sibling不动。模板O1按已存在fixture marker判定，不额外要求meta；发行material-owner先于build/backup rename，marker-only壳/构建中断/部分删/finish重入均有归属和出口，正式发行owner不改。旧无marker不补owned。
- [ ] 三材料inventory零写，safe-legacy逐判据核严格旧结果/可验孤儿/空rmdir壳。manual-retained覆盖可验结果/独立fixture及坏journal的完整缓存key reset；unproven历史缓存必须额外TTY确认unproven-cache，名称只用于发现，不能自动/safe删。坏journal不修、不信路径，材料/marker先清、journal最后移，下一次真实入口正常重建。原KEEP/早死等处置保持；结果无owner、非TTY/漂移/忙锁/活持有者/能力不足/非本UID/越界等硬拒绝，外部报告先建、部分失败停止、幂等重盘点，真实用户存量不动。
- [ ] observe只由真实root维护前一次调用、仅本次使用根，计划/内嵌/per-case零次；浅层标not-measured/partial不授删除权，用户显式inventory才完整大小/摘要。
- [ ] 回归C2信号/FD/最终发布、C1公开parser、T0/慢契约/缓存窗口及维护矩阵，报告本项validation；最终父AC15/16集成未执行则明确未完成。

## 授权边界

用户批准后按[共享激活门控](../11-16-wf-runner-lifecycle-contracts/activation.md)核验实际平台再start本项；必要协议变动先修共享设计和所有消费者。当前只做规划，无commit/push/归档授权。
