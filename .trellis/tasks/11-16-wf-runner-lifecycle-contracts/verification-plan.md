# 共享验证命令与隔离前置

> 以下为实施期计划；实施已在 DSH inline 执行，结果见 [validation.md](./validation.md)，不把计划本身记为pass。各子implement只选择本项命令；父最终集成对组合内容运行，不能要求C1/C2验证未实现的C3功能。

## 1. 所有写测试的隔离前置

- cwd保持仓库根，解释器/脚本按项目指定。以下代码在**仓库根的新Bash子会话**使用；先读完并获准实施；本轮实施已按此隔离执行。
- 每个真实root调用显式隔离results/cache/state/pycache/release/candidate/fixture；HOME与TMPDIR保留宿主语义（结果根校验以宿主临时区为边界），repro相位TMPDIR由execution在结果树内派生并回收。root/慢契约串行，失败先诊断，不盲重试。
- 普通无scope库/CLI兼容测试仍由测试自有TemporaryDirectory隔离，不全局export scope；故障注入用例在自身fixture另建有效scope。不得把能力不足/未运行记pass。

下段本身执行marker验证和逐调用环境净化，而非仅在文字要求。wf_clean只枚举变量名用于移除WF_*及已知runner/启动定位，不输出变量值；显式调用参数中的env赋值在净化后生效，故障/选择器仅由具体用例主动添加。每次调用重新取名称列表，不能初始化时快照后漏掉新继承的locator。

