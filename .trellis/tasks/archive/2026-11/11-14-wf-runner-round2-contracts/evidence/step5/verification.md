# Step 5 验证记录（2026-11-14 20:5x）

## 新增闸门测试

- `test_runner_hygiene.py`（10 项中的 9 项）：
  - G1：`scripts/tests/**/*.py` 中 `/tmp` 导入注入零命中（needle 以拼接构造，测试自身不含字面量）。
  - G2：run_all.sh 含 `PYTHONPYCACHEPREFIX`；run_all/run_one/repro 均不再 `export PYTHONDONTWRITEBYTECODE`。
  - G3：仓库 `.gitignore` 含 `__pycache__/` 与 `*.pyc`。
  - G8：按写死口径解析 run_all.sh 静态 `"$HERE/<路径>"` 引用，全部 ∈ COPY∪STUB∪SPECIAL∪注册表 script；
    三桶条目真实存在；STUB 与 COPY/SPECIAL 互斥。
  - G9：缺失根 snapshot/check 退出 0 且输出 `HYGIENE-ABSENT`；strict 模式对缺失根同构。
- `test_runner_budgets.py`：`wf.py status`（pyc 预热）5 次中位数 **68ms** < 500ms
  （样本 69/66/68/73/67ms；`WF_PERF_GUARD=0` 可关且原因写在断言消息里）。
- 闸门落点索引（实现位置，不是另加机制）：
  G1/G2/G3/G8/G9 → 本步两个测试；G4 → `plan.load_units`；G6 → summary `budget`；G7 → run_all 的 source_hygiene 前后对拍。

## 文档同步

- `scripts/tests/wf_runtime/full/README.md`：并行与子集（units.json/五段记录/WF_TOTAL_JOBS/串行域）、
  结果缓存轮转（模板跨 run 缓存 key/发布/命中/开关 + pyc 策略）、性能（90.3/88.8→49.9/49.7s）、
  解释器契约（手工 T0 也要带 pycache 前缀）。
- `.trellis/spec/docs/wf-delivery-discipline.md`：§7（units.json、PLAN_ISOLATED_UNITS/WF_ISOLATED_UNITS、
  注册表与记录契约、模板缓存四条不变量、pyc 策略）、§8（T0 命令加前缀）、§12（fixture_scope move、
  summary schema 2 分段与计数不变式、新增两个闸门测试）。

## 验证命令

- T0：`PYTHONPYCACHEPREFIX=/tmp/wf-unit-pycache python3 -m unittest discover -s scripts/tests -t .`
  → 883 tests OK（skipped=10，7.8s）。
- `python3 scripts/validate-wf-design.py` → rc=0（629 引用 / 92+14 场景 / 七项检查通过）。
- `python3 scripts/check-doc-refs.py` → 0 problem(s)。
- `./scripts/validate-skills.sh` → 25 skills OK。
- full `--repro green` → rc=0（54s，缓存重建后首跑）；representative → 26s；r67 → 17/17。
