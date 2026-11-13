# Implementation and verification plan

## Phase gate

- 用户已批准最终方案并明确要求实施；任务已转 in_progress，Codex inline。
- prd.md、design.md、implement.md 的摘要已获批准；实施授权持续有效；用户已要求收尾，Phase 3.4 一次性批次已获用户确认，执行工作提交、归档及会话记录。
- Codex inline，不使用子代理；不创建无用途的 JSONL 内容。

## Ordered work

1. [x] 固定基线：记录 HEAD、工作区、解释器、实际 unshare/挂载能力、发行来源摘要和完整计划。在实现改动前，r68/r71 各三次定向计时，保留原始记录；将既有 204 秒运行作为历史参考而非本轮实测。
2. [x] 先建立 assertion-map.md：逐条映射 r68/r71 的所有 rec、写入后像和恢复结果；列出不可迁移到函数层的集成义务。
3. [x] R1：先补可变目标→green→auto、helper 改动→子集 both→其他 auto、red-only、旧状态、失败和运行中输入变化回归，观察预期失败；再实现按输入指纹记录两面证据，验证状态提交失败传播。
4. [x] R5：先补 rc/status 矛盾、多缺失/重复、空结果、错误身份/模式与 repro 重复覆盖反例；统一规范化与汇总规则，验证 Python→shell 传输，不保留第二套口径。
5. [x] R3/R4：先以短命令和可清理子孙进程验证超时、取消与日志，再提取共用执行模块，接入 suite/flow/extra/fixture/init/repro。验证负路径断言不被前置失败规则误杀。
6. [x] R2/R6：先用哨兵文件和临时测试目录证明拒绝路径无写入，再实现夹具所有权与共享资源独占；覆盖全部重建入口及模板分支。验证挂载只读实际生效、失败明确、父子调用不死锁。
7. [x] R8：补齐低成本层的等价行为测试并证实能抓住目标缺陷，再迁移报告变体、保留关键集成路径；更新 suites.json、plan.py 选择映射与串行原因。逐条关闭 assertion-map，不允许 unknown 被当作完成。
8. [x] R7：同步 README、wf-delivery-discipline、diagnosis-and-fixture-hygiene 的命令/副作用/计数与实际并发；补 summary 精确计时及回退信息。
9. [x] 最终同范围验证、性能配对、自查 diff、记录结果；收尾按 Phase 3.4 批次确认提交；不推送/开 PR。

## Expected affected files

- full/repro/repro_select.py、_worker.py、run.sh：证据、统一执行和汇总接入。
- full/plan.py、run_all.sh、run_one.sh、results_gate.py：计划兼容、执行与结果契约、实际并发。
- full/wf_fixture.sh、f2_setup.sh、template_check.py 及有关自建夹具调用点：统一生命周期，按实际需要修改。
- full 下新增只用于公共进程执行/夹具生命周期的模块：从现有重复实现提取，不新增通用框架。
- full/r68_tests.py、r71_tests.py、suites.json 及 wf_review 有关测试：按行为映射重组。
- wf_runtime/test_repro_selection.py、test_results_gate.py、test_run_all_contract.py、test_fixture_template.py 及新增针对执行/所有权的测试：先红后绿。
- full/README.md、.trellis/spec/docs/wf-delivery-discipline.md、.trellis/spec/guides/diagnosis-and-fixture-hygiene.md：只同步本次有关规范。

上面 full 指 scripts/tests/wf_runtime/full。若发现超出该边界的产品行为缺陷，先说明并评估，不悄悄修改产品规则。

## Verification sequence

1. 每个缺陷的最小回归先观察红，再实现并观察绿；多进程/目录权限测试使用任务独立临时根。
2. /softwares/python/bin/python3 -B -m unittest discover -s scripts/tests -t .
3. WF_SLOW_TESTS=1 /softwares/python/bin/python3 -B -m unittest scripts.tests.wf_runtime.test_run_all_contract scripts.tests.wf_runtime.test_fixture_template
4. bash -n 检查改动 shell；新增 CLI --help；相关 r67/r68/r70/r71 冒烟；迁移目标的 green/red 注入及旧状态迁移验证。
5. /softwares/python/bin/python3 -B scripts/build-wf-release.py --verify --verify-token-parity（先核实副作用，保留产品树摘要）。
6. 真实 full green 和 full green --serial 依次运行、禁止重叠；比较每一项行为和退出结论，迁移造成的计数变动按 assertion-map 解释。不能用声明并发数代替实际执行分支。
7. candidate 代表闭环使用当前候选版本、已校验带 tag 的独立仓库根；不手改产品发行树，不将重装声称为升级。
8. r68/r71 改后同条件各三次，报告配对中位数、进程调用数/阶段时间和实际并发。合计中位耗时目标下降至少 25%，完整 green 不恶化；不达标继续定位。
9. 项目有关必检：validate-wf-design.py、check-doc-refs.py、validate-skills.sh；如修改超出测试/docs 再选择相关校验。不为未改动的模块重复跑无关重型测试。
10. 产品发行树摘要不变；git diff --check；审阅全部 diff、untracked 与 staged；在本任务内记录实际通过/失败/未运行和限制。

## Completion review

- [x] R1–R8 与 AC1–AC10 全部有证据；无临时探针、假绿豁免或未说明剩余问题。
- [x] 性能改善未依赖跳过原独有断言；旧入口与 candidate 边界仍可用。
- [x] 中断、错误路径和旧状态迁移都有行为验证，日志足够定位而无需重跑。
- [x] 采用 trellis-check 自查；用户已确认提交批次；工作提交后使用原生 finish-work 归档与记录，不推送。