~~~bash
wf_clean() {
  local name
  local -a clean=(env)
  while IFS= read -r name; do
    case "$name" in
      WF_*|FIX|HERE|PY|RESULTS_DIR|SHARED_RELEASE|PLAN_FILE|PLAN_SHA256|PLAN_SIZE|PYTHONPATH|PYTHONHOME|PYTHONPYCACHEPREFIX|TMPDIR|BASH_ENV|ENV)
        clean+=(-u "$name") ;;
    esac
  done < <(compgen -e)
  "${clean[@]}" "$@"
}
SCOPE=$(wf_clean env TMPDIR=/tmp PYTHONDONTWRITEBYTECODE=1 /softwares/python/bin/python3 -B scripts/tests/wf_runtime/full/fixture_scope.py create-scope) || exit "$?"
UNIT_PYCACHE="$SCOPE/unit-pycache"
wf_clean env WF_TEST_SCOPE_ROOT="$SCOPE" PYTHONDONTWRITEBYTECODE=1 /softwares/python/bin/python3 -B scripts/tests/wf_runtime/full/fixture_scope.py check-scope "$SCOPE" "$UNIT_PYCACHE" || exit "$?"
scoped_run() {
  [ "$#" -ge 2 ] || return 2
  local label=$1
  shift
  [[ "$label" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || return 2
  wf_clean env WF_TEST_SCOPE_ROOT="$SCOPE" PYTHONDONTWRITEBYTECODE=1 /softwares/python/bin/python3 -B scripts/tests/wf_runtime/full/fixture_scope.py check-scope \
    "$SCOPE" "$SCOPE/results/$label" "$SCOPE/fixtures/$label" "$SCOPE/cache" \
    "$SCOPE/state" "$SCOPE/test-release" "$SCOPE/pycache/$label" "$SCOPE/tmp/$label" "$UNIT_PYCACHE" || return "$?"
  mkdir -p "$SCOPE/tmp/$label" || return "$?"
  # 不覆盖根命令的 TMPDIR：fixture_scope.validate 只接受宿主临时区（或 ~/.cache）之下的
  # 结果/夹具根；把 TMPDIR 指进 scope 会让所有 root 命令在首次写前被正确拒绝。
  # 相位 TMPDIR（repro worker）由 execution 按 command_id 建在各自结果树内并负责回收。
  wf_clean env WF_TEST_SCOPE_ROOT="$SCOPE" \
    WF_RESULTS_DIR="$SCOPE/results/$label" WF_FIX="$SCOPE/fixtures/$label" \
    WF_RESULTS_CACHE="$SCOPE/cache" WF_TEST_RUN_CACHE="$SCOPE/state" \
    WF_TEST_RELEASE_CACHE="$SCOPE/test-release" WF_PYCACHE="$SCOPE/pycache/$label" \
    PYTHONPYCACHEPREFIX="$UNIT_PYCACHE" "$@"
}
~~~

scope创建非零、marker不匹配、路径检查失败立即停，不运行后续验证；check-scope通过WF_TEST_SCOPE_ROOT触发既有marker读取，不能仅把scope当普通路径传入而未设active scope。故障用例显式赋值只加在scoped_run之后的env参数中，普通命令不继承父会话故障。T0/定向/慢契约命令也走wf_clean，继承HOME/Git等宿主语义，但剥离外来runner定位。

实施时把wf_clean/scoped_run行为加入test_run_all_contract的同层定向检查：污染WF locator/fault的环境启动假child，只验证净化结果、scope marker及显式参数覆盖，不运行真实suite；父marker坏/label含路径跳转必须在child前拒绝。规划阶段只核片段语法/结构，不执行它。

最后核本scope owned进程/FD/锁，正常资源可回收才清scope；故障探针只回收自建PID/启动身份，未知现场保留，必要小证据记任务validation，不按名称通配kill/删。

## 2. 按责任选择的验证命令

V-T0：各子项完成后与父最终组合。已包含runtime/review，不为凑数重复跑子目录。

~~~bash
wf_clean env PYTHONPYCACHEPREFIX="$UNIT_PYCACHE" /softwares/python/bin/python3 -B -m unittest discover -s scripts/tests -t .
~~~

V-C1：公开parser、原有repro兼容和新增同层test_repro*.py；不涉及C2/C3未来断言。

~~~bash
bash -n scripts/tests/wf_runtime/full/repro/run.sh
wf_clean env PYTHONPYCACHEPREFIX="$UNIT_PYCACHE" /softwares/python/bin/python3 -B -m unittest discover -s scripts/tests/wf_runtime -t . -p 'test_repro*.py'
~~~

V-C2：命令证据/初始化/信号/清理/摘要定向。包含有scope/无scope（普通TemporaryDirectory和用户输出锚点）正常与拒绝、库异常/缺失父链；lines严格五列与unit JSON阶段引用/prep失败/旧invocation；root started不误报与最终root缺失拒绝；metrics本代ID/输入摘要/缺坏半写及正常复用、债务/卫生对照。新模块测试由V-T0发现，不用不存在的测试名当证据。

同组新增初始化helper os._exit(97)的首次/计划转执行/重用×三点及public整体退出/锁副本释放；finalize的首删前故障与delete-after-first真实部分完成（至少两资源）、单根rmtree内部部分失败；并核第1节片段的marker前置和逐调用环境净化。

慢契约teardown新增定向：注入class-cost写入OSError，要求非零且明确evidence failure；先完成leftover进程/FD与宿主保护断言，再决定scope是否保留。注入/构造leftover或host变化时也必须保留scope并先报告，不能先rmtree再断言，失败证据不以空报告替代。

~~~bash
bash -n scripts/tests/wf_runtime/full/run_all.sh scripts/tests/wf_runtime/full/run_one.sh scripts/tests/wf_runtime/full/repro/run.sh
wf_clean env PYTHONPYCACHEPREFIX="$UNIT_PYCACHE" /softwares/python/bin/python3 -B -m unittest scripts.tests.wf_runtime.test_execution scripts.tests.wf_runtime.test_supervision scripts.tests.wf_runtime.test_runner_cleanup scripts.tests.wf_runtime.test_results_gate scripts.tests.wf_runtime.test_results_summary scripts.tests.wf_runtime.test_runner_protocol scripts.tests.wf_runtime.test_fixture_scope scripts.tests.wf_runtime.test_evidence_protocol scripts.tests.wf_runtime.test_candidate_audit
~~~

V-C3：恢复与维护定向；含模板已有marker与新发行material-owner的O1/marker-only壳/碰撞拒绝/旧有效journal兼容、坏journal完整key reset后同key真重建、历史unproven额外确认、部分失败journal最后保留、sibling不动。PTY/选择/拒绝矩阵加同层测试并由V-T0发现；不得实际处置用户cache。

~~~bash
wf_clean env PYTHONPYCACHEPREFIX="$UNIT_PYCACHE" /softwares/python/bin/python3 -B -m unittest scripts.tests.wf_runtime.test_template_cache scripts.tests.wf_runtime.test_test_release scripts.tests.wf_runtime.test_release_lock scripts.tests.wf_runtime.test_fixture_scope scripts.tests.wf_runtime.test_repro_selection scripts.tests.wf_runtime.test_source_coverage
~~~

V-CONTRACT：C2只执行该时点已有完整契约类与新增C2用例；C2真实root预期observe=0且报告disabled/not-enabled；C3新增W1–W5/O1/F1/retirement/observe后才由C3和父验证，enabled时按实际配置根各一次、计划/per-case/内嵌为0。不存在的future用例标未实现，不据此跳过整类。

C2新增真实root用例须按design第5.2节覆盖metrics write/missing/truncated/old-run/input-mismatch固定故障及正常对照，确认run_id/输入证据与无成功/原rc；无开关相同变量不生效。故障spec不借任意文件路径，不污染unit/repro。无scope兼容是定向库/CLI的测试域：测试拥有TemporaryDirectory并负责回收，不给它伪装WF_TEST_SCOPE_ROOT；下面root命令仍全部显式scope隔离。

~~~bash
wf_clean env WF_SLOW_TESTS=1 PYTHONPYCACHEPREFIX="$UNIT_PYCACHE" /softwares/python/bin/python3 -B -m unittest scripts.tests.wf_runtime.test_run_all_contract
scoped_run smoke env WF_SUITES="r67_tests r70_tests" bash scripts/tests/wf_runtime/full/run_all.sh
~~~

V-FULL：父最终组合必过；C2/C3只有在受影响接口/未决风险需要时跑定向subset，不能以子项未跑full宣称父完成。每次label确保独立结果目录。

~~~bash
scoped_run full-green bash scripts/tests/wf_runtime/full/run_all.sh --full --repro green
scoped_run full-serial bash scripts/tests/wf_runtime/full/run_all.sh --full --repro green --serial
scoped_run full-both bash scripts/tests/wf_runtime/full/run_all.sh --full --repro both
~~~

逐ID比较lines的name/rc/status、repro的case/mode/green/red/verified及各run_id下receipt/state/summary；运行期ID可变化，归属必须自洽，非只比数量/耗时。

V-CANDIDATE：manifest实际版本唯一，候选输出在SCOPE；保持现有candidate-clean过滤，不为通过改声明。

~~~bash
VERSION=$(wf_clean /softwares/python/bin/python3 -B -c 'import json; print(json.load(open("docs/workflows/wf-release/wf-release.json"))["version"])')
wf_clean env WF_TEST_SCOPE_ROOT="$SCOPE" PYTHONPYCACHEPREFIX="$UNIT_PYCACHE" /softwares/python/bin/python3 -B scripts/tests/wf_runtime/full/prepare_candidate_repo.py --tree docs/workflows/wf-release --version "$VERSION" --out "$SCOPE/candidate"
scoped_run candidate bash scripts/tests/wf_runtime/full/run_all.sh --full --repro green --fixture-deploy candidate --release-root "$SCOPE/candidate" --release-ref "refs/tags/wf-v$VERSION" --release-version "$VERSION"
~~~

suite字节改变时，按现有candidate_audit CLI在自建workdir重生成相应审计并核差异，不手填通过；只改helper不自动重跑所有suite审计，按实际依赖判定。

## 3. 发行、文档与资产检查

V-RELEASE：只在临时区重建对拍正式树和token parity；若失败先查diff/来源，禁止用 --version 重建掩盖。执行前将TMPDIR指向scope内新建目录，确保所有写入面可回收；不要全局污染其他测试。

~~~bash
mkdir -p "$SCOPE/verify-tmp"
wf_clean env TMPDIR="$SCOPE/verify-tmp" PYTHONPYCACHEPREFIX="$UNIT_PYCACHE" /softwares/python/bin/python3 -B scripts/build-wf-release.py --verify --verify-token-parity
~~~

V-DOC：子项改工件后跑第一条并加上实际改动的README/spec路径；父最终还要默认文档与其余项目要求命令。

~~~bash
wf_clean env PYTHONDONTWRITEBYTECODE=1 /softwares/python/bin/python3 -B scripts/check-doc-refs.py .trellis/tasks/11-16-wf-runner-lifecycle-contracts/*.md .trellis/tasks/11-17-wf-runner-cli-contracts/*.md .trellis/tasks/11-17-wf-runner-controller-lifecycle/*.md .trellis/tasks/11-17-wf-runner-cache-maintenance/*.md
wf_clean env PYTHONDONTWRITEBYTECODE=1 /softwares/python/bin/python3 -B scripts/check-doc-refs.py
wf_clean env PYTHONDONTWRITEBYTECODE=1 /softwares/python/bin/python3 -B scripts/validate-wf-design.py
wf_clean ./scripts/validate-skills.sh
wf_clean env PYTHONDONTWRITEBYTECODE=1 /softwares/python/bin/python3 -B trellis-library/cli.py validate --strict-warnings
~~~

文档引用脚本不核Markdown链接/章节语义/AC闭合，故仍需机械核父子三件套、所有文件链接与本文V编号、producer/consumer/终止出口及Git diff/untracked/staged。最后一次修改后重跑受影响检查，不擅自提交/归档。
