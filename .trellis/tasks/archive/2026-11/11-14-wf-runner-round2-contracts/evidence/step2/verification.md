# Step 2 验证记录（2026-11-14 20:12:29）

## 注册表
suites.json → units.json（git mv），schema_version=2，67 条（59 suite + 4 flow + 1 extra + 1 candidate + 2 manual）；每条可计划单元有 expect/fixture/script。expect 由 Step 0 全绿结果机械生成（r64 6→5、r67 15→16、f1_candidate_smoke=17）。

## 子集冒烟
WF_SUITES="r67_tests r64_tests cp1_tests" → rc=0，3 项全绿（cp1 20、r64 5、r67 16）。

## 全量
--full --repro green → rc=0，149 单元 0 失败，86s（模板 2s / suite 292s 累计）。

## T0
873 tests, OK (skipped=10)。

## WF_SLOW_TESTS=1 契约
9 tests OK (97s)，含 candidate 代表集（f1_candidate_smoke expect=17）与 plan.json units 键。

## 负例 1（单元层）
saved 3/3：expected=3 → ok=True；expected=4 → ok=False（reason: observed=3 expected=4）；steps 输出同构（TASK_ID + 2 行，expected=3 红）。

## 负例 2（运行器层，r67 4c）
[PASS] 4c 少一行 PASS → 红且指出期望/实际: exit=1，单元日志含 EXECUTION-FAILED: cp1_tests … expected=20。

## 负例 3（plan 层）
缺 expect / expect=0 / 未知字段 / script 不存在 / 非法 kind / 非法 fixture / manual 缺 notes 全部 PlanError；manual 缺 script 不报错。

## 记录契约
PLAN_UNITS 每条恰五段；f0 记录为 f0:flow:9:install:p5_f0.py（script 来自注册表）；r67 桩文件名取 script。
