# C3 设计归属与维护边界

> planning / 未实现。规范主体为[父design](../11-16-wf-runner-lifecycle-contracts/design.md)第4.1–4.3、5、5.1节；本项依赖C2结果身份/生命周期已通过。

- template_cache.acquire统一当前key恢复/迁移/命中/发布；坏journal仅阻当前key普通维护，readonly lookup拒绝。模板沿用_build现有fixture marker；发行staging/backup新增父design第5节的typed material-owner，先marker后build/rename，树消失后才移marker、journal最后删。它不是第二journal，不改正式发行owner/摘要算法；旧无marker不伪迁移。
- checkpoint按W1–W5/O1/F1共享表，不把六个代码点当五个场景；测试开关+scope+枚举，真实发布器退出后真实入口重入。无生产force开关/外部sleep-kill猜时序。
- 维护统一消费父design第4.2节的归属等级/授权规则。safe-legacy只收严格旧结果/可验marker孤儿/空壳；manual-retained覆盖owner可验结果/fixture与显式缓存key reset，历史unproven缓存须额外unproven-cache TTY授权，绝不改标owned/自动删。坏journal按固定路径构造完整key集合，不修原文件、不追坏引用，材料/marker全删后最后删journal；新入口可重建。路径/UID/活持有者/忙锁/必要能力等硬门禁不可覆盖，报告先建、部分失败停止，结果无owner仍拒绝。
- runner_cleanup.observe_roots在C2的runner_control固定调用位接线；三个observe适配器按实际根浅扫，stderr快照与inventory命令，不递归容量/不新增结果sidecar。
- 变更产物/目录消费者/fake-tree/proof identity/有字节变化suite的candidate审计同批同步，不能只加名称白名单。

回退：仅移除本项确定diff和接线，回到C2保守保留与旧缓存路径，不能打开自动删除未知材料；R2在回退后重新标未完成。新协议目录保留，真实用户缓存不自动迁移。
