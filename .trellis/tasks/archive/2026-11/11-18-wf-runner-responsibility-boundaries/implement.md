# 实施顺序与交付验收（审查稿）

以 [PRD 中的 F1–F5、R1–R7 和 A1–A7](prd.md#审查发现与要求) 为准。用户明确批准当前方案后进入 Trellis 实施阶段。实现前读取脚本规范、交付纪律和诊断指南。接手时按 [项目工作流](../../workflow.md) 核对当前实际平台和调度模式。需要分派时先按工作流准备上下文清单。inline 入口由主会话加载上下文。

## 实施顺序

1. **先钉住外部行为。** 读取 full/独立/内嵌 repro、candidate audit、maintenance 的现有负对照。补能暴露 F1–F5 的最小实际入口断言。核对当前 CLI、[持久字段的消费方](design.md#34-持久字段与读者迁移)及测试分母。以业务行为作断言。
2. **改资源权限的源头。** 从两个入口的冻结计划和 `wf_test_paths` 一次派生本次目录与所选资源。把 [目录认领表和历史删除授权](design.md#2-目录认领与历史材料授权)落到现有生命周期与维护入口。执行和显式预览共用新/空目录判定，删除旧代 prepare 和执行中的历史轮转及观察分支。轮转只报告，精确退役复用现有清单、租约、确认和报告。盘点、退役资格与实际删除用同一份授权事实。把既有测试发行构建和校验接到本次工作区及显式 `--no-build`，接通跨次模板明示启用。同步锁、namespace、pycache 和本次路径的回收。覆盖 A1、A2。
3. **统一收尾使用的事实与提交。** 在 controller 汇总监督、单元结果、候选核验、取消和回收事实。候选终核失败、未执行或异常时仍走同一清理出口。两个 repro 入口和 writer 共用相位判定。按迁移表同批调整写入者、运行时读者、测试及文档，核对旧 schema 读兼容。删除旧的成功位和发布分支，消费端用同一提交点。覆盖 A3、A4、A6。
4. **核对实际候选来源及覆盖。** 在做完计划选择后用同一注册资格处理全部 kind，检查代表闭环仍可达。对齐 audit/source coverage。审阅 R72 在 dev/candidate 的真实入口。将 R67 假树断言迁到现有契约入口，逐条核对产品和运行器断言仍可执行。先跑真实候选取证，再更新 audit 和 coverage 基线。覆盖 A5。
5. **固化边界并清理已替代接口。** 在已有 `wf-delivery-discipline.md` 写入可观察的默认写范围、显式维护、候选资格和唯一结论。更新两个 runner README 及实际变更参数的帮助，记录旧数据、固定目录和共享缓存的使用迁移。检查旧分支、测试自带桩、环境变量、错误提示、调用方和历史数据读取。按 A7 核对契约及改动范围。

## 验证矩阵

| 验收 | 实际入口与反例 | 证据要求 |
| --- | --- | --- |
| A1、A2（F1） | 对真实执行及显式计划镜像走完目录认领表。准备历史树，加入 `*.json/`、手工 `logs/` 或替换同名 `summary.json`。另覆盖 PID 复用、租约竞争、旧 selection、TTY 确认前后增改和合规退役。 | 比对历史根的条目、字节和权限。拒绝目录认领时仅需要换路径。轮转只报告。退役显示所有删除项，同名手工材料在未经确认或内容变化时保持原样。合法删除后报告精确。跨次模板冷/热和 `--no-build` 新鲜/陈旧另有对照。 |
| A3（F2） | 用确定性同步点验证真实候选取消，分别在 worker 运行与终核运行时请求取消。另走终核实际拒绝路径。dev 正常与候选成功为对照。 | 查看退出码、同代记录、进程和夹具残留、下一次租约可重取。资源没有有效清理证明时保留。检查本次发行与 sidecar 的回收，以及持有共享发行期间的互斥。 |
| A4（F3） | 独立/内嵌 repro 覆盖缺整条结果、坏记录、错代、未回收和正常的目标断言失败。显式 dev red/both 后 candidate auto，改变摘要后重跑。 | 逐相位校验守恒。坏 case 只影响对应事实。默认路径保持共享状态不变。新鲜 proof 可消费，失效 proof 不进入 auto。既有可独立保存的合格 case 语义受测。 |
| A5（F4） | 候选子集、代表集、全量、audit 与 source coverage。R72 真正的卸载闭环和 R67 的迁移前后断言表。 | 按 ID 核对计划、实际来源、排除原因、结果和分母。代表集实跑。候选全量核对实际执行与安装身份。 |
| A6（F5） | 实际入口注入控制记录、生命周期与 summary 写失败。覆盖取消、失败、成功与重试。按迁移表回查字段读者，覆盖旧代三文件及事实不一致的历史记录。 | 非零时无本代正式成功证据。控制记录所见的目标状态、收尾和整次取消各自可定位。`finished+cleaned` 且缺新版摘要时不能判为成功。旧文件可读、字节不变，旧成功不冒充新版提交。 |
| A7 | 仓库单元层、运行器慢契约、定向并行与串行、dev 全量、独立 repro 和候选发行入口。 | 回看所有修改、生成证据与新增文件。按单元 ID、退出和断言对拍，快慢不纳入判定。 |

## 实施阶段验证命令

使用独立 owned scope 保存每次运行的结果和夹具，显式测试候选与共享缓存也落在准备好的 scope。保持宿主解释器确认、Git 身份和产品树只读要求。默认路径与显式缓存测试使用不同目录。以下是批准后执行的主要入口。

```bash
PYTHONPYCACHEPREFIX=/tmp/wf-runner-boundaries-unit-pycache /softwares/python/bin/python3 -m unittest discover -s scripts/tests -t .
PYTHONPYCACHEPREFIX=/tmp/wf-runner-boundaries-unit-pycache WF_SLOW_TESTS=1 /softwares/python/bin/python3 -m unittest scripts.tests.wf_runtime.test_run_all_contract
WF_SUITES="r67_tests r70_tests r72_tests" bash scripts/tests/wf_runtime/full/run_all.sh --repro none
WF_SUITES="r67_tests r70_tests r72_tests" bash scripts/tests/wf_runtime/full/run_all.sh --serial --repro none
bash scripts/tests/wf_runtime/full/run_all.sh --full --repro green
bash scripts/tests/wf_runtime/full/run_all.sh --full --repro both
bash scripts/tests/wf_runtime/full/repro/run.sh --group install --mode green
/softwares/python/bin/python3 -B scripts/tests/wf_runtime/full/source_coverage.py --format json
/softwares/python/bin/python3 -B scripts/build-wf-release.py --verify --verify-token-parity
git diff --check
```

在 scope 内用 `prepare_candidate_repo.py` 按受控输入树的实际版本准备候选。将其真实根、版本和 ref 分别交给 `--representative --repro green --repro-group install --fixture-deploy candidate` 与 `--full --repro none --fixture-deploy candidate`。如需刷新审计，先用 `candidate_audit.py --candidate-root … --workdir … --out …` 输到 scope，再审阅差集与真实安装来源。覆盖基线用 `source_coverage.py --baseline-out` 产出待审核版本。正式文档改动运行对应文档校验并记录既存失败。

## 交付与异常处理

- 各条交付证据按 PRD 的 F1–F5 → R → A 映射回填，逐项核销。若真实候选、隔离 scope 或信号注入不能运行，保留可复算事实并明确对应的未验证条目。已知缺陷不能被新基线、降级条件或跳过分支掩盖。
- 高风险面包括目录认领与历史删除授权、持久字段消费方迁移和历史读兼容、租约/挂载、候选覆盖与发布顺序。逐项审查实际调用方和旧材料。在实施期同批修复已发现且属于这些契约的回归。需要改变用户审定的默认行为或公开兼容性时，更新方案后重新审查。
- 回退以单一职责的改动为单位保留用户工作和每次结果。历史缓存和运行记录便于复核并保持原样。分支、提交和发布仍需用户明确授权。
