# C3 缓存、处置与观察实施验证切片

> planning / 未执行。前置C1/C2验收通过，尤其owner/state/receipt/分类和单controller接口；依赖未满足不启动。

## 必读输入与进入条件

读本目录三件套，再读父 [activation.md](../11-16-wf-runner-lifecycle-contracts/activation.md)、[共享设计](../11-16-wf-runner-lifecycle-contracts/design.md)第4–5.1节和spec；获批后按实际平台启动本项。隔离与命令见 [verification-plan.md](../11-16-wf-runner-lifecycle-contracts/verification-plan.md)。

## 有序实施

1. 核工作树/C2接口，逐W1–W5/O1/F1列日志/磁盘/真实入口证据。先盘点模板fixture marker与发行新material-owner的生产/读取/finish/空壳/删除出口，不把模板staging误当无主，不为旧发行残留伪造marker；两缓存摘要时机分别验证。
2. 先写真实run_all顺序反例，再按总开关+scope+有限枚举加checkpoint；未开总开关不生效、非法点/越界首次写前拒绝，发布器精确退出后真从run_all/ensure重入，不外部kill竞速。
3. acquire收拢恢复→验证/迁移/命中→发布，普通入口坏journal保留拒绝。发行material-owner按父设计先原子落再build/rename，材料/marker确认清理后才删journal；异常无journal也按同一归属流程收尾，不吞错。核marker-only壳、坏key、无关key/sibling、readonly lookup及重复收尾。
4. 按已确认R10统一实现inventory归属等级、safe-legacy与manual-retained：缓存坏journal固定路径完整key reset、unproven历史缓存在路径/UID/锁/活引用等硬检查后，逐次额外TTY+集合摘要确认放弃；可验结果/fixture保持原门禁。选择格式同一处定义，报告先建、锁内整批复验；不补cleaned/owner、不杀进程、不从坏journal取任意路径，不把策略批准当成本次材料已获确认。
5. 处置矩阵含plan-only/早死/死active/unknown/failed/KEEP、O1可验与旧无marker、坏journal/两代不可验/marker-only壳。自建PTY核确认/拒绝/EOF/非TTY/漂移/忙锁/活引用/非本UID/越界；测试完整reset后同key真实重建、其他key不动、部分删除保留journal、报告失败停下及新报告幂等。结果归属不足和检查能力不足仍拒绝，不能按缓存unproven规则扩到任意目录。
6. 将C2的disabled/not-enabled调用位切为enabled，仅本次实际使用根各一次浅扫，计划/内嵌/per-case仍零次；C3接线前不读取根也不输出计数。stderr分类/未测容量/完整inventory命令，不以partial推cleaned、不因坏无关材料阻当前key。
7. README写三类完整流程：结果保留、坏journal完整key reset、历史unproven精确放弃；各含盘点/集合/存证/身份停止/TTY/报告/重盘点，cache再真重建。可恢复journal优先正常恢复，坏证据不要求手修，不伪owner；替换错误结果owner/无锁删锁示例。验证前置片段实际做marker检查与净化，不能只在文案要求。

## 本项验证与交付

1. V-C3定向→V-T0；maintenance/PTY新测试入实际发现范围，safe-legacy可验/自动拒绝与manual-retained新授权分开；含C2早死/KEEP、material-owner、旧unproven、坏journal完整reset与同key重建。env净化验证防继承故障误入上述正例。
2. V-CONTRACT完整慢契约和C3七场景、observe次数/根集合、inventory/retirement；回归C2取消/receipt/最终发布与C1公开parser。
3. 按真实输入依赖更受影响suite审计和source coverage/fake-tree；V-DOC首条含本项/父工件和README/spec；必要candidate按V-CANDIDATE，不改过滤声明绕失败。
4. validation记录AC04–06/17–19和AC09/15/20维护分片的反例/正常/命令rc/证据/处置结果；审阅diff、owned进程/FD/锁，未知现场按流程保留。
5. 父最终组合执行V-FULL/V-CANDIDATE/V-RELEASE/V-DOC，不用定向绿替代；未授权不commit/archive、不清真实用户缓存，协议重大变化先修共享设计。
