# 父任务集成与最终验收计划

> 实施与验证已完成，等待用户批准提交/收尾；详细证据见 [validation.md](./validation.md)。
> 下文的复选框保留为规划核对项，不代表任务状态；实际完成/未运行/限制一律以 validation.md 为准。父任务负责共享契约、集成及最终验证；实现按交付树由C1/C2/C3独立完成。子任务的顺序清单在各自目录，不再引用父计划中已删除的实现章节。

## 0. 激活与共同前置

- [ ] 用户批准最新共享设计、交付树及相应子项后，按 [activation.md](./activation.md) 在实际实施会话核验平台/模式/上下文，再启动有责任的子任务；父任务不直接激活改全包。
- [ ] 按 [verification-plan.md](./verification-plan.md) 第1节准备owned scope、pycache及逐CLI写入隔离；实施时已按本节执行命令；所有子项和父集成均受此规则约束。
- [ ] C1无依赖；C2依赖C1公开解析接口；C3依赖C2身份、receipt和controller分类接口。依赖未验收，不启动下游；不得靠JSONL或children列表隐含调度。

## 1. 子项成果与跨层检查

- [ ] C1以自己的PRD/implement完成公开参数终止性、兼容和无副作用证据，使用验证目录V-C1/V-T0；不得提前改C2/C3协议。
- [ ] C2完成controller/身份/receipt/local/摘要、初始化真死亡与finalize部分完成；验证前置片段必须实际验marker/净化环境，含无scope兼容、五列+unit JSON、metrics等现有约束。用V-C2/V-T0/V-CONTRACT，不要求C3未来功能。
- [ ] C3完成材料归属、恢复、safe-legacy与显式manual-retained、坏key reset后重建及observe/README；R10的unproven缓存人工放弃范围已于2026-11-17确认，按硬门禁及每次额外TTY+摘要确认实现。用V-C3/V-T0/V-CONTRACT，再回归C2实际最终出口，不自动清真实存量；本轮已在 DSH inline 下实施并记录验证。
- [ ] 父按AC01–20合并各子证据，核producer→交接文件→reader→最终结论的完整身份链；逐schema与保留的lines五列契约核所有消费者、错误及处置出口。子项绿不自动等于父绿，不把输出锚点当清理授权。
- [ ] 共享协议发生变化时先修共享设计和受影响子计划，重大边界变化重新交审，不在子实现里追加私有兼容路径。

## 2. 最终组合验证（全部子项完成后）

按 [verification-plan.md](./verification-plan.md) 的精确命令和前置，依次执行：

1. V-T0，全量作者单测；V-CONTRACT，完整实际入口慢契约/冒烟（含已实现的C2/C3全部新断言）。
2. V-FULL：full green并行、full green串行、full both；比逐ID rc/status/phase及每代receipt/state/summary，不以总数或耗时证明等价。
3. V-CANDIDATE，在scope内创建候选并运行现有candidate-clean完整路径；受影响suite审计按现有生成器更新，不手写通过。
4. V-RELEASE：build-wf-release.py --verify --verify-token-parity，仅临时区重建对拍，不用 --version 重建正式树掩盖差异。
5. V-DOC：check-doc-refs.py（实际工件及默认文档）、validate-wf-design.py、validate-skills.sh、trellis-library/cli.py validate --strict-warnings；核README/spec与owner、结果处置文案一致。
6. 最后一次编辑后重跑受影响检查，读实际diff/untracked/staged、父子任务状态与owned进程/FD/锁；skip/fail/not-run据实记父validation，不把能力缺失算pass。

具体命令只维护在verification-plan的V编号段；子implement引用对应V编号和自己的实施顺序。命令目录不是“未来自行补测试”的替代品，新断言必须由负责子项加入实际发现范围并证明旧反例失效。

## 3. 停止、回退与交付

- [ ] 范围内AC/处置出口未闭合，报告未完成，不擅自把问题降成known-gap；外部能力边界按事实单列。
- [ ] 回退需依据实际路径所有权检查当前用户diff，不能reset/clean或回掉兄弟任务成果；新协议现场保留，不补旧owner/cleaned。
- [ ] 只有AC全关闭和最终组合通过才交付；无需为已批准固定顺序每一步重新索权。规划本身仍须后续明确批准才可实施；不擅自commit/archive/push/PR。
