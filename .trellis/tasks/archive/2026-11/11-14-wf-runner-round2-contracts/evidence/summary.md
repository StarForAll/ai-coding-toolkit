# 收口证据索引（11-14-wf-runner-round2-contracts）

基线（同机重测，2026-11-14 19:54–20:02）：full 并行 90.32s / 88.75s；full 串行 267.38s；
单套件 cp2 11.51s（模板 3s + 套件 8s）；r67 8.06s。设计稿的 92.9/94.5s 与本机重测差 −2.8%/−6.1%，
同机同口径、量级一致；本任务验收以重测基线为准。

## AC1 提速（验收证据，不是运行期门禁）

| 指标 | 基线 | 收口实测 | 结论 |
|---|---|---|---|
| full 并行（两次采样） | 90.32s / 88.75s | **50.81s / 44.82s** | 硬性 ≤65s ✓；目标 ≤60s ✓（−44% / −50%） |
| full 串行（对拍） | 267.38s | 268.33s | 行为等价（见下） |
| representative | 48.1s | **26.16s** | — |
| 单套件 cp2 | 11.51s（首跑）/ 6.11s（命中） | — | 目标 ≤7s ✓ |
| `--repro-concurrent` 抽样（非默认） | — | 46.76s | 与默认路径对拍一致 |

- 计数三分量（唯一写法，两次采样一致）：`lines`=64 == suite_ran 59 + flow_ran 5；
  `units_total`=149 == 59+5+85；`repro_ran`=85 == REPRO_TOTAL（不与行数比较）。
- 串并等价：`lines` 64 行（name/rc/status）与 `repro/*.json` 85 项（mode/green/red/verified）逐项相等，
  summary 的 suite_ran/flow_ran/repro_ran/units_total/fail 相等（`evidence/final` 下可直接用脚本复核）。
- 收益归因：字节码缓存（每单元 −35%）、模板跨 run 缓存（单套件 2.73s 固定构建 → 0s，full 首跑 2s）、
  flows/extra 入池（3 个 p5 flow 13.89s 串行 → 池内并发）；不含 repro 并发（决策 #3，默认仍串行）。
- 44.82s 的构成：pool 26s + repro 17s + startup 1s（summary 分段）。**没有 60–65s 区间**，无需差距归因。

## AC2 证据预算

- 注册表 `units.json`（schema 2）：67 条（含 4 flow/1 extra/1 candidate/2 manual），59+5+1 可计划单元全部有 `expect`。
- plan 层负例：缺 expect / expect=0（含 bool）/ 未知字段 / script 不存在 / 非法 kind / 非法 fixture /
  manual 缺 notes → 全部 PlanError；manual 缺 script 不报错（`evidence/step2`）。
- 单元层负例：`saved 3/3` 下 expected=4 → `ok=False`（observed=3）；steps 输出同构。
- 运行器层负例：r67 4c（桩少一行 `[PASS]`，汇总同步为 expect-1）→ `EXECUTION-FAILED: cp1_tests … expected=20`，整次非零。
- 串行段完整性：r67 4d（cp1 标 `parallel:false` + 串行域桩不写行）→ `MISSING-RESULTS:cp1_tests`。
- 记录契约：`PLAN_UNITS` 每条恰五段、`script` 与注册表一致、`f0:flow:9:install:p5_f0.py`；
  r67 桩文件名取自 `script`。断言在 `test_test_runner_plan.py`。

## AC3 卫生

- `sys.path.insert(0, "/tmp")` 全库 0 命中；仓库 `.gitignore` 覆盖 `__pycache__/` 与 `*.pyc`（`git check-ignore` 命中仓库文件）。
- `fallback_representative` 零引用（注册表迁移时删除）。
- P3-1 自证用例已移除；替代实现 `source_hygiene.py` 有两次证伪：
  ① Step 1 植入 `payload/.../__pycache__/x.pyc` → check 退出 1 并列出路径（`evidence/step1`）；
  ② Step 3 去掉缓存策略跑 full → `SOURCE-TREE-POLLUTED`（18 个新增路径）且非零（`evidence/step3`）。
- 绝对判据：`find docs/workflows/wf scripts/tests \( -name '*.pyc' -o -name '__pycache__' \)` = **0**
  （收口时复核；运行期仍只对新增失败，存量给警告 + 清理命令）。

## AC4 不回归

- full 149 单元 0 失败；r67 17/17；`WF_SLOW_TESTS=1` 契约 9 tests OK（47.6s）；T0 883 tests OK。
- `KNOWN_LEGACY` 仍为空（`legacy_debt=0`，不是“有债但没报”）。
- 8 并发最慢单元 r17r24_tests 20.73s（WF_COMMAND_TIMEOUT=180s，≈8.7× 余量）；
  repro 最慢用例 bind-resume-under-lock 6.75s（WF_REPRO_TIMEOUT=120s，≈17.8× 余量）。
- 串行域实证：并行 cp1 运行后宿主 `/tmp` 新增 `cp1_*` 产物 0 个；串行运行后新增 23 个（宿主 /tmp、无 unshare）。
- f0 迁入 worker：representative 与 full 均绿，`lines` 中 `f0 … saved 9`（安装 + 自举在私有 tmpfs 内完成）。

## AC5 缓存正确性

- 七条实证全部演示（`evidence/step3`）：① 内容变更 → 新 key 重建；只 touch → 仍命中
  ② 解释器 3.14 vs 3.13 → 不同 key ③ candidate version/ref → 不同 key ④ 缺 meta → 重建
  ⑤ 整份 template 搬到另一 cache 根 → `TEMPLATE-CACHE-MOVED` → 重建 ⑥ 记录与 meta.root 不一致 →
  克隆改写 0 → `TEMPLATE-REPOINT-MISMATCH`（单元 5 列 bad 行）⑦ 条目塞 pyc → strict 判脏 → 重建。
- pyc “改源码立即生效”：修改夹具 `.wf/lib/wflib/cli.py` 后下一次 `wf.py status` 立即抛新错误；复原后恢复 WF_OK。

## AC6 无遗留

- 文档同步：`full/README.md` 四段、`wf-delivery-discipline.md` §7/§8/§12。
- summary schema_version=2；注册表 schema_version=2。
- “不做清单”原样保留在 `prd.md`（产品面 probe_version/lazy import、57 套件 helper 收敛、覆盖率工具化、
  常驻 SUT、统一解释器、d1 手动套件）。
- 设计修订记录（实施中发现的缺口，未回写 design.md，以此为准）：
  **模板缓存 key 必须包含 dev 的 git 身份**（`dev:<git describe>`）。只按 payload 内容摘要复用会让
  “payload 未变但提交变了”的夹具被复用，r90/p5_v1 的“追加平台”用例按安装记录里的
  `source_commit/release_ref` 判同源，实测因此变红；加入 dev 身份后转绿。candidate 侧仍按
  `<version>-<ref>` 进入同一段 key。
