# C2 设计归属与接口边界

> planning / 未实现。规范主体是[父design](../11-16-wf-runner-lifecycle-contracts/design.md)第1–4.1、5.2、6–6.1节，本文件限定本项责任；冲突时先修共享规范，不双轨实现。

- 固定落点 execution.py::runner_control，由main --runner-control调用；原C进程经原run监督G/S/W，直接调用runner_cleanup.assess_run/finalize和results_summary。CancellationScope贯穿观察（C3后接线）/run/finalize/publish，原目标signal policy先保存。没有独立controller/任意执行role，也没有shell第二成功出口。
- root-control由runner_control写.runner.json，managed写父collector，standalone写log同目录唯一hidden sibling；execution唯一处理started/finished，坏managed拒绝。lifecycle只从commands读取child，不追加root；内层原cleanup聚合分支移除，必要诊断显式children-only/nonfinal，最终root由controller传终态。
- standalone路径/枚举兼容依父design第2.2节；有scope受scope限制，无scope以调用者显式log真实父目录为输出锚点（允许安全创建缺失链），不是测试scope/清理授权。库保留异常语义，普通无scope成功用例不能靠改scope遮兼容。
- lease持锁后一次调用Python begin_run原子owner意图→active→prepare；三个初始化点在helper，失败不交接。controller仅接管，同ID核验，不重做begin_run/prepare。回退不能改旧owner冒充legacy。
- 初始化点严格os._exit(97)并flush到达日志，shell收非零后退出、不清理或启动controller；锁的shell副本只随shell结束释放，测试等待最外public及新锁探针验证。finalize按角色序唯一删除循环，delete-after-first确定覆盖第一项已删、第二项故障，报告部分完成并停；单根rmtree内部失败保留marker，不承诺回滚。
- full/repro共用最终publisher，角色投影不同；full metrics schema1由write_metrics原子交接、read_metrics核预期本代ID/root/role与当前输入摘要，summary schema3记input_evidence。最终gate/cleanup不采shell计数；旧/缺/半写输入拒绝，债务/卫生语义保留。详见父design第6.1节；assess/发布失败保留诊断，不承诺多文件事务原子性。
- lines保持原五列；本次receipt引用只在既有unit结果JSON的unit_execution schema1中传递，prep失败也写明确终态，run_one在command writer退出后串行附加。candidate_audit显式接预期invocation_id核精确阶段引用/行投影；所有reader/fake-tree/产物登记成组更新，不升级lines或把引用塞tail。
- C3后续使用的接口：lifecycle.classify_result、材料分类证据模式shallow/deep、runner_cleanup.observe_roots调用位。C2只保留调用位和显式`disabled/not-enabled`结果，不读根、不调用适配器、不声称计数；C3交付适配器后切`enabled`并接线，父最终才验实际根一次。当前不放假observe实现/豁免门禁，观察/退役AC未伪报完成。
- local保留归属遵循父design第3.4节：结果树内后代或独立fixture marker；HOME每command_id用唯一新根，不reset抹旧现场，direct harness stage先marker后内容；生产者沿用/验证fixture lease，独立路径先取既有lease，不反锁序。C3可据此单独盘点/确认放弃，无需新增通用资源框架。
- standalone sibling默认是可审计输出而非托管run产物：临时测试log目录由测试fixture回收；candidate_audit保留其显式workdir证据并在本次audit JSON中引用receipt；execution普通CLI日志父目录由调用者管理。任何调用方不得只按隐藏文件名前缀自动清理；重用workdir时新invocation id排除旧receipt，明确存量输出界面。

风险与回退：owner/state/receipt/controller/summary所有reader-writer为一个兼容批次，不能只回退writer；C1公开parser不在回退集合。真正决定回退需先核实际用户diff，只移除本项内容，保留新协议现场，旧脚本另选结果根。不自动提交或删除运行现场。
