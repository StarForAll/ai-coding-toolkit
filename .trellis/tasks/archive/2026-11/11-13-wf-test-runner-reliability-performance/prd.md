# wf 测试运行器可靠性与耗时优化

## Goal

缩短 wf 测试的真实执行时间，同时保证测试证据有效、夹具操作有边界、失败可定位、执行可终止。用户要求按此前分析实际修正，避免逐点打补丁、引入新问题或留下未处理的关联路径。

## Background

- 起点：main，HEAD 1c58bce1，任务创建前工作区干净；用户已授权创建任务和进入规划。
- 既有同机记录：149 单元并发运行 204/210/212 秒；套件串行、repro 并发 4 为 301 秒。来源：~/.cache/wf-test-run/run-1964465/summary.json、run-1893353/summary.json、run-1792648/summary.json、run-2034392/summary.json。此处为最初历史基线；本任务实测与最终结果见 validation.md。
- 204 秒记录中，r68_tests/r71_tests 测试体合计约 50 秒；13 个强制串行套件合计约 109 秒；模板 3 秒、夹具准备累计 7 秒。累计时间与墙钟分开解释。
- 下列问题及证据分别归属 R1–R7；此前内存模拟已复现 R1 的两个序列和 R5 的退出码矛盾输入，实际修正仍需先补持久化回归测试并观察失败。

## Requirements

| ID | 要求与问题级别 | 当前证据 | 对应验收 |
|---|---|---|---|
| R1 | P1：green 与 both 的证据独立绑定完整输入，目标/helper/用例变化后不得继承旧 red 证据；处理旧状态 | scripts/tests/wf_runtime/full/repro/repro_select.py:213、238：green 更新新摘要并刷新旧 verified_both_at；全局 helper 摘要可掩盖未复验用例 | AC1 |
| R2 | P1：删除、复制、重建夹具前统一校验路径和所有权；重叠执行受控；拒绝未归属目录，不静默接管旧夹具 | full/wf_fixture.sh:47、full/run_all.sh:198、full/run_one.sh:21、full/f2_setup.sh:4 | AC2 |
| R3 | P1：suite、flow、extra、初始化与 repro 共用进程执行机制；超时/中断结束进程组并形成失败记录，交互读取也有执行上界 | full/run_all.sh:359、429；full/r68_tests.py:57；repro/_worker.py:34 已有局部超时 | AC3 |
| R4 | P2：所有执行阶段保存 stdout/stderr、阶段与退出原因，失败无需为获取原文重跑 | full/run_all.sh:413、439、455：flow 输出未写入 log，F0 安装输出丢弃 | AC4 |
| R5 | P2：结果层独立核验计划、身份、模式、退出码、状态和数量；拒绝缺失/重复/畸形/矛盾结果，不吞状态提交错误 | full/results_gate.py:32；repro/run.sh:181–206 | AC5 |
| R6 | P2：共享发行输入落实只读、校验挂载成败；不得允许 worker 改动共享发行源或模板 | full/run_one.sh:9–12：普通 bind，失败被忽略 | AC6 |
| R7 | 消除与本次行为有关的 README、交付纪律和夹具指引漂移；报告实际并发、回退原因和精确阶段时间 | full/README.md:99–100；full/run_all.sh:356、552；.trellis/spec/guides/diagnosis-and-fixture-hygiene.md:105 | AC7 |
| R8 | 将 r68/r71 的报告字段变体移到最小可验证层，保留关键 CLI、写入拒绝、锁内重核、交接与恢复路径；拆分确有隔离需求的串行场景 | full/r68_tests.py:91、142、200–318；full/r71_tests.py:187、263–365 | AC8–AC9 |

以上相对路径中的 full 为 scripts/tests/wf_runtime/full，repro 为该目录的 repro 子目录。

## Acceptance Criteria

- [x] AC1：变化后先跑 green，再跑 auto，仍要求 both；helper 变化后只复验 A，B 仍要求 both；red 单独成功可记录当前输入的 red 证据；失败、缺目标和旧状态不会生成可信 both 证据。
- [x] AC2：项目根/祖先、home、根目录、符号链接、非空无主目录、与结果/模板/发行重叠的路径都在写入前拒绝；哨兵文件保持不变；首次创建、同所有者重建与不同运行竞争均有行为测试。
- [x] AC3：正常、非零退出、超时、阻塞读取和父进程中断均可结束；子孙进程不残留；超时计失败，后续结果可完整汇总。
- [x] AC4：suite/flow/F0/extra/fixture/init/repro 都有完整日志与可定位结果；控制台给出失败阶段和路径。
- [x] AC5：rc 非零而 status=ok、错误模式/身份、缺失/重复/畸形/计划外记录、零断言成功、状态提交失败均不能被当作成功；shell 与 Python 之间的结果传递有契约测试。
- [x] AC6：worker 实际不能改共享发行源；挂载或只读设置失败时明确失败/按已有计划退回可验证路径，不继续使用未隔离输入；测试发行与产品发行树前后摘要一致。
- [x] AC7：summary 分开记录 requested/effective jobs、执行分支和回退原因；时间采用单调时钟；文档仅使用实际支持的选项，副作用如实描述。
- [x] AC8：迁移前后逐条对照 r68/r71 原断言，给出稳定行为 ID、旧位置、新位置、测试层及是否保留集成；无 unknown 或丢失的独有断言；关键断言做定向缺陷注入，前置失败不算证伪成功。
- [x] AC9：同机同来源同模式下，r68/r71 各至少三次配对测量，中位耗时实质下降；定向目标为合计中位耗时至少下降 25%，未达到就继续定位，不以删覆盖或改计数达标。全量 green 墙钟不恶化，记录环境差异与噪声。绝对秒数不预先承诺。
- [x] AC10：完整单元层、运行器契约、相关 green/red、candidate 代表闭环、full green 及并行/串行语义对拍通过；完成项目要求的有关校验，审阅全部 diff/untracked/staged，并报告实际观察结果。

## Constraints and Out of Scope

- 保留现有 shell 命令入口、full/subset/representative、tag/changed 建议、dev/candidate、green/red/both/auto 和必要环境变量；不改变 wf 产品的判断规则。
- 对旧缓存的安全失效、无所有权的旧夹具拒绝重建属于本次必要的兼容收紧，必须给出可操作错误；不自动删除用户旧目录。
- 不换测试框架，不引入常驻进程，不缓存动态 writer/session/task 状态，不以减少覆盖换取提速。
- 不手改 docs/workflows/wf-release，不修改只读 Trellis 上游，不做无关清理；实现交付时不自行提交；用户随后要求收尾，按 Phase 3.4 批次确认后提交与归档，不推送或开 PR。
- 单任务交付：证据、执行、隔离和计量共同构成运行器契约，慢套件迁移依赖这些基础，因此在同一任务中按顺序验收。
